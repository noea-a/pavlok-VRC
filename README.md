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
│   ├── gui/                       # Tkinter GUI ダッシュボード
│   │   ├── app.py                 # GUIエントリポイント
│   │   ├── tab_dashboard.py       # ダッシュボードタブ
│   │   ├── tab_settings.py        # 設定タブ
│   │   ├── tab_log.py             # ログタブ
│   │   └── tab_stats.py           # 統計タブ
│   └── zap_recorder.py            # Zap 実行記録・統計
│
├── tools/                         # 開発補助ツール
│   ├── generate_intensity_graph.py # Zap強度グラフ生成
│   └── graphs/                    # グラフ出力
│
├── docs/                          # ドキュメント
├── tests/                         # テスト（今後用）
│
├── requirements.txt               # 依存ライブラリ
├── .gitignore                     # Git除外設定
├── .env                           # Pavlok APIキー（未チェックイン）
├── README.md                      # このファイル
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
   - **終了時**: `MIN_GRAB_DURATION` 以上掴んで離すとZapが発動

---

## GUI ダッシュボード

`python src/main.py` 起動時に自動でGUIウィンドウが開きます。

| タブ | 内容 |
|------|------|
| ダッシュボード | Grab状態・Stretch値・計算強度のリアルタイム表示、テスト送信パネル |
| 設定 | `config.py` の主要パラメータをGUIで編集・保存（再起動で反映） |
| ログ | リアルタイムログ表示（レベル別カラー、自動スクロール） |
| 統計 | セッション内・累計のZap回数・強度統計 |

GUIなしで起動する場合：

```bash
python src/main.py --no-gui
```

---

## 動作

- **Grab開始**: PhysBone を掴む → 即座にバイブレーション
- **グラブ中**: Stretch値が高い → 警告用バイブレーション
- **Grab終了**: `MIN_GRAB_DURATION` 以上掴んで離す → 最終的なZapが発動

---

## カスタマイズ（Config）

`src/config.py` で調整できる主な項目：

| 設定 | 内容 |
|------|------|
| `MIN_STIMULUS_VALUE` | 出力強度の最小値 |
| `MAX_STIMULUS_VALUE` | 出力強度の最大値 |
| `MIN_GRAB_DURATION` | Zap発動に必要なグラブの最小時間（秒） |
| `VIBRATION_ON_STRETCH_THRESHOLD` | 警告バイブが発動するStretch値 |
| `VIBRATION_HYSTERESIS_OFFSET` | ヒステリシス幅（連続発動防止） |

強度カーブは以下で確認できます：

```bash
python tools/generate_intensity_graph.py
# → tools/graphs/zap_intensity_curve.png に出力
```

---

## トラブルシューティング

### OSC メッセージが受信されない

1. VRChat で OSC 受信を有効化確認
2. コンソールで「OSC listener started」が表示されているか確認
3. ポート 9001 で受信されているか確認：
   ```bash
   netstat -an | findstr 9001
   ```

### Pavlok が反応しない

1. スマートフォンが Pavlok と接続されているか確認
2. `.env` の PAVLOK_API_KEY が正しいか確認
3. インターネット接続を確認
4. `src/config.py` の設定を確認：
   - `USE_VIBRATION`: テスト用にバイブレーションへ切り替え可能
   - `MIN_STIMULUS_VALUE` / `MAX_STIMULUS_VALUE`: 出力強度の範囲

---

## 開発情報

- **言語**: Python 3.8+
- **主要ライブラリ**:
  - `python-osc`: OSC 受信（9001ポート）
  - `requests`: Pavlok API 通信
  - `python-dotenv`: 環境変数管理
  - `matplotlib`: グラフ生成（tools/generate_intensity_graph.py）
