"""
MARKET BREADTH - Advance/Decline Intelligence | A Hemrek Capital Product
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Streamlit front-end. Computation lives in ``engine.py``; charts in ``charts.py``.
"""

import datetime
import re

import pandas as pd
import streamlit as st

import charts
import engine

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="MARKET BREADTH | Advance-Decline Analytics",
    layout="wide",
    page_icon="🌊",
    initial_sidebar_state="collapsed",
)

VERSION = "v1.9.0"
PRODUCT_NAME = "Market Breadth"
COMPANY = "Hemrek Capital"
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

# ══════════════════════════════════════════════════════════════════════════════
# PRAGYAM/NIRNAY DESIGN SYSTEM CSS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    :root {
        --primary-color: #FFC300;
        --primary-rgb: 255, 195, 0;
        --background-color: #0F0F0F;
        --secondary-background-color: #1A1A1A;
        --bg-card: #1A1A1A;
        --bg-elevated: #2A2A2A;
        --text-primary: #EAEAEA;
        --text-secondary: #EAEAEA;
        --text-muted: #888888;
        --border-color: #2A2A2A;
        --border-light: #3A3A3A;
        --success-green: #10b981;
        --danger-red: #ef4444;
        --warning-amber: #f59e0b;
        --info-cyan: #06b6d4;
        --neutral: #888888;
    }

    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    .main, [data-testid="stSidebar"] { background-color: var(--background-color); color: var(--text-primary); }
    .stApp > header { background-color: transparent; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    .block-container { padding-top: 3.5rem; max-width: 95%; padding-left: 2rem; padding-right: 2rem; }

    /* Sidebar toggle button - always visible */
    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        background-color: var(--secondary-background-color) !important;
        border: 2px solid var(--primary-color) !important;
        border-radius: 8px !important;
        padding: 10px !important;
        margin: 12px !important;
        box-shadow: 0 0 15px rgba(var(--primary-rgb), 0.4) !important;
        z-index: 999999 !important;
        position: fixed !important;
        top: 14px !important;
        left: 14px !important;
        width: 40px !important;
        height: 40px !important;
        align-items: center !important;
        justify-content: center !important;
    }

    [data-testid="collapsedControl"]:hover {
        background-color: rgba(var(--primary-rgb), 0.2) !important;
        box-shadow: 0 0 20px rgba(var(--primary-rgb), 0.6) !important;
        transform: scale(1.05);
    }

    [data-testid="collapsedControl"] svg {
        stroke: var(--primary-color) !important;
        width: 20px !important;
        height: 20px !important;
    }

    [data-testid="stSidebar"] button[kind="header"] {
        background-color: transparent !important;
        border: none !important;
    }

    [data-testid="stSidebar"] button[kind="header"] svg {
        stroke: var(--primary-color) !important;
    }

    button[kind="header"] { z-index: 999999 !important; }

    .premium-header {
        background: var(--secondary-background-color);
        padding: 1.25rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 0 20px rgba(var(--primary-rgb), 0.1);
        border: 1px solid var(--border-color);
        position: relative;
        overflow: hidden;
        margin-top: 1rem;
    }

    .premium-header::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: radial-gradient(circle at 20% 50%, rgba(var(--primary-rgb),0.08) 0%, transparent 50%);
        pointer-events: none;
    }

    .premium-header h1 { margin: 0; font-size: 2rem; font-weight: 700; color: var(--text-primary); letter-spacing: -0.50px; position: relative; }
    .premium-header .tagline { color: var(--text-muted); font-size: 0.9rem; margin-top: 0.25rem; font-weight: 400; position: relative; }

    .metric-card {
        background-color: var(--bg-card);
        padding: 1.25rem;
        border-radius: 12px;
        border: 1px solid var(--border-color);
        box-shadow: 0 0 15px rgba(var(--primary-rgb), 0.08);
        margin-bottom: 0.5rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }

    .metric-card:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(0,0,0,0.3); border-color: var(--border-light); }
    .metric-card h4 { color: var(--text-muted); font-size: 0.75rem; margin-bottom: 0.5rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
    .metric-card h2 { color: var(--text-primary); font-size: 1.75rem; font-weight: 700; margin: 0; line-height: 1; }
    .metric-card .sub-metric { font-size: 0.75rem; color: var(--text-muted); margin-top: 0.5rem; font-weight: 500; }
    .metric-card.success h2 { color: var(--success-green); }
    .metric-card.danger h2 { color: var(--danger-red); }
    .metric-card.warning h2 { color: var(--warning-amber); }
    .metric-card.info h2 { color: var(--info-cyan); }
    .metric-card.neutral h2 { color: var(--neutral); }
    .metric-card.primary h2 { color: var(--primary-color); }

    .signal-card {
        background-color: var(--bg-card);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid var(--border-color);
        box-shadow: 0 0 15px rgba(var(--primary-rgb), 0.08);
        margin-bottom: 1rem;
        position: relative;
        overflow: hidden;
    }

    .signal-card::before { content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%; }
    .signal-card.buy::before { background: var(--success-green); }
    .signal-card.sell::before { background: var(--danger-red); }

    .info-box { background: var(--secondary-background-color); border: 1px solid var(--border-color); border-left: 0px solid var(--primary-color); padding: 1.25rem; border-radius: 12px; margin: 0.5rem 0; box-shadow: 0 0 15px rgba(var(--primary-rgb), 0.08); }
    .info-box h4 { color: var(--primary-color); margin: 0 0 0.5rem 0; font-size: 1rem; font-weight: 700; }
    .info-box p { color: var(--text-muted); margin: 0; font-size: 0.9rem; line-height: 1.6; }

    .stButton>button { border: 2px solid var(--primary-color); background: transparent; color: var(--primary-color); font-weight: 700; border-radius: 12px; padding: 0.75rem 2rem; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); text-transform: uppercase; letter-spacing: 0.5px; width: 100%; }
    .stButton>button:hover { box-shadow: 0 0 25px rgba(var(--primary-rgb), 0.6); background: var(--primary-color); color: #1A1A1A; transform: translateY(-2px); }
    .stButton>button:active { transform: translateY(0); }

    .stTabs [data-baseweb="tab-list"] { gap: 24px; background: transparent; }
    .stTabs [data-baseweb="tab"] { color: var(--text-muted); border-bottom: 2px solid transparent; transition: color 0.3s, border-bottom 0.3s; background: transparent; font-weight: 600; }
    .stTabs [aria-selected="true"] { color: var(--primary-color); border-bottom: 2px solid var(--primary-color); background: transparent !important; }

    .stPlotlyChart { border-radius: 12px; background-color: var(--secondary-background-color); padding: 10px; border: 1px solid var(--border-color); box-shadow: 0 0 25px rgba(var(--primary-rgb), 0.1); margin-bottom: 1.5rem; }
    .stDataFrame { border-radius: 12px; background-color: var(--secondary-background-color); border: 1px solid var(--border-color); }
    .section-divider { height: 1px; background: linear-gradient(90deg, transparent 0%, var(--border-color) 50%, transparent 100%); margin: 1.5rem 0; }

    .sidebar-title { font-size: 0.75rem; font-weight: 700; color: var(--primary-color); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.75rem; }

    [data-testid="stSidebar"] { background: var(--secondary-background-color); border-right: 1px solid var(--border-color); }

    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: var(--background-color); }
    ::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--border-light); }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# CACHED DATA ACCESS
# Failures raise inside the cached functions so they are never cached.
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner=False)
def load_constituents(universe: str, index: str):
    if universe == "India Indexes":
        return engine.get_india_constituents(index)
    if universe == "US Indexes":
        return engine.get_us_constituents(index)
    if universe == "Commodities":
        return engine.get_commodity_list()
    return engine.get_currency_list()


@st.cache_data(ttl=300, show_spinner=False)
def load_close_matrix(tickers: tuple, start_date: datetime.date, end_date: datetime.date):
    return engine.download_close_matrix(list(tickers), start_date, end_date)


def metric_card(title: str, value: str, sub: str, css: str, size: str = "1.6rem") -> str:
    return (f'<div class="metric-card {css}"><h4>{title}</h4>'
            f'<h2 style="font-size: {size};">{value}</h2><div class="sub-metric">{sub}</div></div>')


def chart_section(title: str, caption: str, fig) -> None:
    st.markdown(f"##### {title}")
    st.markdown(f'<p style="color: #888888; font-size: 0.85rem;">{caption}</p>', unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch")
    st.markdown("<br>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
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
        universe = st.selectbox(
            "Analysis Universe", engine.ANALYSIS_UNIVERSE_OPTIONS, index=0,
            help="Choose between India Index Constituents, US Indexes, Commodities or Currencies.",
        )
        if universe == "India Indexes":
            index = st.selectbox("Select Index", engine.INDIA_INDEX_LIST,
                                 index=engine.INDIA_INDEX_LIST.index("NIFTY 500"),
                                 help="Select a specific NIFTY index for constituent analysis.")
        elif universe == "US Indexes":
            index = st.selectbox("Select Index", engine.US_INDEX_LIST, index=0,
                                 help="Select the US index for constituent analysis.")
        elif universe == "Commodities":
            index = "Commodities"
        else:
            index = "Currencies"

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-title">📅 Date Range</div>', unsafe_allow_html=True)
        start_date = st.date_input("Start Date", today - datetime.timedelta(days=100), max_value=today)
        end_date = st.date_input("End Date", today, max_value=today)

        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("◈ RUN ANALYSIS", type="primary")

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class='info-box'>
            <p style='font-size: 0.8rem; margin: 0; color: var(--text-muted); line-height: 1.5;'>
                <strong>Version:</strong> {VERSION}<br>
                <strong>Data:</strong> Yahoo Finance · NSE · Wikipedia<br>
                <strong>Universe:</strong> {universe} – {index}
            </p>
        </div>
        """, unsafe_allow_html=True)
    return universe, index, start_date, end_date, run_btn


def run_pipeline(universe, index, start_date, end_date):
    """Fetch + compute inside a status panel. Returns (breadth_df, movers_df) or None."""
    status_container = st.empty()
    with status_container.status("📡 Fetching market data...", expanded=True) as terminal:
        terminal.write(f"➤ Requesting {universe} universe ({index})...")
        try:
            tickers, msg, is_fallback = load_constituents(universe, index)
        except Exception as e:
            terminal.update(label="❌ Constituent fetch failed", state="error")
            st.error(f"Could not obtain constituents for {index}: {e}")
            return None
        terminal.write(f"&nbsp;&nbsp;&nbsp;↳ {msg}")
        if is_fallback:
            terminal.warning("Built-in fallback tickers in use — results do not represent the selected index.")

        terminal.write(f"➤ Downloading price data ({len(tickers)} symbols)...")
        try:
            close_df, dl_msg = load_close_matrix(tuple(tickers), start_date, end_date)
        except Exception as e:
            terminal.update(label="❌ Price download failed", state="error")
            st.error(f"Price download failed: {e}")
            return None
        terminal.write(f"&nbsp;&nbsp;&nbsp;↳ {dl_msg}")
        missing = len(tickers) - close_df.shape[1]
        if missing > 0:
            terminal.write(f"&nbsp;&nbsp;&nbsp;↳ {missing} symbol(s) returned no data and were skipped")
        if close_df.shape[1] < 20:
            terminal.warning(f"Only {close_df.shape[1]} assets returned usable data — results may be noisy.")

        terminal.write("➤ Computing breadth indicators...")
        breadth_df, movers_df = engine.compute_timeseries(
            close_df, pd.Timestamp(start_date), pd.Timestamp(end_date))
        if breadth_df is None or breadth_df.empty:
            terminal.update(label="❌ No sessions in range", state="error")
            st.error("No trading sessions with sufficient coverage in the selected range "
                     "(weekend, holiday, or data not yet available).")
            return None
    status_container.empty()
    return breadth_df, movers_df


def render_results(universe, index, start_date, end_date, breadth_df, movers_df):
    unit = "Stocks" if universe in ("India Indexes", "US Indexes") else "Assets"
    last_row = breadth_df.iloc[-1]
    last_date = last_row["Date"].strftime("%d %b %Y")
    adr = float(last_row["AD_Ratio"])
    sentiment, s_color = engine.classify_adr(adr)
    net = int(last_row["Net_Advances"])
    n_color = "success" if net > 0 else "danger" if net < 0 else "neutral"

    st.markdown(f"### Breadth Analysis: {index}")
    cols = st.columns(5)
    cards = [
        metric_card("Snapshot", last_date, "Trading Day", "neutral", "1.5rem"),
        metric_card("A/D Ratio", f"{adr:.2f}", sentiment, s_color),
        metric_card("Advances", f"{int(last_row['Advances'])}", f"{unit} Gaining", "success"),
        metric_card("Declines", f"{int(last_row['Declines'])}", f"{unit} Falling", "danger"),
        metric_card("Net Advances", f"{net:+d}", "Breadth Momentum", n_color),
    ]
    for col, html in zip(cols, cards, strict=True):
        col.markdown(html, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["**📈 Time Series Analytics**", "**📋 Raw Data Matrix**",
                                "**🔎 Last Session Movers**"])

    with tab1:
        chart_section("Relative Breadth Oscillator",
                      "Fibonacci Sequence MA Smoothing. Green = Oversold | Red = Overbought",
                      charts.plot_relative_breadth(breadth_df))
        chart_section("Relative A/D Ratio",
                      "Multi-timeframe ADR momentum. Blends daily change with 2/3/5-day smoothed composites. "
                      "Green = Positive Momentum | Red = Negative Momentum",
                      charts.plot_rel_ad_ratio(breadth_df))
        chart_section("Custom Breadth Oscillator",
                      "EMA Smoothed Signal. Green = Oversold | Red = Overbought",
                      charts.plot_custom_breadth(breadth_df))
        chart_section("Advance/Decline Ratio (ADR) Oscillator",
                      "Raw ADR Metric. Green = Bullish Skew | Red = Bearish Skew",
                      charts.plot_ad_ratio(breadth_df))
        chart_section("Cumulative Advance/Decline Line (ADL)",
                      "Summation of net advancing constituents from the start of the selected window.",
                      charts.plot_ad_line(breadth_df))

    with tab2:
        st.markdown(f"##### Historical Breadth Matrix ({index})")
        display_df = breadth_df.copy()
        display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
        display_df = display_df.round({"AD_Ratio": 3, "ADR_MA10": 3, "Custom_Breadth": 3,
                                       "Relative_Breadth": 3, "Rel_AD_Ratio": 4})
        display_df = display_df.rename(columns={
            "Net_Advances": "Net Advances", "AD_Ratio": "A/D Ratio", "AD_Line": "A/D Line",
            "ADR_MA10": "ADR MA (10)", "Custom_Breadth": "Custom Breadth",
            "Relative_Breadth": "Relative Breadth", "Rel_AD_Ratio": "Rel A/D Ratio",
        })
        st.dataframe(display_df, width="stretch", hide_index=True, height=400)

        export = breadth_df.copy()
        export["Date"] = export["Date"].dt.strftime("%Y-%m-%d")
        safe_name = re.sub(r"[^A-Za-z0-9]+", "_", index).strip("_")
        st.download_button("📥 Export Matrix (CSV)", export.to_csv(index=False).encode("utf-8"),
                           f"{safe_name}_breadth_{start_date}_{end_date}.csv", "text/csv")

    with tab3:
        st.markdown(f"##### Constituent Moves on {last_date}")
        if movers_df.empty:
            st.info("Per-asset moves are unavailable for this session.")
        else:
            show = movers_df.copy()
            if not show["Name"].astype(bool).any():
                show = show.drop(columns="Name")
            st.dataframe(
                show, width="stretch", hide_index=True, height=400,
                column_config={
                    "Price": st.column_config.NumberColumn(format="%.4f"),
                    "Change_%": st.column_config.NumberColumn("Change %", format="%+.2f%%"),
                },
            )


def render_landing(index):
    st.markdown("""
    <div class="premium-header">
        <h1>MARKET BREADTH : Advance-Decline Intelligence</h1>
        <div class="tagline">Quantitative Breadth + Trend System</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class='metric-card success' style='min-height: 280px;'>
            <h3 style='color: var(--success-green); margin-bottom: 1rem;'>📈 Advance/Decline Ratio</h3>
            <p style='color: var(--text-muted); font-size: 0.9rem; line-height: 1.6;'>
                Measures market breadth by dividing advancing stocks by declining stocks.
            </p>
            <br>
            <p style='color: var(--text-secondary); font-size: 0.85rem;'>
                <strong>Interpretation:</strong><br>
                • &gt; 1.2 : Strong Bullish<br>
                • &lt; 0.8 : Strong Bearish<br>
            </p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class='metric-card primary' style='min-height: 280px;'>
            <h3 style='color: var(--primary-color); margin-bottom: 1rem;'>🌊 A/D Line (ADL)</h3>
            <p style='color: var(--text-muted); font-size: 0.9rem; line-height: 1.6;'>
                A cumulative tracking of Net Advances (Advances - Declines). Used to confirm underlying trends.
            </p>
            <br>
            <p style='color: var(--text-secondary); font-size: 0.85rem;'>
                <strong>Divergence Detection:</strong><br>
                • Index up, ADL down: Weakening trend<br>
                • Index down, ADL up: Underlying strength<br>
            </p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class='metric-card info' style='min-height: 280px;'>
            <h3 style='color: var(--info-cyan); margin-bottom: 1rem;'>🎯 Universe Selection</h3>
            <p style='color: var(--text-muted); font-size: 0.9rem; line-height: 1.6;'>
                Apply breadth analysis to any major Indian or US Index, commodity futures, or currency pairs.
            </p>
            <br>
            <p style='color: var(--text-secondary); font-size: 0.85rem;'>
                <strong>Current Target:</strong> {index}
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='info-box'>
        <h4>🚀 Getting Started</h4>
        <p style='color: var(--text-muted); line-height: 1.7;'>
            Open the sidebar on the left, choose your target <strong>Universe</strong> and <strong>Index</strong>
            (currently <i>{index}</i>), configure the <strong>Date Range</strong>, and click
            <strong>◈ RUN ANALYSIS</strong>. The system will automatically compute the Time Series Matrix,
            Cumulative ADL, and bi-color gradient Breadth Oscillators.
        </p>
    </div>
    """, unsafe_allow_html=True)


def main():
    universe, index, start_date, end_date, run_btn = render_sidebar()

    if run_btn:
        st.session_state.pop("result", None)
        if start_date > end_date:
            st.error("Start date must not be after End date.")
        else:
            result = run_pipeline(universe, index, start_date, end_date)
            if result is not None:
                # Keep results across reruns (e.g. the CSV download button triggers one).
                st.session_state["result"] = (universe, index, start_date, end_date, *result)

    if "result" in st.session_state:
        render_results(*st.session_state["result"])
    elif not run_btn:
        render_landing(index)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    ist_time = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    st.caption(f"© 2026 {COMPANY} | {PRODUCT_NAME} {VERSION} | {ist_time}")


if __name__ == "__main__":
    main()
