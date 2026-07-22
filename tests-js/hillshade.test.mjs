// docs/js/hillshade.js の単体テスト(Node組み込みのtest runnerを使用、ブラウザ不要)。

import test from "node:test";
import assert from "node:assert/strict";

import { computeHillshade, hillshadeToRgba } from "../docs/js/hillshade.js";

const NODATA = -9999;

function makeSlopeDem() {
  // 20x20、2m解像度、東西方向に一定勾配(最終列はnodata)。
  const width = 20;
  const height = 20;
  const data = new Float32Array(width * height);
  for (let row = 0; row < height; row++) {
    for (let col = 0; col < width; col++) {
      data[row * width + col] = col === 19 ? NODATA : col * 5;
    }
  }
  return { data, width, height, resX: 2, resY: 2, nodata: NODATA };
}

test("computeHillshade returns values in [0,1] and NaN at nodata", () => {
  const dem = makeSlopeDem();
  const hillshade = computeHillshade(dem);

  assert.equal(hillshade.length, dem.width * dem.height);
  for (let row = 0; row < dem.height; row++) {
    assert.ok(Number.isNaN(hillshade[row * dem.width + 19]));
  }

  let sawValid = false;
  for (const v of hillshade) {
    if (!Number.isNaN(v)) {
      sawValid = true;
      assert.ok(v >= 0 && v <= 1);
    }
  }
  assert.ok(sawValid);
});

test("hillshadeToRgba sets alpha=0 for nodata, 255 otherwise", () => {
  const dem = makeSlopeDem();
  const hillshade = computeHillshade(dem);
  const rgba = hillshadeToRgba(hillshade);

  for (let i = 0; i < hillshade.length; i++) {
    if (Number.isNaN(hillshade[i])) {
      assert.equal(rgba[i * 4 + 3], 0);
    } else {
      assert.equal(rgba[i * 4 + 3], 255);
    }
  }
});
