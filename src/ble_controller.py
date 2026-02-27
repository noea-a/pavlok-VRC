import asyncio
import logging
import threading
from bleak import BleakClient, BleakError

logger = logging.getLogger(__name__)

# BLE専用スレッドのイベントループ
_ble_loop: asyncio.AbstractEventLoop | None = None
_ble_thread: threading.Thread | None = None
_ble_instance: "PavlokBLE | None" = None


class PavlokBLE:
    """Pavlok 3 BLE直接制御クラス（接続維持方式）"""

    # webtool.js の c_api UUID（接続確認用）
    _C_API_UUID = "00001004-0000-1000-8000-00805f9b34fb"

    def __init__(self, mac: str, zap_uuid: str, vibe_uuid: str,
                 connect_timeout: float, reconnect_interval: float):
        self._mac = mac
        self._zap_uuid = zap_uuid
        self._vibe_uuid = vibe_uuid
        self._connect_timeout = connect_timeout
        self._reconnect_interval = reconnect_interval
        self._client: BleakClient | None = None
        self._connected = False
        self._reconnecting = False

    async def connect(self) -> bool:
        """Pavlok 3 に BLE 接続する。成功時 True を返す。"""
        try:
            self._client = BleakClient(
                self._mac,
                timeout=self._connect_timeout,
                disconnected_callback=self._on_disconnect,
            )
            await self._client.connect()
            self._connected = True
            logger.info(f"BLE connected: {self._mac}")

            # webtool.js の check_api 相当（接続確認書き込み）
            try:
                await self._client.write_gatt_char(
                    self._C_API_UUID, bytes([87, 84]), response=False
                )
            except Exception:
                pass  # check_api 失敗は致命的でない

            return True

        except (BleakError, asyncio.TimeoutError, Exception) as e:
            logger.error(f"BLE connect failed: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """BLE 接続を切断する。"""
        self._reconnecting = False  # 再接続ループを止める
        if self._client and self._connected:
            try:
                await self._client.disconnect()
            except Exception as e:
                logger.warning(f"BLE disconnect error: {e}")
        self._connected = False
        logger.info("BLE disconnected")

    async def send_zap(self, intensity: int) -> bool:
        """Zap コマンドを送信する。"""
        if not self._connected or not self._client:
            logger.warning("BLE not connected, cannot send zap")
            return False
        try:
            cmd = bytes([0x89, intensity])
            await self._client.write_gatt_char(self._zap_uuid, cmd, response=False)
            logger.info(f"BLE Zap sent: intensity={intensity}")
            return True
        except Exception as e:
            logger.error(f"BLE send_zap failed: {e}")
            return False

    async def send_vibration(self, intensity: int) -> bool:
        """Vibration コマンドを送信する。"""
        if not self._connected or not self._client:
            logger.warning("BLE not connected, cannot send vibration")
            return False
        try:
            cmd = bytes([0x81, 2, intensity, 22, 22])
            await self._client.write_gatt_char(self._vibe_uuid, cmd, response=False)
            logger.info(f"BLE Vibration sent: intensity={intensity}")
            return True
        except Exception as e:
            logger.error(f"BLE send_vibration failed: {e}")
            return False

    def _on_disconnect(self, client: BleakClient) -> None:
        """切断コールバック。再接続ループを起動する。"""
        self._connected = False
        logger.warning("BLE disconnected (unexpected). Starting reconnect loop...")
        if not self._reconnecting:
            self._reconnecting = True
            asyncio.run_coroutine_threadsafe(self._reconnect_loop(), _ble_loop)

    async def _reconnect_loop(self) -> None:
        """切断後に最大5回再接続を試みる。"""
        for attempt in range(1, 6):
            if not self._reconnecting:
                break
            logger.info(f"BLE reconnect attempt {attempt}/5 (waiting {self._reconnect_interval}s)...")
            await asyncio.sleep(self._reconnect_interval)
            if await self.connect():
                self._reconnecting = False
                return
        logger.error("BLE reconnect failed after 5 attempts")
        self._reconnecting = False


# ===== モジュールレベルの同期 API =====

def _run_ble_loop(loop: asyncio.AbstractEventLoop) -> None:
    """BLE 専用スレッドでイベントループを常駐させる。"""
    asyncio.set_event_loop(loop)
    loop.run_forever()


def ble_connect() -> bool:
    """
    BLE 専用スレッドを起動し、Pavlok 3 に接続する。
    成功時 True、失敗時 False を返す。
    """
    global _ble_loop, _ble_thread, _ble_instance

    # config をランタイムで読み込む
    from config import (
        BLE_DEVICE_MAC, BLE_ZAP_UUID, BLE_VIBE_UUID,
        BLE_CONNECT_TIMEOUT, BLE_RECONNECT_INTERVAL
    )

    if not BLE_DEVICE_MAC:
        logger.error("BLE_DEVICE_MAC が設定されていません（config.py を確認してください）")
        return False

    _ble_loop = asyncio.new_event_loop()
    _ble_thread = threading.Thread(target=_run_ble_loop, args=(_ble_loop,), daemon=True)
    _ble_thread.start()

    _ble_instance = PavlokBLE(
        mac=BLE_DEVICE_MAC,
        zap_uuid=BLE_ZAP_UUID,
        vibe_uuid=BLE_VIBE_UUID,
        connect_timeout=BLE_CONNECT_TIMEOUT,
        reconnect_interval=BLE_RECONNECT_INTERVAL,
    )

    future = asyncio.run_coroutine_threadsafe(_ble_instance.connect(), _ble_loop)
    try:
        return future.result(timeout=BLE_CONNECT_TIMEOUT + 2)
    except Exception as e:
        logger.error(f"ble_connect timeout/error: {e}")
        return False


def ble_disconnect() -> None:
    """BLE 接続を切断し、専用スレッドを停止する。"""
    global _ble_instance, _ble_loop

    if _ble_instance and _ble_loop:
        future = asyncio.run_coroutine_threadsafe(_ble_instance.disconnect(), _ble_loop)
        try:
            future.result(timeout=5)
        except Exception:
            pass

    if _ble_loop:
        _ble_loop.call_soon_threadsafe(_ble_loop.stop)


def ble_send_zap(intensity: int) -> bool:
    """同期ラッパー：Zap を送信する。"""
    if not _ble_instance or not _ble_loop:
        logger.error("BLE未接続です。ble_connect() を先に呼んでください。")
        return False
    future = asyncio.run_coroutine_threadsafe(_ble_instance.send_zap(intensity), _ble_loop)
    try:
        return future.result(timeout=5)
    except Exception as e:
        logger.error(f"ble_send_zap error: {e}")
        return False


def ble_send_vibration(intensity: int) -> bool:
    """同期ラッパー：Vibration を送信する。"""
    if not _ble_instance or not _ble_loop:
        logger.error("BLE未接続です。ble_connect() を先に呼んでください。")
        return False
    future = asyncio.run_coroutine_threadsafe(_ble_instance.send_vibration(intensity), _ble_loop)
    try:
        return future.result(timeout=5)
    except Exception as e:
        logger.error(f"ble_send_vibration error: {e}")
        return False
