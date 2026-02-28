"""Zap 記録ハンドラ

Grab 終了時に Zap 実行を JSON ファイルに記録する。
テストモード（is_test_mode=True）の場合は記録しない。
"""

import logging

logger = logging.getLogger(__name__)


class RecorderHandler:
    """Zap 実行記録を ZapRecorder に委譲するハンドラ。"""

    def __init__(self, machine, zap_recorder):
        """
        Args:
            machine: GrabStateMachine（grab_end を購読、is_test_mode を参照）
            zap_recorder: ZapRecorder インスタンス
        """
        self._machine = machine
        self._recorder = zap_recorder

        machine.subscribe_grab_end(self._on_grab_end)

    # ------------------------------------------------------------------ #
    # イベントハンドラ                                                     #
    # ------------------------------------------------------------------ #

    def _on_grab_end(self, stretch: float, duration: float) -> None:
        """Grab 終了時：Zap を記録する（テストモード・Vibe モードは除外）。"""
        from config import MIN_GRAB_DURATION, USE_VIBRATION, MIN_STIMULUS_VALUE, MAX_STIMULUS_VALUE

        # テストモードまたは Vibration モードは記録しない
        if self._machine.is_test_mode or USE_VIBRATION:
            return

        if duration < MIN_GRAB_DURATION:
            return

        from pavlok_controller import calculate_zap_intensity, normalize_intensity_for_display
        intensity = calculate_zap_intensity(stretch)
        if intensity <= 0:
            return

        display = normalize_intensity_for_display(intensity)
        self._recorder.record_zap(
            display_intensity=display,
            actual_intensity=intensity,
            min_stimulus_value=MIN_STIMULUS_VALUE,
            max_stimulus_value=MAX_STIMULUS_VALUE,
        )
        logger.info(f"[Recorder] Zap recorded: display={display}%, actual={intensity}")
