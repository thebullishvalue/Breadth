"""Discrete breadth events and the plain-language desk note."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .indicators import OVERBOUGHT, OVERSOLD

THRUST_LOW, THRUST_HIGH, THRUST_DAYS = 0.40, 0.615, 10   # Zweig breadth thrust
WASHOUT_LEVEL = 15.0                                      # % above 50-DMA
DIVERGENCE_LOOKBACK = 63                                  # ~3 months
DIVERGENCE_GAP = 15.0                                     # percentage points
COOLDOWN = 10                                             # sessions between counted events


@dataclass(frozen=True)
class SignalDef:
    key: str
    label: str
    bias: str          # "bullish" | "bearish" | "context"
    description: str


SIGNALS = [
    SignalDef("thrust", "Breadth Thrust", "bullish",
              f"10-day EMA of A/(A+D) rises from below {THRUST_LOW:.2f} to above {THRUST_HIGH:.3f} "
              f"within {THRUST_DAYS} sessions (Zweig)."),
    SignalDef("rb_oversold", "Relative Breadth Oversold", "bullish",
              f"Relative Breadth crosses below {OVERSOLD:.2f}."),
    SignalDef("rb_overbought", "Relative Breadth Overbought", "bearish",
              f"Relative Breadth crosses above {OVERBOUGHT:.2f}."),
    SignalDef("washout", "Participation Washout", "bullish",
              f"Share of constituents above their 50-DMA falls below {WASHOUT_LEVEL:.0f}%."),
    SignalDef("bear_div", "Bearish Divergence", "bearish",
              f"Benchmark at a {DIVERGENCE_LOOKBACK}-session high while % above 50-DMA is "
              f"{DIVERGENCE_GAP:.0f}+ pts below its own {DIVERGENCE_LOOKBACK}-session high."),
    SignalDef("bull_div", "Bullish Divergence", "bullish",
              f"Benchmark at a {DIVERGENCE_LOOKBACK}-session low while % above 50-DMA is "
              f"{DIVERGENCE_GAP:.0f}+ pts above its own {DIVERGENCE_LOOKBACK}-session low."),
]
SIGNAL_BY_KEY = {s.key: s for s in SIGNALS}


def _cross_below(s: pd.Series, level: float) -> pd.Series:
    return (s < level) & (s.shift(1) >= level)


def _cross_above(s: pd.Series, level: float) -> pd.Series:
    return (s > level) & (s.shift(1) <= level)


def debounce(flags: pd.Series, cooldown: int = COOLDOWN) -> pd.Series:
    """Keep an event only if no event was kept in the previous ``cooldown`` sessions."""
    out = pd.Series(False, index=flags.index)
    last = -cooldown - 1
    for i, f in enumerate(flags.fillna(False).to_numpy()):
        if f and i - last > cooldown:
            out.iloc[i] = True
            last = i
    return out


def align_benchmark(panel: pd.DataFrame, benchmark: pd.Series | None) -> tuple[pd.Series, str]:
    """Benchmark on the panel's sessions; falls back to the equal-weight composite."""
    if benchmark is not None and len(benchmark.dropna()):
        b = benchmark.reindex(panel.index.union(benchmark.index)).ffill().reindex(panel.index)
        if b.notna().mean() > 0.9:
            return b, "benchmark"
    return panel["EW_Index"], "equal-weight composite"


def detect_events(panel: pd.DataFrame, price: pd.Series) -> dict[str, pd.Series]:
    """Boolean event series (debounced) keyed by signal key."""
    cb, rb, p50 = panel["Custom_Breadth"], panel["Relative_Breadth"], panel["Pct_Above_50"]
    thrust = _cross_above(cb, THRUST_HIGH) & (cb.rolling(THRUST_DAYS, min_periods=1).min() < THRUST_LOW)

    n = DIVERGENCE_LOOKBACK
    p_hi = price >= price.rolling(n, min_periods=n).max()
    p_lo = price <= price.rolling(n, min_periods=n).min()
    bear = p_hi & (p50 <= p50.rolling(n, min_periods=n).max() - DIVERGENCE_GAP)
    bull = p_lo & (p50 >= p50.rolling(n, min_periods=n).min() + DIVERGENCE_GAP)

    raw = {
        "thrust": thrust,
        "rb_oversold": _cross_below(rb, OVERSOLD),
        "rb_overbought": _cross_above(rb, OVERBOUGHT),
        "washout": _cross_below(p50, WASHOUT_LEVEL),
        "bear_div": bear,
        "bull_div": bull,
    }
    return {k: debounce(v.fillna(False)) for k, v in raw.items()}


def recent_events(events: dict[str, pd.Series], within: int = 5) -> list[tuple[str, pd.Timestamp, int]]:
    """Events fired in the last ``within`` sessions: (key, date, sessions ago), newest first."""
    out = []
    for key, flags in events.items():
        tail = flags.iloc[-within:]
        hits = tail[tail]
        if len(hits):
            date = hits.index[-1]
            out.append((key, date, len(flags) - 1 - flags.index.get_loc(date)))
    return sorted(out, key=lambda t: t[2])


def _fmt_delta(v: float, unit: str = "") -> str:
    return f"{v:+.1f}{unit}" if pd.notna(v) else "n/a"


def desk_note(panel: pd.DataFrame, events: dict[str, pd.Series], unit: str = "constituents") -> list[str]:
    """Short, factual bullet points describing the latest session."""
    if panel.empty:
        return []
    last = panel.iloc[-1]
    prev5 = panel.iloc[-6] if len(panel) > 5 else panel.iloc[0]
    notes = []

    hs = last["Health_Score"]
    if pd.notna(hs):
        notes.append(f"Structural health is **{last['Regime']}** at {hs:.0f}/100 "
                     f"({_fmt_delta(hs - prev5['Health_Score'])} over 5 sessions).")
    trend = []
    for w in (50, 200):
        v = last.get(f"Pct_Above_{w}")
        if pd.notna(v):
            trend.append(f"{v:.0f}% above the {w}-DMA")
    if trend:
        notes.append(f"Participation: {' and '.join(trend)} of {unit.lower()}.")
    if pd.notna(last.get("NH_NL")):
        notes.append(f"52-week highs/lows: {int(last['New_Highs'])} new highs vs {int(last['New_Lows'])} "
                     f"new lows (net {int(last['NH_NL']):+d}).")

    rb = last["Relative_Breadth"]
    if pd.notna(rb):
        notes.append(f"Tactical: Relative Breadth {rb:.3f} — **{last['Tactical']}** "
                     f"(oversold < {OVERSOLD:.2f}, overbought > {OVERBOUGHT:.2f}).")
    mo = last["McClellan_Osc"]
    if pd.notna(mo):
        slope = mo - prev5["McClellan_Osc"]
        notes.append(f"McClellan Oscillator {mo:+.0f} ({'rising' if slope > 0 else 'falling'} over 5 sessions): "
                     f"short-term breadth momentum is {'positive' if mo > 0 else 'negative'}.")

    recent = recent_events(events)
    if recent:
        items = [f"{SIGNAL_BY_KEY[k].label} ({'today' if ago == 0 else f'{ago} session(s) ago'})"
                 for k, _, ago in recent]
        notes.append("Active signals: " + "; ".join(items) + ".")
    else:
        notes.append("No breadth signals fired in the last 5 sessions.")
    return notes
