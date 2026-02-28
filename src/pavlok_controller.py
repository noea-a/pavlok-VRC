"""
pavlok_controller.py

デバイスへのディスパッチャ と 強度計算関数。
デバイスの初期化は main.py が行い、initialize_device() で登録する。
"""

import logging
from devices.base import PavlokDevice
from intensity import IntensityConfig, calculate_intensity, normalize_for_display

logger = logging.getLogger(__name__)

# モジュールレベルのデバイス参照（main.py が initialize_device() で設定）
_device: PavlokDevice | None = None


def initialize_device(device: PavlokDevice) -> None:
    """使用するデバイスを登録する。アプリ起動時に1回だけ呼ぶ。"""
    global _device
    _device = device


def _get_device() -> PavlokDevice:
    if _device is None:
        raise RuntimeError("デバイスが未初期化です。initialize_device() を先に呼んでください。")
    return _device


# ===== 強度計算（intensity.py への薄いラッパー）=====
# 既存コードが `from pavlok_controller import calculate_zap_intensity` で呼べるよう維持する。

def calculate_zap_intensity(stretch_value: float) -> int:
    """Stretch 値を刺激強度に変換する。設定は実行時に読み込む。"""
    return calculate_intensity(stretch_value, IntensityConfig.from_settings())


def normalize_intensity_for_display(stimulus_value: int) -> int:
    """内部強度値を表示用パーセントに変換する。設定は実行時に読み込む。"""
    return normalize_for_display(stimulus_value, IntensityConfig.from_settings())


# ===== デバイスへのディスパッチ =====

def send_vibration(intensity: int, count: int = 1, ton: int = 10, toff: int = 10) -> bool:
    """バイブレーションを送信する。"""
    from config import MIN_STIMULUS_VALUE, MAX_STIMULUS_VALUE
    if intensity < MIN_STIMULUS_VALUE:
        logger.warning(f"Intensity too low ({intensity}), skipping vibration")
        return False
    intensity = min(intensity, MAX_STIMULUS_VALUE)
    return _get_device().send_vibration(intensity, count, ton, toff)


def send_zap(intensity: int) -> bool:
    """Zap（または USE_VIBRATION=True の場合はバイブ）を送信する。"""
    from config import MIN_STIMULUS_VALUE, MAX_STIMULUS_VALUE, USE_VIBRATION
    if intensity < MIN_STIMULUS_VALUE:
        logger.warning(f"Intensity too low ({intensity}), skipping zap")
        return False
    intensity = min(intensity, MAX_STIMULUS_VALUE)
    device = _get_device()
    if USE_VIBRATION:
        return device.send_vibration(intensity)
    return device.send_zap(intensity)


def send_raw_vibe(cmd: bytes) -> bool:
    """BLE 生コマンドを送信する（テストタブ専用・BLE モードのみ有効）。"""
    from devices.ble_device import BLEDevice
    device = _get_device()
    if isinstance(device, BLEDevice):
        return device.send_raw_vibe(cmd)
    logger.warning("send_raw_vibe: BLE モードでないため無視します")
    return False
