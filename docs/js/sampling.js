// DEM(標高配列)から側線に沿って標高値をサンプリングするコアロジック。
// Pythonローカル版の src/dem_profile/sampling.py の考え方をそのまま移植したもの。
// DOM/fetchには一切依存しないので、Node(`node --test`)でもブラウザでも動く。

/**
 * 始点(距離0)から終点(距離L)までinterval間隔の距離配列を作る。終点は必ず含める。
 * @param {[number, number]} startXY
 * @param {[number, number]} endXY
 * @param {number} interval
 * @returns {number[]}
 */
export function generateStations(startXY, endXY, interval) {
  if (interval <= 0) {
    throw new Error("interval は正の値である必要があります。");
  }
  const [x0, y0] = startXY;
  const [x1, y1] = endXY;
  const length = Math.hypot(x1 - x0, y1 - y0);
  if (length === 0) {
    throw new Error("start と end が同一座標です。");
  }
  const stations = [];
  for (let d = 0; d < length; d += interval) {
    stations.push(d);
  }
  if (stations.length === 0 || stations[stations.length - 1] !== length) {
    stations.push(length);
  }
  return stations;
}

/**
 * デコード済みDEM(geotiff-loader.jsの戻り値)から、start-endを結ぶ側線上を
 * intervalごとにサンプリングする。範囲外・nodataの点はz=NaNになる。
 *
 * @param {{data: Float32Array, width: number, height: number, bbox: number[], resX: number, resY: number, nodata: number|null}} dem
 * @param {[number, number]} startXY
 * @param {[number, number]} endXY
 * @param {number} interval
 * @returns {{distance: number, x: number, y: number, z: number}[]}
 */
export function sampleDemAlongLine(dem, startXY, endXY, interval) {
  const [x0, y0] = startXY;
  const [x1, y1] = endXY;
  const stations = generateStations(startXY, endXY, interval);
  const length = stations[stations.length - 1];
  const [left, bottom, right, top] = dem.bbox;

  return stations.map((distance) => {
    const t = distance / length;
    const x = x0 + t * (x1 - x0);
    const y = y0 + t * (y1 - y0);

    const inBounds = x >= left && x <= right && y >= bottom && y <= top;
    if (!inBounds) {
      return { distance, x, y, z: NaN };
    }

    let col = Math.floor((x - left) / dem.resX);
    let row = Math.floor((top - y) / dem.resY);
    col = Math.min(Math.max(col, 0), dem.width - 1);
    row = Math.min(Math.max(row, 0), dem.height - 1);

    const value = dem.data[row * dem.width + col];
    const z = dem.nodata != null && value === dem.nodata ? NaN : value;
    return { distance, x, y, z };
  });
}

/**
 * 複数DEMの断面データをロング形式の配列にまとめる。
 * @param {{name: string, dem: object}[]} namedDems
 * @returns {{dem: string, distance: number, x: number, y: number, z: number}[]}
 */
export function buildProfileData(namedDems, startXY, endXY, interval) {
  return namedDems.flatMap(({ name, dem }) =>
    sampleDemAlongLine(dem, startXY, endXY, interval).map((row) => ({
      dem: name,
      ...row,
    }))
  );
}
