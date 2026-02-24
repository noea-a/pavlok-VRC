#!/usr/bin/env python3
"""
Zap 強度計算グラフを生成するスクリプト
Stretch 0.0～0.8 の範囲で強度変化を可視化
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

import matplotlib
matplotlib.use('Agg')  # GUI不要、ファイル出力のみ
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.pyplot as plt
import numpy as np
from pavlok_controller import calculate_zap_intensity
from config import (
    MIN_STIMULUS_VALUE, MAX_STIMULUS_VALUE,
    MIN_STRETCH_PLATEAU, MAX_STRETCH_FOR_CALC,
    NONLINEAR_SWITCH_POSITION_PERCENT, INTENSITY_AT_SWITCH_PERCENT
)

# 出力ディレクトリを準備
script_dir = os.path.dirname(__file__)
output_dir = os.path.join(script_dir, 'graphs')
os.makedirs(output_dir, exist_ok=True)

# ========== グラフ描画 ==========

# Stretch値の配列を生成（0.0～1.0、0.01刻み）
stretch_values = np.arange(0.0, 1.01, 0.01)

# 各Stretch値に対応する強度を計算
intensity_values = [calculate_zap_intensity(s) for s in stretch_values]

# グラフ作成
fig, ax = plt.subplots(figsize=(10, 6))

# メインの曲線を描画
ax.plot(stretch_values, intensity_values, 'b-', linewidth=2.5, label='Zap Intensity Curve')

# キー座標をマーカー付きでプロット（config から動的に生成）
switch_stretch = MIN_STRETCH_PLATEAU + (NONLINEAR_SWITCH_POSITION_PERCENT / 100.0) * (MAX_STRETCH_FOR_CALC - MIN_STRETCH_PLATEAU)

key_stretches = [
    0.0,
    MIN_STRETCH_PLATEAU,
    switch_stretch,
    MAX_STRETCH_FOR_CALC
]
key_points = []

for stretch in key_stretches:
    intensity = calculate_zap_intensity(stretch)
    if stretch == 0.0:
        label = f'{stretch:.2f}: MIN'
    elif stretch == MIN_STRETCH_PLATEAU:
        label = f'{stretch:.2f}: Plateau'
    elif stretch == switch_stretch:
        label = f'{stretch:.2f}: Switch({NONLINEAR_SWITCH_POSITION_PERCENT}%)'
    elif stretch == MAX_STRETCH_FOR_CALC:
        label = f'{stretch:.2f}: MAX'
    else:
        label = f'{stretch:.2f}'
    key_points.append((stretch, intensity, label))

for stretch, intensity, label in key_points:
    ax.plot(stretch, intensity, 'ro', markersize=8)
    ax.annotate(label,
                xy=(stretch, intensity),
                xytext=(5, 5),
                textcoords='offset points',
                fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.3))

# グラフの設定
ax.set_xlabel('Stretch Value (0.0 - 1.0)', fontsize=12, fontweight='bold')
ax.set_ylabel('Zap Intensity', fontsize=12, fontweight='bold')
ax.set_title('Zap Intensity Curve\n(Linear + Quadratic with Low/High Side Plateau)',
             fontsize=13, fontweight='bold')

# グリッド
ax.grid(True, alpha=0.3, linestyle='--')

# 軸範囲（固定値で統一表示）
ax.set_xlim(-0.02, 1.02)
ax.set_ylim(-2, 102)

# 凡例
ax.legend(loc='lower right', fontsize=10)

# レイアウト調整
plt.tight_layout()

# PNG ファイルに保存
output_file = os.path.join(output_dir, 'zap_intensity_curve.png')
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"✓ Graph saved: {output_file}")

# ========== テーブル出力 ==========
print("\n=== Zap Intensity Calculation Table ===")
print(f"{'Stretch':<10} {'Intensity':<12} {'Delta':<8}")
print("-" * 30)

prev_intensity = None
for stretch, intensity in zip(stretch_values[::10], intensity_values[::10]):  # 10刻みで表示
    if prev_intensity is not None:
        delta = intensity - prev_intensity
        print(f"{stretch:<10.2f} {intensity:<12.0f} {delta:+.0f}")
    else:
        print(f"{stretch:<10.2f} {intensity:<12.0f} {'—':<8}")
    prev_intensity = intensity
