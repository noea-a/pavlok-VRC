import os
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

# ===== Pavlok認証 =====
PAVLOK_API_KEY = os.getenv("PAVLOK_API_KEY", "")

# ===== OSC設定 =====
LISTEN_PORT = 9001
OSC_STRETCH_PARAM = "/avatar/parameters/ShockPB_Stretch"
OSC_IS_GRABBED_PARAM = "/avatar/parameters/ShockPB_IsGrabbed"
OSC_ANGLE_PARAM = "/avatar/parameters/ShockPB_Angle"
OSC_IS_POSED_PARAM = "/avatar/parameters/ShockPB_IsPosed"

# ===== デバッグログ設定 =====
DEBUG_LOG_STRETCH = True   # Chatbox デバッグ用（一時的に有効）
DEBUG_LOG_IS_GRABBED = True
DEBUG_LOG_ANGLE = False
DEBUG_LOG_IS_POSED = False
DEBUG_LOG_ALL_OSC = False  # すべてのOSCメッセージをログ出力
DEBUG_LOG_OSC_SEND = True  # OSC送信メッセージをログ出力

# ===== ロジック設定 =====
MIN_GRAB_DURATION = 0.8  # 秒
MIN_STRETCH_THRESHOLD = 0.03  # Stretch値の下限
MIN_STRETCH_PLATEAU = 0.12  # Stretch MIN_STRETCH_THRESHOLD～0.12 では MIN_STIMULUS_VALUE で固定
MIN_STRETCH_FOR_CALC = 0.0  # 計算用Stretch入力範囲の下限（0～0.8に正規化）
MAX_STRETCH_FOR_CALC = 0.8  # 計算用Stretch入力範囲の上限（0～0.8に正規化）

# ===== 傾きの切り替わり設定（MIN_STRETCH_PLATEAU～MAX_STRETCH_FOR_CALC の中での位置） =====
NONLINEAR_SWITCH_POSITION_PERCENT = 50  # 切り替え位置（MIN～MAXの%）
INTENSITY_AT_SWITCH_PERCENT = 20  # その地点での強度（MIN_STIMULUS_VALUE～MAX_STIMULUS_VALUE の%）

# ===== Grab開始バイブ設定 =====
GRAB_START_VIBRATION_INTENSITY = 20  # 強度（0～100）
GRAB_START_VIBRATION_COUNT = 1       # 反復回数（1～127）
GRAB_START_VIBRATION_TON = 10        # ON 時間（0～255）
GRAB_START_VIBRATION_TOFF = 10       # OFF 時間（0～255）

# ===== Stretch超過バイブ設定 =====
VIBRATION_ON_STRETCH_INTENSITY = 80  # 強度（0～100）
VIBRATION_ON_STRETCH_COUNT = 2       # 反復回数（1～127）
VIBRATION_ON_STRETCH_TON = 6         # ON 時間（0～255）
VIBRATION_ON_STRETCH_TOFF = 12       # OFF 時間（0～255）
VIBRATION_HYSTERESIS_OFFSET = 0.15   # 発動閾値からのオフセット（解除 = 閾値 - オフセット）
VIBRATION_ON_STRETCH_THRESHOLD = 0.7 # Stretch値の上限閾値（0～1）

# ===== 制御モード =====
CONTROL_MODE = "ble"  # "api" or "ble"

# ===== BLE設定（CONTROL_MODE = "ble" のとき使用） =====
BLE_DEVICE_MAC = os.getenv("BLE_DEVICE_MAC", "")  # .env に設定（デバイス固有値）
BLE_CONNECT_TIMEOUT = 30.0          # 接続タイムアウト（秒）
BLE_RECONNECT_INTERVAL = 5.0        # 再接続間隔（秒）
BLE_KEEPALIVE_INTERVAL = 5.5        # Keep-alive 送信間隔（秒）。Windows supervision timeout (~6秒) より短く設定

# BLE UUID（Pavlok 3 確定値）
BLE_SERVICE_UUID = "156e5000-a300-4fea-897b-86f698d74461"
BLE_ZAP_UUID     = "00001003-0000-1000-8000-00805f9b34fb"
BLE_VIBE_UUID    = "00001001-0000-1000-8000-00805f9b34fb"
BLE_BEEP_UUID    = "00001002-0000-1000-8000-00805f9b34fb"

# ===== Pavlok API設定 =====
PAVLOK_API_URL = "https://api.pavlok.com/api/v5/stimulus/send"
USE_VIBRATION = False        # True: バイブレーション, False: Zap（電気刺激）
MIN_STIMULUS_VALUE = 15      # 出力の最小値
MAX_STIMULUS_VALUE = 70      # 出力の最大値

# ===== OSC送信設定（VRChatへのChatbox出力） =====
OSC_SEND_IP = "127.0.0.1"           # VRChat OSC受信IP
OSC_SEND_PORT = 9000                # VRChat OSC受信ポート（標準）
OSC_CHATBOX_PARAM = "/chatbox/input"  # Chatboxパラメータ
OSC_SEND_INTERVAL = 1.5             # Chatbox送信間隔（秒）
SEND_REALTIME_CHATBOX = True        # リアルタイム Chatbox 送信（True=有効, False=最終送信のみ）

if CONTROL_MODE == "api" and not PAVLOK_API_KEY:
    raise ValueError("PAVLOK_API_KEY is not set in .env file")
if CONTROL_MODE == "ble" and not BLE_DEVICE_MAC:
    raise ValueError("BLE_DEVICE_MAC is not set in .env file")
