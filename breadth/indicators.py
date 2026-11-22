"""Breadth indicators.

All functions take a (date x asset) close matrix with a normalised index and
return per-session series. A session counts an asset only if the asset
actually printed that day; the previous close is carried across gaps of up to
``MAX_GAP`` sessions so a one-exchange holiday does not break the comparison.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .data import normalize_index

EMA_PERIOD = 10
EMA_ALPHA = 2.0 / (EMA_PERIOD + 1)          # ≈ 0.18182
FIB_PERIODS = (2, 3, 5, 8, 13, 21)
MA_WINDOWS = (20, 50, 200)
HIGH_LOW_WINDOW = 252                         # 52 weeks
MCCLELLAN_FAST, MCCLELLAN_SLOW = 0.10, 0.05   # classic 19/39-day smoothing constants
MAX_GAP = 2
MIN_ASSETS_PER_DAY = 10
MIN_COVERAGE = 0.5                            # fraction of universe that must report

# Net new highs as % of eligible constituents mapped onto 0-100 for the Health
# Score: 50 + HL_SCALE x net%, so a net +/-20% of the universe at 52-week
# extremes (an exceptional reading) saturates at 100 / 0.
HL_SCALE = 2.5

# Health score bands (0-100). Order matters: first match from the top wins.
REGIMES = [
    (70, "STRONG", "success"),
    (55, "HEALTHY", "success"),
    (45, "NEUTRAL", "neutral"),
    (30, "WEAK", "danger"),
    (-np.inf, "WASHOUT", "danger"),
]
# Tactical (short-term stretch) bands on the Relative Breadth oscillator.
OVERSOLD, OVERBOUGHT = 0.40, 0.50


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


def _ema(x: pd.Series, alpha: float) -> pd.Series:
    return x.ewm(alpha=alpha, adjust=False, ignore_na=True).mean()


def daily_returns(close: pd.DataFrame) -> pd.DataFrame:
    """Per-asset returns, only on sessions where the asset printed."""
    ref = close.ffill(limit=MAX_GAP).shift(1)
    return (close / ref - 1).where(close.notna())


def _share(flags: pd.DataFrame, eligible: pd.DataFrame, min_count: int) -> pd.Series:
    n = eligible.sum(axis=1)
    pct = 100.0 * (flags & eligible).sum(axis=1) / n.where(n > 0)
    return pct.where(n >= min_count)


def compute_panel(close: pd.DataFrame, volume: pd.DataFrame | None = None) -> pd.DataFrame:
    """Full-history breadth panel indexed by date (sessions with thin coverage dropped)."""
    close = normalize_index(close)
    n_assets = close.shape[1]
    observed = close.notna()
    rets = daily_returns(close)

    adv = (rets > 0).sum(axis=1)
    dec = (rets < 0).sum(axis=1)
    unch = (rets == 0).sum(axis=1)
    total = adv + dec + unch

    min_total = min(max(MIN_ASSETS_PER_DAY, int(np.ceil(MIN_COVERAGE * n_assets))), n_assets)
    keep = total >= min_total
    keep.iloc[0] = False  # first row has no prior close

    p = pd.DataFrame({"Advances": adv, "Declines": dec, "Unchanged": unch, "Total": total})
    p["Coverage"] = 100.0 * total / n_assets

    a, d = adv.astype(float), dec.astype(float)
    p["Net_Advances"] = adv - dec
    p["AD_Ratio"] = np.where(d > 0, a / d.where(d > 0, 1.0), a)

    # Participation in trend: share of assets above their own moving averages.
    filled = close.ffill(limit=MAX_GAP)
    min_elig = max(1, min_total // 2)
    for w in MA_WINDOWS:
        sma = filled.rolling(w, min_periods=int(w * 0.9)).mean()
        p[f"Pct_Above_{w}"] = _share(close > sma, observed & sma.notna(), min_elig)

    # 52-week closing highs / lows.
    hi = filled.rolling(HIGH_LOW_WINDOW, min_periods=int(HIGH_LOW_WINDOW * 0.9)).max()
    lo = filled.rolling(HIGH_LOW_WINDOW, min_periods=int(HIGH_LOW_WINDOW * 0.9)).min()
    elig = observed & hi.notna()
    nh = ((close >= hi) & elig).sum(axis=1).astype(float)
    nl = ((close <= lo) & elig).sum(axis=1).astype(float)
    has_hl = elig.sum(axis=1) >= min_elig
    p["New_Highs"] = nh.where(has_hl)
    p["New_Lows"] = nl.where(has_hl)
    p["NH_NL"] = (nh - nl).where(has_hl)
    n_elig = elig.sum(axis=1).astype(float)
    p["NH_NL_Pct"] = (100.0 * (nh - nl) / n_elig.where(n_elig > 0)).where(has_hl)
    p["HL_Score"] = (50.0 + HL_SCALE * p["NH_NL_Pct"]).clip(0, 100)

    # Traded value on up vs down sessions.
    if volume is not None and not volume.empty:
        val = (close * normalize_index(volume).reindex_like(close)).where(observed)
        uv = val.where(rets > 0).sum(axis=1, min_count=1)
        dv = val.where(rets < 0).sum(axis=1, min_count=1)
        valid = (uv.fillna(0) + dv.fillna(0)) > 0
        uv, dv = uv.fillna(0).where(valid), dv.fillna(0).where(valid)
    else:
        uv = dv = pd.Series(np.nan, index=close.index)
    p["Up_Value"], p["Down_Value"] = uv, dv
    p["UpDown_Value_Ratio"] = uv / dv.where(dv > 0)
    p["TRIN"] = (a / d.where(d > 0)) / p["UpDown_Value_Ratio"].where(p["UpDown_Value_Ratio"] > 0)

    # Equal-weight composite of the universe.
    p["EW_Return"] = rets.mean(axis=1)

    p = p[keep].copy()
    p.index.name = "Date"
    if p.empty:
        return p

    p["EW_Index"] = 100.0 * (1 + p["EW_Return"].fillna(0)).cumprod()
    p["AD_Line"] = p["Net_Advances"].cumsum()
    p["ADR_MA10"] = p["AD_Ratio"].rolling(10, min_periods=1).mean()

    # Custom Breadth: seeded EMA-10 of A/(A+D) (Zweig's breadth thrust measure).
    a, d = p["Advances"].astype(float), p["Declines"].astype(float)
    x = (a / (a + d).where(a + d > 0)).fillna(0.5)
    p["Custom_Breadth"] = seeded_ema(x)
    cb = p["Custom_Breadth"]
    z = sum(cb.rolling(n, min_periods=1).mean() for n in FIB_PERIODS) / len(FIB_PERIODS)
    p["Relative_Breadth"] = (z + cb) / 2.0

    diff_adr = p["AD_Ratio"].diff()
    multi = sum(diff_adr.rolling(n, min_periods=1).mean() for n in (2, 3, 5)) / 3.0
    p["Rel_AD_Ratio"] = (diff_adr + multi) / 2.0

    # Ratio-adjusted McClellan Oscillator / Summation Index (comparable across universe sizes).
    rana = 1000.0 * (a - d) / (a + d).where(a + d > 0)
    rana = rana.fillna(0.0)
    p["McClellan_Osc"] = _ema(rana, MCCLELLAN_FAST) - _ema(rana, MCCLELLAN_SLOW)
    p["McClellan_Sum"] = p["McClellan_Osc"].cumsum()

    # Health: structural participation score, 0-100. Deliberately excludes the
    # 20-DMA reading, which is tactical and would make the score whipsaw.
    parts = p[["Pct_Above_50", "Pct_Above_200", "HL_Score"]]
    p["Health_Score"] = parts.mean(axis=1).where(parts.notna().all(axis=1))
    p["Regime"] = p["Health_Score"].map(classify_health)
    p["Tactical"] = p["Relative_Breadth"].map(classify_tactical)
    return p


def classify_health(score: float) -> str:
    if score is None or pd.isna(score):
        return "N/A"
    for floor, label, _ in REGIMES:
        if score >= floor:
            return label
    return "N/A"


def regime_css(label: str) -> str:
    return next((css for _, lab, css in REGIMES if lab == label), "neutral")


def classify_tactical(rb: float) -> str:
    if rb is None or pd.isna(rb):
        return "N/A"
    if rb < OVERSOLD:
        return "OVERSOLD"
    if rb > OVERBOUGHT:
        return "OVERBOUGHT"
    return "NEUTRAL"


def classify_adr(adr: float) -> tuple[str, str]:
    """Return ``(sentiment label, css class)`` for a single-day A/D ratio (as displayed, 2 dp)."""
    adr = round(float(adr), 2)
    if adr > 1.2:
        return "STRONG BULLISH", "success"
    if adr > 1.0:
        return "BULLISH", "success"
    if adr < 0.8:
        return "STRONG BEARISH", "danger"
    if adr < 1.0:
        return "BEARISH", "danger"
    return "NEUTRAL", "neutral"


def window(panel: pd.DataFrame, start, end) -> pd.DataFrame:
    """Slice the panel to [start, end] and re-anchor cumulative series at the window start."""
    view = panel.loc[pd.Timestamp(start):pd.Timestamp(end)].copy()
    if view.empty:
        return view
    view["AD_Line"] = view["Net_Advances"].cumsum()
    view["McClellan_Sum"] = view["McClellan_Osc"].cumsum()
    view["EW_Index"] = 100.0 * (1 + view["EW_Return"].fillna(0)).cumprod()
    return view


# ══════════════════════════════════════════════════════════════════════════════
# CROSS-SECTION (per-asset snapshot and sector aggregation)
# ══════════════════════════════════════════════════════════════════════════════

def asset_snapshot(close: pd.DataFrame, date, names=None, sectors=None) -> pd.DataFrame:
    """Per-asset state on ``date``: change, 1M return, trend position, 52-week location."""
    close = normalize_index(close)
    cols = ["Symbol", "Name", "Sector", "Price", "Chg_1D_%", "Ret_21D_%", "Above_50DMA",
            "Above_200DMA", "From_52W_High_%", "New_High", "New_Low"]
    date = pd.Timestamp(date)
    if date not in close.index:
        return pd.DataFrame(columns=cols)
    pos = close.index.get_loc(date)
    filled = close.ffill(limit=MAX_GAP)
    hist = filled.iloc[: pos + 1]
    price = close.iloc[pos]
    prev = filled.iloc[pos - 1] if pos > 0 else pd.Series(np.nan, index=close.columns)
    ref21 = filled.iloc[pos - 21] if pos >= 21 else pd.Series(np.nan, index=close.columns)
    sma50 = hist.tail(50).mean().where(hist.tail(50).count() >= 45)
    sma200 = hist.tail(200).mean().where(hist.tail(200).count() >= 180)
    win = hist.tail(HIGH_LOW_WINDOW)
    enough = win.count() >= int(HIGH_LOW_WINDOW * 0.9)
    hi, lo = win.max().where(enough), win.min().where(enough)
    names, sectors = names or {}, sectors or {}
    snap = pd.DataFrame({
        "Symbol": [str(c).removesuffix(".NS") for c in close.columns],
        "Name": [names.get(c, "") for c in close.columns],
        "Sector": [sectors.get(c, "Unclassified") for c in close.columns],
        "Price": price.to_numpy(),
        "Chg_1D_%": ((price / prev - 1) * 100).to_numpy(),
        "Ret_21D_%": ((price / ref21 - 1) * 100).to_numpy(),
        "Above_50DMA": (price > sma50).where(sma50.notna()).to_numpy(),
        "Above_200DMA": (price > sma200).where(sma200.notna()).to_numpy(),
        "From_52W_High_%": ((price / hi - 1) * 100).to_numpy(),
        "New_High": (price >= hi).where(hi.notna()).to_numpy(),
        "New_Low": (price <= lo).where(lo.notna()).to_numpy(),
    }, index=close.columns)
    snap = snap[snap["Price"].notna()]
    return snap.sort_values("Chg_1D_%", ascending=False).reset_index(drop=True)


def sector_table(snapshot: pd.DataFrame) -> pd.DataFrame:
    """Aggregate an asset snapshot by sector."""
    if snapshot.empty:
        return pd.DataFrame()
    s = snapshot.copy()
    for c in ("Above_50DMA", "Above_200DMA", "New_High", "New_Low"):
        s[c] = s[c].astype(float)
    g = s.groupby("Sector")
    out = pd.DataFrame({
        "Members": g.size(),
        "Adv": g["Chg_1D_%"].apply(lambda x: int((x > 0).sum())),
        "Dec": g["Chg_1D_%"].apply(lambda x: int((x < 0).sum())),
        "Pct_Above_50": 100 * g["Above_50DMA"].mean(),
        "Pct_Above_200": 100 * g["Above_200DMA"].mean(),
        "NH": g["New_High"].sum(),
        "NL": g["New_Low"].sum(),
        "EW_Ret_21D_%": g["Ret_21D_%"].mean(),
        "EW_Chg_1D_%": g["Chg_1D_%"].mean(),
    })
    out["NH"] = out["NH"].astype(int)
    out["NL"] = out["NL"].astype(int)
    # Rank by participation, but keep tiny sectors (where one stock is 100%) at the bottom.
    out["_small"] = out["Members"] < 3
    out = out.sort_values(["_small", "Pct_Above_50"], ascending=[True, False]).drop(columns="_small")
    return out.reset_index()


def sector_participation_history(close: pd.DataFrame, sectors: dict, ma: int = 50) -> pd.DataFrame:
    """% of each sector's members above their ``ma``-session MA, per session."""
    close = normalize_index(close)
    filled = close.ffill(limit=MAX_GAP)
    sma = filled.rolling(ma, min_periods=int(ma * 0.9)).mean()
    elig = close.notna() & sma.notna()
    above = (close > sma) & elig
    groups = pd.Series({c: sectors.get(c, "Unclassified") for c in close.columns})
    num = above.T.groupby(groups).sum().T
    den = elig.T.groupby(groups).sum().T
    return 100.0 * num / den.where(den > 0)
