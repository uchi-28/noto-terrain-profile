"""web_export.py の単体テスト。

合成DEM(既知の値パターン)を間引き、出力の解像度・CRS・値が妥当であることを検証する。
"""

from __future__ import annotations

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from dem_profile.web_export import resample_dem


def _write_ramp_dem(path, epsg: int = 6675) -> None:
    """40x40、0.5m解像度の合成DEM。z値は列番号(x方向に沿って線形に増加)。"""
    width = height = 40
    data = np.tile(np.arange(width, dtype="float32"), (height, 1))
    transform = from_origin(0, 20, 0.5, 0.5)
    with rasterio.open(
        path, "w", driver="GTiff", width=width, height=height, count=1,
        dtype="float32", crs=f"EPSG:{epsg}", transform=transform, nodata=-9999.0,
    ) as ds:
        ds.write(data, 1)


def test_resample_dem_reduces_resolution_and_keeps_crs_and_bounds(tmp_path):
    src = tmp_path / "src.tif"
    dst = tmp_path / "dst.tif"
    _write_ramp_dem(src)

    resample_dem(src, dst, target_resolution=2.0)

    with rasterio.open(src) as s, rasterio.open(dst) as d:
        assert d.crs == s.crs
        assert d.nodata == s.nodata
        # 0.5m -> 2.0mなので、幅・高さはおおよそ4分の1になる。
        assert d.width == round(s.width * 0.5 / 2.0)
        assert d.height == round(s.height * 0.5 / 2.0)
        # 実座標の範囲(bounds)は間引いても変わらない。
        assert d.bounds.left == pytest.approx(s.bounds.left)
        assert d.bounds.top == pytest.approx(s.bounds.top)


def test_resample_dem_values_are_reasonable_average(tmp_path):
    src = tmp_path / "src.tif"
    dst = tmp_path / "dst.tif"
    _write_ramp_dem(src)

    resample_dem(src, dst, target_resolution=2.0)

    with rasterio.open(dst) as d:
        data = d.read(1)
        # 元データはx方向に0〜39の線形ランプなので、間引いた後も
        # 全体としての最小値・最大値の範囲は元データの範囲内に収まるはず。
        assert data.min() >= 0.0
        assert data.max() <= 39.0


def test_resample_dem_no_op_when_target_finer_than_source(tmp_path):
    src = tmp_path / "src.tif"
    dst = tmp_path / "dst.tif"
    _write_ramp_dem(src)

    # target_resolution(1.0m) が元の解像度(0.5m)より粗くない(=より細かい)場合、
    # それ以上細かくはできないので元の解像度のまま出力される。
    resample_dem(src, dst, target_resolution=0.1)

    with rasterio.open(src) as s, rasterio.open(dst) as d:
        assert d.width == s.width
        assert d.height == s.height
