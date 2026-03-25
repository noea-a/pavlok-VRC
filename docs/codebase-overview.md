# コードベース概要

やりたいこと別のファイル参照ガイド。

---

## 設定・値

| やりたいこと | 見るファイル |
|---|---|
| 設定値のデフォルトを追加・変更する | `config/default.toml`（デフォルト値）→ `settings.py`（dataclass 定義） |
| 秘密情報（MAC アドレス・API キー）を変える | `.env` |
| バージョンを確認・変更する | `src/version.py` |

## 刺激制御

| やりたいこと | 見るファイル |
|---|---|
| Zap/Vibration の強度計算を変える | `src/intensity.py`（純粋関数） |
| Zap を実際に送信する処理を変える | `src/handlers/stimulus.py` + `src/pavlok_controller.py` |
| Grab 状態遷移のロジックを変える | `src/state_machine.py` |
| 速度ベース Zap の検出ロジックを変える | `src/handlers/speed_mode.py` |

## デバイス接続

| やりたいこと | 見るファイル |
|---|---|
| BLE/API を切り替える | `config/default.toml` の `[device] control_mode` |
| BLE 接続・再接続の挙動を変える | `src/devices/ble_device.py` |
| API 経由の送信を変える | `src/devices/api_device.py` |
| BLE UUID やコマンド形式を調べる | `docs/notes/ble-reference.md` |

## OSC・VRChat

| やりたいこと | 見るファイル |
|---|---|
| VRChat から受け取る OSC パラメータを変える | `src/osc/receiver.py` + `config/default.toml` の `[osc]` |
| VRChat Chatbox への通知を変える | `src/handlers/chatbox.py` + `src/osc/sender.py` |

## GUI

| やりたいこと | 見るファイル |
|---|---|
| GUI の表示内容を変える | `src/gui/tab_dashboard.py` / `tab_stats.py` / `tab_log.py` |
| GUI の設定タブの項目を増やす | `src/gui/tab_settings.py` + `settings.py` + `config/default.toml` |
| GUI のテスト送信を変える | `src/gui/tab_test.py` |

## データ・統計

| やりたいこと | 見るファイル |
|---|---|
| Zap 記録・統計を変える | `src/zap_recorder.py` + `src/handlers/recorder.py` |

## その他

`src/main.py`: アプリ起動・各コンポーネントの組み立て。
