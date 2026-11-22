"""
Breadth engine: universe definitions, constituent fetching, price download and
advance/decline indicator computation.

This module has no Streamlit dependency so it can be imported and unit-tested
on its own. Caching is applied in ``app.py``.
"""

from __future__ import annotations

import datetime
import io

import numpy as np
import pandas as pd
import requests
import yfinance as yf

# ══════════════════════════════════════════════════════════════════════════════
# UNIVERSES
# ══════════════════════════════════════════════════════════════════════════════

INDIA_INDEX_LIST = [
    "NIFTY 50", "NIFTY NEXT 50", "NIFTY 100", "NIFTY 200", "NIFTY 500",
    "NIFTY MIDCAP 50", "NIFTY MIDCAP 100", "NIFTY SMLCAP 100", "NIFTY BANK",
    "NIFTY AUTO", "NIFTY FIN SERVICE", "NIFTY FMCG", "NIFTY IT",
    "NIFTY MEDIA", "NIFTY METAL", "NIFTY PHARMA",
]

US_INDEX_LIST = ["S&P 500", "DOW JONES", "NASDAQ 100"]

ANALYSIS_UNIVERSE_OPTIONS = ["India Indexes", "US Indexes", "Commodities", "Currency"]

NSE_BASE_URL = "https://www.niftyindices.com/IndexConstituent/"
INDEX_URL_MAP = {
    "NIFTY 50": f"{NSE_BASE_URL}ind_nifty50list.csv",
    "NIFTY NEXT 50": f"{NSE_BASE_URL}ind_niftynext50list.csv",
    "NIFTY 100": f"{NSE_BASE_URL}ind_nifty100list.csv",
    "NIFTY 200": f"{NSE_BASE_URL}ind_nifty200list.csv",
    "NIFTY 500": f"{NSE_BASE_URL}ind_nifty500list.csv",
    "NIFTY MIDCAP 50": f"{NSE_BASE_URL}ind_niftymidcap50list.csv",
    "NIFTY MIDCAP 100": f"{NSE_BASE_URL}ind_niftymidcap100list.csv",
    "NIFTY SMLCAP 100": f"{NSE_BASE_URL}ind_niftysmallcap100list.csv",
    "NIFTY BANK": f"{NSE_BASE_URL}ind_niftybanklist.csv",
    "NIFTY AUTO": f"{NSE_BASE_URL}ind_niftyautolist.csv",
    "NIFTY FIN SERVICE": f"{NSE_BASE_URL}ind_niftyfinancelist.csv",
    "NIFTY FMCG": f"{NSE_BASE_URL}ind_niftyfmcglist.csv",
    "NIFTY IT": f"{NSE_BASE_URL}ind_niftyitlist.csv",
    "NIFTY MEDIA": f"{NSE_BASE_URL}ind_niftymedialist.csv",
    "NIFTY METAL": f"{NSE_BASE_URL}ind_niftymetallist.csv",
    "NIFTY PHARMA": f"{NSE_BASE_URL}ind_niftypharmalist.csv",
}

INDIA_INDEX_WIKI_MAP = {
    "NIFTY 50": "https://en.wikipedia.org/wiki/NIFTY_50",
    "NIFTY NEXT 50": "https://en.wikipedia.org/wiki/NIFTY_Next_50",
    "NIFTY 500": "https://en.wikipedia.org/wiki/NIFTY_500",
}

# Candidate pages in priority order (Wikipedia moved the Dow and Nasdaq-100
# component tables to dedicated list articles; the old pages are kept as backups).
US_INDEX_WIKI_MAP = {
    "S&P 500": ["https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"],
    "DOW JONES": [
        "https://en.wikipedia.org/wiki/List_of_Dow_Jones_Industrial_Average_companies",
        "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average",
    ],
    "NASDAQ 100": [
        "https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies",
        "https://en.wikipedia.org/wiki/Nasdaq-100",
    ],
}

# Expected constituent-count bounds used to reject a wrong Wikipedia table.
US_INDEX_SIZE_BOUNDS = {
    "S&P 500": (480, 520),
    "DOW JONES": (28, 32),
    "NASDAQ 100": (95, 110),
}

# Dow Jones Industrial Average components (synced with Wikipedia, Nov 2026).
# Used only if the live Wikipedia fetch fails.
DOW_JONES_TICKERS = [
    "AAPL", "AMGN", "AMZN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS",
    "GS", "HD", "HON", "IBM", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK",
    "MSFT", "NKE", "NVDA", "PG", "SHW", "TRV", "UNH", "V", "GOOGL", "WMT",
]

# Large-cap NSE names used only when both NSE and Wikipedia are unreachable.
FALLBACK_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS", "INFY.NS",
    "ITC.NS", "SBIN.NS", "LT.NS", "BAJFINANCE.NS", "KOTAKBANK.NS", "HINDUNILVR.NS",
    "AXISBANK.NS", "MARUTI.NS", "SUNPHARMA.NS", "ULTRACEMCO.NS", "M&M.NS",
    "ADANIENT.NS", "ADANIPORTS.NS", "ASIANPAINT.NS", "BAJAJ-AUTO.NS", "BAJAJFINSV.NS",
    "NTPC.NS", "ONGC.NS", "POWERGRID.NS", "TITAN.NS",
]

COMMODITY_TICKERS = {
    "GC=F": "Gold", "SI=F": "Silver", "PL=F": "Platinum", "PA=F": "Palladium",
    "HG=F": "Copper", "CL=F": "Crude Oil WTI", "BZ=F": "Brent Crude",
    "NG=F": "Natural Gas", "RB=F": "Gasoline RBOB", "HO=F": "Heating Oil",
    "ZC=F": "Corn", "ZW=F": "Wheat", "ZS=F": "Soybeans", "ZM=F": "Soybean Meal",
    "ZL=F": "Soybean Oil", "CT=F": "Cotton", "KC=F": "Coffee", "SB=F": "Sugar",
    "CC=F": "Cocoa", "OJ=F": "Orange Juice", "LBS=F": "Lumber",
    "LE=F": "Live Cattle", "HE=F": "Lean Hogs", "GF=F": "Feeder Cattle",
}

CURRENCY_TICKERS = {
    "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY",
    "USDCHF=X": "USD/CHF", "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD",
    "NZDUSD=X": "NZD/USD", "USDINR=X": "USD/INR", "EURGBP=X": "EUR/GBP",
    "EURJPY=X": "EUR/JPY", "GBPJPY=X": "GBP/JPY", "AUDJPY=X": "AUD/JPY",
    "EURCHF=X": "EUR/CHF", "EURAUD=X": "EUR/AUD", "GBPCHF=X": "GBP/CHF",
    "GBPAUD=X": "GBP/AUD", "USDSGD=X": "USD/SGD", "USDHKD=X": "USD/HKD",
    "USDCNH=X": "USD/CNH", "USDZAR=X": "USD/ZAR", "USDMXN=X": "USD/MXN",
    "USDTRY=X": "USD/TRY", "USDBRL=X": "USD/BRL", "USDKRW=X": "USD/KRW",
}

ASSET_NAMES = {**COMMODITY_TICKERS, **CURRENCY_TICKERS}

# ══════════════════════════════════════════════════════════════════════════════
# INDICATOR PARAMETERS
# ══════════════════════════════════════════════════════════════════════════════

EMA_PERIOD = 10
EMA_ALPHA = 2.0 / (EMA_PERIOD + 1)          # ≈ 0.18182
FIB_PERIODS = (2, 3, 5, 8, 13, 21)
MIN_ASSETS_PER_DAY = 10                      # absolute floor on reporting assets
MIN_COVERAGE = 0.5                           # fraction of universe that must report

# Calendar-day warm-up downloaded before the requested start date. The indicator
# chain needs 10 sessions to seed the EMA, ~25 more for the seed's weight to
# decay below 1%, and 21 sessions of Custom Breadth for the longest Fibonacci
# MA. ~120 calendar days ≈ 80 trading sessions covers that with holiday slack,
# so values inside the viewing window do not depend on where the download began.
WARMUP_CALENDAR_DAYS = 120

HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
HTTP_TIMEOUT = 15


class ConstituentFetchError(RuntimeError):
    """Raised when a constituent list cannot be obtained from any live source."""


# ══════════════════════════════════════════════════════════════════════════════
# CONSTITUENT FETCHING
# ══════════════════════════════════════════════════════════════════════════════

def _clean_symbols(values) -> list[str]:
    """Strip, drop blanks/NaN and de-duplicate while preserving order."""
    out = []
    for v in values:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            continue
        s = str(v).strip()
        if s and s.lower() != "nan" and len(s) <= 20:
            out.append(s)
    return list(dict.fromkeys(out))


def _read_html_tables(url: str) -> list[pd.DataFrame]:
    response = requests.get(url, headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT)
    response.raise_for_status()
    return pd.read_html(io.StringIO(response.text))


def _wiki_symbol_column(url: str, columns, lo: int, hi: int = 10_000) -> list[str] | None:
    """Return the first table column in ``columns`` whose size lies in [lo, hi]."""
    for tbl in _read_html_tables(url):
        # Some tables are rendered without <th>; promote the first row to headers.
        if len(tbl) and all(isinstance(c, int) for c in tbl.columns):
            tbl = tbl.iloc[1:].set_axis(tbl.iloc[0].astype(str).str.strip(), axis=1)
        for col in columns:
            if col in tbl.columns:
                symbols = _clean_symbols(tbl[col].tolist())
                if lo <= len(symbols) <= hi:
                    return symbols
    return None


def fetch_nse_constituents(index: str) -> list[str]:
    url = INDEX_URL_MAP[index]
    response = requests.get(url, headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT)
    response.raise_for_status()
    stock_df = pd.read_csv(io.StringIO(response.text))
    if "Symbol" not in stock_df.columns:
        raise ConstituentFetchError(f"NSE CSV for {index} has no 'Symbol' column")
    symbols = _clean_symbols(stock_df["Symbol"].tolist())
    if not symbols:
        raise ConstituentFetchError(f"NSE CSV for {index} is empty")
    return [s + ".NS" for s in symbols]


def fetch_india_wiki_constituents(index: str) -> list[str] | None:
    """Wikipedia fallback. Only indexes with a faithful Wikipedia table are supported."""
    if index == "NIFTY 100":
        n50 = _wiki_symbol_column(INDIA_INDEX_WIKI_MAP["NIFTY 50"], ["Symbol"], 45, 55)
        nn50 = _wiki_symbol_column(INDIA_INDEX_WIKI_MAP["NIFTY NEXT 50"], ["Symbol"], 45, 55)
        if n50 and nn50:
            return [s + ".NS" for s in dict.fromkeys(n50 + nn50)]
        return None

    url = INDIA_INDEX_WIKI_MAP.get(index)
    if not url:
        return None
    lo, hi = {"NIFTY 50": (45, 55), "NIFTY NEXT 50": (45, 55), "NIFTY 500": (450, 520)}[index]
    symbols = _wiki_symbol_column(url, ["Symbol"], lo, hi)
    return [s + ".NS" for s in symbols] if symbols else None


def get_india_constituents(index: str) -> tuple[list[str], str, bool]:
    """Return ``(tickers, message, is_fallback)`` for an Indian index."""
    if index not in INDEX_URL_MAP:
        raise ValueError(f"Unknown India index: {index}")

    try:
        symbols = fetch_nse_constituents(index)
        return symbols, f"Fetched {len(symbols)} {index} constituents from NSE", False
    except Exception:
        pass

    try:
        symbols = fetch_india_wiki_constituents(index)
        if symbols:
            return symbols, f"NSE unreachable; fetched {len(symbols)} {index} constituents from Wikipedia", False
    except Exception:
        pass

    return (
        FALLBACK_TICKERS,
        f"NSE and Wikipedia unavailable for {index}; using built-in fallback list "
        f"({len(FALLBACK_TICKERS)} large caps, not the actual index)",
        True,
    )


def fetch_us_wiki_constituents(index: str) -> list[str] | None:
    lo, hi = US_INDEX_SIZE_BOUNDS[index]
    for url in US_INDEX_WIKI_MAP[index]:
        try:
            symbols = _wiki_symbol_column(url, ["Symbol", "Ticker", "Ticker symbol"], lo, hi)
        except Exception:
            continue
        if symbols:
            # Yahoo uses '-' for share classes (BRK.B -> BRK-B)
            return [s.replace(".", "-") for s in symbols]
    return None


def get_us_constituents(index: str) -> tuple[list[str], str, bool]:
    """Return ``(tickers, message, is_fallback)`` for a US index."""
    if index not in US_INDEX_WIKI_MAP:
        raise ValueError(f"Unknown US index: {index}")
    try:
        symbols = fetch_us_wiki_constituents(index)
        if symbols:
            return symbols, f"Fetched {len(symbols)} {index} constituents from Wikipedia", False
    except Exception:
        pass

    if index == "DOW JONES":
        msg = f"Wikipedia unavailable; using built-in {len(DOW_JONES_TICKERS)} Dow Jones tickers"
        return DOW_JONES_TICKERS, msg, True
    raise ConstituentFetchError(f"Could not fetch {index} constituents from Wikipedia")


def get_commodity_list() -> tuple[list[str], str, bool]:
    tickers = list(COMMODITY_TICKERS)
    return tickers, f"Loaded {len(tickers)} commodity futures", False


def get_currency_list() -> tuple[list[str], str, bool]:
    tickers = list(CURRENCY_TICKERS)
    return tickers, f"Loaded {len(tickers)} currency pairs", False


# ══════════════════════════════════════════════════════════════════════════════
# PRICE DOWNLOAD
# ══════════════════════════════════════════════════════════════════════════════

def _normalize_index(df: pd.DataFrame) -> pd.DataFrame:
    """Date-only, tz-naive, sorted, de-duplicated index."""
    idx = pd.to_datetime(df.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    df = df.copy()
    df.index = idx.normalize()
    df = df[~df.index.duplicated(keep="last")]
    return df.sort_index()


def extract_close(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame | None:
    """Pull a (date x ticker) Close matrix out of a yfinance download frame."""
    if raw is None or raw.empty:
        return None
    if isinstance(raw.columns, pd.MultiIndex):
        for level in range(raw.columns.nlevels):
            if "Close" in raw.columns.get_level_values(level):
                close = raw.xs("Close", level=level, axis=1)
                break
        else:
            return None
    elif "Close" in raw.columns:
        close = raw[["Close"]]
        close.columns = tickers[:1]
    else:
        return None
    close = close.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")
    return close if not close.empty else None


def download_close_matrix(
    tickers: list[str],
    start_date: datetime.date,
    end_date: datetime.date,
    today: datetime.date | None = None,
) -> tuple[pd.DataFrame, str]:
    """Download adjusted closes for ``tickers`` with indicator warm-up.

    Raises ``RuntimeError`` when no usable data comes back.
    """
    today = today or datetime.date.today()
    tickers = list(tickers)
    download_start = start_date - datetime.timedelta(days=WARMUP_CALENDAR_DAYS)
    download_end = end_date + datetime.timedelta(days=1)  # yfinance `end` is exclusive

    raw = yf.download(
        tickers,
        start=download_start,
        end=download_end,
        progress=False,
        auto_adjust=True,
        group_by="ticker",
        threads=True,
    )
    close_df = extract_close(raw, tickers)
    if close_df is None:
        raise RuntimeError("No price data returned from Yahoo Finance")
    close_df = _normalize_index(close_df)

    # Best-effort intraday append: the daily history endpoint can lag the
    # current session by a few minutes after the open.
    if end_date >= today and pd.Timestamp(today) not in close_df.index:
        try:
            live_raw = yf.download(
                close_df.columns.tolist(), period="1d", progress=False,
                auto_adjust=True, group_by="ticker", threads=True,
            )
            live_close = extract_close(live_raw, close_df.columns.tolist())
            if live_close is not None:
                live_close = _normalize_index(live_close)
                new_rows = live_close.loc[~live_close.index.isin(close_df.index)]
                if not new_rows.empty:
                    close_df = pd.concat([close_df, new_rows]).sort_index()
        except Exception:
            pass

    return close_df, f"Built close matrix for {close_df.shape[1]} assets ({len(close_df)} sessions incl. warm-up)"


# ══════════════════════════════════════════════════════════════════════════════
# BREADTH COMPUTATION
# ══════════════════════════════════════════════════════════════════════════════

BREADTH_COLUMNS = [
    "Date", "Advances", "Declines", "Unchanged", "Total", "Net_Advances",
    "AD_Ratio", "AD_Line", "ADR_MA10", "Custom_Breadth", "Relative_Breadth", "Rel_AD_Ratio",
]


def seeded_ema(x: pd.Series, period: int = EMA_PERIOD) -> pd.Series:
    """EMA seeded with the first full ``period``-SMA (spreadsheet convention)."""
    x = x.reset_index(drop=True).astype(float)
    alpha = 2.0 / (period + 1)
    seed = x.rolling(period, min_periods=period).mean()
    out = np.full(len(x), np.nan)
    first = seed.first_valid_index()
    if first is None:
        return pd.Series(out)
    vals = x.to_numpy()
    out[first] = seed.iloc[first]
    for i in range(first + 1, len(vals)):
        prev = out[i - 1]
        cur = vals[i]
        out[i] = prev if np.isnan(cur) else prev + alpha * (cur - prev)
    return pd.Series(out)


def compute_breadth(close_df: pd.DataFrame) -> pd.DataFrame:
    """Full-history breadth table (including warm-up rows)."""
    close_df = _normalize_index(close_df)
    observed = close_df.notna()
    # Carry the reference price over short gaps (holidays on one exchange,
    # a missed print), but only count an asset on days it actually printed.
    ref = close_df.ffill(limit=2).shift(1)
    pct = (close_df / ref - 1).where(observed)
    pct = pct.iloc[1:]

    advances = (pct > 0).sum(axis=1)
    declines = (pct < 0).sum(axis=1)
    unchanged = (pct == 0).sum(axis=1)
    total = advances + declines + unchanged

    df = pd.DataFrame({
        "Date": pct.index,
        "Advances": advances.to_numpy(),
        "Declines": declines.to_numpy(),
        "Unchanged": unchanged.to_numpy(),
        "Total": total.to_numpy(),
    })

    min_total = max(MIN_ASSETS_PER_DAY, int(np.ceil(MIN_COVERAGE * close_df.shape[1])))
    min_total = min(min_total, close_df.shape[1])  # tiny universes: require everyone
    df = df[df["Total"] >= min_total].reset_index(drop=True)
    if df.empty:
        return pd.DataFrame(columns=BREADTH_COLUMNS)

    adv = df["Advances"].astype(float)
    dec = df["Declines"].astype(float)

    df["Net_Advances"] = df["Advances"] - df["Declines"]
    # When nothing declined the ratio is undefined; report advances as the ratio
    # (conventional cap) so the series stays finite.
    df["AD_Ratio"] = np.where(dec > 0, adv / dec.where(dec > 0, 1.0), adv)
    df["AD_Line"] = df["Net_Advances"].cumsum()
    df["ADR_MA10"] = df["AD_Ratio"].rolling(10, min_periods=1).mean()

    # Custom Breadth: EMA of A/(A+D). Days with no directional moves are neutral.
    ad_sum = adv + dec
    x = (adv / ad_sum.where(ad_sum > 0)).fillna(0.5)
    df["Custom_Breadth"] = seeded_ema(x).to_numpy()

    cb = df["Custom_Breadth"]
    z = sum(cb.rolling(p, min_periods=1).mean() for p in FIB_PERIODS) / len(FIB_PERIODS)
    df["Relative_Breadth"] = (z + cb) / 2.0

    diff_adr = df["AD_Ratio"].diff()
    multi = sum(diff_adr.rolling(p, min_periods=1).mean() for p in (2, 3, 5)) / 3.0
    df["Rel_AD_Ratio"] = (diff_adr + multi) / 2.0

    return df[BREADTH_COLUMNS]


def compute_movers(close_df: pd.DataFrame, date: pd.Timestamp) -> pd.DataFrame:
    """Per-asset change on ``date`` versus the prior available close."""
    close_df = _normalize_index(close_df)
    if date not in close_df.index:
        return pd.DataFrame(columns=["Symbol", "Name", "Price", "Change_%", "Status"])
    pos = close_df.index.get_loc(date)
    if pos == 0:
        return pd.DataFrame(columns=["Symbol", "Name", "Price", "Change_%", "Status"])
    ref = close_df.ffill(limit=2).iloc[pos - 1]
    price = close_df.iloc[pos]
    chg = (price / ref - 1) * 100
    movers = pd.DataFrame({
        "Symbol": [str(s).removesuffix(".NS") for s in close_df.columns],
        "Name": [ASSET_NAMES.get(s, "") for s in close_df.columns],
        "Price": price.to_numpy(),
        "Change_%": chg.to_numpy(),
    }).dropna(subset=["Price", "Change_%"])
    movers["Status"] = np.select(
        [movers["Change_%"] > 0, movers["Change_%"] < 0], ["Advance", "Decline"], default="Unchanged"
    )
    return movers.sort_values("Change_%", ascending=False).reset_index(drop=True)


def compute_timeseries(
    close_df: pd.DataFrame, start_ts: pd.Timestamp, end_ts: pd.Timestamp
) -> tuple[pd.DataFrame | None, pd.DataFrame]:
    """Breadth table restricted to [start_ts, end_ts] plus last-session movers."""
    full = compute_breadth(close_df)
    if full.empty:
        return None, pd.DataFrame()

    view = full[(full["Date"] >= start_ts) & (full["Date"] <= end_ts)].reset_index(drop=True)
    if view.empty:
        return None, pd.DataFrame()

    # A/D line accumulates net advances from the start of the viewing window.
    view["AD_Line"] = view["Net_Advances"].cumsum()
    movers = compute_movers(close_df, view["Date"].iloc[-1])
    return view, movers


def classify_adr(adr: float) -> tuple[str, str]:
    """Return ``(sentiment label, css class)`` for an A/D ratio."""
    if adr > 1.2:
        return "STRONG BULLISH", "success"
    if adr > 1.0:
        return "BULLISH", "success"
    if adr < 0.8:
        return "STRONG BEARISH", "danger"
    if adr < 1.0:
        return "BEARISH", "danger"
    return "NEUTRAL", "neutral"
