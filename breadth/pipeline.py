"""End-to-end: universe + prices -> oscillators, zone reading, evidence, sectors."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

import pandas as pd

from . import indicators as ind
from . import narrative, study
from .data import MarketData, download_market_data
from .universe import COMMODITIES, CURRENCY, Universe, resolve_universe


@dataclass
class Analysis:
    universe: Universe
    data: MarketData
    panel: pd.DataFrame          # full usable history (the evidence period)
    view: pd.DataFrame           # display window
    price: pd.Series             # index (or equal-weight basket) on panel sessions
    index_name: str              # how the price series is named in sentences
    uses_index: bool             # False when the equal-weight basket stands in for the index
    zone_evidence: pd.DataFrame
    crossing_evidence: pd.DataFrame
    verdict: study.Verdict
    recent: list                 # [(crossing key, sessions ago)]
    reading: list[str]
    watch: list[str]
    oversold_episodes: pd.DataFrame
    sector_osc: dict
    sectors: pd.DataFrame
    stocks: pd.DataFrame

    @property
    def last(self) -> pd.Series:
        return self.view.iloc[-1]

    @property
    def asof(self) -> pd.Timestamp:
        return self.view.index[-1]

    @property
    def zone(self) -> str:
        return self.last["Zone"]

    @property
    def years(self) -> float:
        return len(self.panel) / 252


def history_start(start_date: datetime.date, end_date: datetime.date, years: int) -> datetime.date:
    """Earliest date the analysis needs (before indicator warm-up)."""
    try:
        back = end_date.replace(year=end_date.year - years)
    except ValueError:  # 29 Feb
        back = end_date.replace(year=end_date.year - years, day=28)
    return min(start_date, back)


def _reference(universe: Universe, data: MarketData, panel: pd.DataFrame) -> tuple[pd.Series, str, bool]:
    b = data.benchmark
    if b is not None and len(b.dropna()):
        s = b.reindex(panel.index.union(b.index)).ffill().reindex(panel.index)
        if s.notna().mean() > 0.9:
            return s, universe.name, True
    if universe.kind == COMMODITIES:
        name = "the equal-weighted commodity basket"
    elif universe.kind == CURRENCY:
        name = "the equal-weighted currency basket (vs USD)"
    else:
        name = f"the equal-weighted {universe.name} basket"
    return panel["EW_Index"], name, False


def build_analysis(universe: Universe, data: MarketData, start_date, end_date) -> Analysis | None:
    panel = ind.compute_panel(data.close)
    if panel.empty:
        return None
    ready = panel["AD_Line_MA50"].first_valid_index()
    if ready is None:
        return None
    hist = panel.loc[ready:pd.Timestamp(end_date)]
    view = ind.window(hist, start_date, end_date)
    if view.empty:
        return None

    price, name, uses_index = _reference(universe, data, hist)
    zev = study.zone_evidence(hist, price)
    cev = study.crossing_evidence(hist, price)
    recent = study.recent_crossings(hist)
    sector_osc = ind.sector_oscillators(data.close, universe.sectors)

    return Analysis(
        universe=universe, data=data, panel=hist, view=view, price=price, index_name=name, uses_index=uses_index,
        zone_evidence=zev, crossing_evidence=cev,
        verdict=study.verdict(zev, view["Zone"].iloc[-1], name, hist.index[0]),
        recent=recent, reading=narrative.reading(view, hist, zev, recent, universe.unit),
        watch=narrative.watch(view, cev, zev.loc["ALL"], name),
        oversold_episodes=study.episodes(hist, "OVERSOLD", price),
        sector_osc=sector_osc, sectors=ind.sector_snapshot(sector_osc, view.index[-1]),
        stocks=ind.stock_snapshot(data.close, view.index[-1], universe.names, universe.sectors),
    )


def run(kind: str, index: str | None, start_date, end_date, years: int = 5) -> Analysis | None:
    """Fetch everything and analyse. Convenience entry point for scripts/CLI."""
    universe = resolve_universe(kind, index)
    data = download_market_data(universe.tickers, history_start(start_date, end_date, years), end_date,
                                benchmark=universe.benchmark, invert=universe.invert)
    return build_analysis(universe, data, start_date, end_date)
