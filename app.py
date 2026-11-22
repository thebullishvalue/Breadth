"""
MARKET BREADTH - Advance/Decline Intelligence | A Hemrek Capital Product
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Streamlit front-end. All analytics live in the ``breadth`` package.
"""

import datetime
import re
from pathlib import Path

import pandas as pd
import streamlit as st

from breadth import __version__, build_analysis, charts, history_start
from breadth import indicators as ind
from breadth import universe as uv
from breadth.data import download_market_data
from breadth.signals import COOLDOWN, SIGNAL_BY_KEY, SIGNALS, recent_events
from breadth.study import HORIZONS, MIN_SAMPLE

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
STUDY_YEARS = {"1 year": 1, "3 years": 3, "5 years": 5, "10 years": 10}

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
# SMALL RENDER HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def metric_card(title: str, value: str, sub: str, css: str, size: str = "1.6rem") -> str:
    return (f'<div class="metric-card {css}"><h4>{title}</h4>'
            f'<h2 style="font-size: {size};">{value}</h2><div class="sub-metric">{sub}</div></div>')


def caption(text: str) -> None:
    st.markdown(f'<p class="chart-caption">{text}</p>', unsafe_allow_html=True)


def chart(title: str, text: str, fig) -> None:
    st.markdown(f"##### {title}")
    caption(text)
    st.plotly_chart(fig, width="stretch")


def pill(text: str, css: str) -> str:
    return f'<span class="regime-pill {css}">{text}</span>'


def md_bold(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def fmt(v, spec: str, na: str = "n/a") -> str:
    return format(v, spec) if pd.notna(v) else na


def sign_css(v, threshold: float = 0.0) -> str:
    if pd.isna(v):
        return "neutral"
    return "success" if v > threshold else "danger" if v < threshold else "neutral"


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

        st.markdown('<div class="sidebar-title">🎯 Universe Selection</div>', unsafe_allow_html=True)
        kind = st.selectbox("Analysis Universe", uv.UNIVERSE_KINDS, index=0,
                            help="Index constituents (India/US), commodity futures, or currencies measured vs USD.")
        options = uv.index_options(kind)
        if len(options) > 1:
            default = options.index("NIFTY 500") if "NIFTY 500" in options else 0
            index = st.selectbox("Select Index", options, index=default)
        else:
            index = options[0]

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-title">📅 Display Window</div>', unsafe_allow_html=True)
        start_date = st.date_input("Start Date", today - datetime.timedelta(days=180), max_value=today)
        end_date = st.date_input("End Date", today, max_value=today)
        study_label = st.selectbox(
            "Signal study history", list(STUDY_YEARS), index=1,
            help="How far back the forward-return study looks. Longer is more robust but slower to download.")

        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("◈ RUN ANALYSIS", type="primary")

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class='info-box'>
            <p style='font-size: 0.8rem; margin: 0; color: var(--text-muted); line-height: 1.5;'>
                <strong>Version:</strong> {VERSION}<br>
                <strong>Data:</strong> Yahoo Finance · NSE · Wikipedia<br>
                <strong>Universe:</strong> {kind} – {index}
            </p>
        </div>
        """, unsafe_allow_html=True)
    return kind, index, start_date, end_date, STUDY_YEARS[study_label], run_btn


def run_pipeline(kind, index, start_date, end_date, study_years):
    box = st.empty()
    with box.status("📡 Fetching market data...", expanded=True) as status:
        status.write(f"➤ Resolving {index} constituents...")
        try:
            universe = load_universe(kind, index)
        except Exception as e:
            status.update(label="❌ Constituent fetch failed", state="error")
            st.error(f"Could not obtain constituents for {index}: {e}")
            return None
        status.write(f"&nbsp;&nbsp;&nbsp;↳ {universe.source}")
        if universe.is_fallback:
            status.warning("Fallback constituent list in use. Results may not represent the selected index.")

        hist_start = history_start(start_date, end_date, study_years)
        status.write(f"➤ Downloading {len(universe.tickers)} symbols from {hist_start:%d %b %Y} (+ warm-up)...")
        try:
            data = load_market_data(tuple(universe.tickers), hist_start, end_date,
                                    universe.benchmark, tuple(universe.invert))
        except Exception as e:
            status.update(label="❌ Price download failed", state="error")
            st.error(f"Price download failed: {e}")
            return None
        status.write(f"&nbsp;&nbsp;&nbsp;↳ {data.close.shape[1]} priced, {len(data.missing)} missing, "
                     f"{len(data.close)} sessions")

        status.write("➤ Computing breadth panel, signals and studies...")
        analysis = build_analysis(universe, data, start_date, end_date)
        if analysis is None:
            status.update(label="❌ No usable sessions", state="error")
            st.error("No sessions with sufficient coverage in the selected window "
                     "(weekend, holiday, or data not yet available).")
            return None
    box.empty()
    return analysis


# ══════════════════════════════════════════════════════════════════════════════
# RESULTS
# ══════════════════════════════════════════════════════════════════════════════

def reference_label(a) -> str:
    return a.data.benchmark_ticker if a.price_source == "benchmark" else "EW composite"


def render_header(a):
    last, panel, u = a.last, a.panel, a.universe
    prev5 = panel.iloc[-6] if len(panel) > 5 else panel.iloc[0]
    st.markdown(f"### {u.name} · Breadth Monitor")
    caption(f"As of {a.asof:%d %b %Y} · reference series: {reference_label(a)} · "
            f"{a.data.close.shape[1]}/{len(u.tickers)} {u.unit.lower()} priced · "
            f"session coverage {last['Coverage']:.0f}%")

    pills = [pill(f"HEALTH: {last['Regime']}", ind.regime_css(last["Regime"])),
             pill(f"TACTICAL: {last['Tactical']}",
                  {"OVERSOLD": "success", "OVERBOUGHT": "danger"}.get(last["Tactical"], "neutral"))]
    for key, _, ago in recent_events(a.events):
        sd = SIGNAL_BY_KEY[key]
        when = "today" if ago == 0 else f"{ago}d ago"
        pills.append(pill(f"{sd.label.upper()} · {when}", "success" if sd.bias == "bullish" else "danger"))
    st.markdown(f'<div class="regime-banner">{"".join(pills)}</div>', unsafe_allow_html=True)

    adr = float(last["AD_Ratio"])
    sentiment, s_css = ind.classify_adr(adr)
    hs = last["Health_Score"]
    cards = [
        metric_card("Health Score", fmt(hs, ".0f"),
                    f"{fmt(hs - prev5['Health_Score'], '+.1f')} vs 5 sessions ago", ind.regime_css(last["Regime"])),
        metric_card("% > 50-DMA", fmt(last["Pct_Above_50"], ".0f") + "%", "Intermediate trend",
                    sign_css(last["Pct_Above_50"], 50)),
        metric_card("% > 200-DMA", fmt(last["Pct_Above_200"], ".0f") + "%", "Long-term trend",
                    sign_css(last["Pct_Above_200"], 50)),
        metric_card("Net New Highs", fmt(last["NH_NL"], "+.0f"),
                    f"{fmt(last['New_Highs'], '.0f')} highs / {fmt(last['New_Lows'], '.0f')} lows",
                    sign_css(last["NH_NL"])),
        metric_card("McClellan Osc", fmt(last["McClellan_Osc"], "+.0f"), "Breadth momentum",
                    sign_css(last["McClellan_Osc"])),
        metric_card("A/D Ratio", f"{adr:.2f}",
                    f"{int(last['Advances'])} adv / {int(last['Declines'])} dec · {sentiment}", s_css),
    ]
    for col, html in zip(st.columns(len(cards)), cards, strict=True):
        col.markdown(html, unsafe_allow_html=True)

    items = "".join(f"<li>{md_bold(n)}</li>" for n in a.note)
    st.markdown(f'<div class="desk-note"><h4>Desk Note</h4><ul>{items}</ul></div>', unsafe_allow_html=True)


def tab_overview(a):
    chart("Reference Series vs Structural Health",
          "Top: benchmark (or equal-weight composite) with breadth signals (▲ bullish, ▼ bearish). Bottom: Health "
          "Score, the average of % above 50-DMA, % above 200-DMA and a net-new-highs score. Bands: ≥70 Strong · 55–70 Healthy · "
          "45–55 Neutral · 30–45 Weak · <30 Washout.",
          charts.plot_overview(a.view, a.price, a.events, reference_label(a)))


def tab_participation(a):
    chart("Trend Participation",
          "Share of constituents trading above their own 20/50/200-session moving averages. "
          "Above 80% is broad strength (often stretched); below 20% is capitulation territory.",
          charts.plot_participation(a.view))
    chart("52-Week Highs vs Lows",
          "Constituents closing at a 52-week high (green) or low (red). Expanding new highs confirm a trend; "
          "rising new lows during an index advance warns of narrowing leadership.",
          charts.plot_highs_lows(a.view))


def tab_momentum(a):
    chart("McClellan Oscillator & Summation Index",
          "Ratio-adjusted: EMA(10%) − EMA(5%) of 1000·(A−D)/(A+D), so readings are comparable across universe sizes. "
          "The Summation Index is accumulated from the start of the display window.",
          charts.plot_mcclellan(a.view))
    if a.data.has_volume and a.view["UpDown_Value_Ratio"].notna().any():
        chart("Up/Down Traded Value & Arms Index",
              "Traded value (price × volume) in advancing vs declining constituents. TRIN = (A/D) ÷ (up value / "
              "down value); below 1 means money is concentrated in advancers.",
              charts.plot_volume_breadth(a.view))
    else:
        st.info("No volume data for this universe (e.g. spot FX), so value-weighted breadth is unavailable.")
    chart("Cumulative Advance/Decline Line",
          "Running total of net advances from the start of the display window.",
          charts.plot_ad_line(a.view))


def tab_oscillators(a):
    chart("Relative Breadth Oscillator", "Fibonacci Sequence MA Smoothing. Green = Oversold | Red = Overbought",
          charts.plot_relative_breadth(a.view))
    chart("Relative A/D Ratio",
          "Multi-timeframe ADR momentum. Blends daily change with 2/3/5-day smoothed composites. "
          "Green = Positive Momentum | Red = Negative Momentum",
          charts.plot_rel_ad_ratio(a.view))
    chart("Custom Breadth Oscillator", "EMA Smoothed Signal. Green = Oversold | Red = Overbought",
          charts.plot_custom_breadth(a.view))
    chart("Advance/Decline Ratio (ADR) Oscillator", "Raw ADR Metric. Green = Bullish Skew | Red = Bearish Skew",
          charts.plot_ad_ratio(a.view))


def tab_sectors(a):
    if a.sectors.empty:
        st.info("No sector data available.")
        return
    st.markdown(f"##### Sector Breadth on {a.asof:%d %b %Y}")
    caption("Sorted by participation. EW returns are equal-weighted averages of members.")
    st.dataframe(
        a.sectors, width="stretch", hide_index=True,
        column_config={
            "Pct_Above_50": st.column_config.ProgressColumn("% > 50-DMA", min_value=0, max_value=100, format="%.0f%%"),
            "Pct_Above_200": st.column_config.ProgressColumn("% > 200-DMA", min_value=0, max_value=100,
                                                             format="%.0f%%"),
            "EW_Ret_21D_%": st.column_config.NumberColumn("EW 21D %", format="%+.2f%%"),
            "EW_Chg_1D_%": st.column_config.NumberColumn("EW 1D %", format="%+.2f%%"),
        },
    )
    if not a.sector_history.empty and a.sector_history.shape[1] > 1:
        chart("Sector Participation Rotation",
              "Weekly % of each sector's members above their 50-DMA. Read across for rotation, down for breadth of "
              "the move.", charts.plot_sector_heatmap(a.sector_history))


def tab_study(a):
    st.markdown("##### Signal Forward-Return Study")
    caption(f"Reference: {reference_label(a)} · {a.study_start:%d %b %Y} → {a.asof:%d %b %Y} ({len(a.panel)} "
            f"sessions). Events within {COOLDOWN} sessions of a previous one are ignored. <strong>Edge</strong> = "
            f"average forward return after the signal minus the average over all sessions. Rows with fewer than "
            f"{MIN_SAMPLE} events are flagged. Constituents are today's members, so history carries survivorship "
            f"bias, and nearby events have overlapping forward windows. Treat this as evidence, not proof.")
    metric = st.radio("Metric", ["Avg", "Hit", "Edge"], horizontal=True,
                      captions=["Mean forward return", "% of events with a positive return", "Mean minus baseline"])
    t = a.event_table
    cols = ["Signal", "Bias", "Events", "Last"] + [f"{metric} {h}D %" for h in HORIZONS] + ["Low Sample"]
    fmt_str = "%.0f%%" if metric == "Hit" else "%+.2f%%"
    st.dataframe(t[cols], width="stretch", hide_index=True, column_config={
        **{f"{metric} {h}D %": st.column_config.NumberColumn(f"{h}D", format=fmt_str) for h in HORIZONS},
        "Low Sample": st.column_config.CheckboxColumn("Low n"),
    })

    st.markdown("##### Forward Returns by Health Regime")
    caption("Average 21-session forward return of the reference series, grouped by the regime on the entry day.")
    c1, c2 = st.columns([3, 2])
    with c1:
        st.plotly_chart(charts.plot_regime_returns(a.regime_table), width="stretch")
    with c2:
        st.dataframe(a.regime_table, width="stretch", hide_index=True, column_config={
            "Avg 21D %": st.column_config.NumberColumn(format="%+.2f%%"),
            "Hit 21D %": st.column_config.NumberColumn(format="%.0f%%"),
        })

    with st.expander("Signal definitions"):
        for s in SIGNALS:
            st.markdown(f"- **{s.label}** ({s.bias}): {s.description}")


def tab_constituents(a):
    snap = a.snapshot
    if snap.empty:
        st.info("Per-asset data unavailable for this session.")
        return
    st.markdown(f"##### Constituents on {a.asof:%d %b %Y}")
    sectors = sorted(snap["Sector"].unique())
    pick = st.multiselect("Filter sectors", sectors, default=[]) if len(sectors) > 1 else []
    view = snap[snap["Sector"].isin(pick)] if pick else snap
    if not view["Name"].astype(bool).any():
        view = view.drop(columns="Name")
    st.dataframe(view, width="stretch", hide_index=True, height=520, column_config={
        "Price": st.column_config.NumberColumn(format="%.4f"),
        "Chg_1D_%": st.column_config.NumberColumn("1D %", format="%+.2f%%"),
        "Ret_21D_%": st.column_config.NumberColumn("21D %", format="%+.2f%%"),
        "From_52W_High_%": st.column_config.NumberColumn("vs 52W High", format="%+.1f%%"),
        "Above_50DMA": st.column_config.CheckboxColumn("> 50DMA"),
        "Above_200DMA": st.column_config.CheckboxColumn("> 200DMA"),
        "New_High": st.column_config.CheckboxColumn("52W High"),
        "New_Low": st.column_config.CheckboxColumn("52W Low"),
    })


def tab_data(a, start_date, end_date):
    u, d = a.universe, a.data
    st.markdown("##### Data Quality")
    c = st.columns(4)
    c[0].metric("Constituents requested", len(u.tickers))
    c[1].metric("Priced", d.close.shape[1])
    c[2].metric("Avg session coverage", f"{a.view['Coverage'].mean():.0f}%")
    c[3].metric("Study sessions", len(a.panel))
    lines = [
        f"- **Constituent source:** {u.source}",
        f"- **Reference series:** {reference_label(a) if a.price_source == 'benchmark' else 'equal-weight composite of constituents'}",
        "- **Survivorship:** history uses current constituents; delisted or removed names are absent.",
    ]
    if u.invert:
        lines.append("- **Orientation:** USD-quoted pairs are inverted so an advance means the currency rose vs USD.")
    st.markdown("\n".join(lines))
    if d.missing:
        with st.expander(f"{len(d.missing)} symbols returned no price data"):
            st.write(", ".join(d.missing))

    st.markdown(f"##### Breadth Matrix ({u.name})")
    out = a.view.reset_index()
    out["Date"] = out["Date"].dt.strftime("%Y-%m-%d")
    st.dataframe(out.round(4), width="stretch", hide_index=True, height=400)
    safe = re.sub(r"[^A-Za-z0-9]+", "_", u.name).strip("_")
    st.download_button("📥 Export Matrix (CSV)", out.to_csv(index=False).encode("utf-8"),
                       f"{safe}_breadth_{start_date}_{end_date}.csv", "text/csv")


def render_results(a, start_date, end_date):
    render_header(a)
    tabs = st.tabs(["**📊 Overview**", "**🧭 Participation**", "**⚡ Momentum**", "**〰 Oscillators**",
                    "**🏭 Sectors**", "**🧪 Signal Study**", "**🔎 Constituents**", "**📋 Data**"])
    renderers = [tab_overview, tab_participation, tab_momentum, tab_oscillators, tab_sectors, tab_study,
                 tab_constituents]
    for tab, fn in zip(tabs[:-1], renderers, strict=True):
        with tab:
            fn(a)
    with tabs[-1]:
        tab_data(a, start_date, end_date)


# ══════════════════════════════════════════════════════════════════════════════
# LANDING
# ══════════════════════════════════════════════════════════════════════════════

def landing_card(css: str, color_var: str, title: str, body: str, bullets: list[str]) -> str:
    items = "<br>".join(f"• {b}" for b in bullets)
    return f"""
    <div class='metric-card {css}' style='min-height: 300px;'>
        <h3 style='color: var({color_var}); margin-bottom: 1rem;'>{title}</h3>
        <p style='color: var(--text-muted); font-size: 0.9rem; line-height: 1.6;'>{body}</p>
        <p style='color: var(--text-secondary); font-size: 0.85rem; line-height: 1.7;'>{items}</p>
    </div>"""


def render_landing(index):
    st.markdown("""
    <div class="premium-header">
        <h1>MARKET BREADTH : Advance-Decline Intelligence</h1>
        <div class="tagline">Participation · Momentum · Signals · Evidence</div>
    </div>
    """, unsafe_allow_html=True)
    cards = [
        landing_card("success", "--success-green", "🧭 Structural Health",
                     "Is the move broad or narrow? Participation measured three ways and combined into one score.",
                     ["% above 20 / 50 / 200-DMA", "52-week new highs vs lows", "Sector participation rotation"]),
        landing_card("primary", "--primary-color", "⚡ Tactical Momentum",
                     "How stretched is breadth right now, and is it accelerating?",
                     ["Relative & Custom Breadth oscillators", "McClellan Oscillator / Summation",
                      "Up/down traded value & TRIN"]),
        landing_card("info", "--info-cyan", "🧪 Signals with Evidence",
                     "Every signal is tested against the benchmark's forward returns before you act on it.",
                     ["Zweig breadth thrust, washouts", "Price / participation divergences",
                      "Forward returns vs baseline, by regime"]),
    ]
    for col, html in zip(st.columns(3), cards, strict=True):
        col.markdown(html, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='info-box'>
        <h4>🚀 Getting Started</h4>
        <p style='color: var(--text-muted); line-height: 1.7;'>
            Open the sidebar, choose a <strong>Universe</strong> and <strong>Index</strong>
            (currently <i>{index}</i>), set the <strong>Display Window</strong> and how much history the
            <strong>Signal Study</strong> should use, then click <strong>◈ RUN ANALYSIS</strong>.
        </p>
    </div>
    """, unsafe_allow_html=True)


def main():
    kind, index, start_date, end_date, study_years, run_btn = render_sidebar()

    if run_btn:
        st.session_state.pop("analysis", None)
        if start_date > end_date:
            st.error("Start date must not be after End date.")
        else:
            a = run_pipeline(kind, index, start_date, end_date, study_years)
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
