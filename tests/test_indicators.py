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


def counts(adv, dec, start="2026-01-01"):
    idx = pd.bdate_range(start, periods=len(adv))
    return pd.Series(adv, index=idx, dtype=float), pd.Series(dec, index=idx, dtype=float)


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
    assert px.index[10] not in out.index
    assert (out["Unchanged"] == 0).all()
    assert out.loc[px.index[11], "Total"] == 30


def test_custom_breadth_is_seeded_ema():
    rng = np.random.default_rng(1)
    adv = rng.integers(0, 50, 60)
    a, d = counts(adv, 50 - adv)
    osc = ind.oscillators(a, d)
    x = a / (a + d)
    cb = osc["Custom_Breadth"]
    assert cb.iloc[:9].isna().all()
    expected = x.iloc[:10].mean()
    assert cb.iloc[9] == pytest.approx(expected)
    for i in range(10, 60):
        expected += 2 / 11 * (x.iloc[i] - expected)
        assert cb.iloc[i] == pytest.approx(expected)


def test_relative_breadth_and_rel_ad_ratio_formulas():
    rng = np.random.default_rng(2)
    adv = rng.integers(5, 45, 80)
    osc = ind.oscillators(*counts(adv, 50 - adv))
    cb, i = osc["Custom_Breadth"], 79
    z = np.mean([cb.iloc[i - p + 1:i + 1].mean() for p in ind.FIB_PERIODS])
    assert osc["Relative_Breadth"].iloc[i] == pytest.approx((z + cb.iloc[i]) / 2)
    d = osc["AD_Ratio"].diff()
    multi = np.mean([d.iloc[i - p + 1:i + 1].mean() for p in (2, 3, 5)])
    assert osc["Rel_AD_Ratio"].iloc[i] == pytest.approx((d.iloc[i] + multi) / 2)
    assert osc["AD_Ratio"].iloc[i] == pytest.approx(adv[i] / (50 - adv[i]))


def test_ad_ratio_when_nothing_declines():
    osc = ind.oscillators(*counts([12] * 15, [0] * 15))
    assert (osc["AD_Ratio"] == 12).all()
    assert osc["Custom_Breadth"].dropna().eq(1.0).all()


@pytest.mark.parametrize("rb,zone", [(0.35, "OVERSOLD"), (0.40, "NEUTRAL"), (0.45, "NEUTRAL"), (0.50, "NEUTRAL"),
                                     (0.55, "OVERBOUGHT"), (np.nan, "N/A")])
def test_zone_of(rb, zone):
    assert ind.zone_of(rb) == zone


def _osc(rb, cb=None, rel=None):
    idx = pd.bdate_range("2026-01-01", periods=len(rb))
    return pd.DataFrame({"Relative_Breadth": rb, "Custom_Breadth": cb if cb is not None else rb,
                         "Rel_AD_Ratio": rel if rel is not None else [0.1] * len(rb)}, index=idx)


def test_classify_zone_runs_direction_band_and_momentum():
    rb = [0.45, 0.39, 0.38, 0.41, 0.52, 0.53]
    cb = [0.46, 0.40, 0.383, 0.44, 0.50, 0.53]      # gaps: +.01, +.01, +.003, +.03, -.02, 0
    out = ind.classify(_osc(rb, cb, rel=[1, 1, 1, -5, -5, -5]))
    assert list(out["Zone"]) == ["NEUTRAL", "OVERSOLD", "OVERSOLD", "NEUTRAL", "OVERBOUGHT", "OVERBOUGHT"]
    assert list(out["Days_In_Zone"]) == [1, 1, 2, 1, 1, 2]
    # inside the +/-0.005 band the previous direction is kept
    assert list(out["Direction"]) == ["IMPROVING", "IMPROVING", "IMPROVING", "IMPROVING", "DETERIORATING",
                                      "DETERIORATING"]
    assert out["Momentum"].iloc[0] == "POSITIVE" and out["Momentum"].iloc[-1] == "NEGATIVE"


def test_crossings():
    p = ind.classify(_osc([0.45, 0.39, 0.38, 0.41, 0.52, 0.48]))
    c = {k: list(np.flatnonzero(v.to_numpy())) for k, v in ind.crossings(p).items()}
    assert c == {"OS_IN": [1], "OS_OUT": [3], "OB_IN": [4], "OB_OUT": [5]}


def test_breadth_trend_and_window_reanchoring():
    p = ind.compute_panel(make_prices(160, 30, seed=4))
    valid = p["AD_Line_MA50"].notna()
    assert (p.loc[valid, "Breadth_Trend"] == np.where(p.loc[valid, "AD_Line"] >= p.loc[valid, "AD_Line_MA50"],
                                                      "RISING", "FALLING")).all()
    view = ind.window(p, p.index[100], p.index[-1])
    assert view["AD_Line"].iloc[0] == view["Net_Advances"].iloc[0]
    # the trend comparison is unchanged by re-anchoring
    gap_full = (p["AD_Line"] - p["AD_Line_MA50"]).loc[view.index]
    assert np.allclose(view["AD_Line"] - view["AD_Line_MA50"], gap_full)
    assert np.allclose(view["Relative_Breadth"], p.loc[view.index, "Relative_Breadth"])


def test_tz_aware_index_and_duplicates():
    px = make_prices(30, 12)
    px.index = px.index.tz_localize("Asia/Kolkata") + pd.Timedelta(hours=9, minutes=15)
    px = pd.concat([px, px.iloc[[-1]]])
    out = ind.compute_panel(px)
    assert out.index.is_unique and out.index.tz is None


def test_sector_oscillators_and_snapshot():
    px = make_prices(120, 14, seed=5)
    px.iloc[:, :6] = np.linspace(50, 150, 120)[:, None] * np.linspace(1, 1.1, 6)   # sector A only rises
    sectors = {c: ("A" if i < 6 else "B" if i < 12 else "C") for i, c in enumerate(px.columns)}
    osc = ind.sector_oscillators(px, sectors)
    assert set(osc) == {"A", "B"}                      # C has 2 members, below the minimum
    assert osc["A"]["Custom_Breadth"].dropna().eq(1.0).all()
    snap = ind.sector_snapshot(osc, px.index[-1])
    assert list(snap.columns) == ["Sector", "Stocks", "Zone", "Relative_Breadth", "Direction", "Move_1M_%"]
    assert snap.set_index("Sector").loc["A", "Zone"] == "OVERBOUGHT"
    assert snap["Relative_Breadth"].is_monotonic_increasing


def test_stock_snapshot():
    px = make_prices(40, 5, seed=6)
    snap = ind.stock_snapshot(px, px.index[-1], sectors={"S0": "X"})
    row = snap.set_index("Symbol").loc["S0"]
    assert row["Sector"] == "X"
    assert row["Day_%"] == pytest.approx((px["S0"].iloc[-1] / px["S0"].iloc[-2] - 1) * 100)
    assert row["Month_%"] == pytest.approx((px["S0"].iloc[-1] / px["S0"].iloc[-22] - 1) * 100)
    assert snap["Day_%"].is_monotonic_decreasing
