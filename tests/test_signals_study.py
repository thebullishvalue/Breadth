import numpy as np
import pandas as pd
import pytest

from breadth import signals as sig
from breadth import study


def test_debounce():
    flags = pd.Series([True, True, False, True] + [False] * 10 + [True])
    out = sig.debounce(flags, cooldown=3)
    assert list(out[out].index) == [0, 14]


def _panel(cb, p50=None, rb=None):
    n = len(cb)
    idx = pd.bdate_range("2026-01-01", periods=n)
    return pd.DataFrame({
        "Custom_Breadth": cb, "Relative_Breadth": rb if rb is not None else [0.45] * n,
        "Pct_Above_50": p50 if p50 is not None else [50.0] * n, "EW_Index": np.linspace(100, 110, n),
    }, index=idx)


def test_zweig_thrust_detection():
    cb = [0.45] * 5 + [0.38, 0.42, 0.50, 0.58, 0.62, 0.64] + [0.6] * 5
    p = _panel(cb)
    ev = sig.detect_events(p, p["EW_Index"])
    assert list(ev["thrust"][ev["thrust"]].index) == [p.index[9]]
    # too slow: low point more than THRUST_DAYS sessions before the cross
    slow = [0.38] + [0.45] * 12 + [0.62]
    p2 = _panel(slow)
    assert not sig.detect_events(p2, p2["EW_Index"])["thrust"].any()


def test_bearish_divergence():
    n = 100
    price = pd.Series(np.linspace(100, 150, n))
    p50 = np.r_[np.full(50, 80.0), np.full(50, 55.0)]   # participation fell 25 pts while price kept rising
    p = _panel([0.45] * n, p50=p50)
    price.index = p.index
    ev = sig.detect_events(p, price)
    assert ev["bear_div"].any() and not ev["bull_div"].any()
    # first session with a full 63-session price lookback
    assert ev["bear_div"].idxmax() == p.index[sig.DIVERGENCE_LOOKBACK - 1]


def test_align_benchmark_fallback():
    p = _panel([0.45] * 10)
    s, src = sig.align_benchmark(p, None)
    assert src == "equal-weight composite" and s.equals(p["EW_Index"])
    b = pd.Series(np.arange(10.0), index=p.index)
    s, src = sig.align_benchmark(p, b)
    assert src == "benchmark" and s.equals(b)


def test_recent_events_and_desk_note():
    idx = pd.bdate_range("2026-01-01", periods=20)
    events = {"thrust": pd.Series(False, index=idx), "washout": pd.Series(False, index=idx)}
    events["thrust"].iloc[-2] = True
    rec = sig.recent_events(events)
    assert rec == [("thrust", idx[-2], 1)]


def test_forward_returns_and_event_study():
    idx = pd.bdate_range("2026-01-01", periods=100)
    price = pd.Series(np.linspace(100, 199, 100), index=idx)
    fwd = study.forward_returns(price, (5,))
    assert fwd[5].iloc[0] == pytest.approx((105 / 100 - 1) * 100)
    assert fwd[5].iloc[-5:].isna().all()
    flags = pd.Series(False, index=idx)
    flags.iloc[[10, 40]] = True
    table = study.event_study({"thrust": flags}, price, horizons=(5,))
    row = table.set_index("Signal").loc["Breadth Thrust"]
    expected = np.mean([(price.iloc[15] / price.iloc[10] - 1) * 100, (price.iloc[45] / price.iloc[40] - 1) * 100])
    assert row["Events"] == 2 and row["Avg 5D %"] == pytest.approx(expected) and row["Hit 5D %"] == 100
    base = table.set_index("Signal").loc["All sessions (baseline)", "Avg 5D %"]
    assert row["Edge 5D %"] == pytest.approx(expected - base)
    assert bool(row["Low Sample"])


def test_regime_study():
    idx = pd.bdate_range("2026-01-01", periods=60)
    price = pd.Series(np.linspace(100, 160, 60), index=idx)
    regime = pd.Series(["STRONG"] * 30 + ["WEAK"] * 30, index=idx)
    t = study.regime_study(regime, price, horizon=5).set_index("Regime")
    assert t.loc["STRONG", "Sessions"] == 30 and t.loc["WEAK", "Sessions"] == 25
    assert t.loc["HEALTHY", "Sessions"] == 0


def test_regime_evidence():
    idx = pd.bdate_range("2026-01-01", periods=80)
    price = pd.Series(np.linspace(100, 180, 80), index=idx)
    regime = pd.Series(["STRONG"] * 40 + ["WEAK"] * 40, index=idx)
    t = study.regime_study(regime, price)
    line = study.regime_evidence(t, "STRONG", price)
    assert line.startswith("History: STRONG") and "n=40" in line
    assert study.regime_evidence(t, "WASHOUT", price) is None   # no sample
