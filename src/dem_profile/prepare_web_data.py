"""Web公開用に間引いたDEMを一括生成するCLI。

使用例:
    uv run python -m dem_profile.prepare_web_data \\
        --dem dem/bfeq_pref_07ed694_67ee703.tif \\
        --dem dem/afeq_mliti_07ed694_67ee703.tif \\
        --dem dem/afst_07ed694_67ee703.tif \\
        --target-resolution 2.0 --out-dir docs/data
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dem_profile.web_export import resample_dem


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="DEMをWeb公開向けの解像度まで間引いてGeoTIFFを書き出す。"
    )
    parser.add_argument(
        "--dem", action="append", required=True, dest="dem_paths",
        help="間引く元のDEM(GeoTIFF)のパス。複数回指定可。",
    )
    parser.add_argument(
        "--target-resolution", type=float, default=2.0,
        help="出力解像度(m)。既定は2.0m。",
    )
    parser.add_argument(
        "--out-dir", type=Path, default=Path("docs/data"),
        help="出力先ディレクトリ。既定は docs/data 。",
    )
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    for src in args.dem_paths:
        dst = args.out_dir / Path(src).name
        resample_dem(src, dst, args.target_resolution)
        size_mb = dst.stat().st_size / (1024 * 1024)
        print(f"{src} -> {dst} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
