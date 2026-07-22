"""tifファイルのパスをGUIフォームで入力してから、陰影図クリックで側線を選ぶ。

`pick_transect.py`(`dem-profile-pick`)はDEMのパスをコマンドライン引数で指定して
から実行する必要があったが、本モジュールは起動直後にTkinterのフォーム画面を表示し、
そこでDEMパス(複数可。「+ DEMを追加」ボタンで行を増減できる)・陰影図に使うDEM・
サンプリング間隔・出力先を入力できるようにする。フォームで「陰影図を開く」を押すと
`transect_session.run_transect_session`(陰影図クリック・断面図表示・保存を1つの
ウィンドウで行う既存のロジック)へそのまま処理を引き継ぐため、その先の画面は
`pick_transect.py`と変わらない。

フォーム部分はTkinterのウィジェット配線そのものであり自動テストしにくいため、
入力値の検証ロジック(`_collect_dem_entries` / `_parse_interval` / `_select_hillshade_dem`)
だけを純粋関数として切り出し、`tests/test_pick_transect_gui.py`でウィンドウを開かずに
検証できるようにしてある(`transect_session.py`と`_build_session`を分離した方針と同じ)。
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from dem_profile.transect_session import run_transect_session


def _collect_dem_entries(raw_rows) -> list[tuple[str, str]]:
    """(path, 凡例名)のペアのリストを返す。

    `raw_rows`は(path, 凡例名)のペアの並び。pathが空欄の行は無視する。
    凡例名が空欄ならファイル名にフォールバックする。1つも無い/存在しない
    ファイルがあれば ValueError。
    """
    entries = [
        (path.strip(), name.strip() or Path(path.strip()).name)
        for path, name in raw_rows
        if path.strip()
    ]
    if not entries:
        raise ValueError("DEMのパスを少なくとも1つ入力してください。")
    missing = [path for path, _ in entries if not Path(path).is_file()]
    if missing:
        raise ValueError("以下のファイルが見つかりません:\n" + "\n".join(missing))
    return entries


def _parse_interval(text: str) -> float:
    """サンプリング間隔の文字列を正の float に変換する。不正なら ValueError。"""
    try:
        interval = float(text)
    except ValueError as exc:
        raise ValueError("サンプリング間隔は数値で入力してください。") from exc
    if interval <= 0:
        raise ValueError("サンプリング間隔は正の数値で入力してください。")
    return interval


def _select_hillshade_dem(dem_paths: list[str], requested_path: str) -> str:
    """陰影図に使うDEMを選ぶ。指定がdem_paths内になければ先頭を使う。"""
    if requested_path and requested_path in dem_paths:
        return requested_path
    return dem_paths[0]


class _DemPathRow:
    """DEMパス1行分(陰影図用ラジオボタン・パス入力欄・参照ボタン・凡例名入力欄・削除ボタン)。"""

    def __init__(self, parent: tk.Widget, hillshade_var: tk.StringVar, on_remove):
        self.frame = ttk.Frame(parent)
        self._hillshade_var = hillshade_var

        self.path_var = tk.StringVar()
        self.name_var = tk.StringVar()
        ttk.Radiobutton(
            self.frame, variable=hillshade_var, value=id(self), text="陰影図"
        ).pack(side="left")
        ttk.Entry(self.frame, textvariable=self.path_var, width=45).pack(
            side="left", padx=4, fill="x", expand=True
        )
        ttk.Button(self.frame, text="参照...", command=self._browse).pack(side="left")
        ttk.Label(self.frame, text="凡例名:").pack(side="left", padx=(8, 0))
        ttk.Entry(self.frame, textvariable=self.name_var, width=14).pack(
            side="left", padx=(2, 0)
        )
        ttk.Button(
            self.frame, text="削除", command=lambda: on_remove(self)
        ).pack(side="left", padx=(4, 0))

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            title="DEM (GeoTIFF) を選択",
            filetypes=[("GeoTIFF", "*.tif *.tiff"), ("すべて", "*.*")],
        )
        if path:
            self.path_var.set(path)

    def select_as_hillshade(self) -> None:
        self._hillshade_var.set(str(id(self)))

    def is_selected_as_hillshade(self) -> bool:
        return self._hillshade_var.get() == str(id(self))

    def pack(self) -> None:
        self.frame.pack(fill="x", pady=2)

    def destroy(self) -> None:
        self.frame.destroy()

    @property
    def path(self) -> str:
        return self.path_var.get()

    @property
    def name(self) -> str:
        return self.name_var.get()


class PickTransectForm:
    """DEMパス・サンプリング間隔・出力先を入力するフォーム画面。"""

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("側線ピッカー - DEM設定")

        self._hillshade_var = tk.StringVar(value="")
        self.rows: list[_DemPathRow] = []

        ttk.Label(
            root,
            text=(
                "断面図に使うDEM(GeoTIFF、EPSG:6675)のパスを入力してください。\n"
                "「陰影図」を選んだ1枚が側線クリック用の陰影図に使われます。\n"
                "凡例名は空欄ならファイル名になります。"
            ),
            wraplength=620,
            justify="left",
        ).pack(fill="x", padx=10, pady=(10, 4))

        self.rows_frame = ttk.Frame(root)
        self.rows_frame.pack(fill="x", padx=10)

        ttk.Button(root, text="+ DEMを追加", command=self.add_row).pack(
            anchor="w", padx=10, pady=(4, 10)
        )

        form = ttk.Frame(root)
        form.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Label(form, text="サンプリング間隔 (m):").grid(row=0, column=0, sticky="w")
        self.interval_var = tk.StringVar(value="5")
        ttk.Entry(form, textvariable=self.interval_var, width=10).grid(
            row=0, column=1, sticky="w", padx=(4, 0)
        )

        ttk.Label(form, text="出力CSV (任意):").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.out_csv_var = tk.StringVar(value="out/profile.csv")
        ttk.Entry(form, textvariable=self.out_csv_var, width=50).grid(
            row=1, column=1, sticky="w", padx=(4, 0), pady=(6, 0)
        )
        ttk.Button(form, text="参照...", command=self._browse_csv).grid(
            row=1, column=2, padx=(4, 0), pady=(6, 0)
        )

        ttk.Label(form, text="出力PNG:").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.out_png_var = tk.StringVar(value="out/profile.png")
        ttk.Entry(form, textvariable=self.out_png_var, width=50).grid(
            row=2, column=1, sticky="w", padx=(4, 0), pady=(6, 0)
        )
        ttk.Button(form, text="参照...", command=self._browse_png).grid(
            row=2, column=2, padx=(4, 0), pady=(6, 0)
        )

        ttk.Button(root, text="陰影図を開く >>", command=self.submit).pack(pady=(0, 10))

        self.add_row()
        self.add_row()

    def add_row(self) -> None:
        row = _DemPathRow(self.rows_frame, self._hillshade_var, self.remove_row)
        self.rows.append(row)
        row.pack()
        if len(self.rows) == 1:
            row.select_as_hillshade()

    def remove_row(self, row: _DemPathRow) -> None:
        if len(self.rows) <= 1:
            messagebox.showwarning("側線ピッカー", "DEMは最低1つ必要です。")
            return
        was_hillshade = row.is_selected_as_hillshade()
        self.rows.remove(row)
        row.destroy()
        if was_hillshade and self.rows:
            self.rows[0].select_as_hillshade()

    def _browse_csv(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            self.out_csv_var.set(path)

    def _browse_png(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if path:
            self.out_png_var.set(path)

    def submit(self) -> None:
        try:
            entries = _collect_dem_entries((row.path, row.name) for row in self.rows)
            interval = _parse_interval(self.interval_var.get())
        except ValueError as exc:
            messagebox.showerror("側線ピッカー", str(exc))
            return

        out_png = self.out_png_var.get().strip()
        if not out_png:
            messagebox.showerror("側線ピッカー", "出力PNGのパスを入力してください。")
            return
        out_csv = self.out_csv_var.get().strip() or None

        dem_paths = [path for path, _name in entries]
        dem_names = [name for _path, name in entries]

        hillshade_row = next((r for r in self.rows if r.is_selected_as_hillshade() and r.path.strip()), None)
        requested_hillshade = hillshade_row.path.strip() if hillshade_row else ""
        hillshade_dem = _select_hillshade_dem(dem_paths, requested_hillshade)

        self.root.destroy()

        saved = run_transect_session(
            hillshade_dem=hillshade_dem,
            dem_paths=dem_paths,
            dem_names=dem_names,
            interval=interval,
            out_csv=out_csv,
            out_png=out_png,
        )

        if saved:
            messagebox.showinfo("側線ピッカー", f"断面図を保存しました: {out_png}")
        else:
            messagebox.showinfo("側線ピッカー", "保存しませんでした。")


def main() -> None:
    root = tk.Tk()
    PickTransectForm(root)
    root.mainloop()


if __name__ == "__main__":
    main()
