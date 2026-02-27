# プロジェクト構成

## ディレクトリ構造

```
pavlok_VRC/
│
├── src/                           # ソースコード
│   ├── main.py                    # メインループ・GrabState 管理
│   ├── config.py                  # 設定値（ユーザーが編集）
│   ├── osc_listener.py            # VRChat OSC 受信・Chatbox 送信
│   ├── pavlok_controller.py       # Pavlok 制御・強度計算（API/BLE 切り替え）
│   ├── ble_controller.py          # Pavlok BLE 直接制御
│   ├── zap_recorder.py            # Zap 実行記録・統計管理（JSON 永続化）
│   └── gui/                       # Tkinter GUI
│       ├── app.py                 # GUI エントリポイント・タブ管理
│       ├── tab_dashboard.py       # リアルタイム状態表示
│       ├── tab_settings.py        # config.py パラメータ編集・保存
│       ├── tab_log.py             # ログ表示（レベル別カラー）
│       ├── tab_stats.py           # Zap 統計（セッション・累計）
│       └── tab_test.py            # 単体テスト・Grab シミュレーション
│
├── tools/                         # 開発補助ツール
│   ├── generate_intensity_graph.py # 強度曲線グラフ生成
│   └── graphs/                    # グラフ出力先
│
├── data/                          # 自動生成データ
│   └── zap_records.json           # Zap 実行記録
│
├── docs/                          # ドキュメント
│   └── PROJECT_STRUCTURE.md       # このファイル
│
├── CLAUDE.md                      # 開発ガイド（Claude Code 向け）
├── README.md                      # プロジェクト概要
├── requirements.txt               # Python 依存パッケージ
├── pavlok_vrc.cmd                 # Windows 起動スクリプト
├── .env.example                   # 環境変数テンプレート
└── .env                           # 環境変数（非公開）
```

---

## ファイル説明

### src/ - ソースコード

| ファイル | 役割 |
|---|---|
| `main.py` | GrabState 管理、OSC イベント処理、刺激発動ロジック |
| `config.py` | 全設定値。ユーザーが直接編集するか GUI 設定タブから変更 |
| `osc_listener.py` | VRChat からの OSC 受信（UDP:9001）、Chatbox への強度表示送信 |
| `pavlok_controller.py` | 強度計算、API/BLE 切り替え送信、表示用正規化 |
| `ble_controller.py` | Pavlok BLE 直接制御（接続監視・Keep-alive・強制再接続） |
| `zap_recorder.py` | Zap 実行を JSON に記録・セッション統計・累計統計 |
| `gui/app.py` | Tkinter メインウィンドウ、タブ管理、キュー polling |
| `gui/tab_dashboard.py` | Grab 状態・Stretch・計算強度のリアルタイム表示 |
| `gui/tab_settings.py` | config.py パラメータの GUI 編集・保存 |
| `gui/tab_log.py` | ログストリーム表示（QueueHandler 経由） |
| `gui/tab_stats.py` | Zap 統計表示・記録リセット |
| `gui/tab_test.py` | 単体テスト（Vibration/Zap 直接送信）・Grab シミュ・BLE 生コマンド送信 |

### tools/ - ユーティリティ

| ファイル | 用途 |
|---|---|
| `generate_intensity_graph.py` | 強度計算カーブをグラフ化（`tools/graphs/` に PNG 出力） |

---

## データフロー

```
VRChat (PhysBone Grab/Stretch)
   ↓ OSC パラメータ（UDP:9001）
osc_listener.py
   ↓
main.py / GrabState
   ├─→ pavlok_controller.py → ble_controller.py（BLE 送信）
   │                        → Pavlok API（HTTP 送信）
   ├─→ zap_recorder.py（Zap 記録）
   ├─→ status_queue → gui/app.py → tab_dashboard.py（UI 更新）
   ├─→ log_queue    → gui/app.py → tab_log.py（ログ表示）
   └─→ osc_listener.py（VRChat Chatbox へ強度表示）
```

---

## BLE 接続の仕組み

```
ble_connect()
   └─ 接続成功後に start_monitor() を起動
         ├─ _monitor_loop: 5秒ごとに is_connected を確認 → 切断で自動再接続
         └─ _keepalive_loop: 5.5秒ごとに check_api へ ping（接続維持）

送信時（_write_with_retry）
   └─ write 失敗 → 強制 disconnect → reconnect → リトライ

排他制御: asyncio.Lock (_reconnect_lock) で競合防止
```

---

## セットアップ

```bash
pip install -r requirements.txt

# .env を作成
BLE_DEVICE_MAC=XX:XX:XX:XX:XX:XX   # BLE モード
PAVLOK_API_KEY=your_key             # API モード
```

詳細は `README.md` を参照。
