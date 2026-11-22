import pandas as pd

from breadth import narrative, study


def view(rb, cb, rel=0.1, zone=None, days=3, trend="RISING", adv=300, dec=200):
    n = 30
    idx = pd.bdate_range("2026-01-01", periods=n)
    z = zone or ("OVERSOLD" if rb < 0.40 else "OVERBOUGHT" if rb > 0.50 else "NEUTRAL")
    return pd.DataFrame({
        "Relative_Breadth": [0.45] * (n - days) + [rb] * days, "Custom_Breadth": cb, "Rel_AD_Ratio": rel,
        "Zone": z, "Days_In_Zone": days, "Direction": "IMPROVING" if cb > rb else "DETERIORATING",
        "Momentum": "POSITIVE" if rel > 0 else "NEGATIVE", "Breadth_Trend": trend,
        "Advances": adv, "Declines": dec, "AD_Ratio": adv / dec,
    }, index=idx)


ZEV = pd.DataFrame({"Time_%": [5, 45, 50]}, index=["OVERSOLD", "NEUTRAL", "OVERBOUGHT"])
CEV = pd.DataFrame({"N_1M": [20, 20, 60, 60], "Up_1M_%": [70, 65, 62, 60], "Avg_1M_%": [2.5, 1.8, 1.0, 0.5]},
                   index=["OS_IN", "OS_OUT", "OB_IN", "OB_OUT"])
BASE = pd.Series({"Up_1M_%": 62.0, "Avg_1M_%": 1.0})


def text(paras):
    return " ".join(paras)


def test_oversold_no_turn():
    v = view(0.37, 0.35, rel=-0.2)
    t = text(narrative.reading(v, v, ZEV, [("OS_IN", 2)], "Stocks"))
    assert "below the 0.40 oversold line for 3 sessions" in t
    assert "deteriorating, and daily momentum confirms it" in t
    assert "no sign of a turn yet" in t
    assert "breadth turned oversold (2 sessions ago)" in t
    w = narrative.watch(v, CEV, BASE, "IDX")
    assert "rising 0.030 to get back above 0.40" in w[1] and "Of the 20 past times" in w[1]


def test_overbought_common_note_and_fade():
    v = view(0.52, 0.51, rel=0.3)
    t = text(narrative.reading(v, v, ZEV, [], "Stocks"))
    assert "overbought readings are common" in t and "may be slowing" in t and "starting to fade" in t
    assert narrative.watch(v, CEV, BASE, "IDX")[1].startswith("**The exit:** Relative Breadth falling 0.020")


def test_neutral_after_oversold_exit():
    v = view(0.42, 0.44, rel=0.2, trend="FALLING")
    t = text(narrative.reading(v, v, ZEV, [("OS_OUT", 0), ("OS_IN", 6)], "Stocks"))
    assert "turned oversold (6 sessions ago), then climbed out of oversold (in the latest session)" in t
    assert "move out of oversold is holding" in t and "trend is **falling**" in t
    w = narrative.watch(v, CEV, BASE, "IDX")
    assert "0.020 decline" in w[0] and "0.080 rise" in w[1]


def test_percentile_wording():
    v = view(0.37, 0.35)
    t = text(narrative.reading(v, v, ZEV, [], "Stocks"))
    assert "lower than" in t
    assert study.CROSSING_VERB["OS_OUT"] in narrative.reading(v, v, ZEV, [("OS_OUT", 1)], "Stocks")[0]
