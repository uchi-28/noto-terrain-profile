import { loadDem } from "./js/geotiff-loader.js";
import { computeHillshade, hillshadeToRgba } from "./js/hillshade.js";
import { createPicker } from "./js/picker.js";
import { buildProfileData } from "./js/sampling.js";
import { renderProfileChart } from "./js/profileChart.js";

// E2E(Playwright)テストおよびデバッグ用の状態フック。
window.__state = window.__state || {};

// ページ起動時に0番目のDEM入力欄へプリセットする初期値(既存の同梱サンプルDEM)。
// ユーザーはこれを書き換えたり行を追加/削除したりして、任意のtifパスを指定できる。
const DEFAULT_DEM_PATHS = [
  "data/bfeq_pref_07ed694_67ee703.tif",
  "data/afeq_mliti_07ed694_67ee703.tif",
  "data/afst_07ed694_67ee703.tif",
];
const DEFAULT_HILLSHADE_INDEX = 1; // afeq_mliti(震災後)

const statusEl = document.getElementById("status");
const canvas = document.getElementById("hillshade-canvas");
const profileCanvas = document.getElementById("profile-canvas");
const intervalInput = document.getElementById("interval-input");
const downloadButton = document.getElementById("download-csv");
const demRowsEl = document.getElementById("dem-rows");
const addRowButton = document.getElementById("add-dem-row");
const loadButton = document.getElementById("load-dems");
const coordX1 = document.getElementById("coord-x1");
const coordY1 = document.getElementById("coord-y1");
const coordX2 = document.getElementById("coord-x2");
const coordY2 = document.getElementById("coord-y2");
const coordSubmitButton = document.getElementById("coord-submit");
const coordErrorEl = document.getElementById("coord-error");

const demCache = new Map();
let picker = null;
let lastProfileRows = null;
let currentDemEntries = [];

function getDem(path) {
  if (!demCache.has(path)) {
    demCache.set(path, loadDem(path));
  }
  return demCache.get(path);
}

function setStatus(text) {
  statusEl.textContent = text;
}

function nameFromPath(path) {
  return path.split("/").pop();
}

function addDemRow(path = "", checked = false) {
  const row = document.createElement("div");
  row.className = "dem-row";

  const radio = document.createElement("input");
  radio.type = "radio";
  radio.name = "hillshade-dem";
  radio.checked = checked;

  const radioLabel = document.createElement("label");
  radioLabel.className = "dem-hillshade-label";
  radioLabel.title = "このDEMを陰影図の表示・クリックに使う";
  radioLabel.append(radio, document.createTextNode(" 陰影図"));

  const pathInput = document.createElement("input");
  pathInput.type = "text";
  pathInput.className = "dem-path";
  pathInput.placeholder = "例: data/afeq_mliti_07ed694_67ee703.tif";
  pathInput.value = path;

  const nameInput = document.createElement("input");
  nameInput.type = "text";
  nameInput.className = "dem-name";
  nameInput.placeholder = "凡例名(空欄ならファイル名)";

  const removeButton = document.createElement("button");
  removeButton.type = "button";
  removeButton.className = "remove-row";
  removeButton.textContent = "削除";
  removeButton.addEventListener("click", () => {
    if (demRowsEl.children.length <= 1) return;
    const wasChecked = radio.checked;
    row.remove();
    if (wasChecked && demRowsEl.firstElementChild) {
      demRowsEl.firstElementChild.querySelector('input[type="radio"]').checked = true;
    }
  });

  row.append(radioLabel, pathInput, nameInput, removeButton);
  demRowsEl.appendChild(row);
  return row;
}

function readDemRows() {
  return Array.from(demRowsEl.querySelectorAll(".dem-row"))
    .map((row) => ({
      path: row.querySelector(".dem-path").value.trim(),
      name: row.querySelector(".dem-name").value.trim(),
      isHillshade: row.querySelector('input[type="radio"]').checked,
    }))
    .filter((entry) => entry.path);
}

addRowButton.addEventListener("click", () => addDemRow());

function toCsv(rows) {
  const header = "dem,distance,x,y,z";
  const lines = rows.map((r) =>
    [r.dem, r.distance, r.x, r.y, Number.isNaN(r.z) ? "" : r.z].join(",")
  );
  return [header, ...lines].join("\n");
}

downloadButton.addEventListener("click", () => {
  if (!lastProfileRows) return;
  const blob = new Blob([toCsv(lastProfileRows)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "profile.csv";
  a.click();
  URL.revokeObjectURL(url);
});

function setCoordFields(start, end) {
  coordX1.value = start[0];
  coordY1.value = start[1];
  coordX2.value = end[0];
  coordY2.value = end[1];
}

function setCoordError(message) {
  coordErrorEl.textContent = message;
  coordErrorEl.hidden = !message;
}

async function onPick({ start, end }) {
  downloadButton.disabled = true;
  setStatus("断面図を計算中...");
  setCoordError("");
  setCoordFields(start, end);
  window.__state.picked = { start, end };

  const interval = Number(intervalInput.value) || 5;
  const namedDems = await Promise.all(
    currentDemEntries.map(async ({ name, path }) => ({ name, dem: await getDem(path) }))
  );

  const rows = buildProfileData(namedDems, start, end, interval);
  lastProfileRows = rows;
  renderProfileChart(profileCanvas, rows);
  downloadButton.disabled = false;

  setStatus("完了。別の側線を選ぶには陰影図をもう一度クリックしてください。");
  window.__state.profile = {
    pointCount: rows.length,
    demCount: namedDems.length,
    hasValidZ: rows.some((r) => !Number.isNaN(r.z)),
  };
}

function onReset() {
  setStatus("選択をクリアしました。側線を選択してください(2点クリック)。");
  setCoordError("");
  window.__state.picked = null;
  window.__state.profile = null;
  downloadButton.disabled = true;
}

async function loadFromForm() {
  const entries = readDemRows();
  if (entries.length === 0) {
    setStatus("DEMのパスを少なくとも1つ入力してください。");
    return;
  }
  const hillshadeEntry = entries.find((e) => e.isHillshade) || entries[0];

  window.__state.hillshadeReady = false;
  window.__state.picked = null;
  window.__state.profile = null;
  downloadButton.disabled = true;
  loadButton.disabled = true;
  setStatus("陰影図を読み込み中...");

  try {
    const hillshadeDem = await getDem(hillshadeEntry.path);
    const hillshade = computeHillshade(hillshadeDem);
    const rgba = hillshadeToRgba(hillshade);

    if (picker) picker.destroy();
    picker = createPicker(canvas, hillshadeDem, rgba, { onPick, onReset });

    currentDemEntries = entries.map((e) => ({ name: e.name || nameFromPath(e.path), path: e.path }));

    setStatus("側線を選択してください(2点クリック、Escでやり直し)。");
    window.__state.hillshadeReady = true;
  } catch (err) {
    console.error(err);
    setStatus(`エラーが発生しました: ${err.message}`);
  } finally {
    loadButton.disabled = false;
  }
}

loadButton.addEventListener("click", () => {
  loadFromForm().catch((err) => {
    console.error(err);
    setStatus(`エラーが発生しました: ${err.message}`);
  });
});

coordSubmitButton.addEventListener("click", () => {
  if (!picker) {
    setCoordError("先にDEMを読み込んでください。");
    return;
  }
  const values = [coordX1.value, coordY1.value, coordX2.value, coordY2.value].map(Number);
  if (values.some((v) => !Number.isFinite(v))) {
    setCoordError("座標は4つとも数値で入力してください。");
    return;
  }
  const [x1, y1, x2, y2] = values;
  setCoordError("");
  picker.setPoints([x1, y1], [x2, y2]);
});

DEFAULT_DEM_PATHS.forEach((path, i) => addDemRow(path, i === DEFAULT_HILLSHADE_INDEX));

loadFromForm().catch((err) => {
  console.error(err);
  setStatus(`エラーが発生しました: ${err.message}`);
});
