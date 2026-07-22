"""陰影図をクリックして側線を選び、断面図を作成するCLI。

GUIウィンドウでのクリック操作が必要なため、対話的に実行できる環境(ローカルの
ターミナル等)で実行すること。

使用例:
    uv run python -m dem_profile.pick_transect \\
        --hillshade-dem dem/afeq_mliti_07ed694_67ee703.tif \\
        --dem dem/bfeq_pref_07ed694_67ee703.tif \\
        --dem dem/afeq_mliti_07ed694_67ee703.tif \\
        --dem dem/afst_07ed694_67ee703.tif \\
        --interval 5 \\
        --out-csv out/profile.csv --out-png out/profile.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dem_profile.sampling import DEFAULT_EPSG
from dem_profile.transect_session import run_transect_session


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="陰影図をクリックして側線を選択し、断面図を作成する。"
    )
    parser.add_argument(
        "--hillshade-dem", required=True,
        help=f"陰影図の表示・側線選択に使うDEM(GeoTIFF、EPSG:{DEFAULT_EPSG})",
    )
    parser.add_argument(
        "--dem", action="append", dest="dem_paths",
        help="断面図に重ねるDEM(GeoTIFF)。複数回指定可。省略時は--hillshade-demのみを使う。",
    )
    parser.add_argument("--interval", type=float, required=True, help="サンプリング間隔 (m)")
    parser.add_argument("--out-csv", type=Path, default=None, help="抽出したテーブルの出力先CSVパス(任意)")
    parser.add_argument("--out-png", type=Path, required=True, help="断面図PNGの出力先パス")
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    dem_paths = args.dem_paths or [args.hillshade_dem]
    run_transect_session(
        hillshade_dem=args.hillshade_dem,
        dem_paths=dem_paths,
        interval=args.interval,
        out_csv=args.out_csv,
        out_png=args.out_png,
    )


if __name__ == "__main__":
    main()
