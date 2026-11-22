"""
Vyāpti — Record: what each reading has meant for this index.

  1 TRUST   does any zone matter here?   Zone Record (one card per zone)
  2 ANCHOR  the full comparison          By Zone
  3 STATE   the moments of change        By Crossing
  4 EVENTS  the ledger                   Oversold Episodes

Every figure uses only what was known on its own date; samples are counted in
separate episodes; everything is compared with any session in the same history.
"""

from __future__ import annotations

import pandas as pd

from breadth.study import COOLDOWN, EPISODE_GAP, MIN_EPISODES, judge
from ui import format as fmt
from ui.components import render_kpi_strip, render_note, render_section_header, render_table_panel

VERSUS = {"FAVOURABLE": "Better", "NORMAL": "Normal", "UNFAVOURABLE": "Worse"}
VERSUS_LONG = {"FAVOURABLE": "Better than normal", "NORMAL": "About normal", "UNFAVOURABLE": "Worse than normal"}
_TONE = {"FAVOURABLE": "success", "NORMAL": "neutral", "UNFAVOURABLE": "danger"}
_ZONES = ("OVERSOLD", "NEUTRAL", "OVERBOUGHT")


def zone_cards(a) -> list[dict]:
    zev, base = a.zone_evidence, a.zone_evidence.loc["ALL"]
    cards = []
    for z in _ZONES:
        r = zev.loc[z]
        enough = r["Episodes"] >= MIN_EPISODES and r["N_1M"] > 0
        verdict = judge(r, base) if enough else None
        cards.append({
            "label": z.title(),
            "value": f"{r['Up_1M_%']:.0f}%" if enough else "—",
            "subtext": (f"{VERSUS_LONG[verdict]} · avg {r['Avg_1M_%']:+.1f}% · "
                        f"{int(r['Episodes'])} episodes" if enough
                        else f"only {int(r['Episodes'])} episodes"),
            "color_class": _TONE[verdict] if verdict else "neutral",
            "tooltip": "Share of sessions in this zone after which the index was higher one month later.",
        })
    cards.append({"label": "Any session", "value": f"{base['Up_1M_%']:.0f}%",
                  "subtext": f"the baseline · avg {base['Avg_1M_%']:+.1f}% · {int(base['N_1M']):,} sessions",
                  "color_class": "accent"})
    return cards


def zone_table(a) -> pd.DataFrame:
    zev, base = a.zone_evidence, a.zone_evidence.loc["ALL"]
    rows = []
    for z in _ZONES:
        r = zev.loc[z]
        enough = r["Episodes"] >= MIN_EPISODES
        rows.append({"Zone": z.title(), "Share %": r["Time_%"], "Episodes": int(r["Episodes"]),
                     "Up 1M %": r["Up_1M_%"], "Avg 1M %": r["Avg_1M_%"],
                     "Up 3M %": r["Up_3M_%"], "Avg 3M %": r["Avg_3M_%"],
                     "Versus normal": VERSUS[judge(r, base)] if enough else "Too few"})
    rows.append({"Zone": "Any session", "Share %": 100.0, "Episodes": None,
                 "Up 1M %": base["Up_1M_%"], "Avg 1M %": base["Avg_1M_%"],
                 "Up 3M %": base["Up_3M_%"], "Avg 3M %": base["Avg_3M_%"], "Versus normal": "—"})
    return pd.DataFrame(rows)


def crossing_table(a) -> pd.DataFrame:
    base = a.zone_evidence.loc["ALL"]
    rows = []
    for _, r in a.crossing_evidence.iterrows():
        rows.append({"Crossing": r["What"], "Times": int(r["Times"]), "Per year": r["Per_Year"],
                     "Most recent": r["Last"].date() if pd.notna(r["Last"]) else None,
                     "Up 1M %": r["Up_1M_%"], "Avg 1M %": r["Avg_1M_%"],
                     "Up 3M %": r["Up_3M_%"], "Avg 3M %": r["Avg_3M_%"],
                     "Versus normal": VERSUS[judge(r, base)] if r["N_1M"] >= MIN_EPISODES else "Too few"})
    return pd.DataFrame(rows)


def episode_table(a) -> pd.DataFrame:
    ep = a.oversold_episodes
    if ep.empty:
        return ep
    ref = a.universe.name if a.uses_index else "Basket"
    return pd.DataFrame({
        "Began": ep["Start"].dt.date,
        "Ended": [("ongoing" if o else e.date()) for e, o in zip(ep["End"], ep["Ongoing"], strict=True)],
        "Sessions": ep["Sessions"],
        "Lowest RB": ep["Extreme"],
        f"{ref} during %": ep["Index_During_%"],
        f"{ref} 1M after start %": ep["Index_1M_%"],
    }).iloc[::-1].reset_index(drop=True)


def render(a) -> None:
    since = fmt.when(a.panel.index[0], "%b %Y")
    ctx = f"{a.universe.name} · since {since} · {len(a.panel):,} sessions"

    # ── 1 · TRUST ─────────────────────────────────────────────────────────
    render_section_header(
        "Zone Record",
        f"How often {a.index_name} was higher one month after a session in each zone, against any "
        f"session. Green is a zone whose record is better than normal; red, worse.",
        icon="shield", accent="emerald",
    )
    render_kpi_strip(zone_cards(a), max_cols=4, key="record-zones")

    # ── 2 · ANCHOR ────────────────────────────────────────────────────────
    render_section_header(
        "By Zone",
        "Share of sessions spent in each zone, the number of separate episodes behind it, and the "
        "index one and three months later.",
        icon="bar-chart",
    )
    render_table_panel(
        zone_table(a), key="record-zone-table", context=ctx, label_col="Zone",
        sign_color_cols={"Avg 1M %", "Avg 3M %"},
        col_precision={"Share %": 0, "Episodes": 0, "Up 1M %": 0, "Up 3M %": 0, "Avg 1M %": 2, "Avg 3M %": 2},
        max_height=200,
    )

    # ── 3 · STATE ─────────────────────────────────────────────────────────
    render_section_header(
        "By Crossing",
        f"Measured from the day Relative Breadth crossed a zone line. A repeat crossing within "
        f"{COOLDOWN} sessions of the last one is not counted again.",
        icon="crosshair", accent="cyan",
    )
    render_table_panel(
        crossing_table(a), key="record-crossings", context=ctx, label_col="Crossing",
        sign_color_cols={"Avg 1M %", "Avg 3M %"},
        col_precision={"Per year": 1, "Up 1M %": 0, "Up 3M %": 0, "Avg 1M %": 2, "Avg 3M %": 2},
        max_height=200,
    )

    # ── 4 · EVENTS ────────────────────────────────────────────────────────
    render_section_header(
        "Oversold Episodes",
        f"Every stretch of oversold breadth since {since}, newest first. Stretches fewer than "
        f"{EPISODE_GAP} sessions apart are one episode.",
        icon="layers", accent="emerald",
    )
    ep = episode_table(a)
    if ep.empty:
        render_note("Breadth has not been oversold in this history.")
    else:
        render_table_panel(
            ep, key="record-episodes", context=f"{len(ep)} episodes", label_col="Began",
            sign_color_cols={c for c in ep.columns if c.endswith("%")},
            col_precision={"Lowest RB": 3}, max_height=420,
        )
    render_note("History uses today's index members, so companies that have since left the index are "
                "missing. Past patterns are evidence, not a guarantee.")
