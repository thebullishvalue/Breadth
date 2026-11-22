"""The Aarambh breadth oscillators and the zone reading built on them.

Oscillators (computed from daily advance/decline counts):
    A/D Ratio          A / D
    Custom Breadth     EMA-10 of A/(A+D), seeded with the first 10-session SMA
    Relative Breadth   (Z + Custom Breadth) / 2, Z = mean of its 2/3/5/8/13/21 SMAs
    Relative A/D Ratio (d + mean(SMA2, SMA3, SMA5 of d)) / 2, d = daily change in A/D Ratio
    A/D Line           cumulative net advances

Counting rule: an asset counts on a session only if it printed that day; the
previous close is carried over gaps of up to ``MAX_GAP`` sessions.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .data import normalize_index

EMA_PERIOD = 10
FIB_PERIODS = (2, 3, 5, 8, 13, 21)
OVERSOLD, OVERBOUGHT, MIDLINE = 0.40, 0.50, 0.46
DIRECTION_BAND = 0.005      # Custom vs Relative Breadth gap needed to flip direction
TREND_MA = 50               # A/D line moving average for the breadth trend
MAX_GAP = 2
MIN_ASSETS_PER_DAY = 10
MIN_COVERAGE = 0.5
MIN_SECTOR_MEMBERS = 5

ZONES = ["OVERSOLD", "NEUTRAL", "OVERBOUGHT"]


# ══════════════════════════════════════════════════════════════════════════════
# OSCILLATORS
# ══════════════════════════════════════════════════════════════════════════════

def seeded_ema(x: pd.Series, period: int = EMA_PERIOD) -> pd.Series:
    """EMA seeded with the first full ``period``-SMA (spreadsheet convention). NaNs hold the prior value."""
    idx = x.index
    x = x.astype(float).reset_index(drop=True)
    alpha = 2.0 / (period + 1)
    seed = x.rolling(period, min_periods=period).mean()
    out = np.full(len(x), np.nan)
    first = seed.first_valid_index()
    if first is not None:
        vals = x.to_numpy()
        out[first] = seed.iloc[first]
        for i in range(first + 1, len(vals)):
            prev, cur = out[i - 1], vals[i]
            out[i] = prev if np.isnan(cur) else prev + alpha * (cur - prev)
    return pd.Series(out, index=idx)


def oscillators(adv: pd.Series, dec: pd.Series) -> pd.DataFrame:
    """The four Aarambh oscillators from advance/decline counts on the same index."""
    a, d = adv.astype(float), dec.astype(float)
    out = pd.DataFrame(index=adv.index)
    out["AD_Ratio"] = np.where(d > 0, a / d.where(d > 0, 1.0), a)
    out["ADR_MA10"] = out["AD_Ratio"].rolling(10, min_periods=1).mean()
    x = (a / (a + d).where(a + d > 0)).fillna(0.5)
    cb = seeded_ema(x)
    z = sum(cb.rolling(n, min_periods=1).mean() for n in FIB_PERIODS) / len(FIB_PERIODS)
    out["Custom_Breadth"] = cb
    out["Relative_Breadth"] = (z + cb) / 2.0
    diff = out["AD_Ratio"].diff()
    multi = sum(diff.rolling(n, min_periods=1).mean() for n in (2, 3, 5)) / 3.0
    out["Rel_AD_Ratio"] = (diff + multi) / 2.0
    return out


def daily_returns(close: pd.DataFrame) -> pd.DataFrame:
    """Per-asset returns, only on sessions where the asset printed."""
    ref = close.ffill(limit=MAX_GAP).shift(1)
    return (close / ref - 1).where(close.notna())


# ══════════════════════════════════════════════════════════════════════════════
# STAGE (zone + recent history) AND SUPPORTING READS
# ══════════════════════════════════════════════════════════════════════════════

def zone_of(rb: float) -> str:
    if pd.isna(rb):
        return "N/A"
    return "OVERSOLD" if rb < OVERSOLD else "OVERBOUGHT" if rb > OVERBOUGHT else "NEUTRAL"


def classify(osc: pd.DataFrame) -> pd.DataFrame:
    """Add Zone, Days_In_Zone, Direction and Momentum to an oscillator frame."""
    rb, cb = osc["Relative_Breadth"], osc["Custom_Breadth"]
    out = osc.copy()
    out["Zone"] = rb.map(zone_of).to_numpy()
    run = (out["Zone"] != out["Zone"].shift()).cumsum()
    out["Days_In_Zone"] = out.groupby(run).cumcount() + 1

    # Short-term direction: Custom Breadth vs Relative Breadth, with a small band to avoid flicker.
    direction, cur = [], None
    for g in (cb - rb).to_numpy():
        if not np.isnan(g):
            if g > DIRECTION_BAND:
                cur = "IMPROVING"
            elif g < -DIRECTION_BAND:
                cur = "DETERIORATING"
            elif cur is None:
                cur = "IMPROVING" if g >= 0 else "DETERIORATING"
        direction.append(cur or "N/A")
    out["Direction"] = direction

    m = osc["Rel_AD_Ratio"].rolling(3, min_periods=1).mean()
    out["Momentum"] = np.where(m.isna(), "N/A", np.where(m > 0, "POSITIVE", "NEGATIVE"))
    return out


def crossings(panel: pd.DataFrame) -> dict[str, pd.Series]:
    """Zone-line crossings, known on the day they happen (no look-ahead)."""
    z = pd.Series(panel["Zone"], index=panel.index)
    prev = z.shift()
    return {
        "OS_IN": (z == "OVERSOLD") & (prev != "OVERSOLD") & prev.notna(),
        "OS_OUT": (z != "OVERSOLD") & (prev == "OVERSOLD"),
        "OB_IN": (z == "OVERBOUGHT") & (prev != "OVERBOUGHT") & prev.notna(),
        "OB_OUT": (z != "OVERBOUGHT") & (prev == "OVERBOUGHT"),
    }


def compute_panel(close: pd.DataFrame) -> pd.DataFrame:
    """Full-history daily breadth panel (sessions with thin coverage dropped)."""
    close = normalize_index(close)
    n_assets = close.shape[1]
    rets = daily_returns(close)
    adv, dec, unch = (rets > 0).sum(axis=1), (rets < 0).sum(axis=1), (rets == 0).sum(axis=1)
    total = adv + dec + unch
    min_total = min(max(MIN_ASSETS_PER_DAY, int(np.ceil(MIN_COVERAGE * n_assets))), n_assets)
    keep = total >= min_total
    keep.iloc[0] = False

    p = pd.DataFrame({"Advances": adv, "Declines": dec, "Unchanged": unch, "Total": total,
                      "Coverage": 100.0 * total / n_assets, "EW_Return": rets.mean(axis=1)})[keep]
    p.index.name = "Date"
    if p.empty:
        return p
    p["Net_Advances"] = p["Advances"] - p["Declines"]
    p["AD_Line"] = p["Net_Advances"].cumsum()
    p["AD_Line_MA50"] = p["AD_Line"].rolling(TREND_MA, min_periods=TREND_MA).mean()
    p["Breadth_Trend"] = np.where(p["AD_Line_MA50"].isna(), "N/A",
                                  np.where(p["AD_Line"] >= p["AD_Line_MA50"], "RISING", "FALLING"))
    p["EW_Index"] = 100.0 * (1 + p["EW_Return"].fillna(0)).cumprod()
    return classify(p.join(oscillators(p["Advances"], p["Declines"])))


def window(panel: pd.DataFrame, start, end) -> pd.DataFrame:
    """Slice to [start, end]; the A/D line is re-anchored so the window starts at that day's net advances.

    The trend comparison uses the full-history line (difference to its own MA is anchor-free).
    """
    view = panel.loc[pd.Timestamp(start):pd.Timestamp(end)].copy()
    if view.empty:
        return view
    offset = view["AD_Line"].iloc[0] - view["Net_Advances"].iloc[0]
    view["AD_Line"] -= offset
    view["AD_Line_MA50"] -= offset
    view["EW_Index"] = 100.0 * (1 + view["EW_Return"].fillna(0)).cumprod()
    return view


# ══════════════════════════════════════════════════════════════════════════════
# SECTORS AND STOCKS
# ══════════════════════════════════════════════════════════════════════════════

def sector_oscillators(close: pd.DataFrame, sectors: dict, min_members: int = MIN_SECTOR_MEMBERS) -> dict:
    """Per-sector classified oscillator frames (sectors with fewer members are skipped)."""
    close = normalize_index(close)
    rets = daily_returns(close)
    groups = pd.Series({c: sectors.get(c, "Unclassified") for c in close.columns})
    out = {}
    for sector, members in groups.groupby(groups):
        cols = list(members.index)
        if len(cols) < min_members:
            continue
        r = rets[cols]
        adv, dec = (r > 0).sum(axis=1), (r < 0).sum(axis=1)
        reported = r.notna().sum(axis=1) >= max(2, int(np.ceil(0.5 * len(cols))))
        adv, dec = adv[reported].iloc[1:], dec[reported].iloc[1:]
        if len(adv) < 30:
            continue
        osc = classify(oscillators(adv, dec))
        osc["EW_Return"] = r.mean(axis=1).reindex(osc.index)
        osc["Members"] = len(cols)
        out[sector] = osc
    return out


def sector_snapshot(sector_osc: dict, date) -> pd.DataFrame:
    rows = []
    date = pd.Timestamp(date)
    for sector, osc in sector_osc.items():
        hist = osc.loc[:date]
        if hist.empty:
            continue
        last = hist.iloc[-1]
        rows.append({
            "Sector": sector, "Stocks": int(last["Members"]), "Zone": last["Zone"],
            "Relative_Breadth": last["Relative_Breadth"], "Direction": last["Direction"],
            "Move_1M_%": 100 * ((1 + hist["EW_Return"].tail(21).fillna(0)).prod() - 1),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["_o"] = df["Zone"].map({z: i for i, z in enumerate(ZONES)})
    return df.sort_values(["_o", "Relative_Breadth"]).drop(columns="_o").reset_index(drop=True)


def stock_snapshot(close: pd.DataFrame, date, names=None, sectors=None) -> pd.DataFrame:
    """Per-stock day and 1-month move on ``date``."""
    close = normalize_index(close)
    cols = ["Symbol", "Name", "Sector", "Price", "Day_%", "Month_%"]
    date = pd.Timestamp(date)
    if date not in close.index:
        return pd.DataFrame(columns=cols)
    pos = close.index.get_loc(date)
    filled = close.ffill(limit=MAX_GAP)
    price = close.iloc[pos]
    prev = filled.iloc[pos - 1] if pos > 0 else price * np.nan
    month = filled.iloc[pos - 21] if pos >= 21 else price * np.nan
    names, sectors = names or {}, sectors or {}
    snap = pd.DataFrame({
        "Symbol": [str(c).removesuffix(".NS") for c in close.columns],
        "Name": [names.get(c, "") for c in close.columns],
        "Sector": [sectors.get(c, "Unclassified") for c in close.columns],
        "Price": price.to_numpy(),
        "Day_%": ((price / prev - 1) * 100).to_numpy(),
        "Month_%": ((price / month - 1) * 100).to_numpy(),
    })
    return snap[snap["Price"].notna()].sort_values("Day_%", ascending=False).reset_index(drop=True)
