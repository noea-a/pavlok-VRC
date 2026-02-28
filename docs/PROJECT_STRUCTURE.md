# プロジェクト構成

## ディレクトリ構造

```
pavlok_VRC/
│
├── config/                        # 設定ファイル
│   ├── default.toml               # デフォルト設定（git 管理）
│   └── user.toml                  # ユーザー上書き設定（gitignore）
│
├── src/                           # ソースコード
│   ├── main.py                    # エントリポイント（デバイス・ハンドラの組み立て）
│   ├── settings.py                # TOML 読み込み・設定 dataclass・user.toml 保存
│   ├── config.py                  # 後方互換ラッパー（settings.py を再エクスポート）
│   ├── state_machine.py           # GrabStateMachine（純粋な状態遷移・イベント発行）
│   ├── intensity.py               # 強度計算純粋関数（IntensityConfig + calculate_intensity）
│   ├── pavlok_controller.py       # デバイスディスパッチャ＋強度計算ラッパー
│   ├── zap_recorder.py            # Zap 実行記録・統計管理（JSON 永続化）
│   │
│   ├── devices/                   # Pavlok デバイス抽象化
│   │   ├── base.py                # PavlokDevice Protocol 定義
│   │   ├── ble_device.py          # BLEDevice 実装（Pavlok 3 BLE 直接制御）
│   │   ├── api_device.py          # APIDevice 実装（Cloud API 経由）
│   │   └── factory.py             # CONTROL_MODE に応じたデバイス生成
│   │
│   ├── osc/                       # OSC 通信
│   │   ├── receiver.py            # OSCReceiver（VRChat からの受信専用）
│   │   └── sender.py              # OSCSender（VRChat Chatbox への送信専用）
│   │
│   ├── handlers/                  # イベントハンドラ群
│   │   ├── stimulus.py            # StimulusHandler（Pavlok 刺激送信）
│   │   ├── chatbox.py             # ChatboxHandler（Chatbox 送信・スロットル付き）
│   │   ├── recorder.py            # RecorderHandler（Zap 記録・テストモード除外）
│   │   └── gui_updater.py         # GUIUpdater（status_queue への状態プッシュ）
│   │
│   └── gui/                       # Tkinter GUI
│       ├── app.py                 # メインウィンドウ・タブ管理・キュー polling
│       ├── tab_dashboard.py       # リアルタイム状態表示
│       ├── tab_settings.py        # パラメータ編集・user.toml 保存
│       ├── tab_log.py             # ログ表示（レベル別カラー）
│       ├── tab_stats.py           # Zap 統計（セッション・累計）
│       └── tab_test.py            # 単体テスト・Grab シミュレーション・BLE 生コマンド
│
├── tests/                         # pytest テスト
│   └── test_intensity.py          # 強度計算の単体テスト（16テスト・外部依存なし）
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
├── REFACTORING_PLAN.md            # リファクタリング計画・進捗
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
| `main.py` | デバイス・ハンドラの組み立て、OSC 接続、GUI 起動 |
| `settings.py` | `config/default.toml` + `config/user.toml` + `.env` を読み込み、dataclass として提供 |
| `config.py` | 後方互換ラッパー。既存コードが `from config import X` で読めるよう settings を再エクスポート |
| `state_machine.py` | Grab 状態遷移のみ。subscribe_* でコールバック登録するイベント駆動設計 |
| `intensity.py` | 強度計算純粋関数。設定値を `IntensityConfig` で受け取るのでテストが容易 |
| `pavlok_controller.py` | デバイスへのディスパッチャ。`initialize_device()` で DI される |
| `zap_recorder.py` | Zap 実行を JSON に記録・セッション統計・累計統計 |

### src/devices/ - デバイス抽象化

| ファイル | 役割 |
|---|---|
| `base.py` | `PavlokDevice` Protocol 定義（connect / disconnect / send_zap / send_vibration） |
| `ble_device.py` | `BLEDevice` 実装。`_PavlokBLE`（asyncio）+ 同期ラッパー。接続監視・Keep-alive・強制再接続 |
| `api_device.py` | `APIDevice` 実装。Cloud API 経由（スマートフォンアプリが必要） |
| `factory.py` | `CONTROL_MODE` に応じて `BLEDevice` / `APIDevice` を生成。切り替えはここ1箇所のみ |

### src/osc/ - OSC 通信

| ファイル | 役割 |
|---|---|
| `receiver.py` | `OSCReceiver`。VRChat からの Stretch / IsGrabbed 等を受信し、コールバックに渡す |
| `sender.py` | `OSCSender`。VRChat Chatbox への文字列送信 |

### src/handlers/ - イベントハンドラ群

GrabStateMachine のイベントを購読して副作用を実行する。

| ファイル | 役割 |
|---|---|
| `stimulus.py` | Grab 開始/終了/閾値超過 → Pavlok へ刺激送信 |
| `chatbox.py` | Stretch 変化（スロットル付き）/ Grab 終了 → VRChat Chatbox に強度表示 |
| `recorder.py` | Grab 終了 → ZapRecorder に記録（テストモード・Vibe モード除外） |
| `gui_updater.py` | 状態変化 → status_queue に現在スナップショットをプッシュ |

### tests/ - テスト

| ファイル | 役割 |
|---|---|
| `test_intensity.py` | `intensity.py` の単体テスト（16テスト・外部依存なし、`pytest` で実行） |

---

## データフロー

```
VRChat (PhysBone Grab/Stretch)
   ↓ OSC パラメータ（UDP:9001）
osc/receiver.py (OSCReceiver)
   ↓ on_stretch_change / on_grabbed_change
state_machine.py (GrabStateMachine)
   ↓ イベント発行（subscribe_* で購読）
   ├─→ handlers/stimulus.py   → pavlok_controller → devices/ble_device.py
   ├─→ handlers/chatbox.py    → osc/sender.py → VRChat Chatbox
   ├─→ handlers/recorder.py   → zap_recorder.py → data/zap_records.json
   └─→ handlers/gui_updater.py → status_queue → gui/app.py → 各タブ
```

---

## 設定の優先順位

```
.env（秘密情報: BLE_DEVICE_MAC, PAVLOK_API_KEY）
   ↑ 上書き
config/user.toml（ユーザー調整値・gitignore）
   ↑ 上書き
config/default.toml（デフォルト値・git 管理）
```

GUI の設定タブで変更 → `config/user.toml` に保存（`config.py` は変更しない）。

---

## BLE 接続の仕組み

```
BLEDevice.connect()
   └─ 接続成功後に _PavlokBLE.start_monitor() を起動
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

# 起動
python src/main.py

# テスト実行
python -m pytest tests/
```

詳細は `README.md` を参照。
