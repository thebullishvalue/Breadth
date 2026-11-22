"""
Vyāpti — Breadth Engine: the read, and the oscillators it is taken off.

The app's front door. Reading order — the family's house convention:

  1 TRUST   can I lean on it?           The Read
  2 ANCHOR  the instrument itself       Breadth Oscillators
  3 STATE   what the window contains    Window Statistics
  4 DETAIL  what the read is made of    The Reading
  5 EVENTS  what it has done            Crossing Log

The four-pane stack:

  Row 1 · Relative & Custom Breadth, zone lines at 0.40 and 0.50, the index on
          the second axis (dimmed: it is the reference, not a fifth claim)
  Row 2 · Relative A/D Ratio — day-to-day momentum of the A/D ratio
  Row 3 · A/D ratio per session, log scale, with its 10-session average
  Row 4 · A/D line against its 50-session average — the longer trend
"""

from __future__ import annotations

import html as html_mod

import numpy as np
import pandas as pd
import streamlit as st

from breadth.indicators import OVERBOUGHT, OVERSOLD
from breadth.study import CROSSING_TEXT, events, forward_returns
from ui import charts
from ui import format as fmt
from ui.components import (
    render_chart_panel,
    render_hero_card,
    render_interpretation_card,
    render_note,
    render_section_header,
    render_table_panel,
)
from ui.verdict import build_read

ZONE_TONE = {"OVERSOLD": "success", "NEUTRAL": "neutral", "OVERBOUGHT": "neutral"}

_SERIES = (("Relative Breadth", "Relative_Breadth"), ("Custom Breadth", "Custom_Breadth"),
           ("Relative A/D Ratio", "Rel_AD_Ratio"), ("A/D Ratio", "AD_Ratio"))


def _html(text: str) -> str:
    """Escape, then restore the narrative's **bold** as <strong>."""
    out = html_mod.escape(text)
    while "**" in out:
        out = out.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
    return out


def window_stats(view: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, col in _SERIES:
        s = view[col].astype(float)
        if s.notna().sum() == 0:
            continue
        rows.append({"Series": label, "Last": s.iloc[-1], "High": s.max(), "High on": s.idxmax().date(),
                     "Low": s.min(), "Low on": s.idxmin().date(), "Mean": s.mean(), "Sigma": s.std()})
    return pd.DataFrame(rows)


def crossing_log(a, view: pd.DataFrame) -> pd.DataFrame:
    fwd = forward_returns(a.price)["1M"]
    rows = []
    for key, flags in events(a.panel).items():
        for d in flags[flags].index:
            if d < view.index[0]:
                continue
            rows.append({"Date": d.date(), "Crossing": CROSSING_TEXT[key],
                         "Relative Breadth": a.panel.at[d, "Relative_Breadth"],
                         "Index": a.price.get(d, np.nan), "Index 1M later %": fwd.get(d, np.nan)})
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("Date", ascending=False).reset_index(drop=True)


def render(a, view: pd.DataFrame, tf: str) -> None:
    zone = a.zone

    # ── 1 · TRUST ─────────────────────────────────────────────────────────
    render_section_header(
        "The Read",
        f"Where breadth stands on the Relative Breadth oscillator, whether that zone's own record in "
        f"{a.universe.name} supports leaning on it, and the five readings behind it.",
        icon="target", accent="accent",
    )
    render_hero_card(build_read(a))

    # ── 2 · ANCHOR ────────────────────────────────────────────────────────
    render_section_header(
        "Breadth Oscillators",
        f"Relative Breadth (the instrument) and Custom Breadth, with {a.index_name} on the second axis; "
        f"below them the Relative A/D Ratio, the A/D ratio of each session and the A/D line against its "
        f"50-session average. Green marks the oversold zone and its crossings.",
        icon="activity",
    )
    label = a.universe.name if a.uses_index else "EW basket"
    fig = charts.engine_stack(view, a.price, label, events(a.panel))
    render_chart_panel(
        fig, key="engine-stack",
        chip=(zone, ZONE_TONE[zone]),
        window=True,
        footer=f"{fmt.when(view.index[0])} — {fmt.when(view.index[-1])} · {len(view):,} sessions · "
               f"zone lines fixed at {OVERSOLD:.2f} and {OVERBOUGHT:.2f}.",
    )

    # ── 3 · STATE ─────────────────────────────────────────────────────────
    render_section_header(
        "Window Statistics",
        "Each oscillator over the selected window, with the date each extreme was set.",
        icon="bar-chart", accent="cyan",
    )
    stats = window_stats(view)
    render_table_panel(
        stats, key="engine-stats", label_col="Series",
        col_precision={"Last": 3, "High": 3, "Low": 3, "Mean": 3, "Sigma": 3},
        max_height=220,
    )

    # ── 4 · DETAIL ────────────────────────────────────────────────────────
    render_section_header(
        "The Reading",
        "The read in words: where the oscillator is, which way it is moving and whether momentum "
        "agrees — then what would change it, and what followed the last times that happened.",
        icon="layers", accent="violet",
    )
    c1, c2 = st.columns([3, 2], gap="medium")
    with c1:
        render_interpretation_card(
            f"{zone} · RELATIVE BREADTH {a.last['Relative_Breadth']:.3f}",
            "".join(f"<p>{_html(p)}</p>" for p in a.reading),
            ZONE_TONE[zone],
        )
    with c2:
        render_interpretation_card(
            "WHAT WOULD CHANGE IT",
            "<ul>" + "".join(f"<li>{_html(w)}</li>" for w in a.watch) + "</ul>",
            "info",
        )

    # ── 5 · EVENTS ────────────────────────────────────────────────────────
    render_section_header(
        "Crossing Log",
        "Every time Relative Breadth crossed a zone line in this window, newest first, with the index "
        "then and a month later. The chart marks oversold crossings; the log lists all four kinds.",
        icon="layers", accent="emerald",
    )
    log = crossing_log(a, view)
    if log.empty:
        render_note(f"No zone-line crossings in this {tf} window. Widen the window on the panel above "
                    f"to look further back.")
    else:
        render_table_panel(
            log, key="engine-crossings", context=f"{tf} window · {len(log)} crossings",
            label_col="Date", sign_color_cols={"Index 1M later %"},
            col_precision={"Relative Breadth": 3, "Index": 2, "Index 1M later %": 2},
            max_height=340,
        )
