# VRChat Pavlok Connector

VRChat内のPhysBoneを他プレイヤーが掴んで伸ばすと、Pavlok（電撃デバイス）が発動するシステムです。

## 必要なもの

- Windows PC
- Python 3.8 以上
- Pavlok 3
- VRChat アカウント・対応アバター

## セットアップ

1. `pip install -r requirements.txt`
2. `.env.example` をコピーして `.env` を作成し、接続モードに応じて編集
   - **BLE モード:** `BLE_DEVICE_MAC=XX:XX:XX:XX:XX:XX`
   - **API モード:** `PAVLOK_API_KEY=your_api_key_here`
3. VRChat の OSC 受信を有効化（設定 → OSC → 有効）

## 起動

**Windows:** `pavlok_vrc.cmd` をダブルクリック
**CLI:** `python src/main.py`

## 動作

| タイミング | 動作 |
|---|---|
| **Grab 開始** | 即座にバイブレーション |
| **Grab 中（Stretch 超過）** | 警告バイブレーション |
| **Grab 終了** | 一定時間以上保持で Zap/バイブ発動 |

## トラブルシューティング

- **OSC 未受信:** VRChat の OSC 受信を有効化し、再起動してください
- **BLE 接続失敗:** Pavlok が他デバイスと接続中でないか、MAC アドレスが正しいか確認してください
- **API 反応なし:** スマートフォン側の Pavlok アプリが起動・接続されているか確認してください
