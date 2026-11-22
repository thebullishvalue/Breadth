"""Forward-return studies: what has the benchmark done after each signal / in each regime?

Caveats surfaced in the UI: constituents are today's members (survivorship
bias), forward windows of nearby events overlap, and small samples are noisy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .indicators import REGIMES
from .signals import SIGNALS

HORIZONS = (5, 10, 21, 63)
MIN_SAMPLE = 5


def forward_returns(price: pd.Series, horizons=HORIZONS) -> pd.DataFrame:
    """Percent return from each session's close to the close ``h`` sessions later."""
    return pd.DataFrame({h: (price.shift(-h) / price - 1) * 100 for h in horizons})


def event_study(events: dict[str, pd.Series], price: pd.Series, horizons=HORIZONS) -> pd.DataFrame:
    fwd = forward_returns(price, horizons)
    base = fwd.mean()
    rows = []
    for sig in SIGNALS:
        flags = events.get(sig.key)
        if flags is None:
            continue
        dates = flags.index[flags.to_numpy()]
        row = {"Signal": sig.label, "Bias": sig.bias, "Events": len(dates),
               "Last": f"{dates[-1]:%Y-%m-%d}" if len(dates) else "—"}
        sample = fwd.loc[dates]
        for h in horizons:
            r = sample[h].dropna()
            row[f"Avg {h}D %"] = r.mean() if len(r) else np.nan
            row[f"Hit {h}D %"] = 100 * (r > 0).mean() if len(r) else np.nan
            row[f"Edge {h}D %"] = r.mean() - base[h] if len(r) else np.nan
        row["Low Sample"] = len(dates) < MIN_SAMPLE
        rows.append(row)
    baseline = {"Signal": "All sessions (baseline)", "Bias": "", "Events": int(fwd[horizons[0]].notna().sum()),
                "Last": "", "Low Sample": False}
    for h in horizons:
        r = fwd[h].dropna()
        baseline[f"Avg {h}D %"] = r.mean()
        baseline[f"Hit {h}D %"] = 100 * (r > 0).mean() if len(r) else np.nan
        baseline[f"Edge {h}D %"] = 0.0
    rows.append(baseline)
    return pd.DataFrame(rows)


def regime_study(regime: pd.Series, price: pd.Series, horizon: int = 21) -> pd.DataFrame:
    """Average forward return and hit rate grouped by the health regime on the entry day."""
    fwd = forward_returns(price, (horizon,))[horizon]
    df = pd.DataFrame({"Regime": regime, "fwd": fwd}).dropna()
    df = df[df["Regime"] != "N/A"]
    order = [lab for _, lab, _ in REGIMES]
    rows = []
    for lab in order:
        r = df.loc[df["Regime"] == lab, "fwd"]
        rows.append({"Regime": lab, "Sessions": len(r),
                     f"Avg {horizon}D %": r.mean() if len(r) else np.nan,
                     f"Hit {horizon}D %": 100 * (r > 0).mean() if len(r) else np.nan})
    return pd.DataFrame(rows)


def regime_evidence(table: pd.DataFrame, regime: str, price: pd.Series, horizon: int = 21) -> str | None:
    """One-line historical context for the current regime, or None when the sample is too small."""
    row = table[table["Regime"] == regime]
    if row.empty or row["Sessions"].iloc[0] < 20:
        return None
    base = forward_returns(price, (horizon,))[horizon].dropna()
    avg, hit, n = row[f"Avg {horizon}D %"].iloc[0], row[f"Hit {horizon}D %"].iloc[0], int(row["Sessions"].iloc[0])
    return (f"History: {regime} sessions in this universe were followed by {avg:+.2f}% over {horizon} sessions "
            f"on average ({hit:.0f}% positive, n={n}), vs {base.mean():+.2f}% for all sessions.")
