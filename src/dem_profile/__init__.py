"""DEM断面図(地形プロファイル)ツール。

複数のDEM(GeoTIFF)から任意の側線に沿った標高値を抽出し、地形断面図として
比較表示するためのパッケージ。sampling(抽出) / plotting(描画) / hillshade(陰影図) /
transect_session(陰影図クリック・断面図表示・保存の対話GUI) /
cli・pick_transect・pick_transect_gui(実行)のモジュールに分かれている。
"""

from dem_profile.hillshade import compute_hillshade
from dem_profile.plotting import plot_profiles
from dem_profile.sampling import build_profile_dataframe, sample_dem_along_line, validate_crs

__all__ = [
    "build_profile_dataframe",
    "sample_dem_along_line",
    "validate_crs",
    "plot_profiles",
    "compute_hillshade",
    "main",
]


def main() -> None:
    from dem_profile.cli import main as cli_main

    cli_main()
