"""Plain-language reading of the oscillators: where breadth is, which way it is moving, what would change it."""

from __future__ import annotations

import pandas as pd

from .indicators import OVERBOUGHT, OVERSOLD
from .study import CROSSING_VERB

ZONE_CSS = {"OVERSOLD": "success", "NEUTRAL": "neutral", "OVERBOUGHT": "warning"}
ZONE_LABEL = {"OVERSOLD": "Oversold", "NEUTRAL": "Neutral", "OVERBOUGHT": "Overbought"}
ZONE_MEANING = {
    "OVERSOLD": f"Breadth is washed out. Decliners have outnumbered advancers for long enough to push "
                f"Relative Breadth below {OVERSOLD:.2f}.",
    "NEUTRAL": f"Breadth is in its normal range, between the oversold ({OVERSOLD:.2f}) and overbought "
               f"({OVERBOUGHT:.2f}) lines.",
    "OVERBOUGHT": f"Breadth is stretched. Advancers have outnumbered decliners for long enough to push "
                  f"Relative Breadth above {OVERBOUGHT:.2f}.",
}


def _n(n: int, word: str = "session") -> str:
    return f"{n} {word}{'s' if n != 1 else ''}"


def _ago(n: int) -> str:
    return "in the latest session" if n == 0 else f"{_n(n)} ago"


def percentile(panel: pd.DataFrame) -> float:
    """Share of earlier sessions with a lower Relative Breadth than the latest one."""
    rb = panel["Relative_Breadth"].dropna()
    return 100.0 * (rb.iloc[:-1] < rb.iloc[-1]).mean() if len(rb) > 1 else float("nan")


def reading(view: pd.DataFrame, panel: pd.DataFrame, zone_ev: pd.DataFrame, recent: list, unit: str
            ) -> list[str]:
    """Narrative paragraphs for the latest session, built only from the oscillators."""
    last = view.iloc[-1]
    rb, cb, zone = last["Relative_Breadth"], last["Custom_Breadth"], last["Zone"]
    days = int(last["Days_In_Zone"])
    improving = last["Direction"] == "IMPROVING"
    mom_pos = last["Momentum"] == "POSITIVE"
    recent_keys = {k for k, _ in recent}
    paras = []

    # 1. Where breadth is.
    if zone == "OVERSOLD":
        low = view["Relative_Breadth"].iloc[-days:].min()
        where = (f"Relative Breadth is **{rb:.3f}**, below the {OVERSOLD:.2f} oversold line for {_n(days)} "
                 f"(lowest {low:.3f} so far).")
    elif zone == "OVERBOUGHT":
        high = view["Relative_Breadth"].iloc[-days:].max()
        where = (f"Relative Breadth is **{rb:.3f}**, above the {OVERBOUGHT:.2f} overbought line for {_n(days)} "
                 f"(highest {high:.3f} so far).")
    else:
        where = (f"Relative Breadth is **{rb:.3f}**, {rb - OVERSOLD:.3f} above the oversold line and "
                 f"{OVERBOUGHT - rb:.3f} below the overbought line.")
    pct, since = percentile(panel), f"{panel.index[0]:%b %Y}"
    where += (f" That is higher than {pct:.0f}% of sessions since {since}." if pct >= 50 else
              f" That is lower than {100 - pct:.0f}% of sessions since {since}.")
    if recent:
        steps = [f"{CROSSING_VERB[k]} ({_ago(ago)})" for k, ago in sorted(recent, key=lambda t: -t[1])]
        where += " Over the last two weeks breadth " + ", then ".join(steps) + "."
    if zone == "OVERBOUGHT" and zone_ev.loc["OVERBOUGHT", "Time_%"] >= 35:
        where += (f" In this market breadth has been above {OVERBOUGHT:.2f} "
                  f"{zone_ev.loc['OVERBOUGHT', 'Time_%']:.0f}% of the time, so overbought readings are common.")
    paras.append(where)

    # 2. Which way it is moving, and whether daily momentum agrees.
    if improving and mom_pos:
        move = (f"Custom Breadth ({cb:.3f}) is above Relative Breadth and the Relative A/D Ratio is positive: "
                f"participation is **improving, and daily momentum confirms it**.")
    elif improving:
        move = (f"Custom Breadth ({cb:.3f}) is above Relative Breadth, so participation is **improving**, "
                f"but the Relative A/D Ratio is negative: the improvement is losing pace.")
    elif mom_pos:
        move = (f"Custom Breadth ({cb:.3f}) is below Relative Breadth, so participation is **deteriorating**, "
                f"but the Relative A/D Ratio is positive: the decline may be slowing.")
    else:
        move = (f"Custom Breadth ({cb:.3f}) is below Relative Breadth and the Relative A/D Ratio is negative: "
                f"participation is **deteriorating, and daily momentum confirms it**.")

    # 3. What that means in the context of the zone.
    if zone == "OVERSOLD":
        ctx = ("A turn is forming inside the oversold zone." if improving else
               "There is no sign of a turn yet; oversold readings can deepen before they recover.")
    elif zone == "OVERBOUGHT":
        ctx = "Strength is broad and still building." if improving else "Strength is broad but starting to fade."
    elif "OS_OUT" in recent_keys:
        ctx = ("The move out of oversold is holding." if improving else
               "The move out of oversold is stalling; a slip back below the line would undo it.")
    elif "OB_OUT" in recent_keys:
        ctx = ("Breadth is firming again after cooling off from overbought." if improving else
               "Breadth is cooling off from overbought.")
    else:
        ctx = ("Breadth is drifting higher within the normal range." if improving else
               "Breadth is drifting lower within the normal range.")
    paras.append(move + " " + ctx)

    # 4. Latest session and the longer breadth trend.
    trend_txt = {
        "RISING": "the A/D line is above its 50-session average, so the longer breadth trend is **rising**",
        "FALLING": "the A/D line is below its 50-session average, so the longer breadth trend is **falling**",
    }.get(last["Breadth_Trend"])
    today = (f"Latest session: {int(last['Advances'])} {unit.lower()} advanced and {int(last['Declines'])} "
             f"declined (A/D ratio {last['AD_Ratio']:.2f})")
    paras.append(today + (f"; {trend_txt}." if trend_txt else "."))
    return paras


def _evidence(cev: pd.DataFrame, base: pd.Series, key: str, index_name: str) -> str:
    row = cev.loc[key]
    if row["N_1M"] < 3:
        return ""
    return (f" Of the {int(row['N_1M'])} past times, {index_name} was higher a month later in "
            f"{row['Up_1M_%']:.0f}% (average {row['Avg_1M_%']:+.1f}%), against {base['Up_1M_%']:.0f}% "
            f"(average {base['Avg_1M_%']:+.1f}%) for any month.")


def watch(view: pd.DataFrame, cev: pd.DataFrame, base: pd.Series, index_name: str) -> list[str]:
    """What would change the reading, with distances in oscillator units and the history of each outcome."""
    last = view.iloc[-1]
    rb, cb, zone = last["Relative_Breadth"], last["Custom_Breadth"], last["Zone"]
    if zone == "OVERSOLD":
        return [
            f"**A turn:** Custom Breadth ({cb:.3f}) crossing above Relative Breadth ({rb:.3f}).",
            f"**The exit:** Relative Breadth rising {OVERSOLD - rb:.3f} to get back above {OVERSOLD:.2f}."
            + _evidence(cev, base, "OS_OUT", index_name),
        ]
    if zone == "OVERBOUGHT":
        return [
            f"**Fading:** Custom Breadth ({cb:.3f}) crossing below Relative Breadth ({rb:.3f}).",
            f"**The exit:** Relative Breadth falling {rb - OVERBOUGHT:.3f} to get back below {OVERBOUGHT:.2f}."
            + _evidence(cev, base, "OB_OUT", index_name),
        ]
    return [
        f"**Downside:** a {rb - OVERSOLD:.3f} decline in Relative Breadth would make breadth oversold."
        + _evidence(cev, base, "OS_IN", index_name),
        f"**Upside:** a {OVERBOUGHT - rb:.3f} rise would make breadth overbought."
        + _evidence(cev, base, "OB_IN", index_name),
    ]
