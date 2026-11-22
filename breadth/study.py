"""Historical evidence: what the index did after each Relative Breadth zone and zone crossing.

Everything here uses only information available on the day (no look-ahead):
zone membership is known each session, and a crossing is known the day it
happens. Crossings are de-duplicated with a backward-looking cool-down so a
line being re-crossed a day later does not count twice. Sample sizes are
reported as separate *episodes* because sessions inside one episode are not
independent. Every figure is compared with all sessions in the same history.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .indicators import ZONES, crossings

HORIZONS = {"1M": 21, "3M": 63}
COOLDOWN = 10            # sessions: a crossing within this many sessions of the previous one is ignored
EPISODE_GAP = 10         # sessions: zone stretches closer than this are one episode
MIN_EPISODES = 5
# A zone is called better/worse than normal only when the 1-month average return AND the
# hit rate both differ meaningfully, or the average differs by a lot.
EDGE_PTS, HIT_PTS = 0.5, 3.0
BIG_EDGE_PTS = 1.5

CROSSING_VERB = {
    "OS_IN": "turned oversold",
    "OS_OUT": "climbed out of oversold",
    "OB_IN": "turned overbought",
    "OB_OUT": "slipped from overbought",
}
CROSSING_TEXT = {
    "OS_IN": "Breadth turned oversold",
    "OS_OUT": "Breadth climbed out of oversold",
    "OB_IN": "Breadth turned overbought",
    "OB_OUT": "Breadth slipped from overbought",
}
ZONE_TEXT = {"OVERSOLD": "oversold sessions", "NEUTRAL": "neutral sessions", "OVERBOUGHT": "overbought sessions"}


def forward_returns(price: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({k: (price.shift(-h) / price - 1) * 100 for k, h in HORIZONS.items()})


def debounce(flags: pd.Series, cooldown: int = COOLDOWN) -> pd.Series:
    """Keep an event only if no event was kept in the previous ``cooldown`` sessions."""
    out = np.zeros(len(flags), dtype=bool)
    last = -cooldown - 1
    for i, f in enumerate(flags.fillna(False).to_numpy()):
        if f and i - last > cooldown:
            out[i] = True
            last = i
    return pd.Series(out, index=flags.index)


def events(panel: pd.DataFrame) -> dict[str, pd.Series]:
    return {k: debounce(v) for k, v in crossings(panel).items()}


def episode_spans(inzone: np.ndarray, gap: int = EPISODE_GAP) -> list[tuple[int, int]]:
    """(first, last) positions of zone stretches, merging stretches separated by < ``gap`` sessions."""
    spans = []
    for i in np.flatnonzero(inzone):
        if spans and i - spans[-1][1] <= gap:
            spans[-1][1] = i
        else:
            spans.append([i, i])
    return [tuple(s) for s in spans]


def episodes(panel: pd.DataFrame, zone: str, price: pd.Series) -> pd.DataFrame:
    """History of ``zone`` episodes: when, how long, how deep, and what the index did."""
    cols = ["Start", "End", "Sessions", "Extreme", "Index_During_%", "Index_1M_%", "Ongoing"]
    spans = episode_spans((panel["Zone"] == zone).to_numpy())
    if not spans:
        return pd.DataFrame(columns=cols)
    fwd = forward_returns(price)["1M"]
    rb, idx, n = panel["Relative_Breadth"], panel.index, len(panel)
    rows = []
    for s, e in spans:
        seg = rb.iloc[s:e + 1]
        rows.append({
            "Start": idx[s], "End": idx[e], "Sessions": e - s + 1,
            "Extreme": seg.min() if zone == "OVERSOLD" else seg.max(),
            "Index_During_%": (price.iloc[e] / price.iloc[s] - 1) * 100,
            "Index_1M_%": fwd.iloc[s], "Ongoing": e == n - 1,
        })
    return pd.DataFrame(rows, columns=cols)


def _summary(r: pd.DataFrame) -> dict:
    out = {}
    for k in HORIZONS:
        x = r[k].dropna()
        out[f"Up_{k}_%"] = 100 * (x > 0).mean() if len(x) else np.nan
        out[f"Avg_{k}_%"] = x.mean() if len(x) else np.nan
        out[f"N_{k}"] = len(x)
    return out


def zone_evidence(panel: pd.DataFrame, price: pd.Series) -> pd.DataFrame:
    """Per zone: share of time, separate episodes, and forward index returns from its sessions."""
    fwd = forward_returns(price)
    rows = []
    for zone in ZONES:
        mask = (panel["Zone"] == zone).to_numpy()
        rows.append({"Zone": zone, "Time_%": 100 * mask.mean(), "Sessions": int(mask.sum()),
                     "Episodes": len(episode_spans(mask)), **_summary(fwd[mask])})
    rows.append({"Zone": "ALL", "Time_%": 100.0, "Sessions": len(panel), "Episodes": np.nan, **_summary(fwd)})
    return pd.DataFrame(rows).set_index("Zone")


def crossing_evidence(panel: pd.DataFrame, price: pd.Series) -> pd.DataFrame:
    """Per crossing type: how often, when last, and forward index returns from the crossing day."""
    fwd = forward_returns(price)
    years = max(len(panel) / 252, 1e-9)
    rows = []
    for key, flags in events(panel).items():
        dates = panel.index[flags.to_numpy()]
        rows.append({"Crossing": key, "What": CROSSING_TEXT[key], "Times": len(dates),
                     "Per_Year": len(dates) / years, "Last": dates[-1] if len(dates) else pd.NaT,
                     **_summary(fwd.loc[dates])})
    return pd.DataFrame(rows).set_index("Crossing")


def recent_crossings(panel: pd.DataFrame, within: int = 10) -> list[tuple[str, int]]:
    """Crossings in the last ``within`` sessions as (key, sessions ago), newest first."""
    out = []
    for key, flags in events(panel).items():
        tail = flags.to_numpy()[-within:]
        hits = np.flatnonzero(tail)
        if len(hits):
            out.append((key, int(len(tail) - 1 - hits[-1])))
    return sorted(out, key=lambda t: t[1])


@dataclass
class Verdict:
    label: str           # FAVOURABLE | NORMAL | UNFAVOURABLE | TOO FEW CASES
    css: str
    sentence: str


def judge(row: pd.Series, base: pd.Series) -> str:
    edge = row["Avg_1M_%"] - base["Avg_1M_%"]
    hit = row["Up_1M_%"] - base["Up_1M_%"]
    if (edge >= EDGE_PTS and hit >= HIT_PTS) or (edge >= BIG_EDGE_PTS and hit >= -2):
        return "FAVOURABLE"
    if (edge <= -EDGE_PTS and hit <= -HIT_PTS) or (edge <= -BIG_EDGE_PTS and hit <= 2):
        return "UNFAVOURABLE"
    return "NORMAL"


def verdict(zev: pd.DataFrame, zone: str, index_name: str, since: pd.Timestamp) -> Verdict:
    row, base = zev.loc[zone], zev.loc["ALL"]
    eps = int(row["Episodes"])
    when = f"since {since:%b %Y}"
    if eps < MIN_EPISODES or row["N_1M"] == 0:
        return Verdict("TOO FEW CASES", "neutral",
                       f"Breadth has been {zone.lower()} in only {eps} separate episode{'s' if eps != 1 else ''} "
                       f"{when}, too few to say what it usually means for {index_name}.")
    article = "an" if zone[0] in "AEIOU" else "a"
    core = (f"Since {since:%b %Y}, breadth has been {zone.lower()} in {eps} separate episodes "
            f"({row['Time_%']:.0f}% of sessions). One month after {article} {zone.lower()} session, {index_name} was "
            f"higher {row['Up_1M_%']:.0f}% of the time, by {row['Avg_1M_%']:+.1f}% on average. After any session: "
            f"higher {base['Up_1M_%']:.0f}% of the time, by {base['Avg_1M_%']:+.1f}%.")
    label = judge(row, base)
    tail = {"FAVOURABLE": " The index has usually done better than normal from here.",
            "UNFAVOURABLE": " The index has usually done worse than normal from here.",
            "NORMAL": " The index has usually done about as well as normal from here."}[label]
    css = {"FAVOURABLE": "success", "UNFAVOURABLE": "danger", "NORMAL": "neutral"}[label]
    return Verdict(label, css, core + tail)
