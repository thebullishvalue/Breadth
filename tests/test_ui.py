import datetime

import pandas as pd
import pytest

from breadth import build_analysis
from synthetic import make_market
from ui import charts
from ui.tabs import tab_engine, tab_record, tab_sectors
from ui.verdict import build_read, position


@pytest.fixture(scope="module")
def analysis():
    uni, data = make_market()
    return build_analysis(uni, data, datetime.date(2023, 11, 20), datetime.date(2026, 11, 20))


def test_position():
    assert position(pd.Series([1, 2, 3, 4])) == 1.0
    assert position(pd.Series([1, 3, 4, 2])) == pytest.approx(1 / 3)
    assert position(pd.Series([4, 3, 2, 1])) == 0.0
    assert position(pd.Series([1.0])) == 0.5


def test_read_card_content(analysis):
    r = build_read(analysis)
    assert r["signal"] == analysis.zone
    assert r["trust"]["tier"] in {"favourable", "normal", "unfavourable", "norecord"}
    assert r["signal_class"] in {"buy", "sell", "hold"}
    assert [e["title"] for e in r["evidence"]] == ["Relative Breadth", "Direction", "Momentum",
                                                   "Latest session", "Breadth trend"]
    assert all(0 <= e["value"] <= 1 and e["tone"] in {"supports", "against", "neutral"} for e in r["evidence"])
    assert r["limit"] == analysis.verdict.sentence
    assert "not added into a score" in r["foot"]


def test_record_class_follows_verdict(analysis):
    r = build_read(analysis)
    expected = {"FAVOURABLE": "buy", "UNFAVOURABLE": "sell"}.get(analysis.verdict.label, "hold")
    assert r["signal_class"] == expected


def test_engine_stack_and_heatmap(analysis):
    from breadth.study import events
    view = analysis.panel.tail(130)
    fig = charts.engine_stack(view, analysis.price, "TEST", events(analysis.panel))
    names = {t.name for t in fig.data}
    assert {"Relative Breadth", "Custom Breadth", "TEST", "A/D line"} <= names
    assert any(s.y0 == 0.40 or s.y1 == 0.40 for s in fig.layout.shapes)   # oversold band drawn
    frame = tab_sectors.heatmap_frame(analysis, view.index[0], view.index[-1])
    assert list(frame.columns) and charts.sector_heatmap(frame).data


def test_page_tables(analysis):
    view = analysis.panel.tail(130)
    stats = tab_engine.window_stats(view)
    assert list(stats["Series"]) == ["Relative Breadth", "Custom Breadth", "Relative A/D Ratio", "A/D Ratio"]
    assert len(tab_record.zone_cards(analysis)) == 4
    assert list(tab_record.zone_table(analysis)["Zone"]) == ["Oversold", "Neutral", "Overbought", "Any session"]
    assert len(tab_record.crossing_table(analysis)) == 4
    log = tab_engine.crossing_log(analysis, view)
    assert log.empty or log["Date"].is_monotonic_decreasing


def test_tape_symbols_are_unique_and_short():
    import app
    names = ["Consumer Discretionary", "Consumer Staples", "Information Technology", "Some New Long Sector Name"]
    syms = [app.tape_symbol(n) for n in names]
    assert len(set(syms)) == len(syms) and all(len(s) <= 12 for s in syms)


def test_window_view(analysis):
    import app
    v = app.window_view(analysis, "3M")
    assert v.index[-1] == analysis.asof and (analysis.asof - v.index[0]).days <= 92
    assert app.window_view(analysis, "MAX").index[0] == analysis.panel.index[0]
    assert app.window_view(analysis, "YTD").index[0].year == analysis.asof.year
