"""刺激送信ハンドラ

GrabStateMachine のイベントを受けて Pavlok へ刺激を送る。
zap 送信後は machine.last_zap_* を更新し、GUIUpdater が読めるようにする。

ヒステリシス付き閾値チェック（旧 state_machine 担当）もここで管理する。
"""

import logging

logger = logging.getLogger(__name__)


class StimulusHandler:
    """Grab イベントに応じて Pavlok への刺激送信を担う。"""

    def __init__(self, machine):
        """
        Args:
            machine: GrabStateMachine インスタンス（イベント購読 + last_zap_* 更新用）
        """
        self._machine = machine
        self._stretch_above_threshold: bool = False

        machine.subscribe_grab_start(self._on_grab_start)
        machine.subscribe_grab_end(self._on_grab_end)
        machine.subscribe_stretch_update(self._on_stretch_update_check_threshold)

    # ------------------------------------------------------------------ #
    # イベントハンドラ                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _is_active() -> bool:
        import settings as s_mod
        return s_mod.settings.device.zap_mode == "stretch"

    def _on_grab_start(self) -> None:
        """Grab 開始時：常にバイブレーションを送信する。"""
        self._stretch_above_threshold = False
        if not self._is_active():
            return
        from config import (
            GRAB_START_VIBRATION_INTENSITY, GRAB_START_VIBRATION_COUNT,
            GRAB_START_VIBRATION_TON, GRAB_START_VIBRATION_TOFF,
        )
        import pavlok_controller as ctrl
        logger.info(f"[Stimulus] Grab start vibration: intensity={GRAB_START_VIBRATION_INTENSITY}")
        ctrl.send_vibration(
            GRAB_START_VIBRATION_INTENSITY,
            GRAB_START_VIBRATION_COUNT,
            GRAB_START_VIBRATION_TON,
            GRAB_START_VIBRATION_TOFF,
        )

    def _on_grab_end(self, stretch: float, duration: float) -> None:
        """Grab 終了時：MIN_GRAB_DURATION 以上なら刺激を送信する。"""
        self._stretch_above_threshold = False
        if not self._is_active():
            return
        from config import MIN_GRAB_DURATION, USE_VIBRATION
        from pavlok_controller import calculate_zap_intensity, normalize_intensity_for_display
        import pavlok_controller as ctrl

        if duration < MIN_GRAB_DURATION:
            logger.info(f"[Stimulus] Skipped (too short: {duration:.1f}s < {MIN_GRAB_DURATION}s)")
            return

        intensity = self._resolve_intensity(stretch)
        if intensity <= 0:
            logger.info("[Stimulus] Skipped (intensity too low)")
            return

        stimulus_type = "Vibration" if USE_VIBRATION else "Zap"
        logger.info(f"[Stimulus] Grab end {stimulus_type}: intensity={intensity}")
        ctrl.send_zap(intensity)  # USE_VIBRATION フラグは send_zap 内部で処理

        # Zap の場合のみ last_zap_* を更新（GUI 表示 + RecorderHandler が参照）
        if not USE_VIBRATION:
            display = normalize_intensity_for_display(intensity)
            self._machine.last_zap_display_intensity = display
            self._machine.last_zap_actual_intensity = intensity
            self._machine.notify_state_change()

    def _on_stretch_update_check_threshold(self, stretch: float) -> None:
        """Grab 中の Stretch 変化：ヒステリシス付き閾値チェックを行う。"""
        if not self._is_active():
            return
        import settings as s_mod
        sv = s_mod.settings.stretch_vibration
        threshold = sv.threshold
        hysteresis_offset = sv.hysteresis_offset

        if stretch > threshold:
            if not self._stretch_above_threshold:
                self._stretch_above_threshold = True
                logger.info(f"[Stimulus] Stretch threshold crossed: {stretch:.3f}")
                self._on_threshold_crossed(stretch)
        elif stretch < threshold - hysteresis_offset:
            if self._stretch_above_threshold:
                self._stretch_above_threshold = False
                logger.info(f"[Stimulus] Stretch below hysteresis: {stretch:.3f}")

    def _on_threshold_crossed(self, stretch: float) -> None:
        """Stretch が閾値を超えた：警告バイブレーションを送信する。"""
        from config import (
            VIBRATION_ON_STRETCH_INTENSITY, VIBRATION_ON_STRETCH_COUNT,
            VIBRATION_ON_STRETCH_TON, VIBRATION_ON_STRETCH_TOFF,
        )
        import pavlok_controller as ctrl
        from pavlok_controller import calculate_zap_intensity
        intensity = calculate_zap_intensity(stretch)
        logger.info(f"[Stimulus] Stretch threshold vibration: stretch={stretch:.3f}, intensity={intensity}")
        ctrl.send_vibration(
            intensity,
            VIBRATION_ON_STRETCH_COUNT,
            VIBRATION_ON_STRETCH_TON,
            VIBRATION_ON_STRETCH_TOFF,
        )

    def _resolve_intensity(self, stretch: float) -> int:
        """stretch から強度を算出する。"""
        from intensity import calculate_intensity, IntensityConfig
        cfg = IntensityConfig.from_settings()
        logger.info(f"[Stimulus] stretch={stretch:.3f}")
        return calculate_intensity(stretch, cfg)
