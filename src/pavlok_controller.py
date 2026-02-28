"""
pavlok_controller.py

デバイスへのディスパッチャ と 強度計算関数。
デバイスの初期化は main.py が行い、initialize_device() で登録する。
"""

import logging
from devices.base import PavlokDevice

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


# ===== 強度計算 =====

def normalize_intensity_for_display(stimulus_value: int) -> int:
    """Pavlok 内部値（MIN〜MAX）を表示用パーセント（MIN〜100）に変換する。"""
    from config import MIN_STIMULUS_VALUE, MAX_STIMULUS_VALUE
    if stimulus_value <= MIN_STIMULUS_VALUE:
        return MIN_STIMULUS_VALUE
    if stimulus_value >= MAX_STIMULUS_VALUE:
        return 100
    normalized = MIN_STIMULUS_VALUE + (
        (stimulus_value - MIN_STIMULUS_VALUE)
        / (MAX_STIMULUS_VALUE - MIN_STIMULUS_VALUE)
        * (100 - MIN_STIMULUS_VALUE)
    )
    return int(round(normalized))


def calculate_zap_intensity(stretch_value: float) -> int:
    """Stretch 値（0.0〜1.0）を刺激強度（内部値）に変換する（折れ線グラフ）。"""
    from config import (
        MIN_STRETCH_THRESHOLD, MIN_STRETCH_PLATEAU,
        MIN_STRETCH_FOR_CALC, MAX_STRETCH_FOR_CALC,
        NONLINEAR_SWITCH_POSITION_PERCENT, INTENSITY_AT_SWITCH_PERCENT,
        MIN_STIMULUS_VALUE, MAX_STIMULUS_VALUE,
    )

    if stretch_value < MIN_STRETCH_THRESHOLD:
        return 0
    if stretch_value <= MIN_STRETCH_PLATEAU:
        return MIN_STIMULUS_VALUE
    if stretch_value >= MAX_STRETCH_FOR_CALC:
        return MAX_STIMULUS_VALUE

    switch_stretch = MIN_STRETCH_PLATEAU + (
        NONLINEAR_SWITCH_POSITION_PERCENT / 100.0
    ) * (MAX_STRETCH_FOR_CALC - MIN_STRETCH_PLATEAU)

    intensity_at_switch = MIN_STIMULUS_VALUE + (
        INTENSITY_AT_SWITCH_PERCENT / 100.0
    ) * (MAX_STIMULUS_VALUE - MIN_STIMULUS_VALUE)

    if stretch_value <= switch_stretch:
        t = (stretch_value - MIN_STRETCH_PLATEAU) / (switch_stretch - MIN_STRETCH_PLATEAU)
        intensity = MIN_STIMULUS_VALUE + t * (intensity_at_switch - MIN_STIMULUS_VALUE)
    else:
        t = (stretch_value - switch_stretch) / (MAX_STRETCH_FOR_CALC - switch_stretch)
        intensity = intensity_at_switch + t * (MAX_STIMULUS_VALUE - intensity_at_switch)

    return int(max(MIN_STIMULUS_VALUE, min(MAX_STIMULUS_VALUE, intensity)))


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
