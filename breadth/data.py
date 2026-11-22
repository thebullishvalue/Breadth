"""Price download from Yahoo Finance and matrix normalisation."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

import pandas as pd
import yfinance as yf

# Calendar days loaded before the requested history so every oscillator (and the
# A/D line's 50-session average) is fully formed on the first day used.
WARMUP_CALENDAR_DAYS = 150


@dataclass
class MarketData:
    close: pd.DataFrame                       # date x ticker, adjusted
    benchmark: pd.Series | None = None        # index level
    benchmark_ticker: str | None = None
    missing: list[str] = field(default_factory=list)  # requested tickers with no data


def normalize_index(df):
    """Date-only, tz-naive, sorted, de-duplicated index."""
    idx = pd.to_datetime(df.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    df = df.copy()
    df.index = idx.normalize()
    df = df[~df.index.duplicated(keep="last")]
    return df.sort_index()


def extract_field(raw: pd.DataFrame, fld: str, tickers: list[str]) -> pd.DataFrame | None:
    """Pull a (date x ticker) matrix for one OHLCV field out of a yfinance frame."""
    if raw is None or raw.empty:
        return None
    if isinstance(raw.columns, pd.MultiIndex):
        for level in range(raw.columns.nlevels):
            if fld in raw.columns.get_level_values(level):
                out = raw.xs(fld, level=level, axis=1)
                break
        else:
            return None
    elif fld in raw.columns:
        out = raw[[fld]]
        out.columns = tickers[:1]
    else:
        return None
    out = out.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")
    return out if not out.empty else None


def _yf_download(tickers, **kw) -> pd.DataFrame:
    return yf.download(tickers, progress=False, auto_adjust=True, group_by="ticker", threads=True, **kw)


def download_market_data(
    tickers: list[str],
    start_date: datetime.date,
    end_date: datetime.date,
    benchmark: str | None = None,
    invert: list[str] | None = None,
    today: datetime.date | None = None,
) -> MarketData:
    """Download closes (plus benchmark) from ``start_date - warm-up`` to ``end_date``.

    Raises ``RuntimeError`` when no usable constituent data comes back.
    """
    today = today or datetime.date.today()
    tickers = list(dict.fromkeys(tickers))
    request = tickers + ([benchmark] if benchmark and benchmark not in tickers else [])
    raw = _yf_download(
        request,
        start=start_date - datetime.timedelta(days=WARMUP_CALENDAR_DAYS),
        end=end_date + datetime.timedelta(days=1),  # yfinance `end` is exclusive
    )
    close = extract_field(raw, "Close", request)
    if close is None:
        raise RuntimeError("No price data returned from Yahoo Finance")
    close = normalize_index(close)

    # Best-effort intraday append: the daily endpoint can lag the live session.
    if end_date >= today and pd.Timestamp(today) not in close.index:
        try:
            lc = extract_field(_yf_download(close.columns.tolist(), period="1d"), "Close", close.columns.tolist())
            if lc is not None:
                lc = normalize_index(lc)
                new = lc.loc[~lc.index.isin(close.index)]
                if not new.empty:
                    close = pd.concat([close, new]).sort_index()
        except Exception:
            pass

    bench = None
    if benchmark and benchmark in close.columns:
        bench = close[benchmark].dropna()
        if benchmark not in tickers:
            close = close.drop(columns=benchmark)
        bench = bench if len(bench) else None

    for t in invert or []:
        if t in close.columns:
            close[t] = 1.0 / close[t]

    close = close.dropna(axis=1, how="all")
    if close.empty:
        raise RuntimeError("No constituent price data returned from Yahoo Finance")
    return MarketData(close=close, benchmark=bench, benchmark_ticker=benchmark if bench is not None else None,
                      missing=[t for t in tickers if t not in close.columns])
