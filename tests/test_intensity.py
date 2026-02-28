"""
intensity.py の単体テスト

外部依存ゼロ：settings / config を一切読まず、
IntensityConfig を直接構築してテストする。
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from intensity import IntensityConfig, calculate_intensity, normalize_for_display

# ===== テスト用設定（実際の default.toml と同じ値） =====
DEFAULT_CFG = IntensityConfig(
    min_stimulus_value=15,
    max_stimulus_value=70,
    min_stretch_threshold=0.03,
    min_stretch_plateau=0.12,
    min_stretch_for_calc=0.0,
    max_stretch_for_calc=0.8,
    nonlinear_switch_position_percent=50,
    intensity_at_switch_percent=20,
)

# =========================================================
# calculate_intensity
# =========================================================

class TestCalculateIntensity:

    def test_below_threshold_returns_zero(self):
        """min_stretch_threshold 未満は 0 を返す"""
        assert calculate_intensity(0.0, DEFAULT_CFG) == 0
        assert calculate_intensity(0.02, DEFAULT_CFG) == 0

    def test_at_threshold_boundary(self):
        """min_stretch_threshold ちょうどはまだ 0"""
        assert calculate_intensity(DEFAULT_CFG.min_stretch_threshold - 0.001, DEFAULT_CFG) == 0

    def test_low_plateau(self):
        """min_stretch_threshold〜min_stretch_plateau は min_stimulus_value で固定"""
        assert calculate_intensity(0.03, DEFAULT_CFG) == DEFAULT_CFG.min_stimulus_value
        assert calculate_intensity(0.07, DEFAULT_CFG) == DEFAULT_CFG.min_stimulus_value
        assert calculate_intensity(0.12, DEFAULT_CFG) == DEFAULT_CFG.min_stimulus_value

    def test_high_plateau(self):
        """max_stretch_for_calc 以上は max_stimulus_value で固定"""
        assert calculate_intensity(0.8, DEFAULT_CFG) == DEFAULT_CFG.max_stimulus_value
        assert calculate_intensity(1.0, DEFAULT_CFG) == DEFAULT_CFG.max_stimulus_value
        assert calculate_intensity(9.9, DEFAULT_CFG) == DEFAULT_CFG.max_stimulus_value

    def test_slope1_is_monotone(self):
        """min_stretch_plateau〜switch 間で単調増加"""
        # switch 地点 = 0.12 + 0.5 * (0.8 - 0.12) = 0.12 + 0.34 = 0.46
        values = [calculate_intensity(s, DEFAULT_CFG) for s in [0.12, 0.2, 0.3, 0.46]]
        assert values == sorted(values)

    def test_slope2_is_monotone(self):
        """switch〜max 間で単調増加"""
        values = [calculate_intensity(s, DEFAULT_CFG) for s in [0.46, 0.55, 0.65, 0.8]]
        assert values == sorted(values)

    def test_result_within_range(self):
        """結果は常に 0 または [min, max] 内"""
        import numpy as np
        for s in np.arange(0.0, 1.01, 0.01):
            result = calculate_intensity(float(s), DEFAULT_CFG)
            assert result == 0 or DEFAULT_CFG.min_stimulus_value <= result <= DEFAULT_CFG.max_stimulus_value

    def test_switch_point_intensity(self):
        """switch 地点での強度が intensity_at_switch_percent に近い"""
        # switch_stretch = 0.12 + 0.5 * (0.8 - 0.12) = 0.46
        # intensity_at_switch = 15 + 0.2 * (70 - 15) = 15 + 11 = 26
        switch_stretch = 0.12 + 0.5 * (0.8 - 0.12)
        result = calculate_intensity(switch_stretch, DEFAULT_CFG)
        assert result == 26

    def test_custom_config(self):
        """異なる設定値で正しく動作する"""
        cfg = IntensityConfig(
            min_stimulus_value=10,
            max_stimulus_value=50,
            min_stretch_threshold=0.05,
            min_stretch_plateau=0.1,
            min_stretch_for_calc=0.0,
            max_stretch_for_calc=1.0,
            nonlinear_switch_position_percent=50,
            intensity_at_switch_percent=50,
        )
        assert calculate_intensity(0.0, cfg) == 0
        assert calculate_intensity(0.1, cfg) == 10
        assert calculate_intensity(1.0, cfg) == 50

    def test_slope2_is_steeper_than_slope1(self):
        """傾き2は傾き1より急峻（単位 stretch あたりの強度増加が大きい）"""
        delta = 0.05
        # 傾き1 の区間で計算
        s1a, s1b = 0.2, 0.2 + delta
        slope1 = calculate_intensity(s1b, DEFAULT_CFG) - calculate_intensity(s1a, DEFAULT_CFG)

        # 傾き2 の区間で計算（switch 後）
        s2a, s2b = 0.55, 0.55 + delta
        slope2 = calculate_intensity(s2b, DEFAULT_CFG) - calculate_intensity(s2a, DEFAULT_CFG)

        assert slope2 > slope1, f"slope2={slope2} should be > slope1={slope1}"


# =========================================================
# normalize_for_display
# =========================================================

class TestNormalizeForDisplay:

    def test_min_returns_min(self):
        """min_stimulus_value → min_stimulus_value"""
        assert normalize_for_display(DEFAULT_CFG.min_stimulus_value, DEFAULT_CFG) == DEFAULT_CFG.min_stimulus_value

    def test_max_returns_100(self):
        """max_stimulus_value → 100"""
        assert normalize_for_display(DEFAULT_CFG.max_stimulus_value, DEFAULT_CFG) == 100

    def test_below_min_clamps_to_min(self):
        """min 未満はクランプ"""
        assert normalize_for_display(0, DEFAULT_CFG) == DEFAULT_CFG.min_stimulus_value

    def test_above_max_clamps_to_100(self):
        """max 超過はクランプ"""
        assert normalize_for_display(200, DEFAULT_CFG) == 100

    def test_midpoint(self):
        """中間値が線形変換されている"""
        mid_internal = (DEFAULT_CFG.min_stimulus_value + DEFAULT_CFG.max_stimulus_value) // 2
        result = normalize_for_display(mid_internal, DEFAULT_CFG)
        # min=15, max=70 → mid_internal=42
        # 期待: 15 + (42-15)/(70-15) * (100-15) = 15 + 27/55 * 85 ≈ 57
        assert 50 <= result <= 65

    def test_monotone(self):
        """内部値が増えると表示値も増える"""
        values = [normalize_for_display(v, DEFAULT_CFG)
                  for v in range(DEFAULT_CFG.min_stimulus_value, DEFAULT_CFG.max_stimulus_value + 1, 5)]
        assert values == sorted(values)
