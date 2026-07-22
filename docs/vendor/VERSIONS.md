# vendor済みライブラリ

CDNではなくローカルに固定バージョンで同梱し、公開後にCDN障害やバージョン変更の影響を受けないようにしている。

- `geotiff.js` — [geotiff](https://www.npmjs.com/package/geotiff) v3.0.5 の `dist-browser/geotiff.js` をそのままコピー。グローバル変数 `GeoTIFF` を公開する(`GeoTIFF.fromUrl(...)`など)。
- `chart.umd.min.js` — [chart.js](https://www.npmjs.com/package/chart.js) v4.5.1 の `dist/chart.umd.min.js` をそのままコピー。グローバル変数 `Chart` を公開する。

更新する場合は `npm install geotiff@<version> chart.js@<version>` で取得し、同じファイルを上書きしてこのファイルのバージョン表記も更新すること。
