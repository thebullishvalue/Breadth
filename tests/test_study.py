import numpy as np
import pandas as pd
import pytest

from breadth import study


def panel_with(zones, start="2024-01-01"):
    idx = pd.bdate_range(start, periods=len(zones))
    rb = [0.35 if z == "OVERSOLD" else 0.55 if z == "OVERBOUGHT" else 0.45 for z in zones]
    return pd.DataFrame({"Zone": zones, "Relative_Breadth": rb}, index=idx)


def test_debounce():
    flags = pd.Series([True, True, False, True] + [False] * 10 + [True])
    out = study.debounce(flags, cooldown=3)
    assert list(np.flatnonzero(out)) == [0, 14]


def test_episode_spans_merge_close_stretches():
    z = np.zeros(40, dtype=bool)
    z[[2, 3, 4, 9, 10, 30]] = True
    assert study.episode_spans(z, gap=10) == [(2, 10), (30, 30)]
    assert study.episode_spans(z, gap=3) == [(2, 4), (9, 10), (30, 30)]


def test_episodes_table():
    zones = ["NEUTRAL"] * 5 + ["OVERSOLD"] * 3 + ["NEUTRAL"] * 30 + ["OVERSOLD"] * 2
    p = panel_with(zones)
    price = pd.Series(np.arange(100.0, 100.0 + len(p)), index=p.index)
    ep = study.episodes(p, "OVERSOLD", price)
    assert list(ep["Sessions"]) == [3, 2] and list(ep["Ongoing"]) == [False, True]
    assert ep["Index_During_%"].iloc[0] == pytest.approx((107 / 105 - 1) * 100)
    assert ep["Index_1M_%"].iloc[0] == pytest.approx((126 / 105 - 1) * 100)
    assert np.isnan(ep["Index_1M_%"].iloc[1])


def test_zone_and_crossing_evidence_by_hand():
    zones = (["NEUTRAL"] * 40 + ["OVERSOLD"] * 5 + ["NEUTRAL"] * 40 + ["OVERBOUGHT"] * 5) * 3 + ["NEUTRAL"] * 70
    p = panel_with(zones)
    price = pd.Series(100 * 1.001 ** np.arange(len(p)), index=p.index)  # steady rise: every forward return > 0
    zev = study.zone_evidence(p, price)
    assert zev.loc["OVERSOLD", "Sessions"] == 15 and zev.loc["OVERSOLD", "Episodes"] == 3
    assert zev.loc["OVERSOLD", "Up_1M_%"] == 100
    assert zev.loc["OVERSOLD", "Avg_1M_%"] == pytest.approx((1.001 ** 21 - 1) * 100)
    assert zev.loc["ALL", "Time_%"] == 100
    cev = study.crossing_evidence(p, price)
    assert list(cev["Times"]) == [3, 3, 3, 3]
    assert cev.loc["OS_IN", "Last"] == p.index[40 + 2 * 90]


def test_recent_crossings():
    zones = ["NEUTRAL"] * 30 + ["OVERSOLD"] * 4 + ["NEUTRAL"] * 2
    rec = study.recent_crossings(panel_with(zones))
    assert rec == [("OS_OUT", 1), ("OS_IN", 5)]


@pytest.mark.parametrize("up,avg,label", [(70, 2.5, "FAVOURABLE"), (64, 2.6, "FAVOURABLE"), (64, 1.7, "NORMAL"),
                                          (66, 1.2, "NORMAL"),
                                          (55, 0.4, "UNFAVOURABLE"), (62, -0.6, "UNFAVOURABLE")])
def test_judge(up, avg, label):
    base = pd.Series({"Up_1M_%": 62.0, "Avg_1M_%": 1.0})
    assert study.judge(pd.Series({"Up_1M_%": up, "Avg_1M_%": avg}), base) == label


def test_verdict_text():
    zones = (["NEUTRAL"] * 40 + ["OVERSOLD"] * 5) * 6 + ["NEUTRAL"] * 40
    p = panel_with(zones)
    rng = np.random.default_rng(0)
    price = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(p)))), index=p.index)
    zev = study.zone_evidence(p, price)
    v = study.verdict(zev, "OVERSOLD", "TEST", p.index[0])
    assert v.sentence.startswith("Since Jan 2024, breadth has been oversold in 6 separate episodes")
    assert "an oversold session" in v.sentence
    few = study.verdict(zev, "OVERBOUGHT", "TEST", p.index[0])
    assert few.label == "TOO FEW CASES" and "0 separate episodes" in few.sentence
