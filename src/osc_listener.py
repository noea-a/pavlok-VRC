"""
osc_listener.py - 後方互換ラッパー（Phase 6 で削除予定）

実装は src/osc/receiver.py と src/osc/sender.py に移動済み。
"""

from osc.receiver import OSCReceiver
from osc.sender import OSCSender


class OSCListener(OSCReceiver):
    """後方互換クラス。OSCReceiver に送信機能を追加した旧インターフェース。

    新規コードでは OSCReceiver / OSCSender を個別に使うこと。
    """

    def __init__(self, on_stretch_change=None, on_grabbed_change=None):
        super().__init__()
        self.on_stretch_change = on_stretch_change
        self.on_grabbed_change = on_grabbed_change

        # 送信機能を内包（旧インターフェース維持のため）
        self._sender = OSCSender()

    def send_parameter(self, address, value):
        """後方互換: OSCSender.send_parameter に委譲。"""
        self._sender.send_parameter(address, value)

    def send_chatbox_message(self, message: str, send_immediately: bool = True,
                             notification_sound: bool = True):
        """後方互換: OSCSender.send_chatbox_message に委譲。"""
        self._sender.send_chatbox_message(message, send_immediately, notification_sound)
