import asyncio
import logging
import threading
from bleak import BleakClient, BleakError

logger = logging.getLogger(__name__)

# BLE専用スレッドのイベントループ
_ble_loop: asyncio.AbstractEventLoop | None = None
_ble_thread: threading.Thread | None = None
_ble_instance: "PavlokBLE | None" = None

# 接続直後のデバイス側準備待ち（秒）
_CONNECT_SETTLE_DELAY = 0.3

# 書き込みリトライ回数
_WRITE_RETRIES = 2

# 接続監視ループの確認間隔（秒）
_MONITOR_INTERVAL = 5.0


class PavlokBLE:
    """Pavlok 3 BLE直接制御クラス（接続監視 + 強制再接続方式）

    B: バックグラウンド監視ループで切断を即検知 → 自動再接続
    C: write失敗時は is_connected を信頼せず強制 disconnect → reconnect
    競合防止のため再接続処理は asyncio.Lock で排他制御する。
    """

    # check_api UUID（接続確認用）
    _C_API_UUID = "00001004-0000-1000-8000-00805f9b34fb"

    def __init__(self, mac: str, zap_uuid: str, vibe_uuid: str,
                 connect_timeout: float, reconnect_interval: float):
        self._mac = mac
        self._zap_uuid = zap_uuid
        self._vibe_uuid = vibe_uuid
        self._connect_timeout = connect_timeout
        self._reconnect_interval = reconnect_interval
        self._client: BleakClient | None = None
        self._should_stop = False
        self._reconnect_lock = asyncio.Lock()
        self._monitor_task: asyncio.Task | None = None

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    # ------------------------------------------------------------------ #
    # 接続・切断                                                           #
    # ------------------------------------------------------------------ #

    async def connect(self) -> bool:
        """Pavlok 3 に BLE 接続する。成功時 True を返す。

        毎回新しい BleakClient インスタンスを生成する（再接続安定化）。
        disconnected_callback は使用しない（WinRT 誤発火回避）。
        """
        if self._client is not None:
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._client = None

        try:
            self._client = BleakClient(self._mac, timeout=self._connect_timeout)
            await self._client.connect()

            await asyncio.sleep(_CONNECT_SETTLE_DELAY)

            if not self._client.is_connected:
                logger.error("BLE connect: client reported disconnected after settle")
                return False

            logger.info(f"BLE connected: {self._mac}")

            try:
                await self._client.write_gatt_char(
                    self._C_API_UUID, bytes([87, 84]), response=True
                )
            except Exception as e:
                logger.debug(f"check_api write skipped: {e}")

            return True

        except (BleakError, asyncio.TimeoutError, Exception) as e:
            logger.error(f"BLE connect failed: {e}")
            self._client = None
            return False

    async def start_monitor(self) -> None:
        """接続監視ループを開始する（B: バックグラウンドタスク）。"""
        self._monitor_task = asyncio.ensure_future(self._monitor_loop())

    async def disconnect(self) -> None:
        """BLE 接続を意図的に切断し、監視ループを停止する。"""
        self._should_stop = True

        if self._monitor_task is not None:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

        if self._client is not None:
            try:
                await self._client.disconnect()
            except Exception as e:
                logger.debug(f"BLE disconnect error (ignored): {e}")
            self._client = None

        logger.info("BLE disconnected")

    # ------------------------------------------------------------------ #
    # B: 接続監視ループ                                                    #
    # ------------------------------------------------------------------ #

    async def _monitor_loop(self) -> None:
        """定期的に接続状態を確認し、切断を検知したら即再接続する（B）。"""
        logger.debug("BLE monitor loop started")
        while not self._should_stop:
            await asyncio.sleep(_MONITOR_INTERVAL)
            if self._should_stop:
                break
            if not self.is_connected:
                logger.warning("BLE monitor: connection lost, reconnecting...")
                async with self._reconnect_lock:
                    # ロック取得後に再度確認（送信側が先に再接続済みの場合はスキップ）
                    if not self.is_connected and not self._should_stop:
                        await self._do_reconnect("monitor")
        logger.debug("BLE monitor loop stopped")

    # ------------------------------------------------------------------ #
    # 送信                                                                 #
    # ------------------------------------------------------------------ #

    async def send_zap(self, intensity: int) -> bool:
        """Zap コマンドを送信する。"""
        cmd = bytes([0x89, intensity])
        return await self._write_with_retry(self._zap_uuid, cmd, "Zap", intensity)

    async def send_vibration(self, intensity: int, count: int = 1, ton: int = 22, toff: int = 22) -> bool:
        """Vibration コマンドを送信する。"""
        count = max(1, min(127, int(count)))
        cmd = bytes([0x80 | count, 2, intensity, ton, toff])
        return await self._write_with_retry(self._vibe_uuid, cmd, "Vibration", intensity)

    # ------------------------------------------------------------------ #
    # 内部: 再接続・write                                                  #
    # ------------------------------------------------------------------ #

    async def _do_reconnect(self, caller: str) -> bool:
        """実際の再接続処理（ロック取得済みの状態で呼ぶこと）。"""
        for attempt in range(1, 4):
            if self._should_stop:
                return False
            logger.info(f"BLE reconnect [{caller}] attempt {attempt}/3...")
            if await self.connect():
                return True
            await asyncio.sleep(self._reconnect_interval)
        logger.error(f"BLE reconnect [{caller}] failed")
        return False

    async def _ensure_connected(self) -> bool:
        """接続されていなければロックを取得して再接続する。"""
        if self.is_connected:
            return True

        logger.warning("BLE not connected, acquiring lock for reconnect...")
        async with self._reconnect_lock:
            # ロック取得後に再確認（監視ループが先に回復済みの可能性）
            if self.is_connected:
                logger.info("BLE already reconnected by monitor, skipping")
                return True
            return await self._do_reconnect("ensure")

    async def _write_with_retry(self, uuid: str, cmd: bytes, label: str, intensity: int) -> bool:
        """接続確認 → GATT write。失敗時は強制再接続してリトライ（C）。

        write失敗時は is_connected を信頼せず、必ず強制 disconnect → reconnect する。
        """
        if not await self._ensure_connected():
            return False

        for attempt in range(1, _WRITE_RETRIES + 1):
            try:
                await self._client.write_gatt_char(uuid, cmd, response=True)
                logger.info(f"BLE {label} sent: intensity={intensity}")
                return True
            except Exception as e:
                logger.warning(f"BLE {label} write failed (attempt {attempt}/{_WRITE_RETRIES}): {e}")
                if attempt < _WRITE_RETRIES:
                    # C: is_connected を信頼せず強制再接続
                    logger.info("BLE forcing reconnect after write failure...")
                    async with self._reconnect_lock:
                        await self._do_reconnect("write-retry")

        logger.error(f"BLE {label} write failed after {_WRITE_RETRIES} attempts")
        return False


# ===== モジュールレベルの同期 API =====

def _run_ble_loop(loop: asyncio.AbstractEventLoop) -> None:
    """BLE 専用スレッドでイベントループを常駐させる。"""
    asyncio.set_event_loop(loop)
    loop.run_forever()


def ble_connect() -> bool:
    """BLE 専用スレッドを起動し、Pavlok 3 に接続・監視ループを開始する。"""
    global _ble_loop, _ble_thread, _ble_instance

    from config import (
        BLE_DEVICE_MAC, BLE_ZAP_UUID, BLE_VIBE_UUID,
        BLE_CONNECT_TIMEOUT, BLE_RECONNECT_INTERVAL
    )

    if not BLE_DEVICE_MAC:
        logger.error("BLE_DEVICE_MAC が設定されていません（.env を確認してください）")
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

    # 接続
    future = asyncio.run_coroutine_threadsafe(_ble_instance.connect(), _ble_loop)
    try:
        ok = future.result(timeout=BLE_CONNECT_TIMEOUT + 3)
    except Exception as e:
        logger.error(f"ble_connect timeout/error: {e}")
        return False

    if ok:
        # 接続成功後に監視ループを開始（B）
        asyncio.run_coroutine_threadsafe(_ble_instance.start_monitor(), _ble_loop)

    return ok


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
        return future.result(timeout=10)
    except Exception as e:
        logger.error(f"ble_send_zap error: {e}")
        return False


def ble_send_raw_vibe(cmd: bytes) -> bool:
    """同期ラッパー：生バイト列を c_vibe キャラクタリスティックに送信する（テスト用）。"""
    if not _ble_instance or not _ble_loop:
        logger.error("BLE未接続です。ble_connect() を先に呼んでください。")
        return False
    from config import BLE_VIBE_UUID
    future = asyncio.run_coroutine_threadsafe(
        _ble_instance._write_with_retry(BLE_VIBE_UUID, cmd, "RawVibe", cmd[2] if len(cmd) > 2 else 0),
        _ble_loop,
    )
    try:
        return future.result(timeout=10)
    except Exception as e:
        logger.error(f"ble_send_raw_vibe error: {e}")
        return False


def ble_send_vibration(intensity: int, count: int = 1, ton: int = 22, toff: int = 22) -> bool:
    """同期ラッパー：Vibration を送信する。"""
    if not _ble_instance or not _ble_loop:
        logger.error("BLE未接続です。ble_connect() を先に呼んでください。")
        return False
    future = asyncio.run_coroutine_threadsafe(
        _ble_instance.send_vibration(intensity, count, ton, toff), _ble_loop
    )
    try:
        return future.result(timeout=10)
    except Exception as e:
        logger.error(f"ble_send_vibration error: {e}")
        return False
