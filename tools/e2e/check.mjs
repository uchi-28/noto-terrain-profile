// docs/ の静的サイトを実際にヘッドレスブラウザで開き、陰影図のクリック操作込みで
// 動作確認する開発専用スクリプト。Pythonローカル版(picker.py)は人間のクリックが
// 前提で自動検証できなかったが、Web版はPlaywrightで実際のクリックまで自動化できる。
//
// 使い方: (tools/e2e で) node check.mjs
// 事前に `npm install` (このディレクトリで) と `uv run python -m dem_profile.prepare_web_data ...`
// で docs/data/*.tif の生成が必要。

import { chromium } from "playwright";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..", "..");
const port = 8743;
const baseUrl = `http://127.0.0.1:${port}/`;

function startServer() {
  // `uv run python ...`はuvがpythonを子プロセスとして起動するsupervisorのため、
  // Node側からkill()しても子のpythonまで終了しないことがある。venvのpython.exeを
  // 直接起動することで、kill()で確実にプロセスを止められるようにする。
  const pythonExe = path.join(repoRoot, ".venv", "Scripts", "python.exe");
  const server = spawn(
    pythonExe,
    ["-m", "http.server", String(port), "--directory", "docs"],
    { cwd: repoRoot, stdio: "pipe" }
  );
  server.stderr.on("data", () => {}); // http.serverはアクセスログをstderrに出す(無視)
  return server;
}

async function waitForServer() {
  for (let i = 0; i < 50; i++) {
    try {
      const res = await fetch(baseUrl);
      if (res.ok) return;
    } catch {
      // まだ起動していない
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error("サーバーが起動しませんでした。");
}

function assert(condition, message) {
  if (!condition) throw new Error(`assertion failed: ${message}`);
}

async function main() {
  const server = startServer();
  let browser;
  try {
    await waitForServer();

    browser = await chromium.launch();
    const page = await browser.newPage({ viewport: { width: 1000, height: 1200 } });
    const consoleErrors = [];
    page.on("pageerror", (err) => consoleErrors.push(String(err)));
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    await page.goto(baseUrl, { waitUntil: "load" });

    console.log("陰影図の読み込み待ち...");
    try {
      await page.waitForFunction(() => window.__state && window.__state.hillshadeReady === true, {
        timeout: 30000,
      });
    } catch (err) {
      const statusText = await page.locator("#status").textContent().catch(() => "(取得失敗)");
      console.error("status要素の内容:", statusText);
      console.error("コンソールエラー:", consoleErrors);
      throw err;
    }
    console.log("OK: 陰影図の読み込み完了 (window.__state.hillshadeReady)");

    const canvas = page.locator("#hillshade-canvas");
    const box = await canvas.boundingBox();
    assert(box && box.width > 0 && box.height > 0, "陰影図canvasの表示サイズが取得できること");

    // canvas内の2点をクリックして側線を選択する。DEM選択欄が増えてページが縦に
    // 伸びたため、page.mouse.click(絶対ページ座標)だとビューポート外に外れることが
    // ある。canvas要素基準の相対クリック(自動スクロール込み)にして位置ずれを防ぐ。
    const p1 = { x: box.width * 0.3, y: box.height * 0.4 };
    const p2 = { x: box.width * 0.7, y: box.height * 0.6 };
    await canvas.click({ position: p1 });
    await canvas.click({ position: p2 });
    console.log("OK: 陰影図上で2点クリック");

    console.log("断面図の計算待ち...");
    await page.waitForFunction(() => window.__state && window.__state.profile != null, {
      timeout: 30000,
    });

    const profile = await page.evaluate(() => window.__state.profile);
    assert(profile.demCount === 3, `demCountが3であること (実際: ${profile.demCount})`);
    assert(profile.pointCount > 0, `pointCountが0より大きいこと (実際: ${profile.pointCount})`);
    assert(profile.hasValidZ === true, "少なくとも1つはNaNでないzが含まれること");
    console.log("OK: 断面図が作成された", profile);

    const downloadDisabled = await page.locator("#download-csv").isDisabled();
    assert(downloadDisabled === false, "CSVダウンロードボタンが有効になっていること");
    console.log("OK: CSVダウンロードボタンが有効化された");

    // Escキーでの選択クリアも確認する。
    await canvas.click({ position: p1 }); // 新しい選択の1点目
    await page.keyboard.press("Escape");
    await page.waitForFunction(() => window.__state && window.__state.picked == null, {
      timeout: 5000,
    });
    const downloadDisabledAfterEscape = await page.locator("#download-csv").isDisabled();
    assert(downloadDisabledAfterEscape === true, "Esc後はCSVダウンロードボタンが無効化されること");
    console.log("OK: Escキーで選択がクリアされた");

    if (consoleErrors.length > 0) {
      throw new Error(`ブラウザコンソールにエラーがありました:\n${consoleErrors.join("\n")}`);
    }

    console.log("\nすべての自動検証に合格しました。");
  } finally {
    if (browser) await browser.close();
    server.kill();
  }
}

main().catch((err) => {
  console.error("\nFAILED:", err.message);
  process.exitCode = 1;
});
