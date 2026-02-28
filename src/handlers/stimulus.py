"""刺激送信ハンドラ

GrabStateMachine のイベントを受けて Pavlok へ刺激を送る。
zap 送信後は machine.last_zap_* を更新し、GUIUpdater が読めるようにする。
"""

import logging
from queue import Queue

logger = logging.getLogger(__name__)


class StimulusHandler:
    """Grab イベントに応じて Pavlok への刺激送信を担う。"""

    def __init__(self, machine, status_queue: Queue | None = None):
        """
        Args:
            machine: GrabStateMachine インスタンス（イベント購読 + last_zap_* 更新用）
            status_queue: Zap 送信直後に GUI を即時更新するためのキュー
        """
        self._machine = machine
        self._status_queue = status_queue

        machine.subscribe_grab_start(self._on_grab_start)
        machine.subscribe_grab_end(self._on_grab_end)
        machine.subscribe_threshold_crossed(self._on_threshold_crossed)

    # ------------------------------------------------------------------ #
    # イベントハンドラ                                                     #
    # ------------------------------------------------------------------ #

    def _on_grab_start(self) -> None:
        """Grab 開始時：常にバイブレーションを送信する。"""
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
            self._push_status()

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
        """intensity_mode に応じて effective_stretch を算出し、強度を返す。"""
        from intensity import calculate_intensity, IntensityConfig
        import settings as s_mod
        cfg = IntensityConfig.from_settings()
        s = s_mod.settings
        mode = s.logic.intensity_mode
        max_stretch = cfg.max_stretch_for_calc

        if mode == "speed":
            max_speed = s.logic.max_speed_for_calc
            speed = self._machine.get_max_speed()
            speed_score = min(speed / max_speed, 1.0) if max_speed > 0 else 0.0
            effective_stretch = speed_score * max_stretch
            logger.info(f"[Stimulus] mode=speed speed={speed:.3f} effective_stretch={effective_stretch:.3f}")

        elif mode == "combined":
            max_speed = s.logic.max_speed_for_calc
            speed = self._machine.get_max_speed()
            stretch_score = min(stretch / max_stretch, 1.0) if max_stretch > 0 else 0.0
            speed_score = min(speed / max_speed, 1.0) if max_speed > 0 else 0.0
            effective_stretch = (
                s.logic.stretch_weight * stretch_score
                + s.logic.speed_weight * speed_score
            ) * max_stretch
            logger.info(
                f"[Stimulus] mode=combined stretch_score={stretch_score:.3f} "
                f"speed_score={speed_score:.3f} effective_stretch={effective_stretch:.3f}"
            )

        else:  # "stretch"
            effective_stretch = stretch
            logger.info(f"[Stimulus] mode=stretch effective_stretch={effective_stretch:.3f}")

        return calculate_intensity(effective_stretch, cfg)

    # ------------------------------------------------------------------ #
    # 内部                                                                 #
    # ------------------------------------------------------------------ #

    def _push_status(self) -> None:
        """Zap 送信直後に GUI を即時更新する。"""
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
