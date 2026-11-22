import datetime

import numpy as np
import pandas as pd

from breadth import build_analysis, charts, history_start
from breadth import data as bd
from synthetic import make_market


def test_build_analysis_end_to_end():
    uni, data = make_market()
    a = build_analysis(uni, data, datetime.date(2026, 6, 1), datetime.date(2026, 11, 20))
    assert a is not None and a.price_source == "benchmark"
    assert a.view.index[0] >= pd.Timestamp("2026-06-01") and a.asof == pd.Timestamp("2026-11-20")
    assert a.view["Health_Score"].notna().all() and a.view["Pct_Above_200"].notna().all()
    assert len(a.note) >= 4 and a.note[-1]
    assert set(a.events) == {"thrust", "rb_oversold", "rb_overbought", "washout", "bear_div", "bull_div"}
    assert a.event_table["Signal"].iloc[-1] == "All sessions (baseline)"
    assert len(a.snapshot) == 60 and a.sectors["Members"].sum() == 60
    assert a.sector_history.index[0] >= a.view.index[0]


def test_build_analysis_falls_back_to_ew_composite():
    uni, data = make_market(n_days=500)
    data.benchmark = None
    a = build_analysis(uni, data, datetime.date(2026, 9, 1), datetime.date(2026, 11, 20))
    assert a.price_source == "equal-weight composite"


def test_window_outside_data_returns_none():
    uni, data = make_market(n_days=400)
    assert build_analysis(uni, data, datetime.date(2030, 1, 1), datetime.date(2030, 2, 1)) is None


def test_history_start():
    assert history_start(datetime.date(2026, 6, 1), datetime.date(2026, 11, 20), 3) == datetime.date(2023, 11, 20)
    assert history_start(datetime.date(2020, 1, 1), datetime.date(2026, 11, 20), 1) == datetime.date(2020, 1, 1)


def test_all_charts_build():
    uni, data = make_market()
    a = build_analysis(uni, data, datetime.date(2026, 6, 1), datetime.date(2026, 11, 20))
    figs = [
        charts.plot_overview(a.view, a.price, a.events, "BENCH"), charts.plot_participation(a.view),
        charts.plot_highs_lows(a.view), charts.plot_mcclellan(a.view), charts.plot_volume_breadth(a.view),
        charts.plot_sector_heatmap(a.sector_history), charts.plot_regime_returns(a.regime_table),
        charts.plot_relative_breadth(a.view), charts.plot_custom_breadth(a.view),
        charts.plot_rel_ad_ratio(a.view), charts.plot_ad_ratio(a.view), charts.plot_ad_line(a.view),
    ]
    assert all(f.data for f in figs)
    assert len(figs[0].layout.shapes) == len(charts.REGIME_BANDS)   # regime bands actually drawn


def test_extract_field_multiindex_and_single():
    idx = pd.bdate_range("2026-01-01", periods=3)
    cols = pd.MultiIndex.from_product([["A", "B"], ["Close", "Volume"]])
    raw = pd.DataFrame(np.arange(12.0).reshape(3, 4), index=idx, columns=cols)
    assert list(bd.extract_field(raw, "Close", ["A", "B"]).columns) == ["A", "B"]
    assert list(bd.extract_field(raw, "Volume", ["A", "B"]).columns) == ["A", "B"]
    single = pd.DataFrame({"Close": [1.0, 2, 3]}, index=idx)
    assert list(bd.extract_field(single, "Close", ["X"]).columns) == ["X"]


def test_download_splits_benchmark_inverts_and_warms_up(monkeypatch):
    calls = []

    def fake(tickers, **kw):
        calls.append((tickers, kw))
        idx = pd.bdate_range(kw["start"], kw["end"] - datetime.timedelta(days=1))
        cols = pd.MultiIndex.from_product([[t for t in tickers if t != "DEAD"], ["Close", "Volume"]])
        return pd.DataFrame(2.0, index=idx, columns=cols)

    monkeypatch.setattr(bd, "_yf_download", fake)
    start, end = datetime.date(2026, 3, 2), datetime.date(2026, 3, 31)
    md = bd.download_market_data(["A", "USDX", "DEAD"], start, end, benchmark="^B", invert=["USDX"],
                                 today=datetime.date(2026, 6, 1))
    tickers, kw = calls[0]
    assert tickers == ["A", "USDX", "DEAD", "^B"] and len(calls) == 1
    assert kw["start"] == start - datetime.timedelta(days=bd.WARMUP_CALENDAR_DAYS)
    assert list(md.close.columns) == ["A", "USDX"] and md.missing == ["DEAD"]
    assert (md.close["USDX"] == 0.5).all() and (md.close["A"] == 2.0).all()
    assert md.benchmark_ticker == "^B" and md.has_volume
