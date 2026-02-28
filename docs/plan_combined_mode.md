# Combined モード設計メモ

## コンセプト

首輪の紐を引っ張るイメージ。
- **速度** → 本当に引いたかどうかの判定（たまたま触れただけを除外）
- **距離** → 衝撃の強さそのもの

## 決定事項

### Zap トリガー
- 速度が `SPEED_ZAP_THRESHOLD` を上回ったら Zap 準備
- その後 `SPEED_ZAP_THRESHOLD - SPEED_ZAP_HYSTERESIS_OFFSET` を下回ったら Zap 発火
- Grab 中に何度も繰り返さないよう、1回発火したら次の Zap 準備までリセット
- `SPEED_ZAP_THRESHOLD` — 速度がこれを上回ると Zap 準備
- `SPEED_ZAP_HYSTERESIS_OFFSET` — Zap 準備から Zap 発火までのヒステリシス幅

### 強度計算
- Zap 発火時の強度は**距離スコアのみ**で決定
- 既存の `calculate_intensity()` に stretch をそのまま渡す（変換不要）
- 戻し区間（Stretch 減少）は速度計算から除外（実装済み）
- `MIN_STRETCH_THRESHOLD` — 流用。距離がこれ未満は処理しない

### 速度計測
- `MIN_STRETCH_THRESHOLD` を超えてから `INITIAL_SPEED_STRETCH_WINDOW` に達するまでの最大速度を初速とする
- `INITIAL_SPEED_STRETCH_WINDOW` — 初速計測の終端となる Stretch 距離

## 模索中

- `MIN_SPEED_THRESHOLD`（速度の最小閾値）は設ける → Zap 全体をスキップ
- `INITIAL_SPEED_STRETCH_WINDOW` 到達前に速度が閾値を下回った場合（極短距離）の扱い
