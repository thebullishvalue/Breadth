"""
MARKET BREADTH - Advance/Decline Intelligence | A Hemrek Capital Product
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Reads an index's breadth cycle with the Aarambh oscillators: where breadth
is, what that has meant for the index, and what would change the picture.
All analytics live in the ``breadth`` package.
"""

import datetime
import re
from pathlib import Path

import pandas as pd
import streamlit as st

from breadth import __version__, build_analysis, charts, history_start
from breadth import universe as uv
from breadth.data import download_market_data
from breadth.indicators import MIN_SECTOR_MEMBERS, OVERBOUGHT, OVERSOLD
from breadth.narrative import ZONE_CSS, ZONE_LABEL, ZONE_MEANING
from breadth.study import COOLDOWN, EPISODE_GAP, judge

st.set_page_config(
    page_title="MARKET BREADTH | Advance-Decline Analytics",
    layout="wide",
    page_icon="🌊",
    initial_sidebar_state="collapsed",
)

VERSION = f"v{__version__}"
PRODUCT_NAME = "Market Breadth"
COMPANY = "Hemrek Capital"
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
CHART_PERIODS = {"3 months": 91, "6 months": 182, "1 year": 365, "2 years": 730}
EVIDENCE_YEARS = {"3 years": 3, "5 years": 5, "10 years": 10}
VERSUS = {"FAVOURABLE": "Better", "NORMAL": "Normal", "UNFAVOURABLE": "Worse"}
VERDICT_PILL = {"FAVOURABLE": "BETTER THAN NORMAL", "NORMAL": "ABOUT NORMAL", "UNFAVOURABLE": "WORSE THAN NORMAL",
                "TOO FEW CASES": "TOO FEW CASES"}

CSS = (Path(__file__).parent / "assets" / "style.css").read_text(encoding="utf-8")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# CACHED DATA ACCESS (failures raise inside, so they are never cached)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner=False)
def load_universe(kind: str, index: str):
    return uv.resolve_universe(kind, index)


@st.cache_data(ttl=300, show_spinner=False)
def load_market_data(tickers: tuple, start: datetime.date, end: datetime.date, benchmark, invert: tuple):
    return download_market_data(list(tickers), start, end, benchmark=benchmark, invert=list(invert))


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def html(text: str) -> str:
    """Markdown bold -> HTML bold, for text placed inside raw HTML blocks."""
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def caption(text: str) -> None:
    st.markdown(f'<p class="chart-caption">{text}</p>', unsafe_allow_html=True)


def pct_col(label: str, signed: bool = False):
    return st.column_config.NumberColumn(label, format="%+.1f%%" if signed else "%.0f%%")


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR & PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def render_sidebar():
    today = datetime.date.today()
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0; margin-bottom: 1rem;">
            <div style="font-size: 1.75rem; font-weight: 800; color: #FFC300;">MARKET BREADTH</div>
            <div style="color: #888888; font-size: 0.75rem; margin-top: 0.25rem;">Advance-Decline Analytics</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-title">🎯 Market</div>', unsafe_allow_html=True)
        kind = st.selectbox("Universe", uv.UNIVERSE_KINDS, index=0)
        options = uv.index_options(kind)
        if len(options) > 1:
            default = options.index("NIFTY 500") if "NIFTY 500" in options else 0
            index = st.selectbox("Index", options, index=default)
        else:
            index = options[0]

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-title">📅 Period</div>', unsafe_allow_html=True)
        end_date = st.date_input("As of", today, max_value=today,
                                 help="Read breadth as it stood on this date. Leave at today for the latest reading.")
        period = st.selectbox("Charts show the last", list(CHART_PERIODS), index=1)
        evidence = st.selectbox("Judge against history from the last", list(EVIDENCE_YEARS), index=1,
                                help="How much history is used to say what each reading has meant. "
                                     "Longer is more reliable but slower to load.")

        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("◈ READ BREADTH", type="primary")

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class='info-box'>
            <p style='font-size: 0.8rem; margin: 0; color: var(--text-muted); line-height: 1.5;'>
                <strong>Version:</strong> {VERSION}<br>
                <strong>Data:</strong> Yahoo Finance · NSE · Wikipedia
            </p>
        </div>
        """, unsafe_allow_html=True)
    start_date = end_date - datetime.timedelta(days=CHART_PERIODS[period])
    return kind, index, start_date, end_date, EVIDENCE_YEARS[evidence], run_btn


def run_pipeline(kind, index, start_date, end_date, years):
    box = st.empty()
    with box.status(f"Reading {index} breadth...", expanded=True) as status:
        status.write(f"➤ Finding the {index} constituents...")
        try:
            universe = load_universe(kind, index)
        except Exception as e:
            status.update(label="Could not load the constituent list", state="error")
            st.error(f"Could not load the {index} constituent list: {e}")
            return None
        if universe.is_fallback:
            status.warning("The live constituent list was unavailable, so a substitute list is in use. "
                           "Results will not represent the selected index.")

        hist_start = history_start(start_date, end_date, years)
        status.write(f"➤ Downloading prices for {len(universe.tickers)} {universe.unit.lower()} "
                     f"since {hist_start:%b %Y}...")
        try:
            data = load_market_data(tuple(universe.tickers), hist_start, end_date,
                                    universe.benchmark, tuple(universe.invert))
        except Exception as e:
            status.update(label="Price download failed", state="error")
            st.error(f"Price download failed: {e}")
            return None

        status.write("➤ Computing the oscillators and checking history...")
        analysis = build_analysis(universe, data, start_date, end_date)
        if analysis is None:
            status.update(label="Not enough data", state="error")
            st.error("There are no trading sessions with enough data in this period.")
            return None
    box.empty()
    return analysis


# ══════════════════════════════════════════════════════════════════════════════
# TOP OF PAGE: THE READING
# ══════════════════════════════════════════════════════════════════════════════

def render_reading(a):
    u, last, v = a.universe, a.last, a.verdict
    st.markdown(f"### {u.name} · Breadth")
    caption(f"Latest session {a.asof:%d %b %Y} · based on {a.data.close.shape[1]} of {len(u.tickers)} "
            f"{u.unit.lower()}")

    zone = a.zone
    st.markdown(f"""
    <div class="hero">
      <div>
        <div class="eyebrow">Breadth is</div>
        <div class="zone {ZONE_CSS[zone]}">{ZONE_LABEL[zone].upper()}</div>
        <div class="figure">Relative Breadth {last['Relative_Breadth']:.3f}
            &nbsp;·&nbsp; oversold below {OVERSOLD:.2f}, overbought above {OVERBOUGHT:.2f}</div>
        <div class="meaning">{ZONE_MEANING[zone]}</div>
      </div>
      <div class="right">
        <div class="eyebrow">What this has meant for {a.index_name}</div>
        <span class="regime-pill {v.css}">{VERDICT_PILL[v.label]}</span>
        <div class="verdict">{v.sentence}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    left, right = st.columns([3, 2])
    with left:
        paras = "".join(f"<p>{html(p)}</p>" for p in a.reading)
        st.markdown(f'<div class="panel"><h4>The reading</h4>{paras}</div>', unsafe_allow_html=True)
    with right:
        items = "".join(f"<li>{html(w)}</li>" for w in a.watch)
        st.markdown(f'<div class="panel"><h4>What would change it</h4><ul>{items}</ul></div>',
                    unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════

def tab_cycle(a):
    label = a.universe.name if a.uses_index else "Equal-weighted basket"
    st.markdown("##### The breadth cycle")
    caption(f"<strong>Top:</strong> {a.index_name}, shaded green while breadth was oversold and amber while it was "
            f"overbought. <strong>Middle:</strong> Relative Breadth (gold) and Custom Breadth (cyan). When Custom "
            f"Breadth is above Relative Breadth, participation is improving. <strong>Bottom:</strong> Relative A/D "
            f"Ratio, the day-to-day momentum of the A/D ratio.")
    st.plotly_chart(charts.plot_cycle(a.view, a.price, label), width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Each session: advancers ÷ decliners")
        caption("Green above 1.2, red below 0.8. The gold line is the 10-session average.")
        st.plotly_chart(charts.plot_ad_ratio(a.view), width="stretch")
    with c2:
        st.markdown("##### The longer breadth trend")
        caption("Running total of advancers minus decliners. Above its 50-session average, the trend is rising.")
        st.plotly_chart(charts.plot_ad_line(a.view), width="stretch")


def tab_history(a):
    zev, cev, base = a.zone_evidence, a.crossing_evidence, a.zone_evidence.loc["ALL"]
    since = f"{a.panel.index[0]:%b %Y}"
    st.markdown(f"##### What each zone has meant for {a.index_name}")
    caption(f"Every session since {since} grouped by the zone breadth was in that day, and what {a.index_name} did "
            f"over the following month and three months. <strong>Versus normal</strong> compares the one-month "
            f"figures with all sessions.")
    rows = []
    for z in ["OVERSOLD", "NEUTRAL", "OVERBOUGHT"]:
        r = zev.loc[z]
        rows.append({"Zone": ZONE_LABEL[z], "Share of sessions": r["Time_%"], "Separate episodes": str(int(r["Episodes"])),
                     "Higher 1 month later": r["Up_1M_%"], "Average 1-month move": r["Avg_1M_%"],
                     "Higher 3 months later": r["Up_3M_%"], "Average 3-month move": r["Avg_3M_%"],
                     "Versus normal": VERSUS[judge(r, base)] if r["Episodes"] >= 5 else "Too few"})
    rows.append({"Zone": "Any session", "Share of sessions": 100.0, "Separate episodes": "",
                 "Higher 1 month later": base["Up_1M_%"], "Average 1-month move": base["Avg_1M_%"],
                 "Higher 3 months later": base["Up_3M_%"], "Average 3-month move": base["Avg_3M_%"],
                 "Versus normal": ""})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True, column_config={
        "Share of sessions": pct_col("Share of sessions"),
        "Higher 1 month later": pct_col("Higher 1 month later"),
        "Average 1-month move": pct_col("Average 1-month move", signed=True),
        "Higher 3 months later": pct_col("Higher 3 months later"),
        "Average 3-month move": pct_col("Average 3-month move", signed=True),
    })

    st.markdown(f"##### What each crossing has meant for {a.index_name}")
    caption(f"Measured from the day Relative Breadth crossed a line. A repeat crossing within {COOLDOWN} sessions "
            f"of the last one is not counted again.")
    rows = []
    for _, r in cev.iterrows():
        rows.append({"What happened": r["What"], "Times": int(r["Times"]), "Per year": r["Per_Year"],
                     "Most recent": r["Last"].strftime("%d %b %Y") if pd.notna(r["Last"]) else "never",
                     "Higher 1 month later": r["Up_1M_%"], "Average 1-month move": r["Avg_1M_%"],
                     "Higher 3 months later": r["Up_3M_%"], "Average 3-month move": r["Avg_3M_%"],
                     "Versus normal": VERSUS[judge(r, base)] if r["N_1M"] >= 5 else "Too few"})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True, column_config={
        "Per year": st.column_config.NumberColumn(format="%.1f"),
        "Higher 1 month later": pct_col("Higher 1 month later"),
        "Average 1-month move": pct_col("Average 1-month move", signed=True),
        "Higher 3 months later": pct_col("Higher 3 months later"),
        "Average 3-month move": pct_col("Average 3-month move", signed=True),
    })

    ep = a.oversold_episodes
    st.markdown(f"##### Every oversold episode since {since}")
    caption(f"Oversold stretches less than {EPISODE_GAP} sessions apart are treated as one episode.")
    if ep.empty:
        st.info("Breadth has not been oversold in this history.")
    else:
        show = pd.DataFrame({
            "Began": ep["Start"].dt.strftime("%d %b %Y"),
            "Ended": [("ongoing" if o else e.strftime("%d %b %Y")) for e, o in zip(ep["End"], ep["Ongoing"],
                                                                                    strict=True)],
            "Sessions": ep["Sessions"], "Lowest Relative Breadth": ep["Extreme"],
            f"{a.universe.name if a.uses_index else 'Basket'} during": ep["Index_During_%"],
            "One month after it began": ep["Index_1M_%"],
        }).iloc[::-1]
        idx_col = f"{a.universe.name if a.uses_index else 'Basket'} during"
        st.dataframe(show, width="stretch", hide_index=True, column_config={
            "Lowest Relative Breadth": st.column_config.NumberColumn(format="%.3f"),
            idx_col: pct_col(idx_col, signed=True),
            "One month after it began": pct_col("One month after it began", signed=True),
        })
    caption("History uses today's index members, so companies that have since left the index are missing. "
            "Past patterns are evidence, not a guarantee.")


def tab_sectors(a):
    sec = a.sectors
    if sec.empty:
        st.info(f"No sector has at least {MIN_SECTOR_MEMBERS} members, so sector breadth is not shown.")
        return
    counts = sec["Zone"].value_counts()
    parts = []
    for z in ["OVERSOLD", "NEUTRAL", "OVERBOUGHT"]:
        n = int(counts.get(z, 0))
        if n:
            names = ", ".join(sec.loc[sec["Zone"] == z, "Sector"].head(4))
            more = "" if n <= 4 else f" and {n - 4} more"
            parts.append(f"**{n} {ZONE_LABEL[z].lower()}** ({names}{more})")
    st.markdown("##### Where breadth is coming from")
    st.markdown(f"The same oscillator applied to each sector with at least {MIN_SECTOR_MEMBERS} "
                f"{a.universe.unit.lower()}. Of {len(sec)} sectors: " + "; ".join(parts) + ".")
    table = sec.assign(
        Zone=sec["Zone"].map(ZONE_LABEL),
        Direction=sec["Direction"].str.capitalize(),
    ).rename(columns={"Relative_Breadth": "Relative Breadth", "Move_1M_%": "Last month"})
    st.dataframe(table, width="stretch", hide_index=True, column_config={
        "Relative Breadth": st.column_config.NumberColumn(format="%.3f"),
        "Last month": st.column_config.NumberColumn("Last month (equal-weighted)", format="%+.1f%%"),
    })

    st.markdown("##### Sector breadth week by week")
    caption("Relative Breadth for each sector at the end of each week: green when oversold, amber when "
            "overbought. Sectors are in the same order as the table: lowest latest reading at the top.")
    st.plotly_chart(charts.plot_sector_heatmap(a.sector_osc, a.view.index[0], a.asof), width="stretch")

    with st.expander(f"{a.universe.unit} in a sector"):
        pick = st.selectbox("Sector", ["All"] + sorted(a.stocks["Sector"].unique()))
        stocks = a.stocks if pick == "All" else a.stocks[a.stocks["Sector"] == pick]
        if not stocks["Name"].astype(bool).any():
            stocks = stocks.drop(columns="Name")
        st.dataframe(stocks, width="stretch", hide_index=True, height=420, column_config={
            "Price": st.column_config.NumberColumn(format="%.2f"),
            "Day_%": st.column_config.NumberColumn("Latest session", format="%+.2f%%"),
            "Month_%": st.column_config.NumberColumn("Last month", format="%+.1f%%"),
        })


def tab_data(a, start_date, end_date):
    u, d = a.universe, a.data
    st.markdown("##### About this reading")
    ref = (f"Compared with the {u.name} index (Yahoo Finance: {d.benchmark_ticker})." if a.uses_index else
           f"No index price was available, so results are compared with {a.index_name}: the average daily move "
           f"of the constituents.")
    lines = [
        f"- **Constituents:** {u.source}. {d.close.shape[1]} of {len(u.tickers)} had price data.",
        f"- **History:** {len(a.panel):,} sessions since {a.panel.index[0]:%d %b %Y}.",
        f"- **Index:** {ref}",
    ]
    if u.invert:
        lines.append("- **Currencies:** every currency is measured against the US dollar, so an advance means "
                     "that currency rose against USD.")
    st.markdown("\n".join(lines))
    if d.missing:
        with st.expander(f"{len(d.missing)} symbol(s) without price data"):
            st.write(", ".join(d.missing))

    st.markdown("##### How the oscillators are built")
    st.markdown(f"""
Each session, every constituent that traded is counted as advancing, declining or unchanged.

- **A/D ratio:** advancers ÷ decliners.
- **Custom Breadth:** a 10-session exponential average of advancers ÷ (advancers + decliners).
- **Relative Breadth:** the average of Custom Breadth and Z, where Z is the mean of Custom Breadth's 2, 3, 5, 8,
  13 and 21-session averages. Below {OVERSOLD:.2f} is **oversold**, above {OVERBOUGHT:.2f} is **overbought**.
- **Direction:** Custom Breadth above Relative Breadth means participation is improving; below means it is
  deteriorating.
- **Relative A/D Ratio:** the daily change in the A/D ratio blended with its 2, 3 and 5-session averages.
  Positive means momentum is improving.
- **A/D line:** the running total of advancers minus decliners. Above its 50-session average, the longer trend is
  rising.
""")

    st.markdown("##### Daily figures")
    cols = ["Advances", "Declines", "Unchanged", "AD_Ratio", "Custom_Breadth", "Relative_Breadth", "Rel_AD_Ratio",
            "AD_Line", "Zone", "Direction"]
    out = a.view[cols].reset_index().rename(columns={
        "AD_Ratio": "A/D Ratio", "Custom_Breadth": "Custom Breadth", "Relative_Breadth": "Relative Breadth",
        "Rel_AD_Ratio": "Relative A/D Ratio", "AD_Line": "A/D Line"})
    out["Date"] = out["Date"].dt.strftime("%Y-%m-%d")
    out["Zone"] = out["Zone"].str.capitalize()
    out["Direction"] = out["Direction"].str.capitalize()
    st.dataframe(out.iloc[::-1].round(4), width="stretch", hide_index=True, height=380)
    safe = re.sub(r"[^A-Za-z0-9]+", "_", u.name).strip("_")
    st.download_button("📥 Download (CSV)", out.to_csv(index=False).encode("utf-8"),
                       f"{safe}_breadth_{start_date}_{end_date}.csv", "text/csv")


def render_results(a, start_date, end_date):
    render_reading(a)
    tabs = st.tabs(["**📈 Breadth Cycle**", "**🧪 What History Says**", "**🏭 Sectors**", "**📋 Data & Method**"])
    with tabs[0]:
        tab_cycle(a)
    with tabs[1]:
        tab_history(a)
    with tabs[2]:
        tab_sectors(a)
    with tabs[3]:
        tab_data(a, start_date, end_date)


# ══════════════════════════════════════════════════════════════════════════════
# LANDING
# ══════════════════════════════════════════════════════════════════════════════

def landing_card(css: str, color_var: str, title: str, body: str) -> str:
    return f"""
    <div class='metric-card {css}' style='min-height: 220px;'>
        <h3 style='color: var({color_var}); margin-bottom: 1rem;'>{title}</h3>
        <p style='color: var(--text-muted); font-size: 0.92rem; line-height: 1.65;'>{body}</p>
    </div>"""


def render_landing(index):
    st.markdown("""
    <div class="premium-header">
        <h1>MARKET BREADTH : Advance-Decline Intelligence</h1>
        <div class="tagline">How many stocks are taking part, and what that has meant</div>
    </div>
    """, unsafe_allow_html=True)
    cards = [
        landing_card("success", "--success-green", "1 · Where breadth is",
                     f"The Relative Breadth oscillator places the market in one of three zones: oversold "
                     f"(below {OVERSOLD:.2f}), neutral, or overbought (above {OVERBOUGHT:.2f})."),
        landing_card("primary", "--primary-color", "2 · Which way it is moving",
                     "Custom Breadth against Relative Breadth shows whether participation is improving or "
                     "deteriorating; the Relative A/D Ratio shows whether daily momentum agrees."),
        landing_card("info", "--info-cyan", "3 · What it has meant",
                     "Every reading is checked against the index's own history: how often it was higher a month "
                     "later, compared with any other month."),
    ]
    for col, card in zip(st.columns(3), cards, strict=True):
        col.markdown(card, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='info-box'>
        <h4>🚀 Getting Started</h4>
        <p style='color: var(--text-muted); line-height: 1.7;'>
            Open the sidebar, choose a market (currently <i>{index}</i>) and click <strong>◈ READ BREADTH</strong>.
        </p>
    </div>
    """, unsafe_allow_html=True)


def main():
    kind, index, start_date, end_date, years, run_btn = render_sidebar()

    if run_btn:
        st.session_state.pop("analysis", None)
        a = run_pipeline(kind, index, start_date, end_date, years)
        if a is not None:
            st.session_state["analysis"] = (a, start_date, end_date)

    if "analysis" in st.session_state:
        render_results(*st.session_state["analysis"])
    elif not run_btn:
        render_landing(index)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    ist_time = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    st.caption(f"© 2026 {COMPANY} | {PRODUCT_NAME} {VERSION} | {ist_time}")


if __name__ == "__main__":
    main()
