# VRChat Pavlok Connector

VRChat内のPhysBoneを他プレイヤーが掴んで伸ばすと、Pavlok（電撃デバイス）が発動するシステムです。

---

## 必要なもの

- Windows PC
- Python 3.8 以上
- Pavlok 3
- VRChat アカウント・対応アバター

---

## セットアップ

### 1. Python 依存ライブラリのインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env.example` をコピーして `.env` を作成し、接続モードに応じて編集してください。

**BLE モード（推奨・スマホ不要）:**
```
BLE_DEVICE_MAC=XX:XX:XX:XX:XX:XX
```

**API モード（スマホアプリ経由）:**
```
PAVLOK_API_KEY=your_api_key_here
```

`src/config.py` の `CONTROL_MODE` を使用するモードに合わせて変更してください。

### 3. VRChat の設定

VRChat の OSC 受信を有効化してください（設定 → OSC → 有効）。

---

## 起動方法

**Windows（簡単）:**
`pavlok_vrc.cmd` をダブルクリック

**コマンドラインから:**
```bash
python src/main.py
```

**GUI なし（ヘッドレス）:**
```bash
python src/main.py --no-gui
```

---

## 動作

| タイミング | 動作 |
|---|---|
| **Grab 開始** | 即座にバイブレーション |
| **Grab 中（Stretch 超過）** | 警告バイブレーション（ヒステリシス付き） |
| **Grab 終了** | 一定時間以上保持していた場合に Zap/バイブ発動 |

---

## GUI ダッシュボード

起動すると自動でウィンドウが開きます。

| タブ | 内容 |
|---|---|
| ダッシュボード | Grab 状態・Stretch 値・計算強度のリアルタイム表示 |
| 設定 | 各パラメータを GUI で変更・保存 |
| ログ | 動作ログのリアルタイム表示 |
| 統計 | Zap の回数・強度統計（セッション・累計） |
| テスト | VRChat なしで Vibration/Zap を直接送信してテスト |

---

## 設定のカスタマイズ

GUI の「設定」タブから変更できます。変更は保存後、次の操作から反映されます。

| 設定 | 内容 |
|---|---|
| `MIN_STIMULUS_VALUE` | Zap 強度の最小値 |
| `MAX_STIMULUS_VALUE` | Zap 強度の最大値 |
| `MIN_GRAB_DURATION` | Zap 発動に必要な最小グラブ時間（秒） |
| `VIBRATION_ON_STRETCH_THRESHOLD` | 警告バイブが発動する Stretch 値 |
| `VIBRATION_HYSTERESIS_OFFSET` | 警告バイブの連続発動防止（ヒステリシス幅） |
| `GRAB_START_VIBRATION_INTENSITY` | Grab 開始バイブの強度 |
| `GRAB_START_VIBRATION_COUNT` | Grab 開始バイブの反復回数 |
| `GRAB_START_VIBRATION_TON` | Grab 開始バイブの長さ |
| `VIBRATION_ON_STRETCH_INTENSITY` | 警告バイブの強度 |
| `VIBRATION_ON_STRETCH_COUNT` | 警告バイブの反復回数 |
| `VIBRATION_ON_STRETCH_TON` | 警告バイブの長さ |

---

## トラブルシューティング

### OSC メッセージが届かない

- VRChat の OSC 受信が有効になっているか確認してください
- VRChat を再起動すると解決する場合があります

### BLE で接続できない

- Pavlok が他のデバイス（スマホなど）と接続中でないか確認してください
- `.env` の `BLE_DEVICE_MAC` が正しいか確認してください

### API モードで反応しない

- スマートフォンの Pavlok アプリが起動・接続されているか確認してください
- `.env` の `PAVLOK_API_KEY` が正しいか確認してください
