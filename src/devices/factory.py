"""デバイスファクトリ

CONTROL_MODE の判定はここ1箇所のみ。
"""

from .base import PavlokDevice


def create_device() -> PavlokDevice:
    """設定に基づいて適切な PavlokDevice を生成して返す。"""
    import settings as s_mod
    cfg = s_mod.settings

    mode = cfg.device.control_mode

    if mode == "ble":
        from .ble_device import BLEDevice
        return BLEDevice(
            mac=cfg.ble.device_mac,
            zap_uuid=cfg.ble.zap_uuid,
            vibe_uuid=cfg.ble.vibe_uuid,
            connect_timeout=cfg.ble.connect_timeout,
            reconnect_interval=cfg.ble.reconnect_interval,
            keepalive_interval=cfg.ble.keepalive_interval,
        )

    if mode == "api":
        from .api_device import APIDevice
        return APIDevice(
            api_key=cfg.api.api_key,
            api_url=cfg.api.url,
            use_vibration=cfg.device.use_vibration,
        )

    raise ValueError(f"不明な CONTROL_MODE: {mode!r}（'ble' または 'api' を設定してください）")
