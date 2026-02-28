"""
config.py - 後方互換ラッパー

既存コードが `from config import X` で読めるように、
settings.py の値をフラットな変数として再エクスポートする。
設定値の変更・保存は settings.py 経由で行うこと。
"""

from settings import settings as _s

# ===== Pavlok認証 =====
PAVLOK_API_KEY = _s.api.api_key

# ===== OSC設定 =====
LISTEN_PORT = _s.osc.listen_port
OSC_STRETCH_PARAM = _s.osc.stretch_param
OSC_IS_GRABBED_PARAM = _s.osc.is_grabbed_param
OSC_ANGLE_PARAM = _s.osc.angle_param
OSC_IS_POSED_PARAM = _s.osc.is_posed_param

# ===== デバッグログ設定 =====
DEBUG_LOG_STRETCH = _s.debug.log_stretch
DEBUG_LOG_IS_GRABBED = _s.debug.log_is_grabbed
DEBUG_LOG_ANGLE = _s.debug.log_angle
DEBUG_LOG_IS_POSED = _s.debug.log_is_posed
DEBUG_LOG_ALL_OSC = _s.debug.log_all_osc
DEBUG_LOG_OSC_SEND = _s.debug.log_osc_send

# ===== ロジック設定 =====
MIN_GRAB_DURATION = _s.logic.min_grab_duration
MIN_STRETCH_THRESHOLD = _s.logic.min_stretch_threshold
MIN_STRETCH_PLATEAU = _s.logic.min_stretch_plateau
MIN_STRETCH_FOR_CALC = _s.logic.min_stretch_for_calc
MAX_STRETCH_FOR_CALC = _s.logic.max_stretch_for_calc
NONLINEAR_SWITCH_POSITION_PERCENT = _s.logic.nonlinear_switch_position_percent
INTENSITY_AT_SWITCH_PERCENT = _s.logic.intensity_at_switch_percent

# ===== Grab開始バイブ設定 =====
GRAB_START_VIBRATION_INTENSITY = _s.grab_start_vibration.intensity
GRAB_START_VIBRATION_COUNT = _s.grab_start_vibration.count
GRAB_START_VIBRATION_TON = _s.grab_start_vibration.ton
GRAB_START_VIBRATION_TOFF = _s.grab_start_vibration.toff

# ===== Stretch超過バイブ設定 =====
VIBRATION_ON_STRETCH_INTENSITY = _s.stretch_vibration.intensity
VIBRATION_ON_STRETCH_COUNT = _s.stretch_vibration.count
VIBRATION_ON_STRETCH_TON = _s.stretch_vibration.ton
VIBRATION_ON_STRETCH_TOFF = _s.stretch_vibration.toff
VIBRATION_HYSTERESIS_OFFSET = _s.stretch_vibration.hysteresis_offset
VIBRATION_ON_STRETCH_THRESHOLD = _s.stretch_vibration.threshold

# ===== 制御モード =====
CONTROL_MODE = _s.device.control_mode

# ===== BLE設定 =====
BLE_DEVICE_MAC = _s.ble.device_mac
BLE_CONNECT_TIMEOUT = _s.ble.connect_timeout
BLE_RECONNECT_INTERVAL = _s.ble.reconnect_interval
BLE_KEEPALIVE_INTERVAL = _s.ble.keepalive_interval
BLE_SERVICE_UUID = _s.ble.service_uuid
BLE_ZAP_UUID = _s.ble.zap_uuid
BLE_VIBE_UUID = _s.ble.vibe_uuid
BLE_BEEP_UUID = _s.ble.beep_uuid

# ===== Pavlok API設定 =====
PAVLOK_API_URL = _s.api.url
USE_VIBRATION = _s.device.use_vibration
MIN_STIMULUS_VALUE = _s.device.min_stimulus_value
MAX_STIMULUS_VALUE = _s.device.max_stimulus_value

# ===== OSC送信設定 =====
OSC_SEND_IP = _s.osc.send.ip
OSC_SEND_PORT = _s.osc.send.port
OSC_CHATBOX_PARAM = _s.osc.send.chatbox_param
OSC_SEND_INTERVAL = _s.osc.send.interval
SEND_REALTIME_CHATBOX = _s.osc.send.realtime_chatbox

# ===== 起動時バリデーション =====
if CONTROL_MODE == "api" and not PAVLOK_API_KEY:
    raise ValueError("PAVLOK_API_KEY is not set in .env file")
if CONTROL_MODE == "ble" and not BLE_DEVICE_MAC:
    raise ValueError("BLE_DEVICE_MAC is not set in .env file")
