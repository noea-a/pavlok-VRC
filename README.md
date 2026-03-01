# VRChat Pavlok Connector

VRChat内のPhysBoneを伸ばすと、Pavlok（電撃デバイス）が発動するシステムです。

## 必要なもの

- Windows PC
- Python 3.11 以上
- Pavlok 3
- VRChat アカウント・対応アバター

## セットアップ

1. `pip install -r requirements.txt`
2. `.env.example` をコピーして `.env` を作成し、接続モードに応じて編集
   - **BLE モード:** `BLE_DEVICE_MAC=XX:XX:XX:XX:XX:XX`
   - **API モード:** `PAVLOK_API_KEY=your_api_key_here`
3. VRChat の OSC 受信を有効化（設定 → OSC → 有効）

## アバターセットアップ

対象の PhysBone に以下の設定を追加してください：

1. PhysBone のパラメータ名に `ShockPB` を割り当てる
2. PhysBone を掴めるように設定（Allow Grabbing）

## できること

- **stretch モード** — Grab を離したときの引っ張り量に応じて Zap 強度を決定
- **speed モード** — 素早い引っ張り動作を検出して Zap を発動
- BLE（直接接続）と API（クラウド経由）の切替

## 起動

- **Windows:** `pavlok_vrc.cmd` をダブルクリック
- **CLI:** `python src/main.py`

## トラブルシューティング

- **OSC 未受信:** VRChat の OSC 受信を有効化し、リセットしてください
- **BLE 接続失敗:** Pavlok が他デバイスと接続中でないか、MAC アドレスが正しいか確認してください
- **API 反応なし:** スマートフォン側の Pavlok アプリが起動・接続されているか確認してください
