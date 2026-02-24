import threading
import logging
from pythonosc import osc_server
from pythonosc import dispatcher
from pythonosc.udp_client import SimpleUDPClient
from config import (
    LISTEN_PORT, OSC_STRETCH_PARAM, OSC_IS_GRABBED_PARAM, OSC_ANGLE_PARAM, OSC_IS_POSED_PARAM,
    DEBUG_LOG_STRETCH, DEBUG_LOG_IS_GRABBED, DEBUG_LOG_ANGLE, DEBUG_LOG_IS_POSED, DEBUG_LOG_ALL_OSC,
    DEBUG_LOG_OSC_SEND, OSC_SEND_IP, OSC_SEND_PORT, OSC_CHATBOX_PARAM
)

logger = logging.getLogger(__name__)


class OSCListener:
    def __init__(self, on_stretch_change=None, on_grabbed_change=None):
        """
        OSCリスナーを初期化

        Args:
            on_stretch_change: Stretch値が変更されたときのコールバック(float値を受け取る)
            on_grabbed_change: IsGrabbed状態が変更されたときのコールバック(bool値を受け取る)
        """
        self.on_stretch_change = on_stretch_change
        self.on_grabbed_change = on_grabbed_change
        self.server = None
        self.disp = None
        self.running = False

        # OSC送信用クライアント（VRChatへ）
        try:
            self.osc_client = SimpleUDPClient(OSC_SEND_IP, OSC_SEND_PORT)
            logger.info(f"OSC client initialized for sending to {OSC_SEND_IP}:{OSC_SEND_PORT}")
        except Exception as e:
            logger.warning(f"Failed to initialize OSC client: {e}")
            self.osc_client = None

    def send_parameter(self, address, value):
        """
        OSCパラメータをVRChatに送信

        Args:
            address: OSCアドレス（例："/chatbox/input"）
            value: パラメータ値（単一値またはリスト）
        """
        if self.osc_client:
            try:
                # リストの場合は複数値、単一値の場合はそのまま送信
                if isinstance(value, (list, tuple)):
                    self.osc_client.send_message(address, value)
                    if DEBUG_LOG_OSC_SEND:
                        logger.info(f"[OSC SEND] Address: {address}, Values: {value}")
                else:
                    self.osc_client.send_message(address, value)
                    if DEBUG_LOG_OSC_SEND:
                        logger.info(f"[OSC SEND] Address: {address}, Value: {value}")
            except Exception as e:
                logger.error(f"Failed to send OSC message to {address}: {e}")
        else:
            logger.warning("OSC client not initialized, cannot send message")

    def send_chatbox_message(self, message: str, send_immediately: bool = True, notification_sound: bool = True):
        """
        VRChatのChatboxに文字列メッセージを送信

        Args:
            message: Chatboxに表示させるメッセージ（最大144文字）
            send_immediately: True=すぐに送信、False=キーボードを開いて入力欄に入力
            notification_sound: True=通知音を鳴らす（デフォルト）、False=通知音なし

        OSC仕様: /chatbox/input (string s, bool b, bool n)
          - s: メッセージテキスト
          - b: True=送信、False=入力欄に入力
          - n: True=通知音あり、False=通知音なし

        参考: https://docs.vrchat.com/docs/osc-as-input-controller
        """
        # /chatbox/input に3つの値を送信：メッセージ、送信フラグ、通知音フラグ
        self.send_parameter(OSC_CHATBOX_PARAM, [message, send_immediately, notification_sound])

    def _handle_debug_all(self, addr, *args):
        """すべてのOSCメッセージをデバッグ出力"""
        if DEBUG_LOG_ALL_OSC:
            logger.info(f"[OSC] Address: {addr}, Values: {args}")

    def _handle_stretch(self, addr, value):
        """Stretch値が受信されたときのハンドラ"""
        if DEBUG_LOG_STRETCH:
            logger.info(f"[STRETCH] {value}")
        if self.on_stretch_change:
            self.on_stretch_change(value)

    def _handle_grabbed(self, addr, value):
        """IsGrabbed状態が受信されたときのハンドラ"""
        if DEBUG_LOG_IS_GRABBED:
            logger.info(f"[IS_GRABBED] {value}")
        if self.on_grabbed_change:
            self.on_grabbed_change(value)

    def _handle_angle(self, addr, value):
        """Angle値が受信されたときのハンドラ"""
        if DEBUG_LOG_ANGLE:
            logger.info(f"[ANGLE] {value}")

    def _handle_is_posed(self, addr, value):
        """IsPosed状態が受信されたときのハンドラ"""
        if DEBUG_LOG_IS_POSED:
            logger.info(f"[IS_POSED] {value}")

    def start(self):
        """OSCサーバーを起動"""
        if self.running:
            logger.warning("OSC listener is already running")
            return

        try:
            self.disp = dispatcher.Dispatcher()
            self.disp.map(OSC_STRETCH_PARAM, self._handle_stretch)
            self.disp.map(OSC_IS_GRABBED_PARAM, self._handle_grabbed)
            self.disp.map(OSC_ANGLE_PARAM, self._handle_angle)
            self.disp.map(OSC_IS_POSED_PARAM, self._handle_is_posed)
            # すべてのOSCメッセージをキャッチしてデバッグ出力
            self.disp.set_default_handler(self._handle_debug_all)

            self.server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", LISTEN_PORT), self.disp)
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()

            self.running = True
            logger.info(f"OSC listener started on port {LISTEN_PORT}")

        except Exception as e:
            logger.error(f"Failed to start OSC listener: {e}")
            self.running = False

    def stop(self):
        """OSCサーバーを停止"""
        if not self.running:
            return

        try:
            if self.server:
                self.server.shutdown()
            self.running = False
            logger.info("OSC listener stopped")
        except Exception as e:
            logger.error(f"Error stopping OSC listener: {e}")
