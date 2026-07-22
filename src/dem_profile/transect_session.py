"""1つのウィンドウで陰影図クリックと断面図表示を両方行う対話セッション。

以前は「陰影図クリック(1画面)→断面図プレビュー(別画面)→保存」という2画面構成
だったが、画面を切り替えずに済むよう、陰影図の下に断面図の枠を常設した1つの
ウィンドウに統合した。側線を2点クリックすると、ウィンドウを切り替えずにその場で
下の断面図が更新される。3点目をクリックすると側線を選び直せ(Webアプリの
`docs/js/picker.js`と同じUX)、Escキーでも選び直せる。「保存」ボタンで、その時点の
断面図をCSV/PNGに書き出す(何度でも押し直せる。押すたびに同じ出力先を上書きする)。

`picker.py`/`profile_viewer.py`(旧2画面構成、廃止)と同じ方針で、ウィジェット配線
(`_build_session`)と実際にウィンドウを表示してブロックする関数
(`run_transect_session`)を分離してあり、前者はmatplotlibの合成イベントで
自動テストできる(`tests/test_transect_session.py`)。
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.widgets import Button

from dem_profile.fonts import configure_japanese_font
from dem_profile.hillshade import compute_hillshade
from dem_profile.plotting import draw_profile, plot_profiles
from dem_profile.sampling import build_profile_dataframe

_PROFILE_PLACEHOLDER_TITLE = "断面図(陰影図で側線を2点クリックすると表示されます)"


def _reset_profile_axes(ax) -> None:
    ax.clear()
    ax.set_title(_PROFILE_PLACEHOLDER_TITLE)
    ax.set_xlabel("開始点からの距離 (m)")
    ax.set_ylabel("標高 (m)")
    ax.grid(True, linewidth=0.3)


def _build_session(hillshade, extent, dem_paths, interval: float, out_csv, out_png, dem_names=None):
    """陰影図+断面図+保存ボタンを持つウィンドウを組み立てる(plt.show()はしない)。

    `dem_names`はdem_pathsと同じ長さの凡例名リスト(任意)。省略時は
    `build_profile_dataframe`の既定通りファイル名を凡例に使う。

    戻り値 (fig, state) の state は以下を保持する可変dict:
        picked: クリックされた(x, y)のリスト(0〜2個。2個目で断面図を更新、
                その後の3個目のクリックで選び直しになる)
        df: 直近に作成した断面データ(DataFrame、未選択ならNone)
        saved_any: 一度でも保存ボタンで保存したか
    """
    configure_japanese_font()

    fig, (ax_hillshade, ax_profile) = plt.subplots(
        2, 1, figsize=(9, 11), gridspec_kw={"height_ratios": [3, 2]}
    )
    fig.subplots_adjust(right=0.78, bottom=0.08, hspace=0.3)

    ax_hillshade.imshow(hillshade, extent=extent, cmap="gray", vmin=0, vmax=1, origin="upper")
    ax_hillshade.set_xlabel("X (m)")
    ax_hillshade.set_ylabel("Y (m)")
    ax_hillshade.set_title(
        "側線の始点・終点をクリックしてください(2点目で断面図を表示、"
        "3点目で選び直し、Escでクリア)"
    )
    ax_hillshade.set_aspect("equal")
    line, = ax_hillshade.plot([], [], "-o", color="red", linewidth=1.5, markersize=6)

    _reset_profile_axes(ax_profile)

    ax_button = fig.add_axes((0.82, 0.02, 0.13, 0.045))
    button = Button(ax_button, "保存")

    state = {"picked": [], "df": None, "saved_any": False}

    def update_profile() -> None:
        p0, p1 = state["picked"]
        df = build_profile_dataframe(dem_paths, p0, p1, interval, names=dem_names)
        state["df"] = df
        ax_profile.clear()
        draw_profile(ax_profile, df)
        ax_profile.grid(True, linewidth=0.3)
        fig.canvas.draw_idle()

    def clear_selection() -> None:
        state["picked"] = []
        state["df"] = None
        line.set_data([], [])
        _reset_profile_axes(ax_profile)
        fig.canvas.draw_idle()

    def on_click(event) -> None:
        if event.inaxes is not ax_hillshade or event.button != 1:
            return
        if len(state["picked"]) >= 2:
            clear_selection()
        state["picked"].append((event.xdata, event.ydata))
        line.set_data([p[0] for p in state["picked"]], [p[1] for p in state["picked"]])
        fig.canvas.draw_idle()
        if len(state["picked"]) == 2:
            update_profile()

    def on_key(event) -> None:
        if event.key == "escape":
            clear_selection()

    def on_save(_event) -> None:
        df = state["df"]
        if df is None:
            return
        if out_csv is not None:
            csv_path = Path(out_csv)
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        png_path = Path(out_png)
        png_path.parent.mkdir(parents=True, exist_ok=True)
        plot_profiles(df, png_path)
        state["saved_any"] = True
        ax_profile.set_title(f"地形断面図(保存しました: {png_path.name})")
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect("button_press_event", on_click)
    fig.canvas.mpl_connect("key_press_event", on_key)
    button.on_clicked(on_save)
    # Buttonはfigが直接参照を持たないとイベント配線がGCされて効かなくなることがあるため保持する。
    fig._dem_profile_save_button = button

    return fig, state


def run_transect_session(
    hillshade_dem, dem_paths, interval: float, out_csv, out_png, dem_names=None
) -> bool:
    """陰影図クリック・断面図表示・保存を1つのウィンドウで行う。

    ウィンドウを閉じるまでブロックする(側線は何度でも選び直せ、保存も何度でも
    やり直せる)。戻り値は、閉じるまでの間に一度でも保存ボタンで保存したかどうか。
    """
    hillshade, extent = compute_hillshade(hillshade_dem)
    fig, state = _build_session(
        hillshade, extent, dem_paths, interval, out_csv, out_png, dem_names=dem_names
    )
    plt.show()
    return state["saved_any"]
