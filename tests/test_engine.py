import datetime

import numpy as np
import pandas as pd
import pytest

import charts
import engine


def make_prices(n_days=120, n_assets=30, seed=0, start="2026-01-01"):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start, periods=n_days)
    rets = rng.normal(0, 0.01, (n_days, n_assets))
    return pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)), index=idx,
                        columns=[f"S{i}" for i in range(n_assets)])


def test_counts_match_manual():
    px = make_prices(5, 12)
    out = engine.compute_breadth(px)
    pct = px.pct_change().iloc[1:]
    assert list(out["Advances"]) == list((pct > 0).sum(axis=1))
    assert list(out["Declines"]) == list((pct < 0).sum(axis=1))
    assert (out["Total"] == 12).all()


def test_missing_prints_are_not_counted_as_unchanged():
    px = make_prices(20, 30)
    px.iloc[10, 5:] = np.nan  # only 5 of 30 assets print that day
    out = engine.compute_breadth(px).set_index("Date")
    # thin day is dropped (below 50% coverage), and no stale-price "unchanged" rows anywhere
    assert px.index[10] not in out.index
    assert (out["Unchanged"] == 0).all()
    # the day after the gap still compares against the last real close
    assert out.loc[px.index[11], "Total"] == 30


def test_ema_alignment_survives_dropped_rows():
    px = make_prices(60, 30)
    px.iloc[3, 3:] = np.nan  # forces a dropped breadth row early in the history
    out = engine.compute_breadth(px)
    x = out["Advances"] / (out["Advances"] + out["Declines"])
    seed_pos = 9
    assert out["Custom_Breadth"].iloc[:seed_pos].isna().all()
    assert out["Custom_Breadth"].iloc[seed_pos] == pytest.approx(x.iloc[:10].mean())
    expected = out["Custom_Breadth"].iloc[seed_pos]
    for i in range(seed_pos + 1, len(out)):
        expected += engine.EMA_ALPHA * (x.iloc[i] - expected)
        assert out["Custom_Breadth"].iloc[i] == pytest.approx(expected)


def test_relative_breadth_formula():
    out = engine.compute_breadth(make_prices(80, 30))
    cb = out["Custom_Breadth"]
    i = len(out) - 1
    z = np.mean([cb.iloc[i - p + 1:i + 1].mean() for p in engine.FIB_PERIODS])
    assert out["Relative_Breadth"].iloc[i] == pytest.approx((z + cb.iloc[i]) / 2)


def test_zero_declines_uses_a_over_a_plus_d():
    idx = pd.bdate_range("2026-01-01", periods=15)
    px = pd.DataFrame({f"S{i}": np.linspace(100, 120, 15) for i in range(12)}, index=idx)
    out = engine.compute_breadth(px)
    assert (out["Declines"] == 0).all()
    assert out["AD_Ratio"].iloc[0] == 12
    # every day is 100% advancers, so the EMA must sit at exactly 1.0
    assert out["Custom_Breadth"].dropna().eq(1.0).all()


def test_window_view_and_ad_line_start():
    px = make_prices(120, 30)
    start, end = px.index[90], px.index[-1]
    view, movers = engine.compute_timeseries(px, start, end)
    assert view["Date"].iloc[0] == start and view["Date"].iloc[-1] == end
    assert view["AD_Line"].iloc[0] == view["Net_Advances"].iloc[0]
    assert view["Custom_Breadth"].notna().all()
    # indicator values inside the window do not depend on the warm-up length
    full = engine.compute_breadth(px).set_index("Date")
    assert np.allclose(view.set_index("Date")["Relative_Breadth"], full.loc[start:end, "Relative_Breadth"])
    assert len(movers) == 30
    assert movers["Change_%"].is_monotonic_decreasing


def test_empty_window_returns_none():
    px = make_prices(30, 30)
    view, movers = engine.compute_timeseries(px, pd.Timestamp("2030-01-01"), pd.Timestamp("2030-02-01"))
    assert view is None and movers.empty


def test_tz_aware_index_and_duplicates():
    px = make_prices(30, 12)
    px.index = px.index.tz_localize("Asia/Kolkata") + pd.Timedelta(hours=9, minutes=15)
    px = pd.concat([px, px.iloc[[-1]]])
    out = engine.compute_breadth(px)
    assert out["Date"].is_unique and out["Date"].dt.tz is None


@pytest.mark.parametrize("adr,label", [(1.5, "STRONG BULLISH"), (1.1, "BULLISH"), (1.0, "NEUTRAL"),
                                       (0.9, "BEARISH"), (0.5, "STRONG BEARISH")])
def test_classify_adr(adr, label):
    assert engine.classify_adr(adr)[0] == label


def test_extract_close_multiindex_and_single():
    idx = pd.bdate_range("2026-01-01", periods=3)
    cols = pd.MultiIndex.from_product([["A", "B"], ["Open", "Close"]])
    raw = pd.DataFrame(np.arange(12.0).reshape(3, 4), index=idx, columns=cols)
    assert list(engine.extract_close(raw, ["A", "B"]).columns) == ["A", "B"]
    single = pd.DataFrame({"Open": [1.0, 2, 3], "Close": [1.0, 2, 3]}, index=idx)
    assert list(engine.extract_close(single, ["X"]).columns) == ["X"]


def test_download_uses_warmup(monkeypatch):
    calls = []

    def fake_download(tickers, **kw):
        calls.append(kw)
        idx = pd.bdate_range(kw["start"], kw["end"] - datetime.timedelta(days=1))
        cols = pd.MultiIndex.from_product([tickers, ["Close"]])
        return pd.DataFrame(1.0, index=idx, columns=cols)

    monkeypatch.setattr(engine.yf, "download", fake_download)
    start, end = datetime.date(2026, 3, 2), datetime.date(2026, 3, 31)
    df, _ = engine.download_close_matrix(["A", "B"], start, end, today=datetime.date(2026, 6, 1))
    assert calls[0]["start"] == start - datetime.timedelta(days=engine.WARMUP_CALENDAR_DAYS)
    assert len(calls) == 1  # no live append for historical windows
    assert df.index.max() == pd.Timestamp(end)


def test_us_fallback_only_for_dow(monkeypatch):
    def boom(*a, **k):
        raise OSError("offline")

    monkeypatch.setattr(engine, "_read_html_tables", boom)
    tickers, _, is_fallback = engine.get_us_constituents("DOW JONES")
    assert is_fallback and len(tickers) == 30 and "GOOGL" in tickers and "DOW" not in tickers
    with pytest.raises(engine.ConstituentFetchError):
        engine.get_us_constituents("S&P 500")


def test_india_fallback_flagged(monkeypatch):
    def boom(*a, **k):
        raise OSError("offline")

    monkeypatch.setattr(engine.requests, "get", boom)
    tickers, msg, is_fallback = engine.get_india_constituents("NIFTY BANK")
    assert is_fallback and tickers == engine.FALLBACK_TICKERS and "fallback" in msg


def test_charts_build():
    view, _ = engine.compute_timeseries(make_prices(80, 30), pd.Timestamp("2026-03-01"), pd.Timestamp("2026-12-31"))
    for fn in (charts.plot_relative_breadth, charts.plot_custom_breadth, charts.plot_rel_ad_ratio,
               charts.plot_ad_ratio, charts.plot_ad_line):
        assert fn(view).data
