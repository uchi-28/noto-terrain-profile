// vendor/chart.js(グローバル変数 Chart)を使い、DEMごとに色分けした断面図を描画する。
// Pythonローカル版のplotting.pyと同じ考え方: DEMごとに色を変え、凡例はグラフ本体と
// 重ならない位置(下部)に固定で確保する。

const PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"];

/**
 * @param {HTMLCanvasElement} canvas
 * @param {{dem: string, distance: number, z: number}[]} profileRows ロング形式のサンプリング結果
 */
export function renderProfileChart(canvas, profileRows) {
  const demNames = [...new Set(profileRows.map((r) => r.dem))];

  const datasets = demNames.map((name, i) => ({
    label: name,
    data: profileRows
      .filter((r) => r.dem === name)
      .map((r) => ({ x: r.distance, y: Number.isNaN(r.z) ? null : r.z })),
    borderColor: PALETTE[i % PALETTE.length],
    backgroundColor: PALETTE[i % PALETTE.length],
    borderWidth: 1.5,
    pointRadius: 0,
    spanGaps: false,
  }));

  if (canvas.__chart) {
    canvas.__chart.destroy();
  }

  canvas.__chart = new Chart(canvas.getContext("2d"), {
    type: "line",
    data: { datasets },
    options: {
      responsive: true,
      parsing: false,
      scales: {
        x: { type: "linear", title: { display: true, text: "開始点からの距離 (m)" } },
        y: { title: { display: true, text: "標高 (m)" } },
      },
      plugins: {
        title: { display: true, text: "地形断面図" },
        legend: { position: "bottom" },
      },
    },
  });

  return canvas.__chart;
}
