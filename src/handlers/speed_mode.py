"""速度モード Zap ハンドラ

Grab 中の Stretch 変化速度を監視し、素早い引っ張りを検出したら Zap を発火する。
"""

import time
import threading
import logging
from collections import deque
from queue import Queue

logger = logging.getLogger(__name__)


class SpeedModeHandler:
    """速度ベースの Zap 発火ハンドラ。"""

    def __init__(self, machine, status_queue: Queue | None = None):
        self._machine = machine
        self._status_queue = status_queue

        # 状態変数
        self._grab_start_time: float = 0.0
        self._is_settled: bool = False
        self._history: deque[tuple[float, float]] = deque(maxlen=300)
        self._origin_stretch: float = 0.0
        self._origin_time: float = 0.0
        self._measuring: bool = False
        self._peak_stretch: float = 0.0
        self._stop_start_time: float | None = None
        self._stop_timer: threading.Timer | None = None
        self._zap_fired: bool = False
        self._zap_fire_stretch: float = 0.0

        machine.subscribe_grab_start(self._on_grab_start)
        machine.subscribe_grab_end(self._on_grab_end)
        machine.subscribe_stretch_update(self._on_stretch_update)

    # ------------------------------------------------------------------ #
    # イベントハンドラ                                                     #
    # ------------------------------------------------------------------ #

    def _on_grab_start(self) -> None:
        self._cancel_stop_timer()
        self._grab_start_time = time.time()
        self._is_settled = False
        self._history.clear()
        self._measuring = False
        self._peak_stretch = 0.0
        self._stop_start_time = None
        self._zap_fired = False
        self._zap_fire_stretch = 0.0
        logger.debug("[SpeedMode] Grab started, settling...")

    def _on_grab_end(self, stretch: float, duration: float) -> None:
        self._cancel_stop_timer()
        self._is_settled = False
        self._measuring = False
        self._zap_fired = False
        self._peak_stretch = 0.0
        self._update_machine_state(0.0)
        logger.debug("[SpeedMode] Grab ended, state reset")

    def _on_stretch_update(self, stretch: float) -> None:
        now = time.time()
        sm = self._get_settings()

        # A. settle チェック
        elapsed = now - self._grab_start_time
        if elapsed < sm.grab_settle_time:
            return
        if not self._is_settled:
            self._is_settled = True
            logger.debug(f"[SpeedMode] Settled after {elapsed:.3f}s")

        # 履歴に追記
        self._history.append((now, stretch))

        # B. ZAP_RESET_PULLBACK 監視（_zap_fired=True のとき）
        if self._zap_fired:
            if self._zap_fire_stretch > 0:
                pullback_ratio = (self._zap_fire_stretch - stretch) / self._zap_fire_stretch
                threshold = sm.zap_reset_pullback / 100.0
                if pullback_ratio >= threshold:
                    logger.info(f"[SpeedMode] Pullback detected ({pullback_ratio:.2%}), resetting origin")
                    self._zap_fired = False
                    self._reset_origin(stretch, now)
            self._update_machine_state(stretch)
            return  # Zap 済みは pullback 解除待ち

        # C. Onset 判定（_measuring=False のとき）
        if not self._measuring:
            avg_speed = self._calc_avg_speed_recent(sm.speed_onset_ticks)
            if avg_speed > sm.speed_onset_threshold:
                logger.info(f"[SpeedMode] Onset detected (avg_speed={avg_speed:.3f}), starting measurement")
                self._reset_origin(stretch, now)
            self._update_machine_state(stretch)
            return

        # D. _measuring=True のとき
        if stretch > self._peak_stretch:
            self._peak_stretch = stretch

        # 停止検知（stretch 方向のみ）
        recent_speed = self._calc_recent_speed()
        if recent_speed > sm.speed_stop_threshold:
            # 動いている → タイマーリセット
            if self._stop_start_time is not None:
                self._cancel_stop_timer()
                self._stop_start_time = None
        else:
            # 停止とみなす → 初回のみタイマー開始
            if self._stop_start_time is None:
                self._stop_start_time = now
                self._start_stop_timer(sm.speed_zap_hold_time)

        self._update_machine_state(stretch)

    # ------------------------------------------------------------------ #
    # 内部ロジック                                                         #
    # ------------------------------------------------------------------ #

    def _start_stop_timer(self, hold_time: float) -> None:
        """停止タイマーを開始する。OSC 更新がなくても hold_time 後に発火チェックする。"""
        self._cancel_stop_timer()
        self._stop_timer = threading.Timer(hold_time, self._on_stop_timer_fired)
        self._stop_timer.daemon = True
        self._stop_timer.start()
        logger.debug(f"[SpeedMode] Stop timer started ({hold_time:.2f}s)")

    def _cancel_stop_timer(self) -> None:
        if self._stop_timer is not None:
            self._stop_timer.cancel()
            self._stop_timer = None

    def _on_stop_timer_fired(self) -> None:
        """タイマー満了：発火チェックを実行する。"""
        self._stop_timer = None
        if not self._measuring or self._zap_fired:
            return
        self._stop_start_time = None
        self._check_zap_fire(time.time(), self._get_settings())

    def _reset_origin(self, stretch: float, now: float) -> None:
        """原点をリセットして計測開始"""
        self._cancel_stop_timer()
        self._stop_start_time = None
        self._origin_stretch = stretch
        self._origin_time = now
        self._measuring = True
        self._peak_stretch = stretch
        self._stop_start_time = None
        self._history.clear()
        self._history.append((now, stretch))
        self._update_machine_state(stretch)

    def _check_zap_fire(self, now: float, sm) -> None:
        """発火条件チェック。全通過で Zap 発火。"""
        # ① 計測時間超過チェック
        elapsed = now - self._origin_time
        if elapsed > sm.max_zap_duration:
            logger.info(f"[SpeedMode] Cancel: max duration exceeded ({elapsed:.2f}s > {sm.max_zap_duration}s)")
            self._measuring = False
            self._update_machine_state(self._peak_stretch)
            return

        stretch_range = self._peak_stretch - self._origin_stretch
        if stretch_range <= 0:
            logger.info("[SpeedMode] Cancel: no stretch movement")
            self._measuring = False
            self._update_machine_state(self._peak_stretch)
            return

        # ② INITIAL_SPEED_STRETCH_WINDOW 区間の速度チェック
        window_end = self._origin_stretch + stretch_range * (sm.initial_speed_stretch_window / 100.0)
        initial_avg = self._calc_avg_speed_in_range(self._origin_stretch, window_end)
        if initial_avg < sm.speed_zap_threshold:
            logger.info(f"[SpeedMode] Cancel: initial speed too low ({initial_avg:.3f} < {sm.speed_zap_threshold})")
            self._measuring = False
            self._update_machine_state(self._peak_stretch)
            return

        # ③ MIN_SPEED_EVAL_WINDOW 区間の速度チェック
        eval_end = self._origin_stretch + stretch_range * (sm.min_speed_eval_window / 100.0)
        eval_avg = self._calc_avg_speed_in_range(self._origin_stretch, eval_end)
        if eval_avg < sm.min_speed_threshold:
            logger.info(f"[SpeedMode] Cancel: eval speed too low ({eval_avg:.3f} < {sm.min_speed_threshold})")
            self._measuring = False
            self._update_machine_state(self._peak_stretch)
            return

        # 全チェック通過 → Zap 発火
        delta = self._peak_stretch - self._origin_stretch
        logger.info(
            f"[SpeedMode] ZAP FIRE! origin={self._origin_stretch:.3f}, "
            f"peak={self._peak_stretch:.3f}, delta={delta:.3f}, "
            f"initial_avg={initial_avg:.3f}, eval_avg={eval_avg:.3f}"
        )
        self._fire_zap()

    def _fire_zap(self) -> None:
        from intensity import calculate_intensity, IntensityConfig
        from pavlok_controller import normalize_intensity_for_display
        import pavlok_controller as ctrl
        from config import USE_VIBRATION

        cfg = IntensityConfig.from_settings()
        delta = self._peak_stretch - self._origin_stretch
        intensity = calculate_intensity(delta, cfg)
        if intensity <= 0:
            logger.info("[SpeedMode] Zap skipped: intensity=0")
            self._measuring = False
            return

        ctrl.send_zap(intensity)

        if not USE_VIBRATION:
            display = normalize_intensity_for_display(intensity)
            self._machine.last_zap_display_intensity = display
            self._machine.last_zap_actual_intensity = intensity
            self._push_status()

        self._zap_fired = True
        self._zap_fire_stretch = self._peak_stretch
        self._measuring = False
        self._update_machine_state(self._peak_stretch)

    # ------------------------------------------------------------------ #
    # 速度計算ヘルパー                                                     #
    # ------------------------------------------------------------------ #

    def _calc_avg_speed_recent(self, ticks: int) -> float:
        """直近 ticks 個のエントリから平均速度を計算"""
        history = list(self._history)
        if len(history) < 2:
            return 0.0
        recent = history[-min(ticks + 1, len(history)):]
        return self._avg_speed_of(recent)

    def _calc_recent_speed(self) -> float:
        """直近 2 エントリの速度（stretch 方向のみ、戻しは 0）"""
        history = list(self._history)
        if len(history) < 2:
            return 0.0
        t_prev, s_prev = history[-2]
        t_curr, s_curr = history[-1]
        if s_curr <= s_prev:
            return 0.0
        dt = t_curr - t_prev
        if dt <= 0:
            return 0.0
        return (s_curr - s_prev) / dt

    def _calc_avg_speed_in_range(self, stretch_from: float, stretch_to: float) -> float:
        """stretch_from ~ stretch_to の範囲にある履歴エントリから平均速度を計算"""
        history = list(self._history)
        filtered = [(t, s) for t, s in history if stretch_from <= s <= stretch_to]
        if len(filtered) < 2:
            return 0.0
        return self._avg_speed_of(filtered)

    @staticmethod
    def _avg_speed_of(entries: list[tuple[float, float]]) -> float:
        """エントリリスト（時刻, stretch）から平均速度（total stretch / total time）を返す"""
        if len(entries) < 2:
            return 0.0
        total_stretch = entries[-1][1] - entries[0][1]
        total_time = entries[-1][0] - entries[0][0]
        if total_time <= 0 or total_stretch <= 0:
            return 0.0
        return total_stretch / total_time

    def _update_machine_state(self, current_stretch: float) -> None:
        """machine.speed_mode_state に現在の内部状態を書き込む（tab_test が参照）"""
        self._machine.speed_mode_state = {
            "settled":        self._is_settled,
            "measuring":      self._measuring,
            "zap_fired":      self._zap_fired,
            "origin_stretch": self._origin_stretch,
            "peak_stretch":   self._peak_stretch,
            "delta":          self._peak_stretch - self._origin_stretch,
            "current_stretch": current_stretch,
            "recent_speed":   self._calc_recent_speed(),
            "stop_detecting": self._stop_start_time is not None,
            "history_len":    len(self._history),
        }

    def _get_settings(self):
        import settings as s_mod
        return s_mod.settings.speed_mode

    def _push_status(self) -> None:
        if not self._status_queue:
            return
        try:
            from pavlok_controller import calculate_zap_intensity
            m = self._machine
            intensity = calculate_zap_intensity(m.current_stretch) if m.is_grabbed else 0
            self._status_queue.put({
                "is_grabbed": m.is_grabbed,
                "stretch": m.current_stretch,
                "intensity": intensity,
                "last_zap_display_intensity": m.last_zap_display_intensity,
                "last_zap_actual_intensity": m.last_zap_actual_intensity,
            })
        except Exception:
            pass
