# VRChat Pavlok Connector

VRChat内のPhysBoneを他プレイヤーが掴んで伸ばすと、Pavlok（電撃デバイス）が発動するシステムです。

---

## プロジェクト構造

```
pavlok_VRC/
├── src/                           # ソースコード
│   ├── main.py                    # メインロジック（GrabState管理）
│   ├── config.py                  # 設定（ユーザーが編集）
│   ├── osc_listener.py            # VRChat OSC 受信・Chatbox 送信
│   ├── pavlok_controller.py       # Pavlok 制御・強度計算
│   ├── ble_controller.py          # Pavlok BLE 直接制御
│   ├── zap_recorder.py            # Zap 実行記録・統計（JSON）
│   └── gui/                       # Tkinter GUI ダッシュボード
│       ├── app.py                 # GUI エントリポイント
│       ├── tab_dashboard.py       # ダッシュボードタブ
│       ├── tab_settings.py        # 設定タブ
│       ├── tab_log.py             # ログタブ
│       ├── tab_stats.py           # 統計タブ
│       └── tab_test.py            # テストタブ（単体テスト・Grab シミュ）
│
├── tools/                         # 開発補助ツール
│   ├── generate_intensity_graph.py # Zap強度グラフ生成
│   └── graphs/                    # グラフ出力先
│
├── data/                          # 自動生成データ
│   └── zap_records.json           # Zap 実行記録
│
├── docs/                          # ドキュメント
├── requirements.txt               # 依存ライブラリ
├── .env.example                   # 環境変数テンプレート
├── .env                           # Pavlok 認証情報（未チェックイン）
├── pavlok_vrc.cmd                 # Windows 起動スクリプト
└── README.md                      # このファイル
```

---

## クイックスタート

### 1. 初回セットアップ

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env.example` をコピーして `.env` を作成：

```
# BLE モード（推奨）
BLE_DEVICE_MAC=XX:XX:XX:XX:XX:XX

# API モード（スマホアプリ経由）
PAVLOK_API_KEY=your_api_key_here
```

### 3. 起動

```bash
# GUI あり（通常）
python src/main.py

# GUI なし（ヘッドレス）
python src/main.py --no-gui

# Windows（ダブルクリック）
pavlok_vrc.cmd
```

---

## 動作

| タイミング | 動作 |
|---|---|
| **Grab 開始**（IsGrabbed: 0→1） | 即座にバイブレーション |
| **Grab 中**（Stretch 超過） | 警告バイブレーション（ヒステリシス付き） |
| **Grab 終了**（IsGrabbed: 1→0） | `MIN_GRAB_DURATION` 以上保持で Zap/バイブ発動 |

---

## GUI ダッシュボード

| タブ | 内容 |
|---|---|
| ダッシュボード | Grab状態・Stretch値・計算強度のリアルタイム表示 |
| 設定 | `config.py` の主要パラメータを GUI で編集・保存 |
| ログ | リアルタイムログ（レベル別カラー・自動スクロール） |
| 統計 | セッション内・累計の Zap 回数・強度統計 |
| テスト | 単体テスト（Vibration/Zap 直接送信）・Grab シミュレーション |

---

## 接続モード

`src/config.py` の `CONTROL_MODE` で切り替え：

| モード | 説明 |
|---|---|
| `"ble"` | Pavlok に BLE で直接接続（推奨）。スマホ不要。 |
| `"api"` | Pavlok API Cloud 経由。スマホアプリと接続が必要。 |

### BLE モードの安定化

- **Keep-alive**: `BLE_KEEPALIVE_INTERVAL`（デフォルト5.5秒）ごとに ping を送信し接続維持
- **監視ループ**: 5秒ごとに接続状態を確認、切断検知で自動再接続
- **write 失敗時**: `is_connected` を信頼せず強制 disconnect → reconnect してリトライ
- **排他制御**: `asyncio.Lock` で再接続の競合を防止

---

## カスタマイズ（config.py）

### Grab 開始バイブ

| 設定 | 内容 |
|---|---|
| `GRAB_START_VIBRATION_INTENSITY` | 強度（0〜100） |
| `GRAB_START_VIBRATION_COUNT` | 反復回数（1〜127） |
| `GRAB_START_VIBRATION_TON` | ON 時間（0〜255） |
| `GRAB_START_VIBRATION_TOFF` | OFF 時間（0〜255） |

### Stretch 超過バイブ（警告）

| 設定 | 内容 |
|---|---|
| `VIBRATION_ON_STRETCH_THRESHOLD` | 発動する Stretch 値（0〜1） |
| `VIBRATION_HYSTERESIS_OFFSET` | ヒステリシス幅（連続発動防止） |
| `VIBRATION_ON_STRETCH_INTENSITY` | 強度（0〜100） |
| `VIBRATION_ON_STRETCH_COUNT` | 反復回数（1〜127） |
| `VIBRATION_ON_STRETCH_TON` | ON 時間（0〜255） |
| `VIBRATION_ON_STRETCH_TOFF` | OFF 時間（0〜255） |

### Zap（Grab 終了時）

| 設定 | 内容 |
|---|---|
| `MIN_STIMULUS_VALUE` | 出力強度の最小値 |
| `MAX_STIMULUS_VALUE` | 出力強度の最大値 |
| `MIN_GRAB_DURATION` | Zap 発動に必要なグラブの最小時間（秒） |

強度カーブの確認：

```bash
python tools/generate_intensity_graph.py
# → tools/graphs/zap_intensity_curve.png に出力
```

---

## トラブルシューティング

### OSC メッセージが届かない

- VRChat で OSC 受信が有効になっているか確認
- ポート 9001 が開いているか確認：`netstat -an | findstr 9001`

### BLE で接続できない

- `BLE_DEVICE_MAC` が `.env` に正しく設定されているか確認
- Pavlok が他のデバイスと接続中でないか確認
- ログに `BLE connected` が表示されるか確認

### API モードで反応しない

- スマートフォンが Pavlok と接続されているか確認
- `.env` の `PAVLOK_API_KEY` が正しいか確認

---

## 開発情報

- **言語**: Python 3.8+
- **主要ライブラリ**: `python-osc`, `bleak`, `requests`, `python-dotenv`, `matplotlib`
