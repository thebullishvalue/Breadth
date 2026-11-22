"""End-to-end analysis: universe + market data -> panel, signals, studies, cross-section."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

import pandas as pd

from . import indicators as ind
from . import signals as sig
from . import study
from .data import MarketData, download_market_data
from .universe import Universe, resolve_universe


@dataclass
class Analysis:
    universe: Universe
    data: MarketData
    panel: pd.DataFrame             # full history
    view: pd.DataFrame              # selected window, cumulative series re-anchored
    price: pd.Series                # benchmark (or EW composite) on panel sessions
    price_source: str
    events: dict                    # key -> debounced bool Series (full history)
    note: list[str]
    snapshot: pd.DataFrame          # per-asset state on the last session
    sectors: pd.DataFrame
    sector_history: pd.DataFrame    # % above 50-DMA by sector (view window)
    event_table: pd.DataFrame
    regime_table: pd.DataFrame
    study_start: pd.Timestamp | None

    @property
    def last(self) -> pd.Series:
        return self.view.iloc[-1]

    @property
    def asof(self) -> pd.Timestamp:
        return self.view.index[-1]


def history_start(start_date: datetime.date, end_date: datetime.date, study_years: int) -> datetime.date:
    """Earliest date the analysis needs (excluding indicator warm-up)."""
    try:
        back = end_date.replace(year=end_date.year - study_years)
    except ValueError:  # 29 Feb
        back = end_date.replace(year=end_date.year - study_years, day=28)
    return min(start_date, back)


def build_analysis(universe: Universe, data: MarketData, start_date, end_date) -> Analysis | None:
    panel = ind.compute_panel(data.close, data.volume if data.has_volume else None)
    if panel.empty:
        return None
    # Drop indicator warm-up: start the usable history once the slowest series exists.
    ready = panel["Health_Score"].first_valid_index()
    usable = panel.loc[ready:] if ready is not None else panel
    view = ind.window(usable, start_date, end_date)
    if view.empty:
        return None

    price, src = sig.align_benchmark(usable, data.benchmark)
    hist = usable.loc[: view.index[-1]]
    price_hist = price.loc[: view.index[-1]]
    events = sig.detect_events(hist, price_hist)
    note = sig.desk_note(hist, events, unit=universe.unit)

    snapshot = ind.asset_snapshot(data.close, view.index[-1], universe.names, universe.sectors)
    sector_hist = ind.sector_participation_history(data.close, universe.sectors).loc[view.index[0]:view.index[-1]]

    regime_table = study.regime_study(hist["Regime"], price_hist)
    evidence = study.regime_evidence(regime_table, hist["Regime"].iloc[-1], price_hist)
    if evidence:
        note.insert(1, evidence)

    return Analysis(
        universe=universe, data=data, panel=hist, view=view,
        price=price_hist, price_source=src, events=events, note=note,
        snapshot=snapshot, sectors=ind.sector_table(snapshot), sector_history=sector_hist,
        event_table=study.event_study(events, price_hist), regime_table=regime_table,
        study_start=hist.index[0] if len(hist) else None,
    )


def run(kind: str, index: str | None, start_date, end_date, study_years: int = 3) -> Analysis | None:
    """Fetch everything and analyse. Convenience entry point for scripts/CLI."""
    universe = resolve_universe(kind, index)
    data = download_market_data(universe.tickers, history_start(start_date, end_date, study_years),
                                end_date, benchmark=universe.benchmark, invert=universe.invert)
    return build_analysis(universe, data, start_date, end_date)
