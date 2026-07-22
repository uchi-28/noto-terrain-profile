"""断面図(縦断プロファイル)の描画。

DEMごとの色分け・凡例のファイル名表示を担当する(日本語フォント対応は fonts.py)。
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from dem_profile.fonts import configure_japanese_font


def draw_profile(ax, df: pd.DataFrame) -> None:
    """既存のaxに断面図を描く(既存の内容はclearしない。呼び出し側でclear済み前提)。

    - x軸: 開始点からの距離、y軸: 標高
    - DEMごとに線の色を変える
    - 凡例はDEMのファイル名。グラフ本体と重ならないよう外側に配置する

    `build_profile_figure`(単独の図として作る)と`transect_session.py`(陰影図と
    同じウィンドウの1つのaxに描く)の両方から使われる共通の描画ロジック。
    """
    for name, group in df.groupby("dem", sort=False):
        ax.plot(group["distance"], group["z"], label=name, linewidth=1.5)

    ax.set_xlabel("開始点からの距離 (m)")
    ax.set_ylabel("標高 (m)")
    ax.set_title("地形断面図")
    ax.grid(True, linewidth=0.3)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), borderaxespad=0, title="DEM")


def build_profile_figure(df: pd.DataFrame):
    """dem列でグループ化した断面図の(fig, ax)を作る(保存・表示は呼び出し側の責務)。"""
    configure_japanese_font()

    fig, ax = plt.subplots(figsize=(10, 5))
    draw_profile(ax, df)

    fig.tight_layout()
    return fig, ax


def plot_profiles(df: pd.DataFrame, output_path) -> None:
    """dem列でグループ化した断面図を作成しoutput_pathへ保存する。"""
    fig, _ax = build_profile_figure(df)
    fig.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close(fig)
