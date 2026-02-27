import requests
import logging
from config import (
    PAVLOK_API_URL, PAVLOK_API_KEY,
    MIN_STRETCH_THRESHOLD, MIN_STRETCH_PLATEAU, USE_VIBRATION,
    MIN_STIMULUS_VALUE, MAX_STIMULUS_VALUE,
    MIN_STRETCH_FOR_CALC, MAX_STRETCH_FOR_CALC,
    NONLINEAR_SWITCH_POSITION_PERCENT, INTENSITY_AT_SWITCH_PERCENT,
    CONTROL_MODE
)

logger = logging.getLogger(__name__)


def normalize_intensity_for_display(stimulus_value: int) -> int:
    """
    Pavlok刺激値（MIN_STIMULUS_VALUE～MAX_STIMULUS_VALUE）を表示値に変換

    MIN_STIMULUS_VALUE → MIN_STIMULUS_VALUE表示、MAX_STIMULUS_VALUE → 100表示

    Args:
        stimulus_value: MIN_STIMULUS_VALUE～MAX_STIMULUS_VALUE の値

    Returns:
        表示用の値（MIN_STIMULUS_VALUE～100）
    """
    if stimulus_value <= MIN_STIMULUS_VALUE:
        return MIN_STIMULUS_VALUE
    if stimulus_value >= MAX_STIMULUS_VALUE:
        return 100

    # 線形変換：MIN_STIMULUS_VALUE→MIN_STIMULUS_VALUE, MAX_STIMULUS_VALUE→100
    normalized = MIN_STIMULUS_VALUE + (stimulus_value - MIN_STIMULUS_VALUE) / (MAX_STIMULUS_VALUE - MIN_STIMULUS_VALUE) * (100 - MIN_STIMULUS_VALUE)
    return int(round(normalized))


def calculate_zap_intensity(stretch_value: float) -> int:
    """
    Stretch値（0.0～1.0）を刺激強度に変換（傾きの異なる2本直線）

    仕様：
    - Stretch < MIN_STRETCH_THRESHOLD: 強度0（刺激なし）
    - Stretch MIN_STRETCH_THRESHOLD～MIN_STRETCH_PLATEAU: MIN_STIMULUS_VALUE で固定
    - Stretch MIN_STRETCH_PLATEAU～MAX_STRETCH_FOR_CALC: 2本の直線で計算
      - 第1段階：MIN_STRETCH_PLATEAU から切り替え地点まで
      - 第2段階：切り替え地点から MAX_STRETCH_FOR_CALC まで
    - Stretch >= MAX_STRETCH_FOR_CALC: MAX_STIMULUS_VALUE
    """
    # MIN_STRETCH_THRESHOLD未満は刺激なし
    if stretch_value < MIN_STRETCH_THRESHOLD:
        return 0

    # MIN_STRETCH_PLATEAU以下は MIN_STIMULUS_VALUE で固定
    if stretch_value <= MIN_STRETCH_PLATEAU:
        return MIN_STIMULUS_VALUE

    # 入力範囲クランプ
    if stretch_value >= MAX_STRETCH_FOR_CALC:
        return MAX_STIMULUS_VALUE

    # 切り替え地点の Stretch 値を計算（MIN～MAX の何%地点か）
    switch_stretch = MIN_STRETCH_PLATEAU + (NONLINEAR_SWITCH_POSITION_PERCENT / 100.0) * (MAX_STRETCH_FOR_CALC - MIN_STRETCH_PLATEAU)

    # その地点での強度を計算（MIN～MAX の何%か）
    intensity_at_switch = MIN_STIMULUS_VALUE + (INTENSITY_AT_SWITCH_PERCENT / 100.0) * (MAX_STIMULUS_VALUE - MIN_STIMULUS_VALUE)

    # 傾きの異なる2本の直線で計算
    if stretch_value <= switch_stretch:
        # 線形1：MIN_STRETCH_PLATEAU～switch_stretch を MIN_STIMULUS_VALUE～intensity_at_switch に
        range_stretch_1 = switch_stretch - MIN_STRETCH_PLATEAU
        range_stimulus_1 = intensity_at_switch - MIN_STIMULUS_VALUE
        intensity = MIN_STIMULUS_VALUE + (stretch_value - MIN_STRETCH_PLATEAU) / range_stretch_1 * range_stimulus_1
    else:
        # 線形2：switch_stretch～MAX_STRETCH_FOR_CALC を intensity_at_switch～MAX_STIMULUS_VALUE に
        range_stretch_2 = MAX_STRETCH_FOR_CALC - switch_stretch
        range_stimulus_2 = MAX_STIMULUS_VALUE - intensity_at_switch
        intensity = intensity_at_switch + (stretch_value - switch_stretch) / range_stretch_2 * range_stimulus_2

    intensity = max(MIN_STIMULUS_VALUE, min(MAX_STIMULUS_VALUE, intensity))
    return int(intensity)


def _send_api_vibration(intensity: int) -> bool:
    """API経由でバイブレーションを送信する内部関数。"""
    stimulus_type = "vibe"

    payload = {
        "stimulus": {
            "stimulusType": stimulus_type,
            "stimulusValue": intensity
        }
    }
    headers = {
        "Authorization": f"Bearer {PAVLOK_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(PAVLOK_API_URL, json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            logger.info(f"Vibration sent successfully! Intensity: {intensity}")
            return True
        else:
            logger.error(f"Pavlok API error: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send {stimulus_type}: {e}")
        return False


def _send_api_zap(intensity: int) -> bool:
    """API経由でZap（またはVibe）を送信する内部関数。"""
    stimulus_type = "vibe" if USE_VIBRATION else "zap"

    payload = {
        "stimulus": {
            "stimulusType": stimulus_type,
            "stimulusValue": intensity
        }
    }
    headers = {
        "Authorization": f"Bearer {PAVLOK_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(PAVLOK_API_URL, json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            logger.info(f"{stimulus_type.capitalize()} sent successfully! Intensity: {intensity}")
            return True
        else:
            logger.error(f"Pavlok API error: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send {stimulus_type}: {e}")
        return False


def send_vibration(intensity: int) -> bool:
    """
    バイブレーションを送信する（API / BLE を CONTROL_MODE で切り替え）

    Args:
        intensity: 強度（MIN_STIMULUS_VALUE～MAX_STIMULUS_VALUE）

    Returns:
        成功した場合True、失敗した場合False
    """
    if intensity < MIN_STIMULUS_VALUE:
        logger.warning(f"Intensity too low ({intensity}), skipping vibration")
        return False
    if intensity > MAX_STIMULUS_VALUE:
        logger.warning(f"Intensity capped from {intensity} to {MAX_STIMULUS_VALUE}")
        intensity = MAX_STIMULUS_VALUE

    if CONTROL_MODE == "ble":
        from ble_controller import ble_send_vibration
        return ble_send_vibration(intensity)
    else:
        return _send_api_vibration(intensity)


def send_zap(intensity: int) -> bool:
    """
    Zapを送信する（API / BLE を CONTROL_MODE で切り替え、USE_VIBRATION も尊重）

    Args:
        intensity: 強度（MIN_STIMULUS_VALUE～MAX_STIMULUS_VALUE）

    Returns:
        成功した場合True、失敗した場合False
    """
    if intensity < MIN_STIMULUS_VALUE:
        logger.warning(f"Intensity too low ({intensity}), skipping zap")
        return False
    if intensity > MAX_STIMULUS_VALUE:
        logger.warning(f"Intensity capped from {intensity} to {MAX_STIMULUS_VALUE}")
        intensity = MAX_STIMULUS_VALUE

    if CONTROL_MODE == "ble":
        from ble_controller import ble_send_zap, ble_send_vibration
        if USE_VIBRATION:
            return ble_send_vibration(intensity)
        else:
            return ble_send_zap(intensity)
    else:
        return _send_api_zap(intensity)
