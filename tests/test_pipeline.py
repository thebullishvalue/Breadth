import datetime

import numpy as np
import pandas as pd

from breadth import build_analysis, history_start
from breadth import data as bd
from synthetic import make_market


def test_build_analysis_end_to_end():
    uni, data = make_market()
    a = build_analysis(uni, data, datetime.date(2026, 6, 1), datetime.date(2026, 11, 20))
    assert a is not None and a.uses_index and a.index_name == "TEST"
    assert a.view.index[0] >= pd.Timestamp("2026-06-01") and a.asof == pd.Timestamp("2026-11-20")
    assert a.zone in {"OVERSOLD", "NEUTRAL", "OVERBOUGHT"}
    assert a.verdict.label in {"FAVOURABLE", "NORMAL", "UNFAVOURABLE", "TOO FEW CASES"}
    assert len(a.reading) == 3 and len(a.watch) == 2
    assert set(a.zone_evidence.index) == {"OVERSOLD", "NEUTRAL", "OVERBOUGHT", "ALL"}
    assert set(a.crossing_evidence.index) == {"OS_IN", "OS_OUT", "OB_IN", "OB_OUT"}
    assert len(a.stocks) == 60 and a.sectors["Stocks"].sum() == 60


def test_equal_weight_fallback_names_the_basket():
    uni, data = make_market(n_days=500)
    data.benchmark = None
    a = build_analysis(uni, data, datetime.date(2026, 9, 1), datetime.date(2026, 11, 20))
    assert not a.uses_index and a.index_name == "the equal-weighted TEST basket"
    assert "the equal-weighted TEST basket" in a.verdict.sentence


def test_as_of_date_ignores_later_data():
    uni, data = make_market()
    a = build_analysis(uni, data, datetime.date(2026, 3, 1), datetime.date(2026, 6, 30))
    assert a.asof <= pd.Timestamp("2026-06-30") and a.panel.index[-1] == a.asof


def test_window_outside_data_returns_none():
    uni, data = make_market(n_days=400)
    assert build_analysis(uni, data, datetime.date(2030, 1, 1), datetime.date(2030, 2, 1)) is None


def test_history_start():
    assert history_start(datetime.date(2026, 6, 1), datetime.date(2026, 11, 20), 3) == datetime.date(2023, 11, 20)
    assert history_start(datetime.date(2020, 1, 1), datetime.date(2026, 11, 20), 1) == datetime.date(2020, 1, 1)
    assert history_start(datetime.date(2028, 2, 29), datetime.date(2028, 2, 29), 1) == datetime.date(2027, 2, 28)


def test_extract_field_multiindex_and_single():
    idx = pd.bdate_range("2026-01-01", periods=3)
    cols = pd.MultiIndex.from_product([["A", "B"], ["Close", "Volume"]])
    raw = pd.DataFrame(np.arange(12.0).reshape(3, 4), index=idx, columns=cols)
    assert list(bd.extract_field(raw, "Close", ["A", "B"]).columns) == ["A", "B"]
    single = pd.DataFrame({"Close": [1.0, 2, 3]}, index=idx)
    assert list(bd.extract_field(single, "Close", ["X"]).columns) == ["X"]


def test_download_splits_benchmark_inverts_and_warms_up(monkeypatch):
    calls = []

    def fake(tickers, **kw):
        calls.append((tickers, kw))
        idx = pd.bdate_range(kw["start"], kw["end"] - datetime.timedelta(days=1))
        cols = pd.MultiIndex.from_product([[t for t in tickers if t != "DEAD"], ["Close"]])
        return pd.DataFrame(2.0, index=idx, columns=cols)

    monkeypatch.setattr(bd, "_yf_download", fake)
    start, end = datetime.date(2026, 3, 2), datetime.date(2026, 3, 31)
    md = bd.download_market_data(["A", "USDX", "DEAD"], start, end, benchmark="^B", invert=["USDX"],
                                 today=datetime.date(2026, 6, 1))
    tickers, kw = calls[0]
    assert tickers == ["A", "USDX", "DEAD", "^B"] and len(calls) == 1
    assert kw["start"] == start - datetime.timedelta(days=bd.WARMUP_CALENDAR_DAYS)
    assert list(md.close.columns) == ["A", "USDX"] and md.missing == ["DEAD"]
    assert (md.close["USDX"] == 0.5).all() and md.benchmark_ticker == "^B"
