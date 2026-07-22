"""matplotlibの日本語フォント設定。

グラフ(plotting.py)・GUI(transect_session.py)の両方が日本語表記を使うため、
フォント検出ロジックをここに共通化する。
"""

from __future__ import annotations

import warnings

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

# 日本語表記が可能な、Windows/一般的な環境でよく見つかるフォントを優先順に並べる。
_JAPANESE_FONT_CANDIDATES = [
    "Yu Gothic",
    "Meiryo",
    "MS Gothic",
    "MS PGothic",
    "Noto Sans JP",
    "IPAexGothic",
    "IPAGothic",
    "BIZ UDGothic",
]


def configure_japanese_font() -> None:
    """インストール済みの日本語対応フォントを探してmatplotlibに設定する。

    見つからない場合は警告のみを出す(フォントの追加インストールは指示しない)。
    """
    available = {f.name for f in fm.fontManager.ttflist}
    for name in _JAPANESE_FONT_CANDIDATES:
        if name in available:
            plt.rcParams["font.family"] = name
            plt.rcParams["axes.unicode_minus"] = False
            return
    warnings.warn(
        "日本語対応フォントが見つかりませんでした。グラフの日本語表記が"
        "文字化けする可能性があります。"
    )
