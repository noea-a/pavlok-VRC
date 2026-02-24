#!/usr/bin/env python3
"""
非線形強度計算のテストスクリプト
"""

import sys
sys.path.insert(0, 'src')

from pavlok_controller import calculate_zap_intensity
from config import MIN_STIMULUS_VALUE, MAX_STIMULUS_VALUE, STRETCH_NONLINEAR_THRESHOLD, INTENSITY_AT_STRETCH_06, MIN_STRETCH_THRESHOLD, MIN_STRETCH_PLATEAU

print("=== 非線形強度計算テスト ===\n")
print(f"MIN_STIMULUS_VALUE: {MIN_STIMULUS_VALUE}")
print(f"MAX_STIMULUS_VALUE: {MAX_STIMULUS_VALUE}")
print(f"MIN_STRETCH_THRESHOLD: {MIN_STRETCH_THRESHOLD}")
print(f"MIN_STRETCH_PLATEAU: {MIN_STRETCH_PLATEAU}")
print(f"STRETCH_NONLINEAR_THRESHOLD: {STRETCH_NONLINEAR_THRESHOLD}")
print(f"INTENSITY_AT_STRETCH_06: {INTENSITY_AT_STRETCH_06}")
print()

# テストケース
test_cases = [
    (0.0, "最小値"),
    (0.06, "閾値"),
    (0.3, "線形領域の中間"),
    (0.6, "線形→二次関数の境界"),
    (0.7, "二次関数領域"),
    (0.8, "二次関数領域"),
    (0.9, "二次関数領域"),
    (1.0, "最大値"),
]

print(f"{'Stretch':<10} {'説明':<20} {'強度':<8}")
print("-" * 40)

for stretch, description in test_cases:
    result = calculate_zap_intensity(stretch)
    print(f"{stretch:<10.2f} {description:<20} {result:<8}")

print("\n=== 検証ポイント ===")
print(f"✓ Stretch=0.05 → 0 (MIN_STRETCH_THRESHOLD {MIN_STRETCH_THRESHOLD} 未満)")
print(f"✓ Stretch=0.1 → MIN_STIMULUS_VALUE ({MIN_STIMULUS_VALUE}) (低側プラトー)")
print(f"✓ Stretch=0.2 → MIN_STIMULUS_VALUE ({MIN_STIMULUS_VALUE}) (低側プラトー境界)")
print(f"✓ Stretch=0.6 → INTENSITY_AT_STRETCH_06 ({INTENSITY_AT_STRETCH_06})")
print(f"✓ Stretch=1.0 → MAX_STIMULUS_VALUE ({MAX_STIMULUS_VALUE})")
print("✓ 0.6以降で加速度的に増加")

# 詳細チェック
print("\n=== 詳細チェック ===")
val_05 = calculate_zap_intensity(0.05)
val_10 = calculate_zap_intensity(0.1)
val_20 = calculate_zap_intensity(0.2)
val_06 = calculate_zap_intensity(0.6)
val_80 = calculate_zap_intensity(0.8)
val_100 = calculate_zap_intensity(1.0)
print(f"Stretch=0.05: {val_05} (期待値: 0) {'✓' if val_05 == 0 else '✗'}")
print(f"Stretch=0.1: {val_10} (期待値: {MIN_STIMULUS_VALUE}) {'✓' if val_10 == MIN_STIMULUS_VALUE else '✗'}")
print(f"Stretch=0.2: {val_20} (期待値: {MIN_STIMULUS_VALUE}) {'✓' if val_20 == MIN_STIMULUS_VALUE else '✗'}")
print(f"Stretch=0.6: {val_06} (期待値: {INTENSITY_AT_STRETCH_06}) {'✓' if val_06 == INTENSITY_AT_STRETCH_06 else '✗'}")
print(f"Stretch=0.8: {val_80} (期待値: {MAX_STIMULUS_VALUE}) {'✓' if val_80 == MAX_STIMULUS_VALUE else '✗'}")
print(f"Stretch=1.0: {val_100} (期待値: {MAX_STIMULUS_VALUE}) {'✓' if val_100 == MAX_STIMULUS_VALUE else '✗'}")

# 二次関数の加速確認
print("\n=== 加速度の確認 ===")
stretch_values = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
print("Stretch値とそれぞれの間隔での増加量：")
for i in range(len(stretch_values) - 1):
    s1, s2 = stretch_values[i], stretch_values[i+1]
    v1 = calculate_zap_intensity(s1)
    v2 = calculate_zap_intensity(s2)
    delta = v2 - v1
    print(f"  {s1} → {s2}: {v1} → {v2} (Δ={delta})")
