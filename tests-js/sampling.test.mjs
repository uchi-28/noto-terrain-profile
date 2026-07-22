// docs/js/sampling.js の単体テスト(Node組み込みのtest runnerを使用、ブラウザ不要)。
// Pythonローカル版のtests/test_sampling.pyと対になる合成DEMパターンで検証する。

import test from "node:test";
import assert from "node:assert/strict";

import {
  sampleDemAlongLine,
  buildProfileData,
} from "../docs/js/sampling.js";

const NODATA = -9999;

function makeRampDem() {
  // 10x10、1m解像度。z値は列番号と同じ(列8だけnodata)。
  const width = 10;
  const height = 10;
  const data = new Float32Array(width * height);
  for (let row = 0; row < height; row++) {
    for (let col = 0; col < width; col++) {
      data[row * width + col] = col === 8 ? NODATA : col;
    }
  }
  return { data, width, height, bbox: [0, 0, 10, 10], resX: 1, resY: 1, nodata: NODATA };
}

test("sampleDemAlongLine returns expected z values, NaN at nodata column", () => {
  const dem = makeRampDem();
  const rows = sampleDemAlongLine(dem, [0.5, 5], [9.5, 5], 1);

  assert.equal(rows.length, 10);
  rows.forEach((row, i) => {
    assert.ok(Math.abs(row.distance - i) < 1e-9);
    if (i === 8) {
      assert.ok(Number.isNaN(row.z));
    } else {
      assert.equal(row.z, i);
    }
  });
});

test("out-of-bounds points become NaN", () => {
  const dem = makeRampDem();
  // 始点(-5,5)はbbox範囲外(x>=0)。
  const rows = sampleDemAlongLine(dem, [-5, 5], [5, 5], 5);

  assert.ok(Number.isNaN(rows[0].z));
  assert.ok(!Number.isNaN(rows[1].z));
  assert.ok(!Number.isNaN(rows[2].z));
});

test("zero-length line throws", () => {
  const dem = makeRampDem();
  assert.throws(() => sampleDemAlongLine(dem, [1, 1], [1, 1], 1));
});

test("buildProfileData stacks multiple DEMs in long format", () => {
  const dem = makeRampDem();
  const rows = buildProfileData(
    [
      { name: "a.tif", dem },
      { name: "b.tif", dem },
    ],
    [0.5, 5],
    [9.5, 5],
    1
  );

  assert.equal(rows.length, 20);
  const names = new Set(rows.map((r) => r.dem));
  assert.deepEqual([...names].sort(), ["a.tif", "b.tif"]);
  assert.ok(rows.every((r) => "distance" in r && "x" in r && "y" in r && "z" in r));
});
