# プロジェクト構成

## 📁 ディレクトリ構造

```
pavlok_VRC/
│
├── src/                           # ソースコード（メインアプリケーション）
│   ├── __init__.py
│   ├── main.py                    # メインプログラム、GrabState 管理
│   ├── gui.py                     # Tkinter GUI（ダッシュボード、設定、ログ）
│   ├── config.py                  # 設定値（ユーザーがここを編集）
│   ├── osc_listener.py            # VRChat OSC リスナー、送信機
│   └── pavlok_controller.py       # Pavlok API コントローラー
│
├── docs/                          # ドキュメント
│   ├── PROJECT_STRUCTURE.md       # このファイル
│   ├── README.md                  # プロジェクト概要
│   ├── GUI_IMPLEMENTATION.md      # GUI 実装詳細
│   ├── CHATBOX_FIX.md            # Chatbox 修正内容
│   ├── CHATBOX_TROUBLESHOOT.md   # Chatbox トラブルシューティング
│   ├── OFFICIAL_SPEC_FIXED.md    # VRChat OSC 公式仕様対応
│   ├── MONITOR_OSC.md            # OSC メッセージ監視方法
│   ├── QUICKSTART_GUI.md         # GUI クイックスタート
│   └── TEST_QUICK_GUIDE.md       # テスト実行ガイド
│
├── tests/                         # テストスクリプト
│   ├── __init__.py
│   ├── test_gui_integration.py    # GUI 統合テスト
│   ├── test_osc_simulator.py      # OSC シミュレーター
│   ├── test_chatbox_fixed.py      # Chatbox 送信テスト
│   ├── test_osc_chatbox.py        # OSC Chatbox 基本テスト
│   ├── test_chatbox_send.py       # Chatbox 複数パラメータテスト
│   ├── test_osc_params.py         # OSC パラメータテスト
│   ├── test_bleak_pavlok.py       # Pavlok BLE テスト
│   └── その他のテストスクリプト
│
├── tools/                         # ユーティリティ・ツール
│   ├── osc_monitor.py            # OSC パケットモニター
│   └── generate_intensity_graph.py # 強度曲線グラフ生成
│
├── CLAUDE.md                      # 開発ガイド
├── README.md                      # プロジェクト概要
├── requirements.txt               # Python 依存パッケージ
├── .gitignore                     # Git 無視ファイル
└── .env                           # 環境変数（API キーなど）
```

---

## 🚀 実行方法

### メインアプリケーション

```bash
# GUI 付きで実行
python src/main.py
```

### テスト実行

```bash
# GUI 統合テスト
python tests/test_gui_integration.py

# Chatbox 送信テスト
python tests/test_chatbox_fixed.py

# OSC シミュレーター
python tests/test_osc_simulator.py
```

### ツール実行

```bash
# OSC メッセージモニター
python tools/osc_monitor.py

# 強度曲線グラフ生成
python tools/generate_intensity_graph.py
```

---

## 📝 ファイル説明

### **src/ - ソースコード**

| ファイル | 役割 |
|---------|------|
| `main.py` | メインループ、GrabState 管理、OSC 統合 |
| `gui.py` | Tkinter GUI（ダッシュボード、設定、ログ、テスト送信） |
| `config.py` | **ユーザーが編集する設定ファイル** |
| `osc_listener.py` | VRChat からの OSC 受信、VRChat への送信 |
| `pavlok_controller.py` | Pavlok API コントローラー、強度計算 |

### **docs/ - ドキュメント**

| ファイル | 内容 |
|---------|------|
| `PROJECT_STRUCTURE.md` | プロジェクト全体構成（このファイル） |
| `README.md` | プロジェクト概要 |
| `GUI_IMPLEMENTATION.md` | GUI の詳細実装説明 |
| `CHATBOX_FIX.md` | Chatbox メッセージ即座送信の修正内容 |
| `OFFICIAL_SPEC_FIXED.md` | VRChat OSC 公式仕様対応の説明 |
| `MONITOR_OSC.md` | OSC メッセージ監視方法 |
| `QUICKSTART_GUI.md` | GUI の使い方（クイックガイド） |
| `TEST_QUICK_GUIDE.md` | テスト実行方法 |

### **tests/ - テストスクリプト**

| ファイル | テスト内容 |
|---------|----------|
| `test_gui_integration.py` | GUI ウィジェット、ダッシュボード更新 |
| `test_osc_simulator.py` | OSC パラメータシミュレーション |
| `test_chatbox_fixed.py` | Chatbox 公式仕様テスト |
| `test_osc_chatbox.py` | 基本的な Chatbox メッセージ送信 |
| `test_osc_params.py` | OSC パラメータバリエーション |

### **tools/ - ユーティリティ**

| ファイル | 用途 |
|---------|------|
| `osc_monitor.py` | OSC パケットをリアルタイム監視 |
| `generate_intensity_graph.py` | 強度計算カーブをグラフ化 |

---

## 🔧 セットアップ

```bash
# 依存パッケージをインストール
pip install -r requirements.txt

# 環境変数を設定
# .env ファイルを作成して以下を記入
# PAVLOK_API_KEY=your_api_key_here
```

---

## 📊 データフロー

```
VRChat (PhysBone Grab)
   ↓ (OSC パラメータ)
osc_listener.py (受信・パース)
   ↓
main.py (GrabState 管理)
   ↓ (Grab イベント、Stretch 変更)
GUI (ダッシュボール表示)
Pavlok (刺激送信)
VRChat Chatbox (強度表示)
```

---

## 🎯 開発ガイド

### 新しい OSC パラメータを追加

1. `config.py` に定数を追加
2. `osc_listener.py` にハンドラメソッドを追加
3. `main.py` の GrabState にコールバックを追加

### 設定値を変更

`src/config.py` を編集：

```python
MIN_STIMULUS_VALUE = 15      # 最小刺激値
MAX_STIMULUS_VALUE = 70      # 最大刺激値
MIN_GRAB_DURATION = 0.8      # 最小グラブ時間（秒）
# その他の設定...
```

再起動で反映

### GUI に機能を追加

`src/gui.py` を編集：

```python
class PavlokGUI(tk.Tk):
    def _create_new_tab(self):
        # 新しいタブを追加
        pass
```

---

## ✅ チェックリスト

- ✓ ソースコード: `src/`
- ✓ ドキュメント: `docs/`
- ✓ テスト: `tests/`
- ✓ ツール: `tools/`
- ✓ sys.path 参照修正
- ✓ ディレクトリ整理完了

---

## 📍 よく使うコマンド

```bash
# メインアプリケーション
python src/main.py

# GUI テスト
python tests/test_gui_integration.py

# OSC モニター
python tools/osc_monitor.py

# グラフ生成
python tools/generate_intensity_graph.py
```

---

## 🎓 参考ドキュメント

1. **初めての方**: `docs/README.md`
2. **GUI の使い方**: `docs/QUICKSTART_GUI.md`
3. **Chatbox が表示されない**: `docs/CHATBOX_TROUBLESHOOT.md`
4. **OSC メッセージを監視**: `docs/MONITOR_OSC.md`
5. **詳細な実装**: `CLAUDE.md`

---

## ✨ プロジェクト整理完了！

すべてのファイルが適切なフォルダに整理されました。🎉
