# プロジェクト構成

## ディレクトリ構造

```
pavlok_VRC/
│
├── src/                           # ソースコード（メインアプリケーション）
│   ├── __init__.py
│   ├── main.py                    # メインプログラム、GrabState 管理
│   ├── gui.py                     # Tkinter GUI（ダッシュボード、設定、ログ、統計）
│   ├── config.py                  # 設定値（ユーザーがここを編集）
│   ├── osc_listener.py            # VRChat OSC リスナー、Chatbox 送信
│   ├── pavlok_controller.py       # Pavlok API コントローラー、強度計算
│   └── zap_recorder.py            # Zap 実行記録・統計管理（JSON 永続化）
│
├── docs/                          # ドキュメント
│   └── PROJECT_STRUCTURE.md       # このファイル
│
├── tools/                         # ユーティリティ・ツール
│   └── generate_intensity_graph.py # 強度曲線グラフ生成
│
├── data/                          # データ（自動生成）
│   └── zap_records.json           # Zap 実行記録（アプリが自動生成）
│
├── tests/                         # テスト
│   └── __init__.py
│
├── CLAUDE.md                      # 開発ガイド（Claude Code 向け）
├── README.md                      # プロジェクト概要
├── LICENSE                        # ライセンス
├── requirements.txt               # Python 依存パッケージ
├── pavlok_vrc.cmd                 # Windows 起動スクリプト（ダブルクリックで起動）
├── .env.example                   # 環境変数テンプレート
└── .env                           # 環境変数（API キー、非公開）
```

---

## 実行方法

### Windows（簡単）
`pavlok_vrc.cmd` をダブルクリック

### コマンドライン
```bash
python src/main.py
```

---

## ファイル説明

### src/ - ソースコード

| ファイル | 役割 |
|---------|------|
| `main.py` | メインループ、GrabState 管理、OSC 統合 |
| `gui.py` | Tkinter GUI（ダッシュボード、設定、ログ、統計、テスト送信） |
| `config.py` | **ユーザーが編集する設定ファイル** |
| `osc_listener.py` | VRChat からの OSC 受信、Chatbox への送信 |
| `pavlok_controller.py` | Pavlok API コントローラー、強度計算 |
| `zap_recorder.py` | Zap 実行を JSON に記録・統計集計 |

### tools/ - ユーティリティ

| ファイル | 用途 |
|---------|------|
| `generate_intensity_graph.py` | 強度計算カーブをグラフ化（`tools/graphs/` に出力） |

---

## データフロー

```
VRChat (PhysBone Grab)
   ↓ OSC パラメータ（UDP:9001）
osc_listener.py（受信・パース）
   ↓
main.py / GrabState（イベント管理）
   ├─→ pavlok_controller.py（Pavlok API へ刺激送信）
   ├─→ zap_recorder.py（Zap 記録・統計）
   ├─→ gui.py（ダッシュボード更新）
   └─→ osc_listener.py（VRChat Chatbox へ強度表示）
```

---

## セットアップ

```bash
pip install -r requirements.txt
# .env を作成して PAVLOK_API_KEY を設定
```

詳細は `README.md` を参照。
