// 陰影図をcanvasに描画し、クリックで側線の始点・終点(実座標)を選ぶ。
// Pythonローカル版のpicker.pyと同じUX: 2点クリックで確定、Escでその時点までの
// 選択をクリア。ブラウザはウィンドウをブロックできないので、Python版のような
// 戻り値待ち(plt.show())ではなく、確定時に呼ばれるコールバック方式にしている。

/**
 * @param {HTMLCanvasElement} canvas
 * @param {{width: number, height: number, bbox: number[]}} dem
 * @param {Uint8ClampedArray} hillshadeRgba dem.width x dem.height のRGBA配列
 * @param {{onPick: (points: {start: [number, number], end: [number, number]}) => void, onReset?: () => void}} handlers
 */
export function createPicker(canvas, dem, hillshadeRgba, { onPick, onReset }) {
  canvas.width = dem.width;
  canvas.height = dem.height;
  const ctx = canvas.getContext("2d");
  const imageData = new ImageData(hillshadeRgba, dem.width, dem.height);

  const [left, bottom, right, top] = dem.bbox;
  /** @type {[number, number][]} */
  const picked = [];

  function geoToCanvas([x, y]) {
    const px = ((x - left) / (right - left)) * canvas.width;
    const py = ((top - y) / (top - bottom)) * canvas.height;
    return [px, py];
  }

  function canvasToGeo(px, py) {
    const x = left + (px / canvas.width) * (right - left);
    const y = top - (py / canvas.height) * (top - bottom);
    return [x, y];
  }

  function redraw() {
    ctx.putImageData(imageData, 0, 0);
    if (picked.length === 0) return;

    ctx.strokeStyle = "red";
    ctx.fillStyle = "red";
    ctx.lineWidth = Math.max(1, canvas.width / 400);
    ctx.beginPath();
    picked.forEach(([x, y], i) => {
      const [px, py] = geoToCanvas([x, y]);
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    });
    ctx.stroke();

    const markerSize = Math.max(3, canvas.width / 200);
    picked.forEach(([x, y]) => {
      const [px, py] = geoToCanvas([x, y]);
      ctx.fillRect(px - markerSize / 2, py - markerSize / 2, markerSize, markerSize);
    });
  }

  function handleClick(evt) {
    const rect = canvas.getBoundingClientRect();
    const px = ((evt.clientX - rect.left) / rect.width) * canvas.width;
    const py = ((evt.clientY - rect.top) / rect.height) * canvas.height;

    // 既に2点選択済みなら、新しいクリックから選び直す。
    if (picked.length >= 2) picked.length = 0;

    picked.push(canvasToGeo(px, py));
    redraw();

    if (picked.length === 2) {
      onPick({ start: picked[0], end: picked[1] });
    }
  }

  function handleKeyDown(evt) {
    if (evt.key === "Escape") {
      picked.length = 0;
      redraw();
      if (onReset) onReset();
    }
  }

  canvas.addEventListener("click", handleClick);
  window.addEventListener("keydown", handleKeyDown);
  redraw();

  return {
    // 座標入力ボックスなど、クリック以外の経路で側線を確定するためのAPI。
    // クリック2点分と同じ扱い(描画+onPick発火)にすることでUXを揃える。
    setPoints(start, end) {
      picked.length = 0;
      picked.push(start, end);
      redraw();
      onPick({ start: picked[0], end: picked[1] });
    },
    destroy() {
      canvas.removeEventListener("click", handleClick);
      window.removeEventListener("keydown", handleKeyDown);
    },
  };
}
