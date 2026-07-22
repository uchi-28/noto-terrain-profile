"""コマンドラインエントリポイント。

使用例:
    uv run python -m dem_profile.cli \\
        --dem dem/bfeq_pref_07ed694_67ee703.tif \\
        --dem dem/afeq_mliti_07ed694_67ee703.tif \\
        --dem dem/afst_07ed694_67ee703.tif \\
        --start -1500 158000 --end 1500 158500 --interval 5 \\
        --out-csv out/profile.csv --out-png out/profile.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dem_profile.plotting import plot_profiles
from dem_profile.sampling import DEFAULT_EPSG, build_profile_dataframe


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="複数DEMの地形断面図(横断面プロファイル)を作成する。")
    parser.add_argument(
        "--dem", action="append", required=True, dest="dem_paths",
        help="DEM(GeoTIFF)のパス。複数回指定して複数DEMを重ねて比較できる。",
    )
    parser.add_argument(
        "--start", nargs=2, type=float, required=True, metavar=("X", "Y"),
        help=f"側線の始点座標 (EPSG:{DEFAULT_EPSG})",
    )
    parser.add_argument(
        "--end", nargs=2, type=float, required=True, metavar=("X", "Y"),
        help=f"側線の終点座標 (EPSG:{DEFAULT_EPSG})",
    )
    parser.add_argument("--interval", type=float, required=True, help="サンプリング間隔 (m)")
    parser.add_argument("--out-csv", type=Path, default=None, help="抽出したテーブルの出力先CSVパス(任意)")
    parser.add_argument("--out-png", type=Path, required=True, help="断面図PNGの出力先パス")
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    df = build_profile_dataframe(
        args.dem_paths, tuple(args.start), tuple(args.end), args.interval
    )

    if args.out_csv is not None:
        args.out_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(args.out_csv, index=False, encoding="utf-8-sig")

    args.out_png.parent.mkdir(parents=True, exist_ok=True)
    plot_profiles(df, args.out_png)


if __name__ == "__main__":
    main()
