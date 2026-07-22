// vendor/geotiff.js(グローバル変数 GeoTIFF)を使い、DEMのURLから
// sampling.js/hillshade.jsがそのまま使える形にデコードする。
// index.htmlで <script src="vendor/geotiff.js"></script> を先に読み込んでおくこと。

/**
 * DEM(GeoTIFF)をURLから取得・デコードする。
 * @param {string} url
 * @returns {Promise<{data: Float32Array, width: number, height: number, bbox: number[], resX: number, resY: number, nodata: number|null}>}
 */
export async function loadDem(url) {
  // GeoTIFF.fromUrl()はHTTP Rangeリクエストを前提としたソース実装を使うため、
  // Rangeに対応しないサーバー(開発用のPython http.server等)では
  // allowFullFile:trueを指定してもパースに失敗することがある(geotiff.js側の問題)。
  // 単純にfetchで全体を取得し、fromArrayBufferでパースする方が確実。
  // 間引き後のDEM(数MB〜数十MB)を丸ごと読むだけなので問題にならない。
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`DEMの取得に失敗しました: ${url} (HTTP ${response.status})`);
  }
  const arrayBuffer = await response.arrayBuffer();
  const tiff = await GeoTIFF.fromArrayBuffer(arrayBuffer);
  const image = await tiff.getImage();
  const rasters = await image.readRasters();
  const data = rasters[0];

  const bbox = image.getBoundingBox(); // [left, bottom, right, top]
  const [resX, resYRaw] = image.getResolution();
  const nodata = image.getGDALNoData();

  return {
    data,
    width: image.getWidth(),
    height: image.getHeight(),
    bbox,
    resX,
    resY: Math.abs(resYRaw),
    nodata,
  };
}
