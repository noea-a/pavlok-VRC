"""GUI 更新ハンドラ

GrabStateMachine の状態変化を status_queue に流し込む。
Tkinter の poll_data() がキューを消費して画面を更新する。
"""

import logging
from queue import Queue

logger = logging.getLogger(__name__)


class GUIUpdater:
    """状態変化を status_queue に変換して GUI へ渡す。"""

    def __init__(self, machine, status_queue: Queue):
        """
        Args:
            machine: GrabStateMachine（state_change を購読）
            status_queue: GUI が poll する Queue
        """
        self._machine = machine
        self._queue = status_queue

        machine.subscribe_state_change(self._on_state_change)

    # ------------------------------------------------------------------ #
    # イベントハンドラ                                                     #
    # ------------------------------------------------------------------ #

    def _on_state_change(self) -> None:
        """任意の状態変化時に現在のスナップショットをキューに積む。"""
        try:
            from pavlok_controller import calculate_zap_intensity
            m = self._machine
            intensity = calculate_zap_intensity(m.current_stretch) if m.is_grabbed else 0
            self._queue.put({
                "is_grabbed": m.is_grabbed,
                "stretch": m.current_stretch,
                "intensity": intensity,
                "last_zap_display_intensity": m.last_zap_display_intensity,
                "last_zap_actual_intensity": m.last_zap_actual_intensity,
            })
        except Exception as e:
            logger.debug(f"[GUIUpdater] Error: {e}")
