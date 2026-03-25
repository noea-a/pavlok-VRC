# コードベース概要

やりたいこと別のファイル参照ガイド。

---

| やりたいこと | 見るファイル |
|-------------|-------------|
| **設定値を追加・変更する** | `config/default.toml`（デフォルト値）→ `settings.py`（dataclass定義） |
| **BLE UUIDやコマンド形式を調べる** | `docs/notes/ble-reference.md` |
| **秘密情報（MACアドレス・APIキー）を変える** | `.env` |
| **Grab状態遷移のロジックを変える** | `src/state_machine.py` |
| **Zap/Vibrationの強度計算を変える** | `src/intensity.py`（純粋関数） |
| **Zapを実際に送信する処理を変える** | `src/handlers/stimulus.py` + `src/pavlok_controller.py` |
| **BLE接続・再接続の挙動を変える** | `src/devices/ble_device.py` |
| **API経由の送信を変える** | `src/devices/api_device.py` |
| **BLE/API を切り替える** | `config/default.toml` の `[device] control_mode` |
| **VRChat から受け取るOSCパラメータを変える** | `src/osc/receiver.py` + `config/default.toml` の `[osc]` |
| **VRChat Chatbox への通知を変える** | `src/handlers/chatbox.py` + `src/osc/sender.py` |
| **速度ベースZapの検出ロジックを変える** | `src/handlers/speed_mode.py` |
| **Zap記録・統計を変える** | `src/zap_recorder.py` + `src/handlers/recorder.py` |
| **GUIの表示内容を変える** | `src/gui/tab_dashboard.py` / `tab_stats.py` / `tab_log.py` |
| **GUIの設定タブの項目を増やす** | `src/gui/tab_settings.py` + `settings.py` + `config/default.toml` |
| **GUIのテスト送信を変える** | `src/gui/tab_test.py` |
| **アプリ起動・各コンポーネントの組み立て** | `src/main.py` |
| **バージョンを確認・変更する** | `src/version.py` |
