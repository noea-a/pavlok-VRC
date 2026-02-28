"""
ble_controller.py - 後方互換ラッパー（Phase 6 で削除予定）

実装は src/devices/ble_device.py に移動済み。
"""

import logging
from devices.ble_device import BLEDevice

logger = logging.getLogger(__name__)

# モジュールレベルのデバイスインスタンス（旧 API 互換用）
_device: BLEDevice | None = None


def _get_device() -> BLEDevice:
    global _device
    if _device is None:
        raise RuntimeError("ble_connect() が呼ばれていません")
    return _device


def ble_connect() -> bool:
    """後方互換: BLEDevice を生成して接続する。"""
    global _device
    from config import (
        BLE_DEVICE_MAC, BLE_ZAP_UUID, BLE_VIBE_UUID,
        BLE_CONNECT_TIMEOUT, BLE_RECONNECT_INTERVAL, BLE_KEEPALIVE_INTERVAL,
    )
    _device = BLEDevice(
        mac=BLE_DEVICE_MAC,
        zap_uuid=BLE_ZAP_UUID,
        vibe_uuid=BLE_VIBE_UUID,
        connect_timeout=BLE_CONNECT_TIMEOUT,
        reconnect_interval=BLE_RECONNECT_INTERVAL,
        keepalive_interval=BLE_KEEPALIVE_INTERVAL,
    )
    return _device.connect()


def ble_disconnect() -> None:
    """後方互換: 切断する。"""
    if _device is not None:
        _device.disconnect()


def ble_send_zap(intensity: int) -> bool:
    """後方互換: Zap を送信する。"""
    return _get_device().send_zap(intensity)


def ble_send_vibration(intensity: int, count: int = 1, ton: int = 22, toff: int = 22) -> bool:
    """後方互換: Vibration を送信する。"""
    return _get_device().send_vibration(intensity, count, ton, toff)


def ble_send_raw_vibe(cmd: bytes) -> bool:
    """後方互換: 生コマンドを送信する（tab_test.py から呼ばれる）。"""
    return _get_device().send_raw_vibe(cmd)
