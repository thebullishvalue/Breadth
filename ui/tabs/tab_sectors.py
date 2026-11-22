"""
Vyāpti — Sectors: where breadth is coming from.

  1 TRUST   how broad is it?            Sector Zones
  2 ANCHOR  the rotation                Sector Breadth, week by week
  3 STATE   each sector now             Sector Readings
  4 DETAIL  the stocks underneath       Constituents

The same oscillator, the same zones and the same words as the engine page, so a
sector reads exactly like the index it belongs to.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from breadth.indicators import MIN_SECTOR_MEMBERS
from ui import charts
from ui.components import (
    render_chart_panel,
    render_kpi_strip,
    render_note,
    render_section_header,
    render_table_panel,
)


def sector_cards(sec: pd.DataFrame) -> list[dict]:
    n = len(sec)

    def names(mask) -> str:
        picked = list(sec.loc[mask, "Sector"])
        return ", ".join(picked[:3]) + (f" +{len(picked) - 3}" if len(picked) > 3 else "") or "none"

    os_, ob = sec["Zone"] == "OVERSOLD", sec["Zone"] == "OVERBOUGHT"
    imp = sec["Direction"] == "IMPROVING"
    return [
        {"label": "Oversold", "value": f"{int(os_.sum())} of {n}", "subtext": names(os_),
         "color_class": "success" if os_.any() else "neutral"},
        {"label": "Neutral", "value": f"{int((~os_ & ~ob).sum())} of {n}", "subtext": names(~os_ & ~ob),
         "color_class": "neutral"},
        {"label": "Overbought", "value": f"{int(ob.sum())} of {n}", "subtext": names(ob),
         "color_class": "neutral"},
        {"label": "Improving", "value": f"{int(imp.sum())} of {n}",
         "subtext": "Custom Breadth above Relative Breadth",
         "color_class": "success" if imp.sum() > n / 2 else "danger" if imp.sum() < n / 2 else "neutral"},
    ]


def heatmap_frame(a, start, end) -> pd.DataFrame:
    frame = pd.DataFrame({s: o["Relative_Breadth"] for s, o in a.sector_osc.items()})
    frame = frame.loc[pd.Timestamp(start):pd.Timestamp(end)].resample("W-FRI").last().dropna(how="all")
    if frame.empty:
        return frame
    return frame[frame.iloc[-1].sort_values(ascending=False).index]


def render(a, view: pd.DataFrame, tf: str) -> None:
    sec = a.sectors
    unit = a.universe.unit.lower()
    if sec.empty:
        render_note(f"No sector has at least {MIN_SECTOR_MEMBERS} {unit}, so sector breadth is not shown.")
        return

    # ── 1 · TRUST ─────────────────────────────────────────────────────────
    render_section_header(
        "Sector Zones",
        f"The Relative Breadth oscillator applied to each sector with at least {MIN_SECTOR_MEMBERS} "
        f"{unit}. A broad move shows up in most sectors at once; a narrow one in a few.",
        icon="grid", accent="accent",
    )
    render_kpi_strip(sector_cards(sec), max_cols=4, key="sector-zones")

    # ── 2 · ANCHOR ────────────────────────────────────────────────────────
    render_section_header(
        "Sector Breadth, Week by Week",
        "Each sector's Relative Breadth at the end of every week. Green where the sector was oversold; "
        "lighter to darker slate from neutral to overbought. Lowest latest reading at the top.",
        icon="activity",
    )
    frame = heatmap_frame(a, view.index[0], view.index[-1])
    if frame.empty:
        render_note("No complete weeks in this window.")
    else:
        render_chart_panel(charts.sector_heatmap(frame), key="sector-heatmap", window=True,
                           footer=f"{len(frame.columns)} sectors · {len(frame)} weeks.")

    # ── 3 · STATE ─────────────────────────────────────────────────────────
    render_section_header(
        "Sector Readings",
        "Every sector's zone, Relative Breadth and direction on the latest session, oversold first, "
        "with its equal-weighted move over the last month.",
        icon="bar-chart", accent="cyan",
    )
    table = sec.assign(Zone=sec["Zone"].str.title(), Direction=sec["Direction"].str.title()).rename(
        columns={"Relative_Breadth": "Relative Breadth", "Move_1M_%": "Last month %"})
    render_table_panel(table, key="sector-table", label_col="Sector", sign_color_cols={"Last month %"},
                       col_precision={"Relative Breadth": 3, "Last month %": 1}, max_height=520)

    # ── 4 · DETAIL ────────────────────────────────────────────────────────
    render_section_header(
        "Constituents",
        f"The {unit} underneath, by their move in the latest session.",
        icon="layers", accent="violet",
    )
    pick = st.selectbox("Sector", ["All sectors"] + sorted(a.stocks["Sector"].unique()),
                        key="sector_pick", label_visibility="collapsed")
    stocks = a.stocks if pick == "All sectors" else a.stocks[a.stocks["Sector"] == pick]
    if not stocks["Name"].astype(bool).any():
        stocks = stocks.drop(columns="Name")
    stocks = stocks.rename(columns={"Day_%": "Latest session %", "Month_%": "Last month %"})
    render_table_panel(stocks, key="sector-stocks", context=f"{pick} · {len(stocks)} {unit}",
                       label_col="Symbol", sign_color_cols={"Latest session %", "Last month %"},
                       col_precision={"Price": 2, "Latest session %": 2, "Last month %": 1}, max_height=480)
