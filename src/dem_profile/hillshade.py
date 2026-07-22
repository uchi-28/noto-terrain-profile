"""DEMから陰影図(hillshade)を計算する。

側線を選ぶためのGUI(`transect_session.py`)から使われることを想定し、表示・クリック処理には
関与しない。表示速度のため既定で間引いて読み込むが、`extent`は常に元DEMの実際の
地理座標範囲(bounds)を返すため、間引いてもクリック位置と実座標の対応関係は崩れない。
"""

from __future__ import annotations

import numpy as np
import rasterio
from matplotlib.colors import LightSource
from rasterio.enums import Resampling


def compute_hillshade(
    dem_path,
    max_pixels: int = 2000,
    azdeg: float = 315,
    altdeg: float = 45,
):
    """DEMを読み込み、陰影図(0〜1の輝度配列)と地理座標extentを返す。

    Returns:
        (hillshade, extent): hillshade は2次元ndarray(nodata部分はnan)。
        extent は (left, right, bottom, top) で、matplotlibのimshow(extent=...)に
        そのまま渡せる。
    """
    with rasterio.open(dem_path) as ds:
        scale = min(1.0, max_pixels / max(ds.width, ds.height))
        out_height = max(1, round(ds.height * scale))
        out_width = max(1, round(ds.width * scale))
        elevation = ds.read(
            1, out_shape=(out_height, out_width), resampling=Resampling.average
        ).astype("float64")
        if ds.nodata is not None:
            elevation = np.where(
                elevation.astype("float32") == np.float32(ds.nodata), np.nan, elevation
            )
        bounds = ds.bounds
        # 間引き後の解像度に合わせたセルサイズ(実距離に対するスロープ計算に必要)。
        dx = (bounds.right - bounds.left) / out_width
        dy = (bounds.top - bounds.bottom) / out_height

    valid = elevation[~np.isnan(elevation)]
    fill_value = float(valid.min()) if valid.size else 0.0
    ls = LightSource(azdeg=azdeg, altdeg=altdeg)
    hillshade = ls.hillshade(np.nan_to_num(elevation, nan=fill_value), dx=dx, dy=dy)
    hillshade = np.where(np.isnan(elevation), np.nan, hillshade)

    extent = (bounds.left, bounds.right, bounds.bottom, bounds.top)
    return hillshade, extent
