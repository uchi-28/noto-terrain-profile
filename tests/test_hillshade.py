"""hillshade.py の単体テスト。

GUIでのクリック操作(transect_session.py)は対話環境が前提のため自動テスト対象外。
ここでは陰影図の計算ロジック(compute_hillshade)のみを検証する。
"""

from __future__ import annotations

import numpy as np
import rasterio
from rasterio.transform import from_origin

from dem_profile.hillshade import compute_hillshade

NODATA = -9999.0


def _write_slope_dem(path) -> None:
    """20x20、2m解像度、東西方向に一定勾配を持つ合成DEM(最終列はnodata)。"""
    width = height = 20
    data = np.tile(np.arange(width, dtype="float32") * 5.0, (height, 1))
    data[:, 19] = NODATA
    transform = from_origin(0, 40, 2, 2)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=width,
        height=height,
        count=1,
        dtype="float32",
        crs="EPSG:6675",
        transform=transform,
        nodata=NODATA,
    ) as ds:
        ds.write(data, 1)


def test_compute_hillshade_shape_and_extent(tmp_path):
    dem_path = tmp_path / "slope.tif"
    _write_slope_dem(dem_path)

    hillshade, extent = compute_hillshade(dem_path, max_pixels=2000)

    assert hillshade.shape == (20, 20)
    assert extent == (0.0, 40.0, 0.0, 40.0)


def test_compute_hillshade_values_in_range_and_nodata_is_nan(tmp_path):
    dem_path = tmp_path / "slope.tif"
    _write_slope_dem(dem_path)

    hillshade, _ = compute_hillshade(dem_path, max_pixels=2000)

    valid = hillshade[~np.isnan(hillshade)]
    assert valid.size > 0
    assert valid.min() >= 0.0
    assert valid.max() <= 1.0
    assert np.isnan(hillshade[:, 19]).all()


def test_compute_hillshade_downsamples_to_max_pixels(tmp_path):
    dem_path = tmp_path / "slope.tif"
    _write_slope_dem(dem_path)

    hillshade, extent = compute_hillshade(dem_path, max_pixels=10)

    assert max(hillshade.shape) <= 10
    # 間引いてもextentは元DEMの実座標範囲のまま(クリック座標の対応がずれないことが重要)。
    assert extent == (0.0, 40.0, 0.0, 40.0)
