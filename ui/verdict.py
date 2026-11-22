"""The read card's content, built from an Analysis. Pure data in and out.

Tattva's anatomy, applied to breadth: one statement (the Relative Breadth zone),
whether that zone's own record in this universe licenses leaning on it, and the
oscillators behind the statement, each placed in its own history. The rows are
evidence, not votes: nothing is added up.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from breadth.indicators import OVERBOUGHT, OVERSOLD
from breadth.narrative import ZONE_MEANING

_TIER = {"FAVOURABLE": "favourable", "NORMAL": "normal", "UNFAVOURABLE": "unfavourable",
         "TOO FEW CASES": "norecord"}
_ACTION = {
    "FAVOURABLE": ("BETTER THAN NORMAL", "the index has usually done better than normal from here"),
    "NORMAL": ("ABOUT NORMAL", "the index has usually done about as well as normal from here"),
    "UNFAVOURABLE": ("WORSE THAN NORMAL", "the index has usually done worse than normal from here"),
    "TOO FEW CASES": ("NO RECORD", "too few past episodes to say what this zone means here"),
}
_CLASS = {"FAVOURABLE": "buy", "UNFAVOURABLE": "sell"}


def position(series: pd.Series) -> float:
    """Where the latest value sits in the series' own history, 0..1."""
    s = pd.Series(series).dropna()
    if len(s) < 2:
        return 0.5
    return float((s.iloc[:-1] < s.iloc[-1]).mean())


def _ordinal(p: float) -> str:
    n = int(round(p * 100))
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix} percentile"


def _tone(x: float, neutral_band: float = 0.0) -> str:
    if not np.isfinite(x) or abs(x) <= neutral_band:
        return "neutral"
    return "supports" if x > 0 else "against"


def build_read(a) -> dict:
    """``a`` is a ``breadth.pipeline.Analysis``."""
    p, last, zev = a.panel, a.last, a.zone_evidence
    zone, label = a.zone, a.verdict.label
    rb, cb = float(last["Relative_Breadth"]), float(last["Custom_Breadth"])
    days = int(last["Days_In_Zone"])
    since = f"{p.index[0]:%b %Y}"

    # ── Record ───────────────────────────────────────────────────────────
    row, base = zev.loc[zone], zev.loc["ALL"]
    eps = int(row["Episodes"])
    if label == "TOO FEW CASES":
        chip = f"{eps} EPISODE{'S' if eps != 1 else ''} SINCE {since.upper()}"
    else:
        chip = (f"{eps} EPISODES · UP {row['Up_1M_%']:.0f}% VS {base['Up_1M_%']:.0f}% "
                f"ONE MONTH LATER")
    action_label, prose = _ACTION[label]

    # ── Evidence rows: each oscillator in its own history ────────────────
    gap = p["Custom_Breadth"] - p["Relative_Breadth"]
    trend_gap = p["AD_Line"] - p["AD_Line_MA50"]
    rel = float(last["Rel_AD_Ratio"])
    rel3 = float(p["Rel_AD_Ratio"].tail(3).mean())
    adr = float(last["AD_Ratio"])
    tg = float(trend_gap.iloc[-1]) if pd.notna(trend_gap.iloc[-1]) else float("nan")
    zone_pos = position(p["Relative_Breadth"])
    if zone == "OVERSOLD":
        where = f"below {OVERSOLD:.2f} for {days} session{'s' if days != 1 else ''}"
    elif zone == "OVERBOUGHT":
        where = f"above {OVERBOUGHT:.2f} for {days} session{'s' if days != 1 else ''}"
    else:
        where = f"{rb - OVERSOLD:.3f} above {OVERSOLD:.2f} · {OVERBOUGHT - rb:.3f} below {OVERBOUGHT:.2f}"
    zone_tone = {"FAVOURABLE": "supports", "UNFAVOURABLE": "against"}.get(label, "neutral")

    evidence = [
        {"title": "Relative Breadth", "value": zone_pos, "tone": zone_tone,
         "label": f"{rb:.3f} · {zone.title()}",
         "detail": f"{where} · {_ordinal(zone_pos)} since {since}"},
        {"title": "Direction", "value": position(gap), "tone": _tone(float(gap.iloc[-1]), 0.005),
         "label": str(last["Direction"]).title(),
         "detail": f"Custom Breadth {cb:.3f} against Relative Breadth {rb:.3f}"},
        {"title": "Momentum", "value": position(p["Rel_AD_Ratio"]), "tone": _tone(rel3),
         "label": str(last["Momentum"]).title(),
         "detail": f"Relative A/D Ratio {rel:+.3f} · 3-session average {rel3:+.3f}"},
        {"title": "Latest session", "value": position(p["AD_Ratio"]), "tone": _tone(adr - 1.0, 0.05),
         "label": f"A/D {adr:.2f}",
         "detail": f"{int(last['Advances'])} advanced · {int(last['Declines'])} declined"},
        {"title": "Breadth trend", "value": position(trend_gap), "tone": _tone(tg),
         "label": str(last["Breadth_Trend"]).title(),
         "detail": (f"A/D line {tg:+,.0f} against its 50-session average" if np.isfinite(tg)
                    else "A/D line average not yet formed")},
    ]

    # ── Flags ────────────────────────────────────────────────────────────
    risk = None
    if zone == "OVERSOLD" and last["Direction"] == "DETERIORATING":
        risk = "No turn yet: Custom Breadth is still below Relative Breadth, and oversold readings can deepen."
    elif zone == "OVERBOUGHT" and zev.loc["OVERBOUGHT", "Time_%"] >= 35:
        risk = (f"Overbought is common here: breadth has been above {OVERBOUGHT:.2f} on "
                f"{zev.loc['OVERBOUGHT', 'Time_%']:.0f}% of sessions since {since}.")
    caveat = None
    if a.universe.is_fallback:
        caveat = "Built-in substitute constituents are in use; this is not the selected index."
    elif not a.uses_index:
        caveat = f"No index price was available; the record is measured on {a.index_name}."

    return {
        "eyebrow": f"{a.universe.name} · breadth read · one-month record",
        "signal": zone,
        "signal_class": _CLASS.get(label, "hold"),
        "headline": ZONE_MEANING[zone],
        "limit": a.verdict.sentence,
        "evidence": evidence,
        "risk": risk,
        "caveat": caveat,
        "trust": {"tier": _TIER[label], "chip": chip},
        "action": {"level": _TIER[label], "label": action_label, "prose": prose},
        "foot": (f"Bars place each reading in its own history since {since}. "
                 f"Evidence is shown, not added into a score."),
    }
