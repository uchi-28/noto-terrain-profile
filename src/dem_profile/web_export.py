"""Web公開用に、DEMを指定解像度まで間引いて書き出す。

GitHub Pagesは静的ホスティングのみで、通常のgit push(Git LFSなし)では
1ファイル100MBが上限。元DEMは0.5m解像度で数百MB〜600MB超あり、そのままでは
公開できない。断面図の用途には0.5m解像度は過剰なため、間引いたDEMを別途生成する。

`hillshade.py`と同じ「out_shape + Resampling.average で間引いて読み、CRS/nodataは
そのまま引き継ぐ」パターンを使う。
"""

from __future__ import annotations

from pathlib import Path

import rasterio
from rasterio.enums import Resampling


def resample_dem(src_path, dst_path, target_resolution: float) -> None:
    """src_pathのDEMをtarget_resolution(m)まで間引き、dst_pathにGeoTIFFとして書き出す。

    target_resolutionが元の解像度以下の場合は何もしない(それ以上細かくはできない)。
    """
    with rasterio.open(src_path) as src:
        src_res_x, src_res_y = src.res
        scale_x = min(1.0, src_res_x / target_resolution)
        scale_y = min(1.0, src_res_y / target_resolution)
        out_width = max(1, round(src.width * scale_x))
        out_height = max(1, round(src.height * scale_y))

        data = src.read(
            1, out_shape=(out_height, out_width), resampling=Resampling.average
        )

        transform = src.transform * src.transform.scale(
            src.width / out_width, src.height / out_height
        )

        Path(dst_path).parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(
            dst_path,
            "w",
            driver="GTiff",
            width=out_width,
            height=out_height,
            count=1,
            dtype=data.dtype,
            crs=src.crs,
            transform=transform,
            nodata=src.nodata,
            compress="DEFLATE",
            predictor=3 if data.dtype.kind == "f" else 2,
        ) as dst:
            dst.write(data, 1)
