# Pavlok 3 BLE リファレンス

## サービス UUID

| 定数名 | UUID | 説明 |
|---|---|---|
| PAV_DIAG_SVC | `156e0000-a300-4fea-897b-86f698d74461` | 診断 |
| PAV_CFG_SVC | `156e1000-a300-4fea-897b-86f698d74461` | 設定 |
| PAV_NOTI_SVC | `156e2000-a300-4fea-897b-86f698d74461` | 通知 |
| PAV_APP_SVC | `156e5000-a300-4fea-897b-86f698d74461` | アプリ制御（メイン） |
| PAV_OTA_SVC | `156e6000-a300-4fea-897b-86f698d74461` | OTA ファームウェア更新 |
| PAV_SETUP_SVC | `156e7000-a300-4fea-897b-86f698d74461` | セットアップ |
| BLE_DEVINFO_SVC | `0000180a-0000-1000-8000-00805f9b34fb` | デバイス情報（標準） |
| BLE_BATT_SVC | `0000180f-0000-1000-8000-00805f9b34fb` | バッテリー（標準） |
| NORDIC_NUS_SVC | `6e400001-b5a3-f393-e0a9-e50e24dcca9e` | Nordic UART |

## キャラクタリスティック UUID

| 定数名 | UUID | 説明 | 用途 |
|---|---|---|---|
| c_batt | `00002a19-0000-1000-8000-00805f9b34fb` | Battery Level (標準) | read: 0〜100 (%) |
| c_fwver | `00002a26-0000-1000-8000-00805f9b34fb` | Firmware Revision | read: 文字列 |
| c_hwver | `00002a27-0000-1000-8000-00805f9b34fb` | Hardware Revision | read: 文字列 |
| **c_vibe** | **`00001001-0000-1000-8000-00805f9b34fb`** | **Vibration** | **write: `[0x80\|count, mode, intensity, ton, toff]`** |
| c_beep | `00001002-0000-1000-8000-00805f9b34fb` | Beep | write |
| **c_zap** | **`00001003-0000-1000-8000-00805f9b34fb`** | **Zap** | **write: `[0x89, intensity]`** |
| c_leds | `00001004-0000-1000-8000-00805f9b34fb` | LEDs | write |
| **c_api** | **`00007999-0000-1000-8000-00805f9b34fb`** | **API / Keep-alive** | **write: `[87, 84]` で ping** |

（使用していない UUID は省略。全量は旧 PROJECT_STRUCTURE.md 参照）

## コマンド形式

### Vibration

```
bytes([0x80 | count, mode, intensity, ton, toff])

count     : 繰り返し回数 (1〜127)
mode      : 2 固定
intensity : 強度 (0〜100)
ton       : ON 時間
toff      : OFF 時間
```

### Zap

```
bytes([0x89, intensity])

intensity : 強度 (0〜100)
```

### Keep-alive ping

```
bytes([87, 84])   # c_api へ書き込む
```
