"""Chatbox 送信ハンドラ

Stretch 変化（スロットル付き）と Grab 終了時に VRChat Chatbox へメッセージを送る。
"""

import time
import logging

logger = logging.getLogger(__name__)


class ChatboxHandler:
    """VRChat Chatbox へのメッセージ送信を担う。"""

    def __init__(self, machine, osc_sender):
        """
        Args:
            machine: GrabStateMachine（stretch_update / grab_end を購読）
            osc_sender: OSCSender インスタンス
        """
        self._machine = machine
        self._sender = osc_sender
        self._last_send_time: float = 0.0

        machine.subscribe_stretch_update(self._on_stretch_update)
        machine.subscribe_grab_end(self._on_grab_end)

    # ------------------------------------------------------------------ #
    # イベントハンドラ                                                     #
    # ------------------------------------------------------------------ #

    def _on_stretch_update(self, stretch: float) -> None:
        """Grab 中の Stretch 変化：スロットル付きで Chatbox を更新する。"""
        from config import SEND_REALTIME_CHATBOX, OSC_SEND_INTERVAL
        if not SEND_REALTIME_CHATBOX:
            return

        now = time.time()
        if now - self._last_send_time < OSC_SEND_INTERVAL:
            return

        from pavlok_controller import calculate_zap_intensity, normalize_intensity_for_display
        intensity = calculate_zap_intensity(stretch)
        if intensity <= 0:
            return

        display = normalize_intensity_for_display(intensity)
        self._sender.send_chatbox_message(f"Zap: {display}%", send_immediately=True)
        self._last_send_time = now

    def _on_grab_end(self, stretch: float, duration: float) -> None:
        """Grab 終了時：最終刺激強度を Chatbox に表示する。"""
        from config import MIN_GRAB_DURATION, SEND_FINAL_CHATBOX
        if not SEND_FINAL_CHATBOX:
            return
        if duration < MIN_GRAB_DURATION:
            return

        from pavlok_controller import calculate_zap_intensity, normalize_intensity_for_display
        intensity = calculate_zap_intensity(stretch)
        if intensity <= 0:
            return

        display = normalize_intensity_for_display(intensity)
        self._sender.send_chatbox_message(f"Zap: {display}% [Final]", send_immediately=True)
