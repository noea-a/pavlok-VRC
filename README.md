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
│   ├── pavlok_controller.py       # Pavlok API制御
│   ├── gui.py                     # Tkinter GUI ダッシュボード
│   └── zap_recorder.py            # Zap 実行記録・統計
│
├── docs/                          # ドキュメント・ツール
│   ├── generate_intensity_graph.py # Zap強度グラフ生成
│   └── graphs/                    # グラフ出力
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

**Windows（簡単）:**
- `pavlok_vrc.cmd` をダブルクリック

**コマンドラインから:**
```bash
# 仮想環境有効化
venv\Scripts\activate

# メイン実行
python src/main.py
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
```

---

## 使用方法

1. `python src/main.py` を実行
2. スマートフォンで Pavlok と接続
3. VRChat でアバターに PhysBone（ShockPB）を設定
4. 他プレイヤーが PhysBone を掴む
   - **即座**: Grab開始時にバイブレーション
   - **グラブ中**: Stretch値が高くなると警告バイブレーション
   - **終了時**: MIN_GRAB_DURATION (0.8秒) 以上掴んで離すとZapが発動

---

## 動作

- **Grab開始**: PhysBone を掴む → 即座にバイブレーション発動
- **グラブ中**: Stretch値が高くなる → バイブレーション反応
- **Grab終了**: 0.8秒以上掴んで離す → 最終的なZapが発動

---

## カスタマイズ

`src/config.py` で以下を調整できます：

- `USE_VIBRATION`: False（Zap）/ True（バイブレーション）
- `MIN_STIMULUS_VALUE` / `MAX_STIMULUS_VALUE`: 出力強度の範囲
- `MIN_GRAB_DURATION`: グラブ終了時にZapが発動するまでの最小時間

---

## 制御方式

- **Pavlok API**: スマートフォン中継（クラウド API）
- **必要**: Pavlok と接続されたスマートフォン
- **安定性**: 信頼性高い

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
   USE_VIBRATION = False  # 全てバイブレーションに置き換える（テスト用）
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
  - `matplotlib`: グラフ生成（docs/generate_intensity_graph.py）
