"""Universe definitions and constituent resolution (tickers, sectors, names, benchmark)."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import requests

INDIA = "India Indexes"
US = "US Indexes"
COMMODITIES = "Commodities"
CURRENCY = "Currency (vs USD)"
UNIVERSE_KINDS = [INDIA, US, COMMODITIES, CURRENCY]

INDIA_INDEX_LIST = [
    "NIFTY 50", "NIFTY NEXT 50", "NIFTY 100", "NIFTY 200", "NIFTY 500",
    "NIFTY MIDCAP 50", "NIFTY MIDCAP 100", "NIFTY SMLCAP 100", "NIFTY BANK",
    "NIFTY AUTO", "NIFTY FIN SERVICE", "NIFTY FMCG", "NIFTY IT",
    "NIFTY MEDIA", "NIFTY METAL", "NIFTY PHARMA",
]
US_INDEX_LIST = ["S&P 500", "DOW JONES", "NASDAQ 100"]

NSE_BASE_URL = "https://www.niftyindices.com/IndexConstituent/"
INDEX_URL_MAP = {
    "NIFTY 50": "ind_nifty50list.csv",
    "NIFTY NEXT 50": "ind_niftynext50list.csv",
    "NIFTY 100": "ind_nifty100list.csv",
    "NIFTY 200": "ind_nifty200list.csv",
    "NIFTY 500": "ind_nifty500list.csv",
    "NIFTY MIDCAP 50": "ind_niftymidcap50list.csv",
    "NIFTY MIDCAP 100": "ind_niftymidcap100list.csv",
    "NIFTY SMLCAP 100": "ind_niftysmallcap100list.csv",
    "NIFTY BANK": "ind_niftybanklist.csv",
    "NIFTY AUTO": "ind_niftyautolist.csv",
    "NIFTY FIN SERVICE": "ind_niftyfinancelist.csv",
    "NIFTY FMCG": "ind_niftyfmcglist.csv",
    "NIFTY IT": "ind_niftyitlist.csv",
    "NIFTY MEDIA": "ind_niftymedialist.csv",
    "NIFTY METAL": "ind_niftymetallist.csv",
    "NIFTY PHARMA": "ind_niftypharmalist.csv",
}
INDEX_URL_MAP = {k: NSE_BASE_URL + v for k, v in INDEX_URL_MAP.items()}

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
US_INDEX_SIZE_BOUNDS = {"S&P 500": (480, 520), "DOW JONES": (28, 32), "NASDAQ 100": (95, 110)}

# Yahoo Finance tickers for each index level (verified Nov 2026). Indexes not
# listed here (NIFTY MIDCAP 100, NIFTY SMLCAP 100, NIFTY MEDIA have no usable
# Yahoo history) use the equal-weight composite of their constituents, as does
# any benchmark that fails to download.
BENCHMARKS = {
    "NIFTY 50": "^NSEI", "NIFTY NEXT 50": "^NSMIDCP", "NIFTY 100": "^CNX100",
    "NIFTY 200": "^CNX200", "NIFTY 500": "^CRSLDX", "NIFTY MIDCAP 50": "^NSEMDCP50",
    "NIFTY BANK": "^NSEBANK", "NIFTY AUTO": "^CNXAUTO", "NIFTY FIN SERVICE": "NIFTY_FIN_SERVICE.NS",
    "NIFTY FMCG": "^CNXFMCG", "NIFTY IT": "^CNXIT",
    "NIFTY METAL": "^CNXMETAL", "NIFTY PHARMA": "^CNXPHARMA",
    "S&P 500": "^GSPC", "DOW JONES": "^DJI", "NASDAQ 100": "^NDX",
}

# Dow Jones Industrial Average components (synced with Wikipedia, Nov 2026).
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

# ticker -> (name, group)
COMMODITIES_META = {
    "GC=F": ("Gold", "Precious Metals"), "SI=F": ("Silver", "Precious Metals"),
    "PL=F": ("Platinum", "Precious Metals"), "PA=F": ("Palladium", "Precious Metals"),
    "HG=F": ("Copper", "Industrial Metals"),
    "CL=F": ("Crude Oil WTI", "Energy"), "BZ=F": ("Brent Crude", "Energy"),
    "NG=F": ("Natural Gas", "Energy"), "RB=F": ("Gasoline RBOB", "Energy"), "HO=F": ("Heating Oil", "Energy"),
    "ZC=F": ("Corn", "Grains & Oilseeds"), "ZW=F": ("Wheat", "Grains & Oilseeds"),
    "ZS=F": ("Soybeans", "Grains & Oilseeds"), "ZM=F": ("Soybean Meal", "Grains & Oilseeds"),
    "ZL=F": ("Soybean Oil", "Grains & Oilseeds"),
    "CT=F": ("Cotton", "Softs"), "KC=F": ("Coffee", "Softs"), "SB=F": ("Sugar", "Softs"),
    "CC=F": ("Cocoa", "Softs"), "OJ=F": ("Orange Juice", "Softs"), "LBS=F": ("Lumber", "Softs"),
    "LE=F": ("Live Cattle", "Livestock"), "HE=F": ("Lean Hogs", "Livestock"), "GF=F": ("Feeder Cattle", "Livestock"),
}

# Currency breadth is measured against the US dollar: every pair is oriented as
# the foreign currency priced in USD, so an advance always means that currency
# strengthened versus USD. USDxxx quotes are inverted after download. Crosses
# (EUR/GBP etc.) are excluded because their direction has no common reference.
# ticker -> (display name, group, invert)
CURRENCY_META = {
    "EURUSD=X": ("EUR", "G10", False), "GBPUSD=X": ("GBP", "G10", False),
    "AUDUSD=X": ("AUD", "G10", False), "NZDUSD=X": ("NZD", "G10", False),
    "USDJPY=X": ("JPY", "G10", True), "USDCHF=X": ("CHF", "G10", True),
    "USDCAD=X": ("CAD", "G10", True),
    "USDINR=X": ("INR", "Asia", True), "USDSGD=X": ("SGD", "Asia", True),
    "USDHKD=X": ("HKD", "Asia", True), "USDCNH=X": ("CNH", "Asia", True),
    "USDKRW=X": ("KRW", "Asia", True),
    "USDZAR=X": ("ZAR", "EM ex-Asia", True), "USDMXN=X": ("MXN", "EM ex-Asia", True),
    "USDTRY=X": ("TRY", "EM ex-Asia", True), "USDBRL=X": ("BRL", "EM ex-Asia", True),
}

HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
HTTP_TIMEOUT = 15

SYMBOL_COLS = ("Symbol", "Ticker", "Ticker symbol")
SECTOR_COLS = ("Industry", "Sector", "GICS Sector", "ICB Industry")
NAME_COLS = ("Company Name", "Company name", "Company", "Security")


class ConstituentFetchError(RuntimeError):
    """Raised when a constituent list cannot be obtained from any live source."""


@dataclass
class Universe:
    kind: str
    name: str
    tickers: list[str]
    sectors: dict[str, str] = field(default_factory=dict)
    names: dict[str, str] = field(default_factory=dict)
    benchmark: str | None = None
    invert: list[str] = field(default_factory=list)
    source: str = ""
    is_fallback: bool = False

    @property
    def unit(self) -> str:
        return "Stocks" if self.kind in (INDIA, US) else "Assets"


def index_options(kind: str) -> list[str]:
    if kind == INDIA:
        return INDIA_INDEX_LIST
    if kind == US:
        return US_INDEX_LIST
    return [kind]


# ══════════════════════════════════════════════════════════════════════════════
# TABLE PARSING
# ══════════════════════════════════════════════════════════════════════════════

def _clean_header(c) -> str:
    return re.sub(r"\[.*?\]", "", str(c)).strip()


def _clean_symbol(v) -> str | None:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    s = str(v).strip()
    return s if s and s.lower() != "nan" and len(s) <= 20 else None


def _first_col(df: pd.DataFrame, candidates) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def normalize_constituent_table(tbl: pd.DataFrame) -> pd.DataFrame | None:
    """Map a scraped table to columns ``symbol, sector, name``; None if no symbol column."""
    if len(tbl) and all(isinstance(c, int) for c in tbl.columns):
        # Rendered without <th>: promote first row to headers.
        tbl = tbl.iloc[1:].set_axis(tbl.iloc[0].astype(str), axis=1)
    tbl = tbl.rename(columns=_clean_header)
    tbl = tbl.loc[:, ~tbl.columns.duplicated()]
    sym = _first_col(tbl, SYMBOL_COLS)
    if sym is None:
        return None
    sec = _first_col(tbl, SECTOR_COLS)
    nam = _first_col(tbl, NAME_COLS)
    out = pd.DataFrame({
        "symbol": tbl[sym].map(_clean_symbol),
        "sector": tbl[sec].astype(str).str.strip() if sec else "Unclassified",
        "name": tbl[nam].astype(str).str.strip() if nam else "",
    })
    out = out.dropna(subset=["symbol"]).drop_duplicates("symbol")
    out = out[~out["symbol"].str.upper().str.startswith("DUMMY")]  # NSE placeholder rows
    return out.reset_index(drop=True)


def _read_html_tables(url: str) -> list[pd.DataFrame]:
    response = requests.get(url, headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT)
    response.raise_for_status()
    return pd.read_html(io.StringIO(response.text))


def _wiki_constituents(url: str, lo: int, hi: int) -> pd.DataFrame | None:
    for tbl in _read_html_tables(url):
        norm = normalize_constituent_table(tbl)
        if norm is not None and lo <= len(norm) <= hi:
            return norm
    return None


def _to_universe(kind, name, table: pd.DataFrame, suffix: str, source: str, transform=None) -> Universe:
    syms = [transform(s) if transform else s for s in table["symbol"]]
    tickers = [s + suffix for s in syms]
    return Universe(
        kind=kind, name=name, tickers=tickers,
        sectors=dict(zip(tickers, table["sector"], strict=True)),
        names=dict(zip(tickers, table["name"], strict=True)),
        benchmark=BENCHMARKS.get(name), source=source,
    )


# ══════════════════════════════════════════════════════════════════════════════
# RESOLVERS
# ══════════════════════════════════════════════════════════════════════════════

def fetch_nse_constituents(index: str) -> pd.DataFrame:
    response = requests.get(INDEX_URL_MAP[index], headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT)
    response.raise_for_status()
    norm = normalize_constituent_table(pd.read_csv(io.StringIO(response.text)))
    if norm is None or norm.empty:
        raise ConstituentFetchError(f"NSE CSV for {index} has no usable 'Symbol' column")
    return norm


def fetch_india_wiki_constituents(index: str) -> pd.DataFrame | None:
    """Wikipedia fallback. Only indexes with a faithful Wikipedia table are supported."""
    if index == "NIFTY 100":
        n50 = _wiki_constituents(INDIA_INDEX_WIKI_MAP["NIFTY 50"], 45, 55)
        nn50 = _wiki_constituents(INDIA_INDEX_WIKI_MAP["NIFTY NEXT 50"], 45, 55)
        if n50 is None or nn50 is None:
            return None
        return pd.concat([n50, nn50]).drop_duplicates("symbol").reset_index(drop=True)
    url = INDIA_INDEX_WIKI_MAP.get(index)
    if not url:
        return None
    lo, hi = {"NIFTY 50": (45, 55), "NIFTY NEXT 50": (45, 55), "NIFTY 500": (450, 520)}[index]
    return _wiki_constituents(url, lo, hi)


def get_india_universe(index: str) -> Universe:
    if index not in INDEX_URL_MAP:
        raise ValueError(f"Unknown India index: {index}")
    try:
        table = fetch_nse_constituents(index)
        return _to_universe(INDIA, index, table, ".NS", f"NSE index file ({len(table)} constituents)")
    except Exception:
        pass
    try:
        table = fetch_india_wiki_constituents(index)
        if table is not None:
            return _to_universe(INDIA, index, table, ".NS",
                                f"Wikipedia, NSE unreachable ({len(table)} constituents)")
    except Exception:
        pass
    return Universe(
        kind=INDIA, name=index, tickers=list(FALLBACK_TICKERS), benchmark=BENCHMARKS.get(index),
        source=f"Built-in fallback list ({len(FALLBACK_TICKERS)} large caps, NOT the actual index)",
        is_fallback=True,
    )


def get_us_universe(index: str) -> Universe:
    if index not in US_INDEX_WIKI_MAP:
        raise ValueError(f"Unknown US index: {index}")
    lo, hi = US_INDEX_SIZE_BOUNDS[index]
    for url in US_INDEX_WIKI_MAP[index]:
        try:
            table = _wiki_constituents(url, lo, hi)
        except Exception:
            continue
        if table is not None:
            # Yahoo uses '-' for share classes (BRK.B -> BRK-B)
            return _to_universe(US, index, table, "", f"Wikipedia ({len(table)} constituents)",
                                transform=lambda s: s.replace(".", "-"))
    if index == "DOW JONES":
        return Universe(kind=US, name=index, tickers=list(DOW_JONES_TICKERS), benchmark=BENCHMARKS[index],
                        source=f"Built-in list ({len(DOW_JONES_TICKERS)} tickers), Wikipedia unavailable",
                        is_fallback=True)
    raise ConstituentFetchError(f"Could not fetch {index} constituents from Wikipedia")


def get_commodity_universe() -> Universe:
    tickers = list(COMMODITIES_META)
    return Universe(
        kind=COMMODITIES, name=COMMODITIES, tickers=tickers,
        sectors={t: g for t, (_, g) in COMMODITIES_META.items()},
        names={t: n for t, (n, _) in COMMODITIES_META.items()},
        source=f"Built-in futures list ({len(tickers)} contracts)",
    )


def get_currency_universe() -> Universe:
    tickers = list(CURRENCY_META)
    return Universe(
        kind=CURRENCY, name=CURRENCY, tickers=tickers,
        sectors={t: g for t, (_, g, _) in CURRENCY_META.items()},
        names={t: n for t, (n, _, _) in CURRENCY_META.items()},
        invert=[t for t, (_, _, inv) in CURRENCY_META.items() if inv],
        source=f"Built-in list ({len(tickers)} currencies, all oriented vs USD)",
    )


def resolve_universe(kind: str, index: str | None = None) -> Universe:
    if kind == INDIA:
        return get_india_universe(index)
    if kind == US:
        return get_us_universe(index)
    if kind == COMMODITIES:
        return get_commodity_universe()
    if kind == CURRENCY:
        return get_currency_universe()
    raise ValueError(f"Unknown universe kind: {kind}")
