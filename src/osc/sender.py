"""OSC 送信専用モジュール

VRChat へ Chatbox などのパラメータを UDP で送信する。受信機能は持たない。
"""

import logging
from pythonosc.udp_client import SimpleUDPClient

logger = logging.getLogger(__name__)


class OSCSender:
    """VRChat へ OSC メッセージを送信する（送信のみ）。"""

    def __init__(self):
        from config import OSC_SEND_IP, OSC_SEND_PORT
        try:
            self._client = SimpleUDPClient(OSC_SEND_IP, OSC_SEND_PORT)
            logger.info(f"OSCSender initialized: {OSC_SEND_IP}:{OSC_SEND_PORT}")
        except Exception as e:
            logger.warning(f"OSCSender failed to initialize: {e}")
            self._client = None

    # ------------------------------------------------------------------ #
    # 送信メソッド                                                         #
    # ------------------------------------------------------------------ #

    def send_parameter(self, address: str, value) -> None:
        """任意の OSC パラメータを送信する。

        Args:
            address: OSC アドレス（例: "/chatbox/input"）
            value: 送信する値（スカラーまたはリスト）
        """
        if not self._client:
            logger.warning("OSCSender: client not initialized, cannot send")
            return

        from config import DEBUG_LOG_OSC_SEND
        try:
            self._client.send_message(address, value)
            if DEBUG_LOG_OSC_SEND:
                logger.info(f"[OSC SEND] {address} = {value}")
        except Exception as e:
            logger.error(f"OSCSender: failed to send to {address}: {e}")

    def send_chatbox_message(
        self,
        message: str,
        send_immediately: bool = True,
        notification_sound: bool = True,
    ) -> None:
        """VRChat の Chatbox にメッセージを送信する。

        OSC 仕様: /chatbox/input (string s, bool b, bool n)
          s: メッセージテキスト（最大 144 文字）
          b: True=即座に送信 / False=キーボード入力欄に入力
          n: True=通知音あり / False=通知音なし

        Args:
            message: 表示するテキスト
            send_immediately: 即座に送信するか（デフォルト True）
            notification_sound: 通知音を鳴らすか（デフォルト True）
        """
        from config import OSC_CHATBOX_PARAM
        self.send_parameter(OSC_CHATBOX_PARAM, [message, send_immediately, notification_sound])
