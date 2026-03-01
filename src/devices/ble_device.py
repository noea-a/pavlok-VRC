"""BLE デバイス実装（Pavlok 3 直接制御）"""

import asyncio
import logging
import threading
import time
from bleak import BleakClient, BleakError, BleakScanner

logger = logging.getLogger(__name__)

# 接続直後のデバイス側準備待ち（秒）
_CONNECT_SETTLE_DELAY = 1.0
# 書き込みリトライ回数
_WRITE_RETRIES = 2
# 接続監視ループの確認間隔（秒）
_MONITOR_INTERVAL = 5.0
# Keep-alive ping コマンド（check_api への書き込み）
_KEEPALIVE_CMD = bytes([87, 84])


class _PavlokBLE:
    """Pavlok 3 BLE 直接制御クラス（接続監視 + 強制再接続方式）。

    - バックグラウンド監視ループで切断を即検知 → 自動再接続
    - write 失敗時は is_connected を信頼せず強制 disconnect → reconnect
    - 競合防止のため再接続処理は asyncio.Lock で排他制御
    """

    _C_API_UUID  = "00007999-0000-1000-8000-00805f9b34fb"  # c_api UUID
    _C_BATT_UUID = "00002a19-0000-1000-8000-00805f9b34fb"  # 標準 BLE Battery Level

    def __init__(self, mac: str, zap_uuid: str, vibe_uuid: str,
                 connect_timeout: float, reconnect_interval: float,
                 keepalive_interval: float):
        self._mac = mac
        self._zap_uuid = zap_uuid
        self._vibe_uuid = vibe_uuid
        self._connect_timeout = connect_timeout
        self._reconnect_interval = reconnect_interval
        self._keepalive_interval = keepalive_interval
        self._client: BleakClient | None = None
        self._should_stop = False
        self._reconnect_lock = asyncio.Lock()
        self._monitor_task: asyncio.Task | None = None
        self._keepalive_task: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None  # BLEDevice から設定
        self._reconnecting: bool = False  # connect() 実行中フラグ

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    # ------------------------------------------------------------------ #
    # 接続・切断                                                           #
    # ------------------------------------------------------------------ #

    async def connect(self) -> bool:
        self._reconnecting = True
        try:
            if self._client is not None:
                try:
                    await self._client.disconnect()
                except Exception:
                    pass
                self._client = None
                # 前セッションの BT スタック解放を待つ
                await asyncio.sleep(2.0)

            try:
                # Windows の WinRT バックエンドは MAC 直指定で "Device not found" になりやすいため
                # 先にスキャンしてデバイスを発見してから接続する
                scan_timeout = min(self._connect_timeout * 0.6, 20.0)
                logger.info(f"BLE scanning for {self._mac} (timeout={scan_timeout:.0f}s)...")
                device = await BleakScanner.find_device_by_address(self._mac, timeout=scan_timeout)
                if device is None:
                    logger.error(f"BLE scan: device not found: {self._mac}")
                    return False

                logger.info(f"BLE device found: {device.name}, connecting...")
                # スキャン直後は即接続せず少し待機（Pavlok 側の準備を待つ）
                await asyncio.sleep(1.0)
                self._client = BleakClient(
                    device,
                    timeout=self._connect_timeout,
                    disconnected_callback=self._on_disconnected,
                )
                await self._client.connect(dangerous_use_bleak_cache=False)
                await asyncio.sleep(_CONNECT_SETTLE_DELAY)

                if not self._client.is_connected:
                    logger.error("BLE connect: client reported disconnected after settle")
                    return False

                logger.info(f"BLE connected: {self._mac}")

                try:
                    await self._client.write_gatt_char(self._C_API_UUID, bytes([87, 84]), response=True)
                except Exception as e:
                    logger.debug(f"check_api write skipped: {e}")

                return True

            except (BleakError, asyncio.TimeoutError, Exception) as e:
                logger.error(f"BLE connect failed: [{type(e).__name__}] {e!r}")
                self._client = None
                return False

        finally:
            self._reconnecting = False

    def _on_disconnected(self, client: BleakClient) -> None:
        """BLE 切断検知コールバック（WinRT スレッドから呼ばれる）。
        ポーリング待ちなしに即座に再接続をスケジュールする。
        """
        if self._should_stop:
            return
        if self._reconnecting:
            # connect() 実行中の内部切断（クリーンアップや失敗）なので無視
            logger.debug("BLE _on_disconnected ignored: connect in progress")
            return
        logger.warning("BLE unexpected disconnect detected (callback)")
        loop = self._loop
        if loop and not loop.is_closed():
            asyncio.run_coroutine_threadsafe(self._reconnect_from_callback(), loop)

    async def _reconnect_from_callback(self) -> None:
        # 既に再接続中なら追加のコールバック再接続をスキップ
        if self._reconnect_lock.locked():
            logger.debug("BLE reconnect already in progress, skipping callback reconnect")
            return
        # デバイス側 BT スタックの安定を待つ
        await asyncio.sleep(1.0)
        async with self._reconnect_lock:
            if not self.is_connected and not self._should_stop:
                await self._do_reconnect("disconnect-cb")

    async def start_monitor(self) -> None:
        self._monitor_task = asyncio.ensure_future(self._monitor_loop())
        self._keepalive_task = asyncio.ensure_future(self._keepalive_loop())

    async def disconnect(self) -> None:
        self._should_stop = True
        for task in (self._monitor_task, self._keepalive_task):
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._monitor_task = None
        self._keepalive_task = None

        if self._client is not None:
            try:
                await self._client.disconnect()
            except Exception as e:
                logger.debug(f"BLE disconnect error (ignored): {e}")
            self._client = None

        logger.info("BLE disconnected")

    # ------------------------------------------------------------------ #
    # 接続監視・Keep-alive                                                 #
    # ------------------------------------------------------------------ #

    async def _monitor_loop(self) -> None:
        logger.debug("BLE monitor loop started")
        while not self._should_stop:
            await asyncio.sleep(_MONITOR_INTERVAL)
            if self._should_stop:
                break
            if not self.is_connected:
                logger.warning("BLE monitor: connection lost, reconnecting...")
                async with self._reconnect_lock:
                    if not self.is_connected and not self._should_stop:
                        await self._do_reconnect("monitor")
        logger.debug("BLE monitor loop stopped")

    async def _keepalive_loop(self) -> None:
        logger.debug("BLE keepalive loop started")
        while not self._should_stop:
            await asyncio.sleep(self._keepalive_interval)
            if self._should_stop:
                break
            if not self.is_connected:
                continue
            try:
                await self._client.write_gatt_char(self._C_API_UUID, _KEEPALIVE_CMD, response=True)
                logger.debug("BLE keepalive ping sent")
            except Exception as e:
                logger.warning(f"BLE keepalive ping failed: [{type(e).__name__}] {e!r}")
        logger.debug("BLE keepalive loop stopped")

    # ------------------------------------------------------------------ #
    # 送信                                                                 #
    # ------------------------------------------------------------------ #

    async def read_battery(self) -> int | None:
        """バッテリー残量を 0-100 で返す。取得失敗時は None。"""
        if not self.is_connected:
            return None
        try:
            data = await self._client.read_gatt_char(self._C_BATT_UUID)
            return data[0]
        except Exception as e:
            logger.debug(f"BLE battery read failed: {e}")
            return None

    async def send_zap(self, intensity: int) -> bool:
        cmd = bytes([0x89, intensity])
        return await self._write_with_retry(self._zap_uuid, cmd, "Zap", intensity)

    async def send_vibration(self, intensity: int, count: int = 1, ton: int = 22, toff: int = 22) -> bool:
        count = max(1, min(127, int(count)))
        cmd = bytes([0x80 | count, 2, intensity, ton, toff])
        return await self._write_with_retry(self._vibe_uuid, cmd, "Vibration", intensity)

    async def send_raw_vibe(self, cmd: bytes) -> bool:
        return await self._write_with_retry(self._vibe_uuid, cmd, "RawVibe",
                                            cmd[2] if len(cmd) > 2 else 0)

    # ------------------------------------------------------------------ #
    # 内部: 再接続・write                                                  #
    # ------------------------------------------------------------------ #

    async def _do_reconnect(self, caller: str) -> bool:
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
        if self.is_connected:
            return True
        # 再接続中（ロック保持中）なら待たずに失敗を返す（モニターに任せる）
        if self._reconnect_lock.locked():
            logger.warning("BLE reconnecting in progress, skipping send")
            return False
        logger.warning("BLE not connected, acquiring lock for reconnect...")
        async with self._reconnect_lock:
            if self.is_connected:
                return True
            return await self._do_reconnect("ensure")

    async def _write_with_retry(self, uuid: str, cmd: bytes, label: str, intensity: int) -> bool:
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
                    logger.info("BLE forcing reconnect after write failure...")
                    async with self._reconnect_lock:
                        if not await self._do_reconnect("write-retry"):
                            break

        logger.error(f"BLE {label} write failed after {_WRITE_RETRIES} attempts")
        return False


# ================================================================== #
# BLEDevice: PavlokDevice Protocol に準拠した同期ラッパー             #
# ================================================================== #

class BLEDevice:
    """BLE 経由の Pavlok デバイス。PavlokDevice Protocol に準拠。"""

    def __init__(self, mac: str, zap_uuid: str, vibe_uuid: str,
                 connect_timeout: float, reconnect_interval: float,
                 keepalive_interval: float):
        self._mac = mac
        self._zap_uuid = zap_uuid
        self._vibe_uuid = vibe_uuid
        self._connect_timeout = connect_timeout
        self._reconnect_interval = reconnect_interval
        self._keepalive_interval = keepalive_interval
        self._ble: _PavlokBLE | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    def _start_loop(self) -> None:
        """イベントループを起動する。既に動作中なら何もしない（冪等）。"""
        if self._loop is not None and not self._loop.is_closed():
            return
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, args=(self._loop,), daemon=True)
        self._thread.start()

    @staticmethod
    def _run_loop(loop: asyncio.AbstractEventLoop) -> None:
        asyncio.set_event_loop(loop)
        loop.run_forever()

    def _run_coro(self, coro, timeout: float = 10):
        if self._loop is None:
            raise RuntimeError("BLE loop not started")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    # ------------------------------------------------------------------ #
    # PavlokDevice インターフェース                                        #
    # ------------------------------------------------------------------ #

    @property
    def is_connected(self) -> bool:
        return self._ble is not None and self._ble.is_connected

    def connect(self) -> bool:
        if not self._mac:
            logger.error("BLE_DEVICE_MAC が設定されていません（.env を確認してください）")
            return False

        self._start_loop()

        # _PavlokBLE インスタンスは初回のみ生成（ループと同じライフサイクル）
        if self._ble is None:
            self._ble = _PavlokBLE(
                mac=self._mac,
                zap_uuid=self._zap_uuid,
                vibe_uuid=self._vibe_uuid,
                connect_timeout=self._connect_timeout,
                reconnect_interval=self._reconnect_interval,
                keepalive_interval=self._keepalive_interval,
            )
            self._ble._loop = self._loop

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            logger.info(f"BLE 接続試行 {attempt}/{max_attempts}...")
            try:
                # scan (最大 connect_timeout*0.6) + GATT接続 (connect_timeout) + バッファ
                coro_timeout = self._connect_timeout * 1.7 + 3
                ok = self._run_coro(self._ble.connect(), timeout=coro_timeout)
            except Exception as e:
                logger.error(f"BLEDevice.connect error (attempt {attempt}): {e}")
                ok = False

            if ok:
                # モニタータスクが未起動 or 終了済みの場合のみ起動
                if self._ble._monitor_task is None or self._ble._monitor_task.done():
                    asyncio.run_coroutine_threadsafe(self._ble.start_monitor(), self._loop)
                return True

            if attempt < max_attempts:
                logger.info(f"BLE 接続失敗、{self._reconnect_interval:.0f}秒後に再試行...")
                time.sleep(self._reconnect_interval)

        logger.error(f"BLE 接続失敗（{max_attempts}回試行）")
        return False

    def disconnect(self) -> None:
        if self._ble and self._loop:
            try:
                self._run_coro(self._ble.disconnect(), timeout=5)
            except Exception:
                pass
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

    def send_zap(self, intensity: int) -> bool:
        if not self._ble or not self._loop:
            logger.error("BLE未接続です。connect() を先に呼んでください。")
            return False
        try:
            return self._run_coro(self._ble.send_zap(intensity))
        except Exception as e:
            logger.error(f"BLEDevice.send_zap error: {e}")
            return False

    def send_vibration(self, intensity: int, count: int = 1, ton: int = 10, toff: int = 10) -> bool:
        if not self._ble or not self._loop:
            logger.error("BLE未接続です。connect() を先に呼んでください。")
            return False
        try:
            return self._run_coro(self._ble.send_vibration(intensity, count, ton, toff))
        except Exception as e:
            logger.error(f"BLEDevice.send_vibration error: {e}")
            return False

    def read_battery(self) -> int | None:
        """バッテリー残量を 0-100 で返す。取得失敗時は None。"""
        if not self._ble or not self._loop:
            return None
        try:
            return self._run_coro(self._ble.read_battery(), timeout=5)
        except Exception as e:
            logger.debug(f"BLEDevice.read_battery error: {e}")
            return None

    def send_raw_vibe(self, cmd: bytes) -> bool:
        """テスト用：生バイト列を c_vibe キャラクタリスティックに送信する。"""
        if not self._ble or not self._loop:
            logger.error("BLE未接続です。connect() を先に呼んでください。")
            return False
        try:
            return self._run_coro(self._ble.send_raw_vibe(cmd))
        except Exception as e:
            logger.error(f"BLEDevice.send_raw_vibe error: {e}")
            return False
