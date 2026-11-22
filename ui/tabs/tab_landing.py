"""
Vyāpti — cold start: a description of the product, built from the
product's own parts.

Same reading order as the rest of the family:

  1 CLAIM    what is this?              The lede
  2 ANCHOR   what is it made of?        Engines
  3 DETAIL   what does it run on?       Inputs & Scope
  4 OUTCOME  what do I get?             Run Outputs

The grids are plain divs rather than Streamlit containers: everything on them
is static text, and plain divs keep the panels at one height by construction.
"""

from __future__ import annotations

import html as html_mod

import streamlit as st

from breadth.indicators import FIB_PERIODS, OVERBOUGHT, OVERSOLD
from breadth.study import EPISODE_GAP, HORIZONS
from breadth.universe import COMMODITIES_META, CURRENCY_META, INDIA_INDEX_LIST, US_INDEX_LIST
from config import TAGLINE
from ui.components import render_header, render_kpi_strip, render_section_header

_fib = "/".join(str(p) for p in FIB_PERIODS)

#: The three engines, in the order the argument runs: the oscillator makes the
#: claim, its companions say which way it is moving, the record checks whether
#: the claim has ever mattered — without depending on either being right.
_SYSTEM_PANELS = (
    ("RELATIVE BREADTH", "The claim · where breadth is",
     "Counts every constituent that traded as advancing or declining, smooths the share of "
     "advancers into Custom Breadth, then averages it with its own Fibonacci moving averages. "
     "The result places the market in one of three zones. It is a reading of participation — "
     "how many stocks are carrying the index — not of price.",
     (("Zones", f"Oversold < {OVERSOLD:.2f} · Overbought > {OVERBOUGHT:.2f}"),
      ("Built from", f"Custom Breadth + {_fib}-session averages"),
      ("Reads", "Oversold · Neutral · Overbought"))),
    ("DIRECTION & MOMENTUM", "The confirmation · which way",
     "Custom Breadth above Relative Breadth means participation is improving; below, it is "
     "deteriorating. The Relative A/D Ratio says whether the day-to-day advance/decline balance "
     "agrees, and the A/D line against its 50-session average gives the longer trend the "
     "reading sits in.",
     (("Direction", "Custom vs Relative Breadth"),
      ("Momentum", "Relative A/D Ratio · 3 sessions"),
      ("Trend", "A/D line vs 50-session average"))),
    ("RECORD", "The check · what it has meant",
     "Groups every past session by its zone and every crossing of a zone line by its date, and "
     "measures what the index did one and three months later against any session in the same "
     "history. Samples are counted in separate episodes, and nothing uses information from after "
     "its own date.",
     (("Horizons", " and ".join(f"{h} sessions" for h in HORIZONS.values())),
      ("Unit", f"Episodes · stretches < {EPISODE_GAP} sessions apart merge"),
      ("Baseline", "Any session, same history"))),
)

_OUTCOMES = (
    ("A breadth read",
     "Where the market stands on the Relative Breadth oscillator, which way participation is "
     "moving, and the five readings behind it on one card."),
    ("Its record",
     "What the index has done after this zone, and after each crossing of a zone line, against "
     "what it does after any session — with the number of separate episodes behind it."),
    ("Where it comes from",
     "The same oscillator applied to every sector, week by week, so a broad move can be told "
     "from a narrow one."),
    ("The full record",
     "Every daily count and oscillator value behind the read, ready to explore or export."),
)


def render_landing_page() -> None:
    render_header("VYAPTI", "Relative Breadth · Custom Breadth · Relative A/D Ratio · A/D Line")

    st.markdown(
        """<div class="lede">
  <div class="lede-claim">One oscillator says where breadth stands, two more say which way it is
    moving, and the index's own history says whether that reading has ever mattered.</div>
  <div class="lede-cta">Pick a market in the rail, then <strong>Run analysis</strong>.</div>
</div>""",
        unsafe_allow_html=True,
    )

    render_section_header(
        "Engines",
        "Three readings of the same market, in the order the argument runs: one makes the claim, "
        "one says which way it is moving, one checks the claim against history.",
        icon="cpu",
    )
    st.markdown(
        '<div class="system-grid">'
        + "".join(
            f'<div class="system-panel">'
            f'<div class="panel-hdr"><div class="ph-left">'
            f'<span class="ph-title">{html_mod.escape(name)}</span>'
            f'<span class="ph-context">{html_mod.escape(kicker)}</span>'
            f'</div></div>'
            f'<div class="panel-copy">{html_mod.escape(body)}</div>'
            f'<div class="panel-specs">'
            + "".join(
                f'<div class="lookback-row">'
                f'<span class="lbl">{html_mod.escape(k)}</span>'
                f'<span class="val">{html_mod.escape(v)}</span></div>'
                for k, v in specs
            )
            + "</div></div>"
            for name, kicker, body, specs in _SYSTEM_PANELS
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    render_section_header(
        "Inputs & Scope",
        f"What the oscillators can be pointed at, and how much history stands behind each read. {TAGLINE}.",
        icon="database",
    )
    render_kpi_strip(
        [
            {"label": "Indian Indexes", "value": str(len(INDIA_INDEX_LIST)),
             "subtext": "NIFTY broad, mid, small-cap and sector indexes, constituents from the NSE "
                        "index files"},
            {"label": "US Indexes", "value": str(len(US_INDEX_LIST)),
             "subtext": "S&P 500, Dow Jones and NASDAQ 100, constituents and sectors from Wikipedia"},
            {"label": "Futures & Currencies", "value": f"{len(COMMODITIES_META)} · {len(CURRENCY_META)}",
             "subtext": "Commodity futures in six groups; currencies all measured against the US dollar"},
            {"label": "Record", "value": "3–10y",
             "subtext": "Daily prices from Yahoo Finance. Each reading uses only what was known on its "
                        "own date"},
        ],
        max_cols=4,
        key="landing-scope",
    )

    render_section_header(
        "Run Outputs",
        "Four things land on screen when a run finishes, each with the evidence behind it.",
        icon="target",
    )
    st.markdown(
        '<div class="outcome-grid">'
        + "".join(
            f'<div class="outcome"><div class="o-t">{html_mod.escape(t)}</div>'
            f'<div class="o-d">{html_mod.escape(d)}</div></div>'
            for t, d in _OUTCOMES
        )
        + "</div>",
        unsafe_allow_html=True,
    )
