"""1つのウィンドウで陰影図クリックと断面図表示を両方行う対話セッション。

以前は「陰影図クリック(1画面)→断面図プレビュー(別画面)→保存」という2画面構成
だったが、画面を切り替えずに済むよう、陰影図の下に断面図の枠を常設した1つの
ウィンドウに統合した。側線を2点クリックすると、ウィンドウを切り替えずにその場で
下の断面図が更新される。3点目をクリックすると側線を選び直せ(Webアプリの
`docs/js/picker.js`と同じUX)、Escキーでも選び直せる。陰影図上部の始点X/Y・終点X/Yの
`TextBox`に数値を直接入力して「座標で確定」ボタン(または最後の欄でEnter)を押しても
同じように側線を確定でき、クリックと相互に同期する(クリックすれば入力欄にその座標が
反映され、入力欄から確定すれば陰影図に赤線が引かれる)。座標が数値として読めない場合は
`coord_status`にエラーメッセージを表示する。「保存」ボタンで、その時点の断面図をCSV/PNG
に書き出す(何度でも押し直せる。押すたびに同じ出力先を上書きする)。

`picker.py`/`profile_viewer.py`(旧2画面構成、廃止)と同じ方針で、ウィジェット配線
(`_build_session`)と実際にウィンドウを表示してブロックする関数
(`run_transect_session`)を分離してあり、前者はmatplotlibの合成イベントで
自動テストできる(`tests/test_transect_session.py`)。
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.widgets import Button, TextBox

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
    fig.subplots_adjust(right=0.78, bottom=0.08, top=0.85, hspace=0.3)

    ax_hillshade.imshow(hillshade, extent=extent, cmap="gray", vmin=0, vmax=1, origin="upper")
    ax_hillshade.set_xlabel("X (m)")
    ax_hillshade.set_ylabel("Y (m)")
    ax_hillshade.set_title(
        "側線の始点・終点をクリックしてください(2点目で断面図を表示、"
        "3点目で選び直し、Escでクリア)。上の欄に座標を直接入力してもOK"
    )
    ax_hillshade.set_aspect("equal")
    line, = ax_hillshade.plot([], [], "-o", color="red", linewidth=1.5, markersize=6)

    _reset_profile_axes(ax_profile)

    ax_button = fig.add_axes((0.82, 0.02, 0.13, 0.045))
    button = Button(ax_button, "保存")

    # クリックの代わりに座標を直接入力して側線を確定するための入力欄(始点X/Y、終点X/Y)。
    coord_status = fig.text(0.06, 0.975, "", fontsize=9, color="crimson")
    box_x1 = TextBox(fig.add_axes((0.12, 0.925, 0.09, 0.035)), "始点X ")
    box_y1 = TextBox(fig.add_axes((0.29, 0.925, 0.09, 0.035)), "Y ")
    box_x2 = TextBox(fig.add_axes((0.46, 0.925, 0.09, 0.035)), "終点X ")
    box_y2 = TextBox(fig.add_axes((0.63, 0.925, 0.09, 0.035)), "Y ")
    ax_coord_button = fig.add_axes((0.80, 0.925, 0.15, 0.035))
    coord_button = Button(ax_coord_button, "座標で確定")

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
        for box in (box_x1, box_y1, box_x2, box_y2):
            box.set_val("")
        coord_status.set_text("")
        _reset_profile_axes(ax_profile)
        fig.canvas.draw_idle()

    def commit_points(p0, p1) -> None:
        """クリックまたは座標入力で確定した2点から側線・断面図を更新する。"""
        state["picked"] = [p0, p1]
        line.set_data([p0[0], p1[0]], [p0[1], p1[1]])
        box_x1.set_val(f"{p0[0]:g}")
        box_y1.set_val(f"{p0[1]:g}")
        box_x2.set_val(f"{p1[0]:g}")
        box_y2.set_val(f"{p1[1]:g}")
        coord_status.set_text("")
        update_profile()

    def on_click(event) -> None:
        if event.inaxes is not ax_hillshade or event.button != 1:
            return
        if len(state["picked"]) >= 2:
            clear_selection()
        state["picked"].append((event.xdata, event.ydata))
        line.set_data([p[0] for p in state["picked"]], [p[1] for p in state["picked"]])
        fig.canvas.draw_idle()
        if len(state["picked"]) == 2:
            commit_points(*state["picked"])

    def on_key(event) -> None:
        if event.key == "escape":
            clear_selection()

    def on_coord_submit(_arg=None) -> None:
        try:
            p0 = (float(box_x1.text), float(box_y1.text))
            p1 = (float(box_x2.text), float(box_y2.text))
        except ValueError:
            coord_status.set_text("座標は数値で入力してください。")
            fig.canvas.draw_idle()
            return
        commit_points(p0, p1)

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
    coord_button.on_clicked(on_coord_submit)
    box_y2.on_submit(on_coord_submit)  # 最後の入力欄でEnterを押しても確定できるように
    # Button/TextBoxはfigが直接参照を持たないとイベント配線がGCされて効かなくなることがあるため保持する。
    fig._dem_profile_save_button = button
    fig._dem_profile_coord_widgets = (box_x1, box_y1, box_x2, box_y2, coord_button)

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
