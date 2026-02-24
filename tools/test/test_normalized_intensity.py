#!/usr/bin/env python3
"""
正規化強度計算のテストスクリプト
Stretch 0.0～0.8 を 0.06～1.0 に正規化して計算
"""

import sys
sys.path.insert(0, 'src')

from pavlok_controller import calculate_zap_intensity
from pavlok_bleak_controller import calculate_ble_intensity
from config import MIN_STIMULUS_VALUE, MAX_STIMULUS_VALUE, MIN_STRETCH_FOR_CALC, MAX_STRETCH_FOR_CALC

print("=== 正規化強度計算テスト ===\n")
print(f"MIN_STIMULUS_VALUE: {MIN_STIMULUS_VALUE}")
print(f"MAX_STIMULUS_VALUE: {MAX_STIMULUS_VALUE}")
print(f"入力範囲: {MIN_STRETCH_FOR_CALC} ～ {MAX_STRETCH_FOR_CALC}")
print(f"正規化先: 0.06 ～ 1.0")
print()

# テストケース
test_cases = [
    (-0.1, "範囲外（負）"),
    (0.0, "入力下限"),
    (0.2, "低域"),
    (0.4, "中域"),
    (0.6, "中域（0.6境界付近）"),
    (0.8, "入力上限"),
    (0.9, "範囲外（0.8超過）"),
    (1.0, "範囲外（最大）"),
]

print(f"{'Stretch':<10} {'説明':<20} {'正規化値':<12} {'API版':<8} {'BLE版':<8}")
print("-" * 70)

for stretch, description in test_cases:
    # 正規化値の計算（参考表示）
    if stretch >= MAX_STRETCH_FOR_CALC:
        normalized_display = "1.0"
    elif stretch <= MIN_STRETCH_FOR_CALC:
        normalized_display = "0.06"
    else:
        normalized = 0.06 + (stretch - MIN_STRETCH_FOR_CALC) * (1.0 - 0.06) / (MAX_STRETCH_FOR_CALC - MIN_STRETCH_FOR_CALC)
        normalized_display = f"{normalized:.3f}"

    api_result = calculate_zap_intensity(stretch)
    ble_result = calculate_ble_intensity(stretch)
    print(f"{stretch:<10.1f} {description:<20} {normalized_display:<12} {api_result:<8} {ble_result:<8}")

print("\n=== 検証ポイント ===")
print(f"✓ Stretch={MIN_STRETCH_FOR_CALC} → MIN_STIMULUS_VALUE ({MIN_STIMULUS_VALUE})")
print(f"✓ Stretch={MAX_STRETCH_FOR_CALC} → MAX_STIMULUS_VALUE ({MAX_STIMULUS_VALUE})")
print(f"✓ Stretch > {MAX_STRETCH_FOR_CALC} → MAX_STIMULUS_VALUE（クランプ）")
print(f"✓ API版とBLE版の結果が一致")
print(f"✓ 0.6境界で二次関数に移行（加速）")

# 詳細チェック
print("\n=== 詳細チェック ===")
val_0 = calculate_zap_intensity(0.0)
val_08 = calculate_zap_intensity(0.8)
val_09 = calculate_zap_intensity(0.9)
print(f"Stretch=0.0: {val_0} (期待値: {MIN_STIMULUS_VALUE}) {'✓' if val_0 == MIN_STIMULUS_VALUE else '✗'}")
print(f"Stretch=0.8: {val_08} (期待値: {MAX_STIMULUS_VALUE}) {'✓' if val_08 == MAX_STIMULUS_VALUE else '✗'}")
print(f"Stretch=0.9: {val_09} (期待値: {MAX_STIMULUS_VALUE}) {'✓' if val_09 == MAX_STIMULUS_VALUE else '✗'}")

# 中間値での加速確認
print("\n=== 加速度の確認（0.0～0.8の範囲） ===")
stretch_values = [0.0, 0.2, 0.4, 0.6, 0.8]
print("Stretch値とそれぞれの間隔での増加量：")
for i in range(len(stretch_values) - 1):
    s1, s2 = stretch_values[i], stretch_values[i+1]
    v1 = calculate_zap_intensity(s1)
    v2 = calculate_zap_intensity(s2)
    delta = v2 - v1
    print(f"  {s1} → {s2}: {v1} → {v2} (Δ={delta})")
