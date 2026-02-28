"""OSC 受信専用モジュール

VRChat から送られる PhysBone パラメータ（Stretch / IsGrabbed など）を
UDP で受信し、コールバックに渡す。送信機能は持たない。
"""

import threading
import logging
from typing import Callable

from pythonosc import osc_server, dispatcher

logger = logging.getLogger(__name__)


class OSCReceiver:
    """VRChat からの OSC メッセージを受信する（受信のみ）。

    コールバックは属性として後から設定できる：
        receiver.on_stretch_change = my_func
        receiver.on_grabbed_change = my_func
    """

    def __init__(self):
        self.on_stretch_change: Callable[[float], None] | None = None
        self.on_grabbed_change: Callable[[bool], None] | None = None

        self._server = None
        self._server_thread: threading.Thread | None = None
        self._running = False

    # ------------------------------------------------------------------ #
    # サーバー起動・停止                                                   #
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        """OSC サーバーを起動する（ブロッキング呼び出し）。"""
        if self._running:
            logger.warning("OSCReceiver is already running")
            return

        from config import (
            LISTEN_PORT,
            OSC_STRETCH_PARAM, OSC_IS_GRABBED_PARAM,
            OSC_ANGLE_PARAM, OSC_IS_POSED_PARAM,
            DEBUG_LOG_ALL_OSC,
        )

        try:
            disp = dispatcher.Dispatcher()
            disp.map(OSC_STRETCH_PARAM,    self._handle_stretch)
            disp.map(OSC_IS_GRABBED_PARAM, self._handle_grabbed)
            disp.map(OSC_ANGLE_PARAM,      self._handle_angle)
            disp.map(OSC_IS_POSED_PARAM,   self._handle_is_posed)
            if DEBUG_LOG_ALL_OSC:
                disp.set_default_handler(self._handle_debug_all)

            self._server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", LISTEN_PORT), disp)
            self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._server_thread.start()

            self._running = True
            logger.info(f"OSCReceiver started on port {LISTEN_PORT}")

        except Exception as e:
            logger.error(f"OSCReceiver failed to start: {e}")
            self._running = False

    def stop(self) -> None:
        """OSC サーバーを停止する。"""
        if not self._running:
            return
        try:
            if self._server:
                self._server.shutdown()
            self._running = False
            logger.info("OSCReceiver stopped")
        except Exception as e:
            logger.error(f"OSCReceiver stop error: {e}")

    # ------------------------------------------------------------------ #
    # ハンドラ                                                             #
    # ------------------------------------------------------------------ #

    def _handle_stretch(self, addr: str, value: float) -> None:
        from config import DEBUG_LOG_STRETCH
        if DEBUG_LOG_STRETCH:
            logger.info(f"[STRETCH] {value}")
        if self.on_stretch_change:
            self.on_stretch_change(value)

    def _handle_grabbed(self, addr: str, value: bool) -> None:
        from config import DEBUG_LOG_IS_GRABBED
        if DEBUG_LOG_IS_GRABBED:
            logger.info(f"[IS_GRABBED] {value}")
        if self.on_grabbed_change:
            self.on_grabbed_change(value)

    def _handle_angle(self, addr: str, value: float) -> None:
        from config import DEBUG_LOG_ANGLE
        if DEBUG_LOG_ANGLE:
            logger.info(f"[ANGLE] {value}")

    def _handle_is_posed(self, addr: str, value: bool) -> None:
        from config import DEBUG_LOG_IS_POSED
        if DEBUG_LOG_IS_POSED:
            logger.info(f"[IS_POSED] {value}")

    def _handle_debug_all(self, addr: str, *args) -> None:
        logger.info(f"[OSC] Address: {addr}, Values: {args}")
