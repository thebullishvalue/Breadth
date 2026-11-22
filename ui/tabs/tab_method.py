"""
Vyāpti — Method: how every number in the app is made.

One table per layer, in pipeline order: counting → oscillators → reads →
record. Nothing here is computed; it is the specification, rendered from the
same constants the engine uses so the two cannot drift apart.
"""

from __future__ import annotations

import pandas as pd

from breadth.indicators import (
    DIRECTION_BAND,
    FIB_PERIODS,
    MAX_GAP,
    MIN_ASSETS_PER_DAY,
    MIN_COVERAGE,
    MIN_SECTOR_MEMBERS,
    OVERBOUGHT,
    OVERSOLD,
    TREND_MA,
)
from breadth.study import (
    BIG_EDGE_PTS,
    COOLDOWN,
    EDGE_PTS,
    EPISODE_GAP,
    HIT_PTS,
    HORIZONS,
    MIN_EPISODES,
)
from ui.components import render_section_header, render_table_panel

_fib = ", ".join(str(p) for p in FIB_PERIODS)


def _t(rows, cols=("Item", "Rule")) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=list(cols))


def render(a) -> None:
    render_section_header("Counting", "How each session's advances and declines are counted.", icon="database",
                          accent="cyan")
    render_table_panel(_t([
        ("Advancer / decliner", "A constituent whose close is above / below its previous close"),
        ("Who counts", "Only constituents that traded that session"),
        ("Gaps", f"The previous close is carried across gaps of up to {MAX_GAP} sessions"),
        ("Thin sessions", f"Dropped when fewer than max({MIN_ASSETS_PER_DAY}, {MIN_COVERAGE:.0%} of the "
                          f"universe) traded"),
    ]), key="method-counting", context="", label_col="Item", max_height=200)

    render_section_header("The Oscillators", "The Aarambh set — the instrument and its companions.",
                          icon="activity")
    render_table_panel(_t([
        ("A/D Ratio", "Advancers ÷ decliners (advancers when none declined)", "The session"),
        ("Custom Breadth", "10-session EMA of advancers ÷ (advancers + decliners), seeded with the first "
                           "10-session average", "Fast breadth line"),
        ("Relative Breadth", f"(Z + Custom Breadth) ÷ 2, Z = mean of Custom Breadth's {_fib}-session "
                             f"averages", "The instrument: sets the zone"),
        ("Relative A/D Ratio", "Daily change in the A/D ratio blended with its 2, 3 and 5-session averages",
         "Momentum"),
        ("A/D Line", f"Running total of advancers − decliners, against its {TREND_MA}-session average",
         "Longer trend"),
    ], ("Oscillator", "Definition", "Role")), key="method-osc", context="", label_col="Oscillator",
        max_height=240)

    render_section_header("Reads", "How the oscillators become words on screen.", icon="target",
                          accent="violet")
    render_table_panel(_t([
        ("Zone", f"Oversold below {OVERSOLD:.2f} · Overbought above {OVERBOUGHT:.2f} · Neutral between"),
        ("Direction", f"Improving when Custom Breadth is above Relative Breadth, deteriorating when below; "
                      f"a gap of at least {DIRECTION_BAND} is needed to flip"),
        ("Momentum", "Sign of the Relative A/D Ratio's 3-session average"),
        ("Breadth trend", f"Rising when the A/D line is above its {TREND_MA}-session average"),
        ("Sectors", f"The same oscillator per sector with at least {MIN_SECTOR_MEMBERS} members"),
    ]), key="method-reads", context="", label_col="Item", max_height=230)

    render_section_header("The Record", "How 'what it has meant' is measured.", icon="shield",
                          accent="emerald")
    render_table_panel(_t([
        ("Horizons", " and ".join(f"{k} ({v} sessions)" for k, v in HORIZONS.items())),
        ("Zones", "Every session grouped by its zone; forward index return measured from that session"),
        ("Crossings", f"Measured from the crossing day; a repeat within {COOLDOWN} sessions is not counted"),
        ("Episodes", f"Zone stretches fewer than {EPISODE_GAP} sessions apart count as one; fewer than "
                     f"{MIN_EPISODES} episodes is 'too few'"),
        ("Better than normal", f"1-month average ≥ {EDGE_PTS} pts above any session and hit rate ≥ {HIT_PTS:.0f} "
                               f"pts above — or average ≥ {BIG_EDGE_PTS} pts above. Worse: the mirror image"),
        ("No look-ahead", "Every figure uses only information available on its own date"),
        ("Survivorship", "History uses today's constituents; names that left the index are missing"),
    ]), key="method-record", context="", label_col="Item", max_height=300)
