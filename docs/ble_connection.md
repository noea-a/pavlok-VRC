# Pavlok 3 BLE 接続 知見まとめ

## BLE コマンド仕様

### Vibration（`c_vibe` UUID: `00001001-0000-1000-8000-00805f9b34fb`）

```
bytes([0x80 | count, mode, intensity, ton, toff])
```

| バイト | 意味 | 確認状態 | 備考 |
|---|---|---|---|
| `0x80 \| count` | 反復回数 | ✅ 確認済み | 1〜127 |
| `mode` | 不明 | ❓ 未解明 | 現在 `2` 固定 |
| `intensity` | 強度 | ✅ 確認済み | 0〜100 |
| `ton` | ON 時間（バイブの長さ） | ✅ 確認済み | 0〜255 |
| `toff` | OFF 時間（反復間隔） | ✅ 確認済み | 0〜255 |

> **参照元**: [webtool.pavlok.com](https://webtool.pavlok.com/) の `pavlok.js` / `index.js` を解析

### Zap（`c_zap` UUID: `00001003-0000-1000-8000-00805f9b34fb`）

```
bytes([0x89, intensity])
```

| バイト | 意味 | 備考 |
|---|---|---|
| `0x89` | コマンド種別（通常 Zap） | `0x99` `0xA9` `0xB9` でテスト用モードあり |
| `intensity` | 強度 | 0〜100 |

### check_api（`c_leds` UUID: `00001004-0000-1000-8000-00805f9b34fb`）

```
bytes([87, 84])  # "WT"
```

接続直後に送る確認コマンド。失敗しても接続自体は有効。

---

## 接続の不安定要因

### 1. `is_connected` の信頼性（Windows / WinRT）

Bleak の `is_connected` プロパティは WinRT バックエンドで実際の状態と乖離することがある。
物理的に切断されていても `True` を返すケースがあり、write 時に初めて失敗を検知する。

→ **対策 C**: write 失敗時は `is_connected` を無視して強制 disconnect → reconnect する。

### 2. アイドル中の切断

BLE デバイスは一定時間通信がないと省電力で接続を切る。
オンデマンド再接続方式（送信前に確認）では次の送信まで切断を検知できず、送信タイミングで遅延・失敗が起きる。

→ **対策 B**: バックグラウンド監視ループで定期的に接続状態を確認し、切断を即検知・自動再接続する。

### 3. B と C の競合

監視ループと送信側が同時に再接続を試みると競合して両方失敗する可能性がある。

→ **対策**: `asyncio.Lock`（`_reconnect_lock`）で排他制御。
ロック取得後に `is_connected` を再確認して二重再接続を防止。

---

## 現在の実装方針（B + C）

```
B: _monitor_loop（バックグラウンド asyncio タスク）
   └─ 5秒ごとに is_connected を確認
      └─ 切断検知 → _reconnect_lock を取得 → _do_reconnect()

C: _write_with_retry
   └─ write 失敗
      └─ _reconnect_lock を取得 → 強制 disconnect → _do_reconnect() → リトライ

排他制御: asyncio.Lock (_reconnect_lock)
   └─ ロック取得後に is_connected を再確認（二重再接続防止）
```

### 再接続の流れ（`_do_reconnect`）

1. 既存の `BleakClient` を disconnect（残っていれば）
2. 新しい `BleakClient` インスタンスを生成して connect
3. `_CONNECT_SETTLE_DELAY`（0.3秒）待機
4. check_api コマンド送信
5. 失敗時は `BLE_RECONNECT_INTERVAL` 秒待って最大3回リトライ

> 毎回新しい BleakClient インスタンスを生成するのは WinRT での再接続安定化のため。

---

## 未解決事項

- `mode` バイトの意味（現在 `2` 固定。webtool では Beep が `0` を使用）
- Pavlok 側から接続を切る条件（タイムアウト時間など）
- Keep-alive（定期的な軽い通信で接続維持）の効果 → 将来検討

---

## 設定値（`config.py`）

| 設定名 | デフォルト | 意味 |
|---|---|---|
| `BLE_CONNECT_TIMEOUT` | 10.0 秒 | 接続タイムアウト |
| `BLE_RECONNECT_INTERVAL` | 5.0 秒 | 再接続リトライ間隔 |
