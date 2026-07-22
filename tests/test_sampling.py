"""sampling.py の単体テスト。

実データのDEMではなく、rasterioで生成する小さな合成GeoTIFF(既知のz値パターン)
を使い、サンプリング結果が期待通りになることを確認する。
"""

from __future__ import annotations

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from dem_profile.sampling import (
    CrsMismatchError,
    build_profile_dataframe,
    sample_dem_along_line,
    validate_crs,
)

NODATA = -9999.0


def _write_ramp_dem(path, epsg: int = 6675) -> None:
    """10x10、1m解像度の合成DEMを書き出す。z値は列番号と同じ(列8だけnodata)。"""
    width = height = 10
    data = np.tile(np.arange(width, dtype="float32"), (height, 1))
    data[:, 8] = NODATA
    transform = from_origin(0, 10, 1, 1)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=width,
        height=height,
        count=1,
        dtype="float32",
        crs=f"EPSG:{epsg}",
        transform=transform,
        nodata=NODATA,
    ) as ds:
        ds.write(data, 1)


def test_sample_dem_along_line_returns_expected_z(tmp_path):
    dem_path = tmp_path / "ramp.tif"
    _write_ramp_dem(dem_path)

    df = sample_dem_along_line(dem_path, (0.5, 5.0), (9.5, 5.0), interval=1.0)

    assert list(df["distance"]) == pytest.approx(list(range(10)))
    expected = [c if c != 8 else np.nan for c in range(10)]
    np.testing.assert_allclose(df["z"], expected, equal_nan=True)


def test_sample_dem_along_line_out_of_bounds_is_nan(tmp_path):
    dem_path = tmp_path / "ramp.tif"
    _write_ramp_dem(dem_path)

    # 側線の始点(-5,5)はラスタ範囲外(x>=0)なのでNaNになるはず。
    df = sample_dem_along_line(dem_path, (-5.0, 5.0), (5.0, 5.0), interval=5.0)

    assert np.isnan(df.loc[df["distance"] == 0.0, "z"]).all()
    assert not df["z"].iloc[1:].isna().any()


def test_sample_dem_along_line_zero_length_raises(tmp_path):
    dem_path = tmp_path / "ramp.tif"
    _write_ramp_dem(dem_path)

    with pytest.raises(ValueError):
        sample_dem_along_line(dem_path, (1.0, 1.0), (1.0, 1.0), interval=1.0)


def test_validate_crs_raises_on_mismatch(tmp_path):
    good = tmp_path / "good.tif"
    bad = tmp_path / "bad.tif"
    _write_ramp_dem(good, epsg=6675)
    _write_ramp_dem(bad, epsg=4326)

    with pytest.raises(CrsMismatchError):
        validate_crs([good, bad])


def test_build_profile_dataframe_long_format(tmp_path):
    a = tmp_path / "a.tif"
    b = tmp_path / "b.tif"
    _write_ramp_dem(a)
    _write_ramp_dem(b)

    df = build_profile_dataframe([a, b], (0.5, 5.0), (9.5, 5.0), interval=1.0)

    assert set(df["dem"]) == {"a.tif", "b.tif"}
    assert len(df) == 20
    assert list(df.columns) == ["dem", "distance", "x", "y", "z"]


def test_build_profile_dataframe_uses_custom_names_when_given(tmp_path):
    a = tmp_path / "a.tif"
    b = tmp_path / "b.tif"
    _write_ramp_dem(a)
    _write_ramp_dem(b)

    df = build_profile_dataframe(
        [a, b], (0.5, 5.0), (9.5, 5.0), interval=1.0, names=["震災前", "震災後"]
    )

    assert set(df["dem"]) == {"震災前", "震災後"}


def test_build_profile_dataframe_rejects_mismatched_names_length(tmp_path):
    a = tmp_path / "a.tif"
    _write_ramp_dem(a)

    with pytest.raises(ValueError):
        build_profile_dataframe([a], (0.5, 5.0), (9.5, 5.0), interval=1.0, names=["x", "y"])
