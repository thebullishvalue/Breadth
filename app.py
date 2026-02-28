# -*- coding: utf-8 -*-
"""
MARKET BREADTH - Advance/Decline Intelligence | A Hemrek Capital Product
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unified ETF & Index breadth tracking with institutional-grade time series 
analysis, cumulative A/D lines, and real-time market snapshots.
Nirnay.py data fetching mechanism fully integrated (4 universes + live append)
"""

import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import time
import numpy as np
import plotly.graph_objects as go
import requests
import io
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="MARKET BREADTH | Advance-Decline Analytics",
    layout="wide",
    page_icon="🌊",
    initial_sidebar_state="collapsed"
)

VERSION = "v1.7.0 (Nirnay Data Engine Sync)"
PRODUCT_NAME = "Market Breadth"
COMPANY = "Hemrek Capital"

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
    
    .info-box { background: var(--secondary-background-color); border: 1px solid var(--border-color); border-left: 4px solid var(--primary-color); padding: 1.25rem; border-radius: 12px; margin: 0.5rem 0; box-shadow: 0 0 15px rgba(var(--primary-rgb), 0.08); }
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
# CONSTANTS & UNIVERSE LISTS
# ══════════════════════════════════════════════════════════════════════════════

INDIA_INDEX_LIST = [
    "NIFTY 50", "NIFTY NEXT 50", "NIFTY 100", "NIFTY 200", "NIFTY 500",
    "NIFTY MIDCAP 50", "NIFTY MIDCAP 100", "NIFTY SMLCAP 100", "NIFTY BANK",
    "NIFTY AUTO", "NIFTY FIN SERVICE", "NIFTY FMCG", "NIFTY IT",
    "NIFTY MEDIA", "NIFTY METAL", "NIFTY PHARMA"
]

US_INDEX_LIST = ["S&P 500", "DOW JONES", "NASDAQ 100"]

ANALYSIS_UNIVERSE_OPTIONS = ["India Indexes", "US Indexes", "Commodities", "Currency"]

BASE_URL = "https://www.niftyindices.com/IndexConstituent/"
INDEX_URL_MAP = {
    "NIFTY 50": f"{BASE_URL}ind_nifty50list.csv",
    "NIFTY NEXT 50": f"{BASE_URL}ind_niftynext50list.csv",
    "NIFTY 100": f"{BASE_URL}ind_nifty100list.csv",
    "NIFTY 200": f"{BASE_URL}ind_nifty200list.csv",
    "NIFTY 500": f"{BASE_URL}ind_nifty500list.csv",
    "NIFTY MIDCAP 50": f"{BASE_URL}ind_niftymidcap50list.csv",
    "NIFTY MIDCAP 100": f"{BASE_URL}ind_niftymidcap100list.csv",
    "NIFTY SMLCAP 100": f"{BASE_URL}ind_niftysmallcap100list.csv",
    "NIFTY BANK": f"{BASE_URL}ind_niftybanklist.csv",
    "NIFTY AUTO": f"{BASE_URL}ind_niftyautolist.csv",
    "NIFTY FIN SERVICE": f"{BASE_URL}ind_niftyfinancelist.csv",
    "NIFTY FMCG": f"{BASE_URL}ind_niftyfmcglist.csv",
    "NIFTY IT": f"{BASE_URL}ind_niftyitlist.csv",
    "NIFTY MEDIA": f"{BASE_URL}ind_niftymedialist.csv",
    "NIFTY METAL": f"{BASE_URL}ind_niftymetallist.csv",
    "NIFTY PHARMA": f"{BASE_URL}ind_niftypharmalist.csv"
}

INDIA_INDEX_WIKI_MAP = {
    "NIFTY 50": "https://en.wikipedia.org/wiki/NIFTY_50",
    "NIFTY NEXT 50": "https://en.wikipedia.org/wiki/NIFTY_Next_50",
    "NIFTY 500": "https://en.wikipedia.org/wiki/NIFTY_500",
}

DOW_JONES_TICKERS = [
    "AMZN", "AMGN", "AAPL", "BA", "CAT", "CSCO", "CVX", "GS", "HD", "HON",
    "IBM", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK", "MSFT", "NKE", "PG",
    "CRM", "SHW", "TRV", "UNH", "V", "VZ", "WMT", "DIS", "DOW", "NVDA"
]

FALLBACK_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS", "INFY.NS", 
    "ITC.NS", "SBIN.NS", "L&T.NS", "BAJFINANCE.NS", "KOTAKBANK.NS", "HINDUNILVR.NS", 
    "AXISBANK.NS", "MARUTI.NS", "SUNPHARMA.NS", "ULTRACEMCO.NS", "TATAMOTORS.NS"
]

COMMODITY_TICKERS = {
    "GC=F": "Gold", "SI=F": "Silver", "PL=F": "Platinum", "PA=F": "Palladium",
    "HG=F": "Copper", "CL=F": "Crude Oil WTI", "BZ=F": "Brent Crude",
    "NG=F": "Natural Gas", "RB=F": "Gasoline RBOB", "HO=F": "Heating Oil",
    "ZC=F": "Corn", "ZW=F": "Wheat", "ZS=F": "Soybeans", "ZM=F": "Soybean Meal",
    "ZL=F": "Soybean Oil", "CT=F": "Cotton", "KC=F": "Coffee", "SB=F": "Sugar",
    "CC=F": "Cocoa", "OJ=F": "Orange Juice", "LBS=F": "Lumber",
    "LE=F": "Live Cattle", "HE=F": "Lean Hogs", "GF=F": "Feeder Cattle",
}

CURRENCY_TICKERS = {
    "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY",
    "USDCHF=X": "USD/CHF", "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD",
    "NZDUSD=X": "NZD/USD", "USDINR=X": "USD/INR", "EURGBP=X": "EUR/GBP",
    "EURJPY=X": "EUR/JPY", "GBPJPY=X": "GBP/JPY", "AUDJPY=X": "AUD/JPY",
    "EURCHF=X": "EUR/CHF", "EURAUD=X": "EUR/AUD", "GBPCHF=X": "GBP/CHF",
    "GBPAUD=X": "GBP/AUD", "USDSGD=X": "USD/SGD", "USDHKD=X": "USD/HKD",
    "USDCNH=X": "USD/CNH", "USDZAR=X": "USD/ZAR", "USDMXN=X": "USD/MXN",
    "USDTRY=X": "USD/TRY", "USDBRL=X": "USD/BRL", "USDKRW=X": "USD/KRW",
}

# ══════════════════════════════════════════════════════════════════════════════
# DATA FETCH HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _fetch_india_index_from_wikipedia(index):
    """Fallback: Fetch Indian index constituents from Wikipedia"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    def _parse_wiki_table(url, min_count=10):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            tables = pd.read_html(io.StringIO(response.text))
            for tbl in tables:
                if 'Symbol' in tbl.columns:
                    symbols = tbl['Symbol'].dropna().astype(str).str.strip().tolist()
                    symbols = [s for s in symbols if s and len(s) <= 20 and s != 'nan']
                    if len(symbols) >= min_count:
                        return symbols
        except Exception:
            pass
        return None

    try:
        if index == "NIFTY 100":
            n50 = _parse_wiki_table(INDIA_INDEX_WIKI_MAP["NIFTY 50"], min_count=40)
            nn50 = _parse_wiki_table(INDIA_INDEX_WIKI_MAP["NIFTY NEXT 50"], min_count=40)
            if n50 and nn50:
                combined = list(dict.fromkeys(n50 + nn50))
                symbols_ns = [s + ".NS" for s in combined]
                return symbols_ns, f"⚠ Fetched {len(symbols_ns)} {index} constituents from Wikipedia"
            return None, "Wikipedia fallback failed for NIFTY 100"

        if index == "NIFTY 200":
            symbols = _parse_wiki_table(INDIA_INDEX_WIKI_MAP["NIFTY 500"], min_count=100)
            if symbols:
                symbols_200 = symbols[:200]
                symbols_ns = [s + ".NS" for s in symbols_200]
                return symbols_ns, f"⚠ Fetched {len(symbols_ns)} {index} constituents from Wikipedia"
            return None, "Wikipedia fallback failed for NIFTY 200"

        wiki_url = INDIA_INDEX_WIKI_MAP.get(index)
        if wiki_url:
            min_expected = {"NIFTY 50": 40, "NIFTY NEXT 50": 40, "NIFTY 500": 400}.get(index, 10)
            symbols = _parse_wiki_table(wiki_url, min_count=min_expected)
            if symbols:
                symbols_ns = [s + ".NS" for s in symbols]
                return symbols_ns, f"⚠ Fetched {len(symbols_ns)} {index} constituents from Wikipedia"
            return None, f"Wikipedia fallback: could not parse {index} table"

        return None, None
    except Exception as e:
        return None, f"Wikipedia fallback error: {e}"


@st.cache_data(ttl=3600, show_spinner=False)
def get_index_stock_list(index):
    """Fetch Indian index constituents from NSE with Wikipedia fallback"""
    if index in US_INDEX_LIST:
        return get_us_index_stock_list(index)

    url = INDEX_URL_MAP.get(index)
    if not url:
        return FALLBACK_TICKERS, f"Error: No URL for {index}. Using fallback tickers."

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        
        csv_file = io.StringIO(response.text)
        stock_df = pd.read_csv(csv_file)
        
        if 'Symbol' in stock_df.columns:
            symbols = stock_df['Symbol'].tolist()
            symbols_ns = [str(s) + ".NS" for s in symbols if s and str(s).strip()]
            return symbols_ns, f"Success: Fetched {len(symbols_ns)} constituents from NSE."
            
    except Exception:
        pass

    wiki_result, wiki_msg = _fetch_india_index_from_wikipedia(index)
    if wiki_result:
        return wiki_result, wiki_msg

    return FALLBACK_TICKERS, f"Error: Exchange and Wiki endpoints failed. Using top {len(FALLBACK_TICKERS)} liquid fallback constituents."


@st.cache_data(ttl=3600, show_spinner=False)
def get_us_index_stock_list(index):
    """Fetch US index constituents from Wikipedia with hardcoded fallback for Dow Jones"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        if index == "S&P 500":
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            tables = pd.read_html(io.StringIO(response.text))
            if tables:
                df = tables[0]
                if 'Symbol' in df.columns:
                    symbols = df['Symbol'].str.strip().str.replace('.', '-', regex=False).tolist()
                    symbols = [s for s in symbols if s and str(s).strip()]
                    return symbols, f"Success: Fetched {len(symbols)} S&P 500 constituents"
            return None, "Could not parse S&P 500 table"
            
        elif index == "DOW JONES":
            try:
                url = "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average"
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                tables = pd.read_html(io.StringIO(response.text))
                for tbl in tables:
                    for col in ['Symbol', 'Ticker', 'Ticker symbol']:
                        if col in tbl.columns:
                            symbols = tbl[col].str.strip().tolist()
                            symbols = [s for s in symbols if s and str(s).strip() and len(s) <= 5]
                            if 20 <= len(symbols) <= 35:
                                return symbols, f"Success: Fetched {len(symbols)} Dow Jones constituents"
            except Exception:
                pass
            return DOW_JONES_TICKERS.copy(), f"Success: Loaded {len(DOW_JONES_TICKERS)} Dow Jones constituents"
            
        elif index == "NASDAQ 100":
            url = "https://en.wikipedia.org/wiki/Nasdaq-100"
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            tables = pd.read_html(io.StringIO(response.text))
            for tbl in tables:
                if 'Ticker' in tbl.columns:
                    symbols = tbl['Ticker'].str.strip().str.replace('.', '-', regex=False).tolist()
                    symbols = [s for s in symbols if s and str(s).strip()]
                    if len(symbols) >= 90:
                        return symbols, f"Success: Fetched {len(symbols)} NASDAQ 100 constituents"
                elif 'Symbol' in tbl.columns:
                    symbols = tbl['Symbol'].str.strip().str.replace('.', '-', regex=False).tolist()
                    symbols = [s for s in symbols if s and str(s).strip()]
                    if len(symbols) >= 90:
                        return symbols, f"Success: Fetched {len(symbols)} NASDAQ 100 constituents"
            return None, "Could not parse NASDAQ 100 table"
        
        return None, f"Unknown US index: {index}"
        
    except Exception as e:
        return None, f"Error fetching {index}: {e}"


def get_commodity_list():
    tickers = list(COMMODITY_TICKERS.keys())
    return tickers, f"Success: Loaded {len(tickers)} commodity futures"


def get_currency_list():
    tickers = list(CURRENCY_TICKERS.keys())
    return tickers, f"Success: Loaded {len(tickers)} currency pairs"


# ══════════════════════════════════════════════════════════════════════════════
# MAIN DATA FETCH FUNCTION ── ported from nirnay.py
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300, show_spinner=False)
def fetch_market_data(stock_list, start_date, end_date):
    """Nirnay-style fetch: group_by ticker + live today append + extra buffer"""
    if end_date is None:
        end_date = datetime.date.today()
    
    download_end = end_date + datetime.timedelta(days=5)
    start_date_calc = end_date - datetime.timedelta(days=300 + 365)  # extra buffer like nirnay
    
    try:
        all_data = yf.download(
            stock_list,
            start=start_date_calc,
            end=download_end,
            progress=False,
            auto_adjust=True,
            group_by='ticker'
        )
        
        if all_data.empty:
            return None, "No data returned from Exchange."
        
        data_dict = {}
        for ticker in stock_list:
            try:
                if isinstance(all_data.columns, pd.MultiIndex):
                    ticker_df = all_data.xs(ticker, level=0, axis=1)
                else:
                    ticker_df = all_data.get(ticker, pd.DataFrame())
                if not ticker_df.empty and 'Close' in ticker_df.columns:
                    data_dict[ticker] = ticker_df[['Close']].copy()
            except Exception:
                pass
        
        # ── LIVE / TODAY APPEND LOGIC ───────────────────────────────────────
        if end_date == datetime.date.today() and data_dict:
            sample = next(iter(data_dict.values()))
            sample.index = pd.to_datetime(sample.index).normalize().tz_localize(None)
            has_today = any(idx.date() == datetime.date.today() for idx in sample.index)
            
            if not has_today:
                try:
                    live_data = yf.download(
                        list(data_dict.keys()),
                        period="1d",
                        progress=False,
                        auto_adjust=True,
                        group_by='ticker'
                    )
                    if not live_data.empty and isinstance(live_data.columns, pd.MultiIndex):
                        for ticker in list(data_dict.keys()):
                            try:
                                live_t = live_data.xs(ticker, level=0, axis=1)
                                if not live_t.empty and 'Close' in live_t:
                                    hist = data_dict[ticker]
                                    hist.index = pd.to_datetime(hist.index).normalize().tz_localize(None)
                                    live_t.index = pd.to_datetime(live_t.index).normalize().tz_localize(None)
                                    new_dates = live_t.index.difference(hist.index)
                                    if len(new_dates) > 0:
                                        data_dict[ticker] = pd.concat([hist, live_t.loc[new_dates][['Close']]])
                            except Exception:
                                pass
                except Exception:
                    pass
        
        # Build final close DataFrame
        if not data_dict:
            return None, "No valid data for any ticker."
        
        close_df = pd.DataFrame({t: data_dict[t]['Close'] for t in data_dict})
        close_df = close_df.sort_index().dropna(axis=1, how='all')
        
        return close_df, f"Success: Market matrix built for {len(close_df.columns)} assets (live append applied if needed)."
        
    except Exception as e:
        return None, f"Fatal Download Error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# BREADTH CALCULATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def compute_timeseries(close_df, start_ts, end_ts):
    close_df.index = pd.to_datetime(close_df.index).normalize().tz_localize(None)
    close_df = close_df.ffill(limit=2)
    
    pct_change_df = close_df.pct_change(fill_method=None)
    pct_change_df = pct_change_df.iloc[1:] 
    
    if pct_change_df.empty:
        return None, pd.DataFrame()
        
    advances = (pct_change_df > 0).sum(axis=1)
    declines = (pct_change_df < 0).sum(axis=1)
    unchanged = (pct_change_df == 0).sum(axis=1)
    total_traded = advances + declines + unchanged
    
    breadth_df = pd.DataFrame({
        'Date': pct_change_df.index,
        'Advances': advances.values,
        'Declines': declines.values,
        'Unchanged': unchanged.values,
        'Total': total_traded.values
    }).reset_index(drop=True)
    
    breadth_df = breadth_df[breadth_df['Total'] >= 10].copy()
    
    if breadth_df.empty:
        return None, pd.DataFrame()
        
    breadth_df['Net_Advances'] = breadth_df['Advances'] - breadth_df['Declines']
    
    breadth_df['AD_Ratio'] = np.where(
        breadth_df['Declines'] > 0, 
        breadth_df['Advances'] / breadth_df['Declines'], 
        breadth_df['Advances'].astype(float)
    )
    
    breadth_df['AD_Line'] = breadth_df['Net_Advances'].cumsum()
    breadth_df['ADR_MA10'] = breadth_df['AD_Ratio'].rolling(window=10, min_periods=1).mean()
    
    # Custom Breadth
    x_vals = breadth_df['AD_Ratio'] / (breadth_df['AD_Ratio'] + 1)
    x_ma10 = x_vals.rolling(window=10, min_periods=10).mean()
    
    breadth_vals = np.full(len(breadth_df), np.nan)
    first_valid = x_ma10.first_valid_index()
    
    if first_valid is not None:
        breadth_vals[first_valid] = x_ma10.loc[first_valid]
        C = 0.1 
        for i in range(first_valid + 1, len(breadth_df)):
            prev_y = breadth_vals[i-1]
            curr_x = x_vals.iloc[i]
            breadth_vals[i] = prev_y + C * (curr_x - prev_y)
            
    breadth_df['Custom_Breadth'] = breadth_vals
    
    # Relative Breadth
    cb = breadth_df['Custom_Breadth']
    ma2 = cb.rolling(window=2, min_periods=1).mean()
    ma3 = cb.rolling(window=3, min_periods=1).mean()
    ma5 = cb.rolling(window=5, min_periods=1).mean()
    ma8 = cb.rolling(window=8, min_periods=1).mean()
    ma13 = cb.rolling(window=13, min_periods=1).mean()
    ma21 = cb.rolling(window=21, min_periods=1).mean()
    
    Z = (ma2 + ma3 + ma5 + ma8 + ma13 + ma21) / 6.0
    breadth_df['Relative_Breadth'] = (Z + cb) / 2.0
    
    # Filter to user-selected timeframe
    view_mask = (breadth_df['Date'] >= start_ts) & (breadth_df['Date'] <= end_ts)
    final_breadth_df = breadth_df.loc[view_mask].copy().reset_index(drop=True)
    
    if final_breadth_df.empty:
        return None, pd.DataFrame()
        
    final_breadth_df['AD_Line'] = final_breadth_df['AD_Line'] - final_breadth_df['AD_Line'].iloc[0]
    
    last_date = final_breadth_df['Date'].iloc[-1]
    
    if last_date in pct_change_df.index:
        last_changes = pct_change_df.loc[last_date]
        last_prices = close_df.loc[last_date]
        
        movers_df = pd.DataFrame({
            'Symbol': [str(s).replace('.NS', '').replace('=X', '') for s in last_changes.index],
            'Price': last_prices.values,
            'Change_%': last_changes.values * 100
        })
        
        conditions = [movers_df['Change_%'] > 0, movers_df['Change_%'] < 0]
        movers_df['Status'] = np.select(conditions, ['Advance', 'Decline'], default='Unchanged')
    else:
        movers_df = pd.DataFrame()
        
    return final_breadth_df, movers_df


# ══════════════════════════════════════════════════════════════════════════════
# VISUALIZATION COMPONENTS
# ══════════════════════════════════════════════════════════════════════════════

def plot_relative_breadth(df):
    fig = go.Figure()
    
    mean_val = 0.46
    colors = ['#10b981' if v < 0.4 else '#ef4444' if v > 0.5 else '#888888' for v in df['Relative_Breadth']]
    
    fig.add_trace(go.Scatter(x=df['Date'], y=[mean_val]*len(df), line=dict(width=0), showlegend=False, hoverinfo='skip'))
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Relative_Breadth'].clip(lower=mean_val),
        fill='tonexty', fillcolor='rgba(239,68,68,0.15)',
        line=dict(width=0), showlegend=False, hoverinfo='skip'
    ))
    
    fig.add_trace(go.Scatter(x=df['Date'], y=[mean_val]*len(df), line=dict(width=0), showlegend=False, hoverinfo='skip'))
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Relative_Breadth'].clip(upper=mean_val),
        fill='tonexty', fillcolor='rgba(16,185,129,0.15)',
        line=dict(width=0), showlegend=False, hoverinfo='skip'
    ))
    
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Relative_Breadth'], mode='lines+markers', name='Relative Breadth',
        line=dict(color='#FFC300', width=2),
        marker=dict(size=6, color=colors, line=dict(width=0))
    ))
    
    fig.add_hline(y=0.5, line=dict(color='rgba(239,68,68,0.5)', width=1, dash='dash'))
    fig.add_hline(y=0.40, line=dict(color='rgba(16,185,129,0.5)', width=1, dash='dash'))
    fig.add_hline(y=mean_val, line=dict(color='rgba(255,255,255,0.2)', width=1))
    
    v_max = df['Relative_Breadth'].max()
    v_min = df['Relative_Breadth'].min()
    y_max = float(v_max + 0.05) if pd.notna(v_max) and v_max > 0.55 else 0.55
    y_min = float(v_min - 0.05) if pd.notna(v_min) and v_min < 0.35 else 0.35
    
    fig.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='#1A1A1A', height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showgrid=True, gridcolor='rgba(42,42,42,0.5)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(42,42,42,0.5)', title='Relative Breadth', range=[y_min, y_max]),
        font=dict(family='Inter', color='#EAEAEA'), hovermode='x unified'
    )
    return fig


def plot_custom_breadth(df):
    fig = go.Figure()
    
    mean_val = 0.46
    colors = ['#10b981' if v < 0.4 else '#ef4444' if v > 0.5 else '#888888' for v in df['Custom_Breadth']]
    
    fig.add_trace(go.Scatter(x=df['Date'], y=[mean_val]*len(df), line=dict(width=0), showlegend=False, hoverinfo='skip'))
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Custom_Breadth'].clip(lower=mean_val),
        fill='tonexty', fillcolor='rgba(239,68,68,0.15)',
        line=dict(width=0), showlegend=False, hoverinfo='skip'
    ))
    
    fig.add_trace(go.Scatter(x=df['Date'], y=[mean_val]*len(df), line=dict(width=0), showlegend=False, hoverinfo='skip'))
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Custom_Breadth'].clip(upper=mean_val),
        fill='tonexty', fillcolor='rgba(16,185,129,0.15)',
        line=dict(width=0), showlegend=False, hoverinfo='skip'
    ))
    
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Custom_Breadth'], mode='lines+markers', name='Custom Breadth',
        line=dict(color='#FFC300', width=2),
        marker=dict(size=6, color=colors, line=dict(width=0))
    ))
    
    fig.add_hline(y=0.5, line=dict(color='rgba(239,68,68,0.5)', width=1, dash='dash'))
    fig.add_hline(y=0.40, line=dict(color='rgba(16,185,129,0.5)', width=1, dash='dash'))
    fig.add_hline(y=mean_val, line=dict(color='rgba(255,255,255,0.2)', width=1))
    
    v_max = df['Custom_Breadth'].max()
    v_min = df['Custom_Breadth'].min()
    y_max = float(v_max + 0.05) if pd.notna(v_max) and v_max > 0.55 else 0.55
    y_min = float(v_min - 0.05) if pd.notna(v_min) and v_min < 0.35 else 0.35
    
    fig.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='#1A1A1A', height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showgrid=True, gridcolor='rgba(42,42,42,0.5)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(42,42,42,0.5)', title='Custom Breadth', range=[y_min, y_max]),
        font=dict(family='Inter', color='#EAEAEA'), hovermode='x unified'
    )
    return fig


def plot_ad_ratio(df):
    fig = go.Figure()
    
    mean_val = 1.0
    colors = ['#10b981' if v > 1.2 else '#ef4444' if v < 0.8 else '#888888' for v in df['AD_Ratio']]
    
    fig.add_trace(go.Scatter(x=df['Date'], y=[mean_val]*len(df), line=dict(width=0), showlegend=False, hoverinfo='skip'))
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['AD_Ratio'].clip(lower=mean_val),
        fill='tonexty', fillcolor='rgba(16,185,129,0.15)',
        line=dict(width=0), showlegend=False, hoverinfo='skip'
    ))
    
    fig.add_trace(go.Scatter(x=df['Date'], y=[mean_val]*len(df), line=dict(width=0), showlegend=False, hoverinfo='skip'))
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['AD_Ratio'].clip(upper=mean_val),
        fill='tonexty', fillcolor='rgba(239,68,68,0.15)',
        line=dict(width=0), showlegend=False, hoverinfo='skip'
    ))
    
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['AD_Ratio'], mode='lines+markers', name='Daily ADR',
        line=dict(color='#FFC300', width=2),
        marker=dict(size=6, color=colors, line=dict(width=0))
    ))
    
    fig.add_hline(y=mean_val, line=dict(color='rgba(255,255,255,0.2)', width=1))
    
    v_max = df['AD_Ratio'].max()
    v_min = df['AD_Ratio'].min()
    y_max = float(v_max + 0.1) if pd.notna(v_max) and v_max > 1.2 else 1.5
    y_min = float(v_min - 0.1) if pd.notna(v_min) and v_min < 0.8 else 0.5
    
    fig.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='#1A1A1A', height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showgrid=True, gridcolor='rgba(42,42,42,0.5)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(42,42,42,0.5)', title='A/D Ratio', range=[y_min, y_max]),
        showlegend=False,
        font=dict(family='Inter', color='#EAEAEA'), hovermode='x unified'
    )
    return fig


def plot_ad_line(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['AD_Line'], mode='lines', name='A/D Line',
        line=dict(color='#06b6d4', width=2), fill='tozeroy', fillcolor='rgba(6, 182, 212, 0.1)'
    ))
    fig.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='#1A1A1A', height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showgrid=True, gridcolor='rgba(42,42,42,0.5)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(42,42,42,0.5)', title='Cumulative Net Advances'),
        font=dict(family='Inter', color='#EAEAEA'), hovermode='x unified'
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

def main():
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0; margin-bottom: 1rem;">
            <div style="font-size: 1.75rem; font-weight: 800; color: #FFC300;">MARKET BREADTH</div>
            <div style="color: #888888; font-size: 0.75rem; margin-top: 0.25rem;">Advance-Decline Analytics</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        st.markdown('<div class="sidebar-title">🎯 Universe Selection</div>', unsafe_allow_html=True)
        spread_universe = st.selectbox(
            "Analysis Universe",
            ANALYSIS_UNIVERSE_OPTIONS,
            index=0,
            help="Choose between India Index Constituents, US Indexes, Commodities or Currencies."
        )
        
        if spread_universe == "India Indexes":
            spread_index = st.selectbox(
                "Select Index",
                INDIA_INDEX_LIST,
                index=INDIA_INDEX_LIST.index("NIFTY 500"),
                help="Select a specific NIFTY index for constituent analysis."
            )
        elif spread_universe == "US Indexes":
            spread_index = st.selectbox(
                "Select Index",
                US_INDEX_LIST,
                index=0,
                help="Select the US index for constituent analysis."
            )
        elif spread_universe == "Commodities":
            spread_index = "Commodities"
        else:
            spread_index = "Currencies"
            
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-title">📅 Date Range</div>', unsafe_allow_html=True)
        start_date = st.date_input("Start Date", datetime.date.today() - datetime.timedelta(days=100))
        end_date = st.date_input("End Date", datetime.date.today())
        
        st.markdown('<br>', unsafe_allow_html=True)
        run_btn = st.button("◈ RUN ANALYSIS", type="primary")
        
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class='info-box'>
            <p style='font-size: 0.8rem; margin: 0; color: var(--text-muted); line-height: 1.5;'>
                <strong>Version:</strong> {VERSION}<br>
                <strong>Engine:</strong> Vector + Nirnay Data Sync<br>
                <strong>Universe:</strong> {spread_universe} – {spread_index}
            </p>
        </div>
        """, unsafe_allow_html=True)

    if run_btn:
        if start_date >= end_date:
            st.error("Start date must be prior to End date.")
            return

        status_container = st.empty()
        with status_container.status("📡 Establishing Vector Engine Connection...", expanded=True) as terminal:
            st.write(f"➤ Requesting {spread_universe} universe ({spread_index})...")
            
            if spread_universe == "India Indexes":
                stock_list, msg = get_index_stock_list(spread_index)
            elif spread_universe == "US Indexes":
                stock_list, msg = get_us_index_stock_list(spread_index)
            elif spread_universe == "Commodities":
                stock_list, msg = get_commodity_list()
            else:
                stock_list, msg = get_currency_list()
                
            st.write(f"&nbsp;&nbsp;&nbsp;↳ {msg}")
            
            if not stock_list:
                terminal.update(label="❌ Universe Error", state="error")
                st.error("Could not obtain ticker list.")
                return
            
            st.write(f"➤ Connecting to Exchange Data ({len(stock_list)} assets)...")
            fetch_start = end_date - datetime.timedelta(days=300) 
            
            close_df, dl_msg = fetch_market_data(stock_list, fetch_start, end_date)
            
            if close_df is None:
                terminal.update(label="❌ Connection Failed", state="error")
                st.error(dl_msg)
                return
            st.write(f"&nbsp;&nbsp;&nbsp;↳ {dl_msg}")
            
            st.write("➤ Processing Vectorized Algorithms...")
            
            start_ts = pd.Timestamp(start_date)
            end_ts = pd.Timestamp(end_date)
            breadth_df, movers_df = compute_timeseries(close_df, start_ts, end_ts)
            
            if breadth_df is None or breadth_df.empty:
                terminal.update(label="❌ Algorithm Error", state="error")
                st.error("Insufficient market data for the selected timeframe. Could be a weekend or holiday.")
                return
                
        status_container.empty()

        # ── DISPLAY RESULTS ──────────────────────────────────────────────────────
        last_date = breadth_df['Date'].iloc[-1].strftime("%d %b %Y")
        last_row = breadth_df.iloc[-1]
        
        adr = last_row['AD_Ratio']
        if adr > 1.2: sentiment, s_color = "STRONG BULLISH", "success"
        elif adr > 1.0: sentiment, s_color = "BULLISH", "success"
        elif adr < 0.8: sentiment, s_color = "STRONG BEARISH", "danger"
        elif adr < 1.0: sentiment, s_color = "BEARISH", "danger"
        else: sentiment, s_color = "NEUTRAL", "neutral"
        
        st.markdown(f"### Breadth Analysis: {spread_index} ({spread_universe})")
        
        c_date, c1, c2, c3, c4 = st.columns(5)
        with c_date: 
            st.markdown(f'<div class="metric-card neutral"><h4>Snapshot</h4><h2 style="font-size: 1.5rem;">{last_date}</h2><div class="sub-metric">Trading Day</div></div>', unsafe_allow_html=True)
        with c1: 
            st.markdown(f'<div class="metric-card {s_color}"><h4>A/D Ratio</h4><h2 style="font-size: 1.6rem;">{adr:.2f}</h2><div class="sub-metric">{sentiment}</div></div>', unsafe_allow_html=True)
        with c2: 
            st.markdown(f'<div class="metric-card success"><h4>Advances</h4><h2 style="font-size: 1.6rem;">{last_row["Advances"]}</h2><div class="sub-metric">Stocks Gaining</div></div>', unsafe_allow_html=True)
        with c3: 
            st.markdown(f'<div class="metric-card danger"><h4>Declines</h4><h2 style="font-size: 1.6rem;">{last_row["Declines"]}</h2><div class="sub-metric">Stocks Falling</div></div>', unsafe_allow_html=True)
        
        net = last_row["Net_Advances"]
        n_color = "success" if net > 0 else "danger"
        with c4: 
            st.markdown(f'<div class="metric-card {n_color}"><h4>Net Advances</h4><h2 style="font-size: 1.6rem;">{net:+}</h2><div class="sub-metric">Breadth Momentum</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["**📈 Time Series Analytics**", "**📋 Raw Data Matrix**"])
        
        with tab1:
            st.markdown("##### Relative Breadth Oscillator")
            st.markdown('<p style="color: #888888; font-size: 0.85rem;">Fibonacci Sequence MA Smoothing. Green = Oversold | Red = Overbought</p>', unsafe_allow_html=True)
            st.plotly_chart(plot_relative_breadth(breadth_df), use_container_width=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### Custom Breadth Oscillator")
            st.markdown('<p style="color: #888888; font-size: 0.85rem;">EMA Smoothed Signal. Green = Oversold | Red = Overbought</p>', unsafe_allow_html=True)
            st.plotly_chart(plot_custom_breadth(breadth_df), use_container_width=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### Advance/Decline Ratio (ADR) Oscillator")
            st.markdown('<p style="color: #888888; font-size: 0.85rem;">Raw ADR Metric. Green = Bullish Skew | Red = Bearish Skew</p>', unsafe_allow_html=True)
            st.plotly_chart(plot_ad_ratio(breadth_df), use_container_width=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### Cumulative Advance/Decline Line (ADL)")
            st.markdown('<p style="color: #888888; font-size: 0.85rem;">Summation of net advancing stocks to track underlying market momentum.</p>', unsafe_allow_html=True)
            st.plotly_chart(plot_ad_line(breadth_df), use_container_width=True)

        with tab2:
            st.markdown(f"##### Historical Breadth Matrix ({spread_index})")
            display_df = breadth_df.copy()
            display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
            display_df['AD_Ratio'] = display_df['AD_Ratio'].round(3)
            display_df['ADR_MA10'] = display_df['ADR_MA10'].round(3)
            display_df['Custom_Breadth'] = display_df['Custom_Breadth'].round(3)
            display_df['Relative_Breadth'] = display_df['Relative_Breadth'].round(3)
            display_df.columns = ['Date', 'Advances', 'Declines', 'Unchanged', 'Total', 'Net Advances', 'A/D Ratio', 'A/D Line', 'ADR MA (10)', 'Custom Breadth', 'Relative Breadth']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
            
            csv_data = breadth_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Export Matrix (CSV)", csv_data, f"{spread_index.replace(' ', '_')}_breadth_{start_date}_{end_date}.csv", "text/csv")

    else:
        # Pre-Run Landing Page
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
                    • > 1.2 : Strong Bullish<br>
                    • < 0.8 : Strong Bearish<br>
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
                    Apply breadth analysis to major Indian/US indexes, commodities or currencies.
                </p>
                <br>
                <p style='color: var(--text-secondary); font-size: 0.85rem;'>
                    <strong>Current Target:</strong> {spread_index}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class='info-box'>
            <h4>🚀 Getting Started</h4>
            <p style='color: var(--text-muted); line-height: 1.7;'>
                Open the sidebar, choose your target <strong>Universe</strong> and <strong>Index/Symbol group</strong> (currently <i>{spread_index}</i>), configure the <strong>Date Range</strong>, and click <strong>◈ RUN ANALYSIS</strong>. 
                The system fetches constituents (or futures/forex pairs), downloads prices (with live today append), and computes breadth metrics.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    ist_time = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d %H:%M:%S IST")
    st.caption(f"© 2026 {COMPANY} | {PRODUCT_NAME} {VERSION} | {ist_time}")

if __name__ == "__main__":
    main()