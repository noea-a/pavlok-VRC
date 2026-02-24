# VRChat Chatbox Zap強度表示機能 - 実装完了

## 実装日時
2026-02-23

## 概要
VRChat のプレイヤーが Zap（電気刺激）を受け取る際に、その強度をVRChat の Chatbox に表示する機能を実装しました。

## 実装内容

### 1. **config.py** - OSC送信設定の追加
```python
# ===== OSC送信設定（VRChatへのChatbox出力） =====
OSC_SEND_IP = "127.0.0.1"           # VRChat OSC受信IP
OSC_SEND_PORT = 9000                # VRChat OSC受信ポート（標準）
OSC_CHATBOX_PARAM = "/chatbox/input"  # Chatboxパラメータ
OSC_SEND_INTERVAL = 0.1             # Chatbox送信間隔（秒）
```

**目的:**
- VRChat への OSC パラメータ送信ポート（9000）を指定
- Chatbox への入力パラメータ（`/chatbox/input`）を定義
- リアルタイム更新時のスロットル間隔（0.1秒）を設定

### 2. **osc_listener.py** - OSC送信機能の追加

#### インポート追加
```python
from pythonosc.osc_client import SimpleUDPClient
```

#### OSCClient 初期化
`__init__()` メソッドで `SimpleUDPClient` を初期化：
```python
self.osc_client = SimpleUDPClient(OSC_SEND_IP, OSC_SEND_PORT)
```

#### 送信メソッド追加
- `send_parameter(address, value)` - 汎用OSCパラメータ送信
- `send_chatbox_message(message)` - Chatbox への直接メッセージ送信

### 3. **pavlok_controller.py** - 強度正規化関数の追加

```python
def normalize_intensity_for_display(stimulus_value: int) -> int:
    """
    Pavlok刺激値（15～70）を表示用に正規化（20～100）

    内部値 15 → 表示値 20
    内部値 70 → 表示値 100
    """
```

**テスト結果:**
```
15 → 20   (最小値)
30 → 42   (中～低)
42 → 59   (中程度)
56 → 80   (中～高)
70 → 100  (最大値)
```

### 4. **main.py** - Chatbox送信ロジックの統合

#### GrabState クラスの拡張
```python
def __init__(self, osc_sender=None):
    self.last_osc_send_time = 0.0  # スロットル用
    self.osc_sender = osc_sender    # OSC送信リファレンス
```

#### Grab開始時の Chatbox 送信
```python
if self.osc_sender:
    display_intensity = normalize_intensity_for_display(GRAB_START_VIBRATION_INTENSITY)
    self.osc_sender.send_chatbox_message(f"Zap: {display_intensity}%")
```

#### リアルタイム Stretch 更新時の Chatbox 送信（スロットル付き）
```python
if self.osc_sender and time.time() - self.last_osc_send_time > OSC_SEND_INTERVAL:
    intensity = calculate_intensity(value)
    if intensity > 0:
        display_intensity = normalize_intensity_for_display(intensity)
        self.osc_sender.send_chatbox_message(f"Zap: {display_intensity}%")
        self.last_osc_send_time = time.time()
```

#### Grab終了時の Chatbox 送信
```python
if self.osc_sender:
    display_intensity = normalize_intensity_for_display(intensity)
    self.osc_sender.send_chatbox_message(f"Zap: {display_intensity}% [Final]")
```

## 機能フロー

```
VRChat (IsGrabbed, Stretch 送信)
    ↓ UDP:9001 受信
OSCListener (受信)
    ↓
GrabState (状態遷移)
    ├─ Grab開始時 → calculate_zap_intensity() → normalize_intensity_for_display() → Chatbox送信
    ├─ Grab中（Stretch更新） → calculate_zap_intensity() → normalize_intensity_for_display() → Chatbox送信（スロットル）
    └─ Grab終了時 → calculate_zap_intensity() → normalize_intensity_for_display() → Chatbox送信 [Final]
    ↓ UDP:9000 送信
VRChat (Chatbox に「Zap: XX%」を表示)
```

## 送信パターン

| イベント | メッセージ例 | タイミング |
|---------|-----------|---------|
| Grab開始 | `Zap: 27%` | IsGrabbed: false → true |
| リアルタイム更新 | `Zap: 59%` | Stretch値が変更（100ms毎） |
| Grab終了（刺激実行） | `Zap: 80% [Final]` | IsGrabbed: true → false かつ最小継続時間超過 |

## パフォーマンス考慮

- **スロットル機能**: リアルタイム更新は0.1秒間隔で制限（不要な送信を削減）
- **例外処理**: OSC送信失敗時もアプリケーションは継続実行
- **非同期実行**: OSC送信は別スレッド（ThreadingOSCUDPServer）で実行

## テスト

実装したテストスクリプト: `test_chatbox_feature.py`

```bash
python test_chatbox_feature.py
```

**結果: 8/8 テスト成功**

## 既知の制限事項

- VRChat が OSC を有効化している必要あり（`OSC enabled` = True）
- ローカルホスト（127.0.0.1）通信のため、VRChat と同一PC での実行が前提
- Chatbox への送信は UDP/OSC のため、ネットワーク遅延の影響を受ける可能性あり

## 今後の拡張案

- Chatbox メッセージのカスタマイズ（接頭辞、色、フォーマット）
- 統計情報の表示（平均強度、総回数など）
- VRChat 側でのメッセージ履歴表示

## ファイル変更一覧

1. `src/config.py` - OSC送信設定追加
2. `src/osc_listener.py` - OSC送信機能追加
3. `src/pavlok_controller.py` - 強度正規化関数追加
4. `src/main.py` - Chatbox送信ロジック統合
5. `test_chatbox_feature.py` - テストスクリプト作成（新規）
