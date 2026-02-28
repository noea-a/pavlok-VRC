"""
強度計算モジュール

外部状態に依存しない純粋関数のみを提供する。
設定値は IntensityConfig にまとめて渡すので、pytest から任意の値でテスト可能。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class IntensityConfig:
    """強度計算に必要な設定値セット。"""
    min_stimulus_value: int
    max_stimulus_value: int
    min_stretch_threshold: float
    min_stretch_plateau: float
    min_stretch_for_calc: float
    max_stretch_for_calc: float
    nonlinear_switch_position_percent: int
    intensity_at_switch_percent: int

    @staticmethod
    def from_settings() -> "IntensityConfig":
        """現在の settings から IntensityConfig を生成する。"""
        import settings as s_mod
        s = s_mod.settings
        return IntensityConfig(
            min_stimulus_value=s.device.min_stimulus_value,
            max_stimulus_value=s.device.max_stimulus_value,
            min_stretch_threshold=s.logic.min_stretch_threshold,
            min_stretch_plateau=s.logic.min_stretch_plateau,
            min_stretch_for_calc=s.logic.min_stretch_for_calc,
            max_stretch_for_calc=s.logic.max_stretch_for_calc,
            nonlinear_switch_position_percent=s.logic.nonlinear_switch_position_percent,
            intensity_at_switch_percent=s.logic.intensity_at_switch_percent,
        )


def calculate_intensity(stretch: float, cfg: IntensityConfig) -> int:
    """
    Stretch 値（0.0〜1.0）を刺激強度（内部値）に変換する（2段折れ線グラフ）。

    Stretch の範囲と強度の対応：
      < min_stretch_threshold               → 0（刺激なし）
      min_stretch_threshold〜min_stretch_plateau → min_stimulus_value（低プラトー）
      min_stretch_plateau〜switch 地点         → 緩やかに上昇（傾き1）
      switch 地点〜max_stretch_for_calc       → 急峻に上昇（傾き2）
      >= max_stretch_for_calc               → max_stimulus_value（高プラトー）

    Args:
        stretch: PhysBone の Stretch 値（0.0〜1.0）
        cfg: 強度計算設定

    Returns:
        強度値（0 または min_stimulus_value〜max_stimulus_value）
    """
    if stretch < cfg.min_stretch_threshold:
        return 0

    if stretch <= cfg.min_stretch_plateau:
        return cfg.min_stimulus_value

    if stretch >= cfg.max_stretch_for_calc:
        return cfg.max_stimulus_value

    # 折れ線の切り替え地点を計算
    calc_range = cfg.max_stretch_for_calc - cfg.min_stretch_plateau
    switch_stretch = cfg.min_stretch_plateau + (cfg.nonlinear_switch_position_percent / 100.0) * calc_range

    stim_range = cfg.max_stimulus_value - cfg.min_stimulus_value
    intensity_at_switch = cfg.min_stimulus_value + (cfg.intensity_at_switch_percent / 100.0) * stim_range

    if stretch <= switch_stretch:
        # 傾き1: min_stretch_plateau → switch_stretch
        t = (stretch - cfg.min_stretch_plateau) / (switch_stretch - cfg.min_stretch_plateau)
        intensity = cfg.min_stimulus_value + t * (intensity_at_switch - cfg.min_stimulus_value)
    else:
        # 傾き2: switch_stretch → max_stretch_for_calc
        t = (stretch - switch_stretch) / (cfg.max_stretch_for_calc - switch_stretch)
        intensity = intensity_at_switch + t * (cfg.max_stimulus_value - intensity_at_switch)

    return int(max(cfg.min_stimulus_value, min(cfg.max_stimulus_value, intensity)))


def normalize_for_display(intensity: int, cfg: IntensityConfig) -> int:
    """
    Pavlok 内部値（min_stimulus_value〜max_stimulus_value）を
    表示用パーセント（min_stimulus_value〜100）に線形変換する。

    Args:
        intensity: 内部強度値
        cfg: 強度計算設定（min/max_stimulus_value を使用）

    Returns:
        表示用の値（min_stimulus_value〜100）
    """
    if intensity <= cfg.min_stimulus_value:
        return cfg.min_stimulus_value
    if intensity >= cfg.max_stimulus_value:
        return 100
    normalized = cfg.min_stimulus_value + (
        (intensity - cfg.min_stimulus_value)
        / (cfg.max_stimulus_value - cfg.min_stimulus_value)
        * (100 - cfg.min_stimulus_value)
    )
    return int(round(normalized))
