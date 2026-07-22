"""DEMから側線(トランセクト)に沿って標高値をサンプリングするコアロジック。

将来Web版(GitHub Pages)に移植する際もこのモジュールのロジックをそのまま
流用できるよう、ラスタI/O・幾何計算のみに専念し、プロットやCLIには関与しない。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

DEFAULT_EPSG = 6675


class CrsMismatchError(ValueError):
    """DEMの空間参照系が期待値(既定でEPSG:6675)と一致しない場合。"""


def validate_crs(dem_paths, expected_epsg: int = DEFAULT_EPSG) -> None:
    """各DEMのCRSがexpected_epsgと一致することを確認する。

    一致しないDEMがあれば CrsMismatchError を送出する。
    """
    mismatched = []
    for path in dem_paths:
        with rasterio.open(path) as ds:
            # confidence_threshold を下げているのは、実際のDEMのWKTがpyproj内蔵の
            # EPSG定義と完全一致(既定の閾値70)しないことがあるため。TOWGS84等の
            # 付随パラメータの表現差であり、投影自体は同一とみなせる。
            epsg = (
                ds.crs.to_epsg(confidence_threshold=20) if ds.crs is not None else None
            )
            if epsg != expected_epsg:
                mismatched.append((str(path), epsg))
    if mismatched:
        details = ", ".join(f"{p} (EPSG:{e})" for p, e in mismatched)
        raise CrsMismatchError(
            f"期待するCRS(EPSG:{expected_epsg})と一致しないDEMがあります: {details}"
        )


def _generate_stations(start_xy, end_xy, interval: float) -> np.ndarray:
    """始点(距離0)から終点(距離L)までinterval間隔の距離配列を作る。終点は必ず含める。"""
    if interval <= 0:
        raise ValueError("interval は正の値である必要があります。")
    x0, y0 = start_xy
    x1, y1 = end_xy
    length = float(np.hypot(x1 - x0, y1 - y0))
    if length == 0:
        raise ValueError("start と end が同一座標です。")
    stations = np.arange(0.0, length, interval)
    if stations[-1] != length:
        stations = np.append(stations, length)
    return stations


def sample_dem_along_line(dem_path, start_xy, end_xy, interval: float) -> pd.DataFrame:
    """1枚のDEMについて、start_xy-end_xyを結ぶ側線上をintervalごとにサンプリングする。

    戻り値は distance, x, y, z の列を持つDataFrame。
    範囲外・nodataの点は z=NaN になる(折れ線グラフでは自然に途切れる)。
    """
    x0, y0 = start_xy
    x1, y1 = end_xy
    stations = _generate_stations(start_xy, end_xy, interval)
    length = stations[-1]
    t = stations / length
    xs = x0 + t * (x1 - x0)
    ys = y0 + t * (y1 - y0)

    with rasterio.open(dem_path) as ds:
        nodata = ds.nodata
        bounds = ds.bounds
        zs = np.full(len(stations), np.nan, dtype="float64")
        in_bounds = (
            (xs >= bounds.left) & (xs <= bounds.right)
            & (ys >= bounds.bottom) & (ys <= bounds.top)
        )
        coords = list(zip(xs[in_bounds], ys[in_bounds]))
        if coords:
            sampled = np.array([v[0] for v in ds.sample(coords)], dtype="float64")
            if nodata is not None:
                sampled = np.where(
                    sampled.astype("float32") == np.float32(nodata), np.nan, sampled
                )
            zs[in_bounds] = sampled

    return pd.DataFrame({"distance": stations, "x": xs, "y": ys, "z": zs})


def build_profile_dataframe(dem_paths, start_xy, end_xy, interval: float, names=None) -> pd.DataFrame:
    """複数DEMの断面データをロング形式で1つのDataFrameにまとめる。

    列: dem(凡例名。既定はファイル名), distance, x, y, z

    `names`はdem_pathsと同じ長さの表示名リスト(任意)。指定すればdem列(凡例名)に
    ファイル名の代わりに使う。省略時は従来通りファイル名を使う。
    """
    if names is not None and len(names) != len(dem_paths):
        raise ValueError("names は dem_paths と同じ長さである必要があります。")
    validate_crs(dem_paths)
    frames = []
    for i, path in enumerate(dem_paths):
        df = sample_dem_along_line(path, start_xy, end_xy, interval)
        df.insert(0, "dem", names[i] if names is not None else Path(path).name)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)
