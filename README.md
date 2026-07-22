# dem-profile

複数のDEM（GeoTIFF）から任意の側線（トランセクト）に沿った標高値を抽出し、地形断面図として比較表示するツール。

2024年の能登半島地震による地形変化、および同年8月の奥能登豪雨による地形変化を、地震前後・豪雨前後のDEMの断面図比較によって可視化することを目的とする（詳細な背景は [`task01.md`](task01.md) を参照）。

## できること

- 複数枚のDEMと、側線の端点座標（xy）・サンプリング間隔を指定すると、側線上をインターバルごとにサンプリングしたxyzの値を持つデータフレームを作成する。
- 作成したデータフレームから、開始点からの距離をx軸、標高(z)をy軸とした折れ線グラフ（地形断面図）を描画する。
- DEMごとに線の色を変え、凡例にはDEMのファイル名をグラフ本体と重ならない位置に表示する。
- 入力座標・DEMの空間参照系がEPSG:6675であることを検証する。
- 日本語表記（タイトル・軸ラベル・凡例）に対応したグラフを出力する。
- 指定したDEMから陰影図（hillshade）を作成して表示し、その画面上でマウスクリックして側線の始点・終点を選ぶことができる。

まずローカルで実行可能なPythonアプリとして実装し、動作確認ができたため、GitHub Pages上で運用可能な静的Webアプリ（`docs/`）も用意した。

## セットアップ

このプロジェクトは [`uv`](https://docs.astral.sh/uv/) で管理している。システムにPython本体がなくても、`uv`が必要なバージョンのPythonを自動的に取得する。

```
uv sync
```

## 使い方

```
uv run python -m dem_profile.cli \
  --dem dem/bfeq_pref_07ed694_67ee703.tif \
  --dem dem/afeq_mliti_07ed694_67ee703.tif \
  --dem dem/afst_07ed694_67ee703.tif \
  --start -1500 158000 --end 1500 158500 --interval 5 \
  --out-csv out/profile.csv --out-png out/profile.png
```

- `--dem`: DEM（GeoTIFF）のパス。複数回指定して重ねて比較できる。
- `--start` / `--end`: 側線の始点・終点座標（EPSG:6675）。
- `--interval`: サンプリング間隔（m）。
- `--out-csv`: 抽出したテーブルの出力先CSVパス（任意）。
- `--out-png`: 断面図PNGの出力先パス。

### 陰影図から側線をクリックして選ぶ

座標を直接指定する代わりに、陰影図を表示してマウスクリックで側線を選ぶこともできる。GUIウィンドウが開き実際にクリック操作を行うため、ローカルの対話的な環境（自分のPC上のターミナル）で実行すること。

```
uv run python -m dem_profile.pick_transect \
  --hillshade-dem dem/afeq_mliti_07ed694_67ee703.tif \
  --dem dem/bfeq_pref_07ed694_67ee703.tif \
  --dem dem/afeq_mliti_07ed694_67ee703.tif \
  --dem dem/afst_07ed694_67ee703.tif \
  --interval 5 \
  --out-csv out/profile.csv --out-png out/profile.png
```

- `--hillshade-dem`: 陰影図の作成・表示に使うDEM(この例では震災後のDEM)。
- ウィンドウ上で2点クリックすると側線が確定し、自動的にウィンドウが閉じて断面図が作成される（Escキーでキャンセル）。
- `--dem` を省略すると `--hillshade-dem` のみで断面図を作る。

## テスト

```
uv run pytest -q
```

## Web版 (`docs/`)

座標入力・陰影図クリックの両方に対応したブラウザ版。ビルド不要のプレーンなHTML/CSS/ESモジュールJSで、`docs/`をそのままGitHub Pagesで公開できる。

GitHub Pagesは静的ホスティングのみで、通常のgit push(Git LFSなし)ではファイル1つ100MBが上限。元DEM(最大613MB)はそのままでは公開できないため、断面図用途には過剰な0.5m解像度を2mまで間引いた版を`docs/data/`に別途生成して使っている(元DEMの`dem/`ディレクトリ自体はリポジトリに含めない。`.gitignore`参照)。

### Web公開用DEMの生成・更新

元DEMを更新した場合は再生成する。

```
uv run python -m dem_profile.prepare_web_data \
  --dem dem/bfeq_pref_07ed694_67ee703.tif \
  --dem dem/afeq_mliti_07ed694_67ee703.tif \
  --dem dem/afst_07ed694_67ee703.tif \
  --target-resolution 2.0 --out-dir docs/data
```

### ローカルで動作確認する

`docs/`はブラウザの`fetch`でDEMを取得するため、`file://`では動かない(CORSでブロックされる)。簡易HTTPサーバーで配信すること。

```
uv run python -m http.server 8000 --directory docs
```

ブラウザで `http://localhost:8000/` を開き、陰影図(震災後DEM)をクリックして側線を2点選ぶと、3枚のDEM(震災前・震災後・豪雨後)の断面図が表示される。

### 自動検証(クリック操作込み)

ローカルPython版の陰影図クリック(`dem-profile-pick`)は人間の操作が前提で自動検証できなかったが、Web版は`tools/e2e/`のPlaywright(ヘッドレスブラウザ)スクリプトで、実際のクリックから断面図描画・CSVダウンロードボタンの有効化・Escキーでのキャンセルまで自動検証できる。

```
cd tools/e2e
npm install          # 初回のみ
npx playwright install chromium   # 初回のみ
node check.mjs
```

### GitHub Pagesとして公開する(未実施・手順のみ)

1. GitHubでリポジトリを作成し、このリポジトリをpushする(`dem/`は`.gitignore`済みなので含まれない。元DEMは各自で保管しておくこと)。
2. リポジトリの Settings → Pages → Build and deployment で「Deploy from a branch」を選び、ブランチとフォルダに `/docs` を指定する。
3. 数分後、`https://<ユーザー名>.github.io/<リポジトリ名>/` で公開される。

## ディレクトリ構成

- `src/dem_profile/sampling.py` — DEMのCRS検証、側線に沿ったサンプリング、複数DEM分のデータフレーム作成。
- `src/dem_profile/plotting.py` — 断面図の描画（凡例配置）。
- `src/dem_profile/hillshade.py` — DEMからの陰影図(hillshade)計算。
- `src/dem_profile/picker.py` — 陰影図をGUI表示し、クリックで側線の2点を選ぶ。
- `src/dem_profile/fonts.py` — 日本語フォントの自動検出・設定（plotting/pickerで共通利用）。
- `src/dem_profile/cli.py` — 座標を直接指定するコマンドラインエントリポイント。
- `src/dem_profile/pick_transect.py` — 陰影図クリックで側線を選ぶコマンドラインエントリポイント。
- `src/dem_profile/web_export.py` / `prepare_web_data.py` — Web公開用に間引いたDEMを生成する処理・CLI。
- `docs/` — GitHub Pagesで公開する静的Webアプリ本体(HTML/CSS/JS、間引いたDEM、vendor済みライブラリ)。
- `tools/e2e/` — Web版をヘッドレスブラウザで自動検証するPlaywrightスクリプト(開発専用、公開サイトには含まれない)。
- `tests-js/` — `docs/js/`内の純粋なロジック(サンプリング・陰影図計算)のNode単体テスト。
- `dem/` — 元のDEM（GeoTIFF、0.5m解像度）。サイズが大きいため`.gitignore`済み。
- `roi/` — 参照用の範囲シェープファイル（現状ツールでは未使用）。
- `task01.md` — 元の要件・作業の流れ。
- `task01_results.md` — 開発結果のまとめ。

より詳しいアーキテクチャの説明は [`CLAUDE.md`](CLAUDE.md) を参照。
