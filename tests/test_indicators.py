import numpy as np
import pandas as pd
import pytest

from breadth import indicators as ind


def make_prices(n_days=120, n_assets=30, seed=0, start="2026-01-01"):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start, periods=n_days)
    rets = rng.normal(0, 0.01, (n_days, n_assets))
    return pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)), index=idx,
                        columns=[f"S{i}" for i in range(n_assets)])


def test_counts_match_manual():
    px = make_prices(5, 12)
    out = ind.compute_panel(px)
    pct = px.pct_change().iloc[1:]
    assert list(out["Advances"]) == list((pct > 0).sum(axis=1))
    assert list(out["Declines"]) == list((pct < 0).sum(axis=1))
    assert (out["Total"] == 12).all() and (out["Coverage"] == 100).all()


def test_missing_prints_are_not_counted_as_unchanged():
    px = make_prices(20, 30)
    px.iloc[10, 5:] = np.nan
    out = ind.compute_panel(px)
    assert px.index[10] not in out.index          # thin session dropped
    assert (out["Unchanged"] == 0).all()           # no stale-price "unchanged"
    assert out.loc[px.index[11], "Total"] == 30    # next day compares to last real close


def test_custom_breadth_is_seeded_ema_and_survives_dropped_rows():
    px = make_prices(60, 30)
    px.iloc[3, 3:] = np.nan
    out = ind.compute_panel(px)
    x = out["Advances"] / (out["Advances"] + out["Declines"])
    cb = out["Custom_Breadth"]
    assert cb.iloc[:9].isna().all()
    expected = x.iloc[:10].mean()
    assert cb.iloc[9] == pytest.approx(expected)
    for i in range(10, len(out)):
        expected += ind.EMA_ALPHA * (x.iloc[i] - expected)
        assert cb.iloc[i] == pytest.approx(expected)


def test_relative_breadth_formula():
    out = ind.compute_panel(make_prices(80, 30))
    cb = out["Custom_Breadth"]
    i = len(out) - 1
    z = np.mean([cb.iloc[i - p + 1:i + 1].mean() for p in ind.FIB_PERIODS])
    assert out["Relative_Breadth"].iloc[i] == pytest.approx((z + cb.iloc[i]) / 2)


def test_all_advancing_universe():
    idx = pd.bdate_range("2025-01-01", periods=300)
    px = pd.DataFrame({f"S{i}": np.linspace(100, 200, 300) * (1 + i / 100) for i in range(12)}, index=idx)
    out = ind.compute_panel(px)
    assert (out["Declines"] == 0).all() and out["AD_Ratio"].iloc[0] == 12
    assert out["Custom_Breadth"].dropna().eq(1.0).all()
    last = out.iloc[-1]
    assert last["Pct_Above_20"] == last["Pct_Above_50"] == last["Pct_Above_200"] == 100
    assert last["New_Highs"] == 12 and last["New_Lows"] == 0 and last["NH_NL_Pct"] == 100
    assert last["HL_Score"] == 100 and last["Health_Score"] == 100 and last["Regime"] == "STRONG"
    assert last["McClellan_Osc"] == pytest.approx(0, abs=1e-9)   # constant RANA of 1000 -> EMAs converge


def test_pct_above_ma_hand_example():
    idx = pd.bdate_range("2026-01-01", periods=60)
    up = np.linspace(100, 160, 60)
    down = np.linspace(160, 100, 60)
    px = pd.DataFrame({**{f"U{i}": up for i in range(7)}, **{f"D{i}": down for i in range(3)}}, index=idx)
    out = ind.compute_panel(px)
    assert out["Pct_Above_50"].iloc[-1] == pytest.approx(70)
    assert out["Pct_Above_200"].isna().all()   # not enough history


def test_mcclellan_definition():
    px = make_prices(200, 40, seed=3)
    out = ind.compute_panel(px)
    a, d = out["Advances"].astype(float), out["Declines"].astype(float)
    rana = 1000 * (a - d) / (a + d)
    osc = rana.ewm(alpha=0.10, adjust=False).mean() - rana.ewm(alpha=0.05, adjust=False).mean()
    assert np.allclose(out["McClellan_Osc"], osc)
    assert np.allclose(out["McClellan_Sum"], osc.cumsum())


def test_value_breadth_and_trin():
    idx = pd.bdate_range("2026-01-01", periods=3)
    px = pd.DataFrame({f"S{i}": [10.0, 11.0 if i < 8 else 9.0, 11.0] for i in range(12)}, index=idx)
    vol = pd.DataFrame(100.0, index=idx, columns=px.columns)
    vol.iloc[1, 8:] = 300.0
    out = ind.compute_panel(px, vol).iloc[0]
    assert out["Up_Value"] == 8 * 11 * 100 and out["Down_Value"] == 4 * 9 * 300
    ratio = (8 * 11 * 100) / (4 * 9 * 300)
    assert out["UpDown_Value_Ratio"] == pytest.approx(ratio)
    assert out["TRIN"] == pytest.approx((8 / 4) / ratio)


def test_no_volume_gives_nan_value_breadth():
    out = ind.compute_panel(make_prices(30, 12))
    assert out["TRIN"].isna().all()


def test_window_reanchors_cumulative_series():
    out = ind.compute_panel(make_prices(120, 30))
    view = ind.window(out, out.index[90], out.index[-1])
    assert view["AD_Line"].iloc[0] == view["Net_Advances"].iloc[0]
    assert view["McClellan_Sum"].iloc[0] == pytest.approx(view["McClellan_Osc"].iloc[0])
    assert np.allclose(view["Relative_Breadth"], out.loc[view.index, "Relative_Breadth"])


def test_tz_aware_index_and_duplicates():
    px = make_prices(30, 12)
    px.index = px.index.tz_localize("Asia/Kolkata") + pd.Timedelta(hours=9, minutes=15)
    px = pd.concat([px, px.iloc[[-1]]])
    out = ind.compute_panel(px)
    assert out.index.is_unique and out.index.tz is None


@pytest.mark.parametrize("score,label", [(80, "STRONG"), (60, "HEALTHY"), (50, "NEUTRAL"), (35, "WEAK"),
                                         (10, "WASHOUT"), (np.nan, "N/A")])
def test_classify_health(score, label):
    assert ind.classify_health(score) == label


@pytest.mark.parametrize("rb,label", [(0.35, "OVERSOLD"), (0.45, "NEUTRAL"), (0.55, "OVERBOUGHT")])
def test_classify_tactical(rb, label):
    assert ind.classify_tactical(rb) == label


@pytest.mark.parametrize("adr,label", [(1.5, "STRONG BULLISH"), (1.1, "BULLISH"), (1.0, "NEUTRAL"),
                                       (249 / 250, "NEUTRAL"),
                                       (0.9, "BEARISH"), (0.5, "STRONG BEARISH")])
def test_classify_adr(adr, label):
    assert ind.classify_adr(adr)[0] == label


def test_snapshot_and_sectors():
    px = make_prices(300, 8, seed=1)
    px.iloc[:, 0] = np.linspace(50, 150, 300)   # steady riser: above MAs, at 52W high
    sectors = {c: ("A" if i < 4 else "B") for i, c in enumerate(px.columns)}
    snap = ind.asset_snapshot(px, px.index[-1], sectors=sectors)
    row = snap.set_index("Symbol").loc["S0"]
    assert row["Above_50DMA"] and row["Above_200DMA"] and row["New_High"]
    assert row["From_52W_High_%"] == pytest.approx(0)
    assert snap["Chg_1D_%"].is_monotonic_decreasing
    sec = ind.sector_table(snap).set_index("Sector")
    assert sec.loc["A", "Members"] == 4 and sec.loc["B", "Members"] == 4
    hist = ind.sector_participation_history(px, sectors)
    assert list(hist.columns) == ["A", "B"] and hist.iloc[-1].between(0, 100).all()


HL_TOL = ind.HL_SCALE * 5   # noise should leave at most ~5% of the universe at net highs


def test_health_score_not_dominated_by_tiny_high_low_counts():
    """2 new highs vs 0 lows in a 100-stock universe must barely move the 52W component."""
    idx = pd.bdate_range("2025-01-01", periods=300)
    rng = np.random.default_rng(5)
    flat = 100 + rng.normal(0, 0.5, (300, 100)).cumsum(axis=0) * 0.01
    px = pd.DataFrame(flat, index=idx, columns=[f"S{i}" for i in range(100)])
    px.iloc[-1, :2] = px.iloc[:, :2].max() * 1.10   # two names break out
    last = ind.compute_panel(px).iloc[-1]
    assert last["New_Highs"] >= 2
    assert abs(last["HL_Score"] - 50) <= HL_TOL
    expected = (last["Pct_Above_50"] + last["Pct_Above_200"] + last["HL_Score"]) / 3
    assert last["Health_Score"] == pytest.approx(expected)
