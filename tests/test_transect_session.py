"""transect_session.py の単体テスト。

実際に人がマウスでクリックする操作そのものは自動テストできないが、
matplotlibの合成イベント機能(`FigureCanvasBase`のbutton_press_event/
button_release_event/key_press_event)を使えば、`_build_session`が配線した
イベント処理(2点クリック→断面図の描画、3点目クリックでの選び直し、Escでの
クリア、保存ボタンでのCSV/PNG書き出し)を実際のGUI操作なしに検証できる。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import rasterio
from matplotlib.backend_bases import KeyEvent, MouseEvent
from rasterio.transform import from_origin

plt = pytest.importorskip("matplotlib.pyplot")
# ヘッドレス環境でも実行できるよう、明示的にAggへ切り替える。
plt.switch_backend("Agg")

from dem_profile.transect_session import _build_session  # noqa: E402

NODATA = -9999.0


def _write_ramp_dem(path, epsg: int = 6675) -> None:
    """10x10、1m解像度の合成DEM(bounds: x/y ともに0〜10)。z値は列番号と同じ。"""
    width = height = 10
    data = np.tile(np.arange(width, dtype="float32"), (height, 1))
    transform = from_origin(0, 10, 1, 1)
    with rasterio.open(
        path, "w", driver="GTiff", width=width, height=height, count=1,
        dtype="float32", crs=f"EPSG:{epsg}", transform=transform, nodata=NODATA,
    ) as ds:
        ds.write(data, 1)


def _click_at(fig, ax, data_xy) -> None:
    x_px, y_px = ax.transData.transform(data_xy)
    event = MouseEvent("button_press_event", fig.canvas, x_px, y_px, button=1)
    fig.canvas.callbacks.process("button_press_event", event)


def _click_button_center(fig, button_ax) -> None:
    # matplotlibのButtonはpress→grab_mouse→releaseで初めて"clicked"を発火するため
    # (Button._click/_release参照)、pressだけでなくreleaseイベントも送る必要がある。
    x_px, y_px = button_ax.transAxes.transform((0.5, 0.5))
    press = MouseEvent("button_press_event", fig.canvas, x_px, y_px, button=1)
    fig.canvas.callbacks.process("button_press_event", press)
    release = MouseEvent("button_release_event", fig.canvas, x_px, y_px, button=1)
    fig.canvas.callbacks.process("button_release_event", release)


@pytest.fixture
def session(tmp_path):
    dem_path = tmp_path / "ramp.tif"
    _write_ramp_dem(dem_path)
    hillshade = np.zeros((5, 5))
    extent = (0.0, 10.0, 0.0, 10.0)
    out_csv = tmp_path / "out" / "profile.csv"
    out_png = tmp_path / "out" / "profile.png"
    fig, state = _build_session(
        hillshade, extent, [dem_path], interval=1.0, out_csv=out_csv, out_png=out_png
    )
    ax_hillshade = fig.axes[0]
    button_ax = fig._dem_profile_save_button.ax
    yield fig, state, ax_hillshade, button_ax, out_csv, out_png
    plt.close(fig)


def test_two_clicks_populate_profile(session):
    fig, state, ax_hillshade, _button_ax, _out_csv, _out_png = session

    _click_at(fig, ax_hillshade, (2.0, 3.0))
    _click_at(fig, ax_hillshade, (8.0, 7.0))

    assert len(state["picked"]) == 2
    assert isinstance(state["df"], pd.DataFrame)
    assert not state["df"].empty
    assert plt.fignum_exists(fig.number)  # ウィンドウは閉じない(常設パネルで更新するだけ)


def test_custom_dem_names_are_used_as_legend(tmp_path):
    dem_path = tmp_path / "ramp.tif"
    _write_ramp_dem(dem_path)
    hillshade = np.zeros((5, 5))
    extent = (0.0, 10.0, 0.0, 10.0)
    fig, state = _build_session(
        hillshade, extent, [dem_path], interval=1.0,
        out_csv=tmp_path / "out" / "profile.csv", out_png=tmp_path / "out" / "profile.png",
        dem_names=["震災前"],
    )
    ax_hillshade = fig.axes[0]

    _click_at(fig, ax_hillshade, (2.0, 3.0))
    _click_at(fig, ax_hillshade, (8.0, 7.0))

    assert set(state["df"]["dem"]) == {"震災前"}
    plt.close(fig)


def test_third_click_restarts_selection(session):
    fig, state, ax_hillshade, _button_ax, _out_csv, _out_png = session

    _click_at(fig, ax_hillshade, (2.0, 3.0))
    _click_at(fig, ax_hillshade, (8.0, 7.0))
    _click_at(fig, ax_hillshade, (1.0, 1.0))  # 3点目: 選び直し

    assert len(state["picked"]) == 1
    assert state["df"] is None


def test_escape_clears_selection(session):
    fig, state, ax_hillshade, _button_ax, _out_csv, _out_png = session

    _click_at(fig, ax_hillshade, (2.0, 3.0))
    _click_at(fig, ax_hillshade, (8.0, 7.0))
    event = KeyEvent("key_press_event", fig.canvas, "escape")
    fig.canvas.callbacks.process("key_press_event", event)

    assert state["picked"] == []
    assert state["df"] is None


def test_save_button_without_selection_does_nothing(session):
    fig, state, _ax_hillshade, button_ax, out_csv, out_png = session

    _click_button_center(fig, button_ax)

    assert state["saved_any"] is False
    assert not out_csv.exists()
    assert not out_png.exists()


def test_save_button_writes_csv_and_png(session):
    fig, state, ax_hillshade, button_ax, out_csv, out_png = session

    _click_at(fig, ax_hillshade, (2.0, 3.0))
    _click_at(fig, ax_hillshade, (8.0, 7.0))
    _click_button_center(fig, button_ax)

    assert state["saved_any"] is True
    assert out_csv.exists()
    assert out_png.exists()


def test_coord_boxes_submit_populate_profile(session):
    fig, state, _ax_hillshade, _button_ax, _out_csv, _out_png = session
    box_x1, box_y1, box_x2, box_y2, coord_button = fig._dem_profile_coord_widgets

    box_x1.set_val("2")
    box_y1.set_val("3")
    box_x2.set_val("8")
    box_y2.set_val("7")
    _click_button_center(fig, coord_button.ax)

    assert state["picked"] == [(2.0, 3.0), (8.0, 7.0)]
    assert isinstance(state["df"], pd.DataFrame)
    assert not state["df"].empty


def test_coord_boxes_invalid_input_shows_error(session):
    fig, state, _ax_hillshade, _button_ax, _out_csv, _out_png = session
    box_x1, box_y1, box_x2, box_y2, coord_button = fig._dem_profile_coord_widgets

    box_x1.set_val("not-a-number")
    box_y1.set_val("3")
    box_x2.set_val("8")
    box_y2.set_val("7")
    _click_button_center(fig, coord_button.ax)

    assert state["picked"] == []
    assert state["df"] is None


def test_click_syncs_coord_boxes(session):
    fig, state, ax_hillshade, _button_ax, _out_csv, _out_png = session
    box_x1, box_y1, box_x2, box_y2, _coord_button = fig._dem_profile_coord_widgets

    _click_at(fig, ax_hillshade, (2.0, 3.0))
    _click_at(fig, ax_hillshade, (8.0, 7.0))

    assert float(box_x1.text) == pytest.approx(2.0)
    assert float(box_y1.text) == pytest.approx(3.0)
    assert float(box_x2.text) == pytest.approx(8.0)
    assert float(box_y2.text) == pytest.approx(7.0)


def test_escape_clears_coord_boxes(session):
    fig, state, ax_hillshade, _button_ax, _out_csv, _out_png = session
    box_x1, box_y1, box_x2, box_y2, _coord_button = fig._dem_profile_coord_widgets

    _click_at(fig, ax_hillshade, (2.0, 3.0))
    _click_at(fig, ax_hillshade, (8.0, 7.0))
    event = KeyEvent("key_press_event", fig.canvas, "escape")
    fig.canvas.callbacks.process("key_press_event", event)

    assert box_x1.text == ""
    assert box_y2.text == ""
