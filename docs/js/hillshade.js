// DEM(標高配列)から陰影(hillshade)を計算する。
// Pythonローカル版のhillshade.py(matplotlib.colors.LightSource)と同じ考え方
// (地表面の法線ベクトルと光源方向ベクトルの内積で照度を求める)をJSで実装したもの。
// DOM依存はないのでNodeでもブラウザでも動く。

/**
 * 標高配列から各セルの陰影強度(0〜1、nodataはNaN)を計算する。
 * @param {{data: Float32Array, width: number, height: number, resX: number, resY: number, nodata: number|null}} dem
 * @param {{azimuth?: number, altitude?: number, vertExaggeration?: number}} [options]
 * @returns {Float32Array}
 */
export function computeHillshade(dem, options = {}) {
  const { azimuth = 315, altitude = 45, vertExaggeration = 1 } = options;
  const { data, width, height, resX, resY, nodata } = dem;

  const azRad = (azimuth * Math.PI) / 180;
  const altRad = (altitude * Math.PI) / 180;
  const lightX = -Math.sin(azRad) * Math.cos(altRad);
  const lightY = -Math.cos(azRad) * Math.cos(altRad);
  const lightZ = Math.sin(altRad);

  const isNodata = (v) => nodata != null && v === nodata;
  const valueAt = (row, col) => {
    const r = Math.min(Math.max(row, 0), height - 1);
    const c = Math.min(Math.max(col, 0), width - 1);
    const v = data[r * width + c];
    return isNodata(v) ? NaN : v;
  };

  const hillshade = new Float32Array(width * height);
  for (let row = 0; row < height; row++) {
    for (let col = 0; col < width; col++) {
      const center = valueAt(row, col);
      if (Number.isNaN(center)) {
        hillshade[row * width + col] = NaN;
        continue;
      }

      const west = valueAt(row, col - 1);
      const east = valueAt(row, col + 1);
      const north = valueAt(row - 1, col);
      const south = valueAt(row + 1, col);

      const dzdx =
        Number.isNaN(west) || Number.isNaN(east)
          ? 0
          : ((east - west) / (2 * resX)) * vertExaggeration;
      const dzdy =
        Number.isNaN(north) || Number.isNaN(south)
          ? 0
          : ((north - south) / (2 * resY)) * vertExaggeration;

      const nx = -dzdx;
      const ny = -dzdy;
      const nz = 1;
      const norm = Math.sqrt(nx * nx + ny * ny + nz * nz);

      const intensity = (nx * lightX + ny * lightY + nz * lightZ) / norm;
      hillshade[row * width + col] = Math.max(0, Math.min(1, intensity));
    }
  }
  return hillshade;
}

/**
 * 陰影強度配列(0〜1、NaN=nodata)をcanvasに描画できるRGBA配列に変換する。
 * nodataは透明(alpha=0)にする。
 * @param {Float32Array} hillshade
 * @returns {Uint8ClampedArray}
 */
export function hillshadeToRgba(hillshade) {
  const rgba = new Uint8ClampedArray(hillshade.length * 4);
  for (let i = 0; i < hillshade.length; i++) {
    const v = hillshade[i];
    if (Number.isNaN(v)) {
      rgba[i * 4 + 3] = 0;
    } else {
      const gray = Math.round(v * 255);
      rgba[i * 4] = gray;
      rgba[i * 4 + 1] = gray;
      rgba[i * 4 + 2] = gray;
      rgba[i * 4 + 3] = 255;
    }
  }
  return rgba;
}
