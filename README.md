# VRChat Pavlok Connector

VRChat内のPhysBoneを他プレイヤーが掴んで伸ばすと、Pavlok（電撃デバイス）が発動するシステムです。

---

## プロジェクト構造

```
pavlok_VRC/
├── src/                           # ソースコード
│   ├── main.py                    # メインロジック（常駐実行）
│   ├── config.py                  # 設定管理
│   ├── osc_listener.py            # OSC受信モジュール
│   └── pavlok_controller.py       # Pavlok API制御
│
├── tools/                         # ツール・ユーティリティ
│   ├── generate_intensity_graph.py # Zap強度グラフ生成
│   ├── graphs/                    # グラフ出力
│   │   └── zap_intensity_curve.png
│   └── test/                      # テストスクリプト
│       ├── test_nonlinear_intensity.py
│       └── test_normalized_intensity.py
│
├── tests/                         # その他テスト
│   ├── test_integration.py
│   └── test_pavlok.py
│
├── requirements.txt               # 依存ライブラリ
├── .gitignore                     # Git除外設定
├── .env                           # Pavlok APIキー（未チェックイン）
├── README.md                      # このファイル
├── CLAUDE.md                      # Claude Code ガイド
└── venv/                          # Python仮想環境
```

---

## クイックスタート

### 1. 初回セットアップ

```bash
# 仮想環境作成
python -m venv venv

# 有効化（Windows）
venv\Scripts\activate

# 依存ライブラリインストール
pip install -r requirements.txt
```

### 2. 起動方法

```bash
# 仮想環境有効化
venv\Scripts\activate

# メイン実行
python src/main.py
```

### 3. グラフ生成・テスト実行

```bash
# Zap強度計算グラフを生成
python tools/generate_intensity_graph.py
# 出力: tools/graphs/zap_intensity_curve.png

# 強度計算テスト
python tools/test/test_nonlinear_intensity.py
```

---

## 設定（.env）

`.env.example` をコピーして `.env` を作成してください：

```bash
cp .env.example .env
```

その後、`.env` を編集して Pavlok API キーを設定：

```
PAVLOK_API_KEY=your_api_key_here
LIMIT_PAVLOK_ZAP_VALUE=70
```

---

## 使用方法

1. `python src/main.py` を実行
2. スマートフォンで Pavlok と接続
3. VRChat でアバターに PhysBone（ShockPB）を設定
4. 他プレイヤーが PhysBone を掴む
   - **即座**: Grab開始時にバイブレーション
   - **グラブ中**: Stretch値が高くなるとバイブレーション
   - **終了時**: 3秒以上掴んで離すと最終刺激が発動

---

## ロジック

### 1. Grab開始時（即座）
```
IsGrabbed: false → true
    ↓
【バイブレーション発動】 (強度: 20)
```

### 2. グラブ中のStretch超過時
```
IsGrabbed: true かつ Stretch > VIBRATION_ON_STRETCH_THRESHOLD (0.7)
    ↓
【バイブレーション発動】 (ヒステリシス付き)
    ↓
Stretch < VIBRATION_ON_STRETCH_THRESHOLD - VIBRATION_HYSTERESIS_OFFSET
    (0.7 - 0.15 = 0.55) に低下するまで再発動しない
```

### 3. Grab終了時（設定時間以上）
```
IsGrabbed: true [MIN_GRAB_DURATION秒 (0.8秒)] → false
    ↓
Stretch値を計算 → 最終刺激が発動 (Zap/Vibration)
```

### 強度計算（非線形 Piecewise-Linear）

Stretch値を刺激強度に段階的に変換します（config.py で詳細なパラメータ調整可能）：

- **Stretch < MIN_STRETCH_THRESHOLD (0.03)**: 強度 0（刺激なし）
- **Stretch 0.03～MIN_STRETCH_PLATEAU (0.12)**: MIN_STIMULUS_VALUE (15) で固定（低側プラトー）
- **Stretch 0.12～切り替え点**: 線形で上昇
- **切り替え点～MAX_STRETCH_FOR_CALC (0.8)**: より急な勾配で上昇（加速）
- **Stretch ≥ 0.8**: MAX_STIMULUS_VALUE (70) で固定（高側プラトー）

| Stretch | 強度 | 説明 |
|---------|------|------|
| 0.0     | 15   | 最小値 |
| 0.1     | 20   | 低側プラトー |
| 0.3     | 28   | 線形領域 |
| 0.5     | 42   | 線形領域 |
| 0.6     | 48   | 切り替え点付近 |
| 0.8     | 70   | 最大値（クランプ） |

---

## 設定項目（config.py）

### Grab・Stretch関連の刺激設定

| 設定項目 | デフォルト | 説明 |
|---------|----------|------|
| `GRAB_START_VIBRATION_INTENSITY` | 20 | Grab開始時のバイブ強度（0～100） |
| `VIBRATION_ON_STRETCH_THRESHOLD` | 0.7 | Stretch超過の判定閾値（0～1） |
| `VIBRATION_HYSTERESIS_OFFSET` | 0.15 | ヒステリシスオフセット（発動閾値からの差分） |
| `MIN_GRAB_DURATION` | 0.8 | Grab終了時刺激の最小継続時間（秒） |
| `MIN_STIMULUS_VALUE` | 15 | 出力刺激の最小値 |
| `MAX_STIMULUS_VALUE` | 70 | 出力刺激の最大値 |

---

## 制御方式

- **Pavlok API**: スマートフォン中継（クラウド API）
- **必要**: Pavlok と接続されたスマートフォン
- **安定性**: 信頼性高い

---

## テスト検証

- **OSC リスナー**: ポート 9001 で VRChat パラメータ受信
- **API 制御**: Pavlok API 経由でバイブレーション/ザップ送信
- **強度計算**: 非線形正規化計算（テスト済み）

```
実行例:
[API] VRChat Pavlok Connector Starting
OSC listener started on port 9001
Listening for OSC messages...
```

---

## トラブルシューティング

### OSC メッセージが受信されない

1. VRChat で OSC 受信を有効化確認
2. コンソールで「OSC listener started」が表示されているか確認
3. ポート 9001 がリッスンされているか確認：
   ```bash
   netstat -an | findstr 9001
   ```

### Pavlok が反応しない

1. スマートフォンが Pavlok と接続されているか確認
2. `.env` の PAVLOK_API_KEY が正しいか確認
3. インターネット接続を確認
4. config.py の設定を確認：
   ```python
   USE_VIBRATION = False  # False: Zap, True: Vibration
   MIN_STIMULUS_VALUE = 15   # 出力最小値
   MAX_STIMULUS_VALUE = 70   # 出力最大値
   ```

---

## 開発情報

- **言語**: Python 3.8+
- **主要ライブラリ**:
  - `python-osc`: OSC 受信（9001ポート）
  - `requests`: Pavlok API 通信
  - `python-dotenv`: 環境変数管理
  - `matplotlib`: グラフ生成（tools用）
