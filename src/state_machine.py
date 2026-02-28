"""
GrabState 状態機械

純粋な状態遷移ロジックのみを保持する。
副作用（刺激送信・Chatbox・記録・GUI更新）は一切持たず、
イベントコールバックを通じてハンドラに通知する。

GUI 互換のため以下の公開属性を持つ（state machine が内部で使うわけではない）：
  - zap_recorder : tab_stats.py からアクセス
  - last_zap_display_intensity : StimulusHandler が設定し、GUIUpdater が読む
  - last_zap_actual_intensity  : 同上
"""

import time
import logging
from collections import deque
from typing import Callable

logger = logging.getLogger(__name__)

Event = Callable[..., None]


class GrabStateMachine:
    """PhysBone の Grab / Stretch 状態を管理する状態機械。"""

    def __init__(self):
        # --- 純粋な状態 ---
        self.is_grabbed: bool = False
        self.current_stretch: float = 0.0
        self.grab_start_time: float | None = None
        self.stretch_above_threshold: bool = False

        # --- Stretch 履歴（速度計算用） ---
        self._stretch_history: deque[tuple[float, float]] = deque(maxlen=50)

        # --- テストモードフラグ（tab_test.py から外部設定） ---
        self.is_test_mode: bool = False

        # --- GUI 表示用データ（StimulusHandler が更新、GUIUpdater が読む） ---
        self.last_zap_display_intensity: int = 0
        self.last_zap_actual_intensity: int = 0

        # --- GUI サービス参照（tab_stats.py から読まれる） ---
        self.zap_recorder = None

        # --- イベントコールバックリスト ---
        self._on_grab_start: list[Event] = []
        self._on_grab_end: list[Event] = []          # (stretch: float, duration: float)
        self._on_stretch_update: list[Event] = []    # (stretch: float)  ← grabbed 中のみ
        self._on_threshold_crossed: list[Event] = [] # (stretch: float)
        self._on_threshold_cleared: list[Event] = [] # (stretch: float)
        self._on_state_change: list[Event] = []      # ()  どんな状態変化でも発火

    # ------------------------------------------------------------------ #
    # Subscribe メソッド                                                   #
    # ------------------------------------------------------------------ #

    def subscribe_grab_start(self, cb: Event) -> None:
        self._on_grab_start.append(cb)

    def subscribe_grab_end(self, cb: Event) -> None:
        self._on_grab_end.append(cb)

    def subscribe_stretch_update(self, cb: Event) -> None:
        self._on_stretch_update.append(cb)

    def subscribe_threshold_crossed(self, cb: Event) -> None:
        self._on_threshold_crossed.append(cb)

    def subscribe_threshold_cleared(self, cb: Event) -> None:
        self._on_threshold_cleared.append(cb)

    def subscribe_state_change(self, cb: Event) -> None:
        self._on_state_change.append(cb)

    # ------------------------------------------------------------------ #
    # OSC コールバック（OSCReceiver から呼ばれる / tab_test.py が直接呼ぶ） #
    # ------------------------------------------------------------------ #

    def on_stretch_change(self, value: float) -> None:
        """Stretch 値が更新された。"""
        self.current_stretch = value
        self._fire(self._on_state_change)

        if not self.is_grabbed:
            return

        self._stretch_history.append((time.time(), value))
        logger.debug(f"Stretch updated: {value:.3f}")
        self._fire(self._on_stretch_update, value)

        # ヒステリシス付き閾値チェック
        from config import VIBRATION_ON_STRETCH_THRESHOLD, VIBRATION_HYSTERESIS_OFFSET
        if value > VIBRATION_ON_STRETCH_THRESHOLD:
            if not self.stretch_above_threshold:
                self.stretch_above_threshold = True
                logger.info(f"[SM] Stretch threshold crossed: {value:.3f}")
                self._fire(self._on_threshold_crossed, value)
        elif value < VIBRATION_ON_STRETCH_THRESHOLD - VIBRATION_HYSTERESIS_OFFSET:
            if self.stretch_above_threshold:
                self.stretch_above_threshold = False
                logger.info(f"[SM] Stretch below hysteresis: {value:.3f}")
                self._fire(self._on_threshold_cleared, value)

    def on_grabbed_change(self, value: bool) -> None:
        """IsGrabbed 状態が変化した。"""
        old_state = self.is_grabbed
        self.is_grabbed = value
        self._fire(self._on_state_change)

        if not old_state and value:
            # false → true: Grab 開始
            self.grab_start_time = time.time()
            self.stretch_above_threshold = False
            self._stretch_history.clear()
            logger.info("[SM] Grab started")
            self._fire(self._on_grab_start)

        elif old_state and not value:
            # true → false: Grab 終了
            if self.grab_start_time is not None:
                duration = time.time() - self.grab_start_time
                stretch = self.current_stretch
                logger.info(f"[SM] Grab ended: duration={duration:.1f}s, stretch={stretch:.3f}")
                self._fire(self._on_grab_end, stretch, duration)
                self.grab_start_time = None
                self.current_stretch = 0.0
            self.stretch_above_threshold = False

    def get_max_speed(self) -> float:
        """Grab 中に記録した Stretch 履歴から最大引っ張り速度（stretch/秒）を返す。"""
        history = list(self._stretch_history)
        if len(history) < 2:
            return 0.0
        max_speed = 0.0
        for i in range(1, len(history)):
            t_prev, s_prev = history[i - 1]
            t_curr, s_curr = history[i]
            if s_curr <= s_prev:
                continue  # 戻し区間は除外
            dt = t_curr - t_prev
            if dt <= 0:
                continue
            speed = (s_curr - s_prev) / dt
            if speed > max_speed:
                max_speed = speed
        return max_speed

    # ------------------------------------------------------------------ #
    # 内部                                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _fire(callbacks: list[Event], *args) -> None:
        for cb in callbacks:
            try:
                cb(*args)
            except Exception as e:
                logger.error(f"[SM] Event callback error: {e}", exc_info=True)
