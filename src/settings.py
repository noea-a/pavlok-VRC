"""
設定管理モジュール

読み込み優先順位（後勝ち）:
  1. config/default.toml  （デフォルト値・git管理）
  2. config/user.toml     （ユーザー上書き・gitignore）
  3. .env                 （秘密情報: API KEY, MAC アドレス）

GUI からの設定変更は user.toml にのみ書き込む。
"""

import tomllib
import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

# .env を読み込む
load_dotenv()

# プロジェクトルート（src/ の一つ上）
_ROOT = Path(__file__).parent.parent
_DEFAULT_TOML = _ROOT / "config" / "default.toml"
_USER_TOML = _ROOT / "config" / "user.toml"


def _load_toml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def _deep_merge(base: dict, override: dict) -> dict:
    """override を base にマージ（ネストも対応）"""
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


@dataclass
class OscSendSettings:
    ip: str = "127.0.0.1"
    port: int = 9000
    chatbox_param: str = "/chatbox/input"
    interval: float = 1.5
    realtime_chatbox: bool = True
    final_chatbox: bool = True


@dataclass
class OscSettings:
    listen_port: int = 9001
    stretch_param: str = "/avatar/parameters/ShockPB_Stretch"
    is_grabbed_param: str = "/avatar/parameters/ShockPB_IsGrabbed"
    angle_param: str = "/avatar/parameters/ShockPB_Angle"
    is_posed_param: str = "/avatar/parameters/ShockPB_IsPosed"
    send: OscSendSettings = field(default_factory=OscSendSettings)


@dataclass
class DebugSettings:
    log_stretch: bool = True
    log_is_grabbed: bool = True
    log_angle: bool = False
    log_is_posed: bool = False
    log_all_osc: bool = False
    log_osc_send: bool = True
    log_to_file: bool = True


@dataclass
class LogicSettings:
    min_grab_duration: float = 0.8
    min_stretch_threshold: float = 0.03
    min_stretch_plateau: float = 0.12
    min_stretch_for_calc: float = 0.0
    max_stretch_for_calc: float = 0.8
    nonlinear_switch_position_percent: int = 50
    intensity_at_switch_percent: int = 20


@dataclass
class SpeedModeSettings:
    grab_settle_time: float = 0.08
    speed_onset_threshold: float = 1.0
    speed_onset_ticks: int = 5
    initial_speed_stretch_window: int = 50
    speed_zap_threshold: float = 1.5
    min_speed_eval_window: int = 90
    min_speed_threshold: float = 0.5
    speed_stop_threshold: float = 0.1
    speed_zap_hold_time: float = 0.3
    max_zap_duration: float = 1.0
    zap_reset_pullback: int = 30


@dataclass
class GrabStartVibrationSettings:
    intensity: int = 20
    count: int = 1
    ton: int = 10
    toff: int = 10


@dataclass
class StretchVibrationSettings:
    intensity: int = 80
    count: int = 2
    ton: int = 6
    toff: int = 12
    threshold: float = 0.7
    hysteresis_offset: float = 0.15


@dataclass
class DeviceSettings:
    control_mode: str = "ble"
    use_vibration: bool = False
    zap_mode: str = "stretch"  # "stretch" または "speed"
    min_stimulus_value: int = 15
    max_stimulus_value: int = 70


@dataclass
class BleSettings:
    device_mac: str = ""  # .env から読む
    connect_timeout: float = 30.0
    reconnect_interval: float = 5.0
    keepalive_interval: float = 5.5
    battery_refresh_interval: float = 180.0
    service_uuid: str = "156e5000-a300-4fea-897b-86f698d74461"
    zap_uuid: str = "00001003-0000-1000-8000-00805f9b34fb"
    vibe_uuid: str = "00001001-0000-1000-8000-00805f9b34fb"
    beep_uuid: str = "00001002-0000-1000-8000-00805f9b34fb"


@dataclass
class ApiSettings:
    api_key: str = ""  # .env から読む
    url: str = "https://api.pavlok.com/api/v5/stimulus/send"


@dataclass
class Settings:
    osc: OscSettings = field(default_factory=OscSettings)
    debug: DebugSettings = field(default_factory=DebugSettings)
    logic: LogicSettings = field(default_factory=LogicSettings)
    grab_start_vibration: GrabStartVibrationSettings = field(default_factory=GrabStartVibrationSettings)
    stretch_vibration: StretchVibrationSettings = field(default_factory=StretchVibrationSettings)
    device: DeviceSettings = field(default_factory=DeviceSettings)
    ble: BleSettings = field(default_factory=BleSettings)
    api: ApiSettings = field(default_factory=ApiSettings)
    speed_mode: SpeedModeSettings = field(default_factory=SpeedModeSettings)


def _apply_toml(settings: Settings, data: dict) -> None:
    """TOML の dict を Settings に適用する"""
    def _set(obj, keys: list, value):
        for k in keys[:-1]:
            obj = getattr(obj, k)
        setattr(obj, keys[-1], value)

    def _walk(obj, d: dict, path: list):
        for k, v in d.items():
            if isinstance(v, dict):
                sub = getattr(obj, k, None)
                if sub is not None:
                    _walk(sub, v, path + [k])
            else:
                if hasattr(obj, k):
                    setattr(obj, k, v)

    _walk(settings, data, [])


def _load() -> Settings:
    """設定を読み込んで Settings を返す"""
    default_data = _load_toml(_DEFAULT_TOML)
    user_data = _load_toml(_USER_TOML)
    merged = _deep_merge(default_data, user_data)

    s = Settings()
    _apply_toml(s, merged)

    # .env の秘密情報で上書き
    s.ble.device_mac = os.getenv("BLE_DEVICE_MAC", "")
    s.api.api_key = os.getenv("PAVLOK_API_KEY", "")

    return s


# モジュールロード時に一度だけ読み込む
settings = _load()


def reload() -> None:
    """設定を再読み込みする（GUI保存後などに呼ぶ）"""
    global settings
    settings = _load()


# ===== user.toml への保存 =====

# GUI から変更可能なキーとその TOML セクションのマッピング
_SAVEABLE_KEYS: dict[str, tuple[str, str]] = {
    # key: (section, field_name)
    "MIN_STIMULUS_VALUE":                 ("device", "min_stimulus_value"),
    "MAX_STIMULUS_VALUE":                 ("device", "max_stimulus_value"),
    "MIN_GRAB_DURATION":                  ("logic", "min_grab_duration"),
    "MIN_STRETCH_THRESHOLD":              ("logic", "min_stretch_threshold"),
    "VIBRATION_ON_STRETCH_THRESHOLD":     ("stretch_vibration", "threshold"),
    "VIBRATION_HYSTERESIS_OFFSET":        ("stretch_vibration", "hysteresis_offset"),
    "GRAB_START_VIBRATION_INTENSITY":     ("grab_start_vibration", "intensity"),
    "GRAB_START_VIBRATION_COUNT":         ("grab_start_vibration", "count"),
    "GRAB_START_VIBRATION_TON":           ("grab_start_vibration", "ton"),
    "GRAB_START_VIBRATION_TOFF":          ("grab_start_vibration", "toff"),
    "VIBRATION_ON_STRETCH_INTENSITY":     ("stretch_vibration", "intensity"),
    "VIBRATION_ON_STRETCH_COUNT":         ("stretch_vibration", "count"),
    "VIBRATION_ON_STRETCH_TON":           ("stretch_vibration", "ton"),
    "VIBRATION_ON_STRETCH_TOFF":          ("stretch_vibration", "toff"),
    "ZAP_MODE":                           ("device", "zap_mode"),
    "OSC_SEND_INTERVAL":                  ("osc.send", "interval"),
    "SEND_REALTIME_CHATBOX":              ("osc.send", "realtime_chatbox"),
    "SEND_FINAL_CHATBOX":                 ("osc.send", "final_chatbox"),
    # Speed モード設定
    "SPEED_GRAB_SETTLE_TIME":             ("speed_mode", "grab_settle_time"),
    "SPEED_ONSET_THRESHOLD":              ("speed_mode", "speed_onset_threshold"),
    "SPEED_ONSET_TICKS":                  ("speed_mode", "speed_onset_ticks"),
    "INITIAL_SPEED_STRETCH_WINDOW":       ("speed_mode", "initial_speed_stretch_window"),
    "SPEED_ZAP_THRESHOLD":                ("speed_mode", "speed_zap_threshold"),
    "MIN_SPEED_EVAL_WINDOW":              ("speed_mode", "min_speed_eval_window"),
    "MIN_SPEED_THRESHOLD":                ("speed_mode", "min_speed_threshold"),
    "SPEED_STOP_THRESHOLD":               ("speed_mode", "speed_stop_threshold"),
    "SPEED_ZAP_HOLD_TIME":                ("speed_mode", "speed_zap_hold_time"),
    "MAX_ZAP_DURATION":                   ("speed_mode", "max_zap_duration"),
    "ZAP_RESET_PULLBACK":                 ("speed_mode", "zap_reset_pullback"),
    # 詳細設定
    "BLE_CONNECT_TIMEOUT":               ("ble", "connect_timeout"),
    "BLE_RECONNECT_INTERVAL":            ("ble", "reconnect_interval"),
    "BLE_KEEPALIVE_INTERVAL":            ("ble", "keepalive_interval"),
    "BLE_BATTERY_REFRESH_INTERVAL":      ("ble", "battery_refresh_interval"),
    "OSC_LISTEN_PORT":                   ("osc", "listen_port"),
    "OSC_SEND_PORT":                     ("osc.send", "port"),
    "LOG_STRETCH":                       ("debug", "log_stretch"),
    "LOG_IS_GRABBED":                    ("debug", "log_is_grabbed"),
    "LOG_ANGLE":                         ("debug", "log_angle"),
    "LOG_IS_POSED":                      ("debug", "log_is_posed"),
    "LOG_OSC_SEND":                      ("debug", "log_osc_send"),
    "LOG_ALL_OSC":                       ("debug", "log_all_osc"),
    "LOG_TO_FILE":                       ("debug", "log_to_file"),
}


def save_user_settings(changed: dict) -> None:
    """
    変更された設定を user.toml に保存する。

    Args:
        changed: {CONFIG_KEY: new_value} の dict（config.py の変数名を使う）
    """
    # 現在の user.toml を読み込む（既存の上書き設定を保持）
    user_data: dict = {}
    if _USER_TOML.exists():
        with open(_USER_TOML, "rb") as f:
            user_data = tomllib.load(f)

    for config_key, new_value in changed.items():
        if config_key not in _SAVEABLE_KEYS:
            continue
        section, field_name = _SAVEABLE_KEYS[config_key]

        # ネストされたセクション（"osc.send" など）に対応
        parts = section.split(".")
        node = user_data
        for part in parts:
            node = node.setdefault(part, {})
        node[field_name] = new_value

    _write_toml(_USER_TOML, user_data)
    reload()


def _write_toml(path: Path, data: dict) -> None:
    """dict を TOML 形式でファイルに書き出す（シンプルな実装）"""
    lines = ["# user.toml - ユーザー設定上書き（自動生成）\n"]

    def _write_section(d: dict, prefix: str = "") -> list[str]:
        result = []
        nested = {}
        scalars = {}
        for k, v in d.items():
            if isinstance(v, dict):
                nested[k] = v
            else:
                scalars[k] = v

        for k, v in scalars.items():
            result.append(f"{k} = {_toml_value(v)}\n")

        for k, sub in nested.items():
            section_name = f"{prefix}.{k}" if prefix else k
            result.append(f"\n[{section_name}]\n")
            result.extend(_write_section(sub, section_name))

        return result

    lines.extend(_write_section(data))

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def _toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return f'"{v}"'
    return str(v)
