"""pick_transect_gui.py の入力検証ロジックの単体テスト。

Tkinterのウィンドウ配線自体(`PickTransectForm`)は`transect_session.py`のGUI部分と同様に
実機での目視確認が必要なため対象外とし、ウィンドウを開かずに呼べる純粋関数
(`_collect_dem_entries` / `_parse_interval` / `_select_hillshade_dem`)だけを検証する。
"""

from __future__ import annotations

import pytest

from dem_profile.pick_transect_gui import (
    _collect_dem_entries,
    _parse_interval,
    _select_hillshade_dem,
)


def test_collect_dem_entries_strips_blanks_and_keeps_order(tmp_path):
    dem_a = tmp_path / "a.tif"
    dem_b = tmp_path / "b.tif"
    dem_a.write_bytes(b"")
    dem_b.write_bytes(b"")

    result = _collect_dem_entries([(f"  {dem_a}  ", ""), ("", ""), (f"{dem_b}", "")])

    assert result == [(str(dem_a), "a.tif"), (str(dem_b), "b.tif")]


def test_collect_dem_entries_uses_custom_name_when_given(tmp_path):
    dem_a = tmp_path / "a.tif"
    dem_a.write_bytes(b"")

    result = _collect_dem_entries([(str(dem_a), "  震災前  ")])

    assert result == [(str(dem_a), "震災前")]


def test_collect_dem_entries_rejects_empty_list():
    with pytest.raises(ValueError, match="少なくとも1つ"):
        _collect_dem_entries([("", ""), ("   ", "")])


def test_collect_dem_entries_rejects_missing_file(tmp_path):
    missing = tmp_path / "missing.tif"
    with pytest.raises(ValueError, match="見つかりません"):
        _collect_dem_entries([(str(missing), "")])


def test_parse_interval_accepts_positive_number():
    assert _parse_interval("5") == 5.0
    assert _parse_interval("2.5") == 2.5


@pytest.mark.parametrize("text", ["0", "-1", "abc", ""])
def test_parse_interval_rejects_invalid_values(text):
    with pytest.raises(ValueError):
        _parse_interval(text)


def test_select_hillshade_dem_uses_requested_when_valid():
    dem_paths = ["a.tif", "b.tif", "c.tif"]
    assert _select_hillshade_dem(dem_paths, "b.tif") == "b.tif"


def test_select_hillshade_dem_falls_back_to_first_when_missing_or_blank():
    dem_paths = ["a.tif", "b.tif"]
    assert _select_hillshade_dem(dem_paths, "") == "a.tif"
    assert _select_hillshade_dem(dem_paths, "not-in-list.tif") == "a.tif"
