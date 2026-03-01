# MARKET BREADTH

**Advance-Decline Intelligence | Hemrek Capital**

A quantitative breadth analytics system that computes institutional-grade advance/decline metrics, custom EMA-smoothed breadth oscillators, and Fibonacci-sequence relative breadth signals across Indian indexes, US indexes, commodities, and currencies.

Built with Streamlit. Powered by yfinance.

---

## Core Indicators

### 1. Advance/Decline Ratio (ADR)

Raw breadth metric. For each trading day across the selected universe:

```
AD_Ratio = Advances / Declines
```

Sentiment thresholds: > 1.2 Strong Bullish, > 1.0 Bullish, < 1.0 Bearish, < 0.8 Strong Bearish.

A 10-day SMA of the AD Ratio is also computed for trend smoothing.

### 2. Cumulative A/D Line

Running sum of net advances (Advances − Declines) across the selected window. Used for divergence detection: index rising while ADL falls signals weakening participation, and vice versa.

### 3. Custom Breadth Oscillator

An EMA-smoothed signal derived from the normalized advance ratio. The computation pipeline:

```
Step 1:  x = AD_Ratio / (AD_Ratio + 1)          # equivalent to A/(A+D), bounded [0, 1]
Step 2:  Seed = SMA(x, 10)                       # first valid 10-period simple average
Step 3:  BREADTH(t) = BREADTH(t-1) + C × (x(t) - BREADTH(t-1))
```

Where `C = 2 / (10 + 1) ≈ 0.18182` is the standard EMA smoothing constant for a 10-period window.

Zone interpretation: below 0.40 is oversold (green), above 0.50 is overbought (red).

### 4. Relative Breadth Oscillator

A multi-timeframe smoothing of the Custom Breadth signal using Fibonacci-sequence moving averages:

```
Step 1:  Compute SMAs of Custom Breadth at periods: 2, 3, 5, 8, 13, 21
Step 2:  Z = average of the six Fibonacci MAs
Step 3:  REL_BREADTH = (Z + Custom_Breadth) / 2
```

This produces a slower, more stable oscillator that filters out single-day noise while preserving regime shifts. Same 0.40/0.50 oversold/overbought thresholds apply.

---

## Supported Universes

| Universe | Indexes / Assets |
|----------|-----------------|
| **India** | NIFTY 50, NIFTY NEXT 50, NIFTY 100, NIFTY 200, NIFTY 500, NIFTY MIDCAP 50/100, NIFTY SMLCAP 100, NIFTY BANK, AUTO, FIN SERVICE, FMCG, IT, MEDIA, METAL, PHARMA |
| **US** | S&P 500, DOW JONES, NASDAQ 100 |
| **Commodities** | 24 futures — Gold, Silver, Crude Oil WTI/Brent, Natural Gas, Copper, Corn, Wheat, Soybeans, Coffee, Cotton, and more |
| **Currencies** | 24 FX pairs — EUR/USD, GBP/USD, USD/JPY, USD/INR, and more |

Constituent lists are fetched live from NSE India and Wikipedia, with hardcoded fallbacks for resilience.

---

## Data Pipeline

```
NSE CSV / Wikipedia Scrape / Hardcoded Tickers
                    │
                    ▼
          yfinance Download
       (300-day lookback window)
                    │
                    ▼
        Live Intraday Append
     (if end_date is today and
      today's bar is missing)
                    │
                    ▼
       Close Matrix Assembly
      (forward-fill, min 10 stocks)
                    │
                    ▼
        Pct Change → A/D/U Count
                    │
                    ▼
    ADR, ADL, Custom Breadth,
    Relative Breadth Computation
                    │
                    ▼
     Date Window Filter → Display
```

Data is cached with a 5-minute TTL for price data and 1-hour TTL for constituent lists.

---

## Dashboard Layout

**Sidebar** — Universe selection (India / US / Commodities / Currency), index picker, date range, and the RUN ANALYSIS trigger.

**Metric Cards** — Snapshot date, A/D Ratio with sentiment label, Advances count, Declines count, and Net Advances with directional coloring.

**Time Series Analytics Tab:**
- Relative Breadth Oscillator — bi-color gradient fill with Fibonacci MA smoothing
- Custom Breadth Oscillator — EMA-smoothed signal with oversold/overbought zones
- A/D Ratio Oscillator — raw daily ADR with bullish/bearish gradient
- Cumulative A/D Line — area chart of net advance accumulation

**Raw Data Matrix Tab** — Full historical breadth table with CSV export.

All charts use Plotly with the Hemrek dark theme (background `#0F0F0F`, accent `#FFC300`, green `#10b981`, red `#ef4444`).

---

## Installation & Usage

### Requirements

- Python 3.9+
- Dependencies listed in `requirements.txt`

### Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

### Dependencies

```
streamlit >= 1.28.0
pandas >= 2.0.0
numpy >= 1.24.0
yfinance >= 0.2.31
plotly >= 5.18.0
requests >= 2.31.0
lxml >= 4.9.0
beautifulsoup4 >= 4.12.0
```

---

## Aarambh Spreadsheet Correspondence

The system replicates the computations from the Aarambh master spreadsheet:

| Spreadsheet Column | App Column | Formula |
|---|---|---|
| `A/(A+D)` (Col C) | Derived internally | `AD_Ratio / (AD_Ratio + 1)` |
| `BREADTH` (Col J) | `Custom_Breadth` | EMA of A/(A+D) with smoothing constant `2/(10+1)` |
| 2D–21D MAs (Cols K–P) | Intermediate | Fibonacci-period SMAs of Custom Breadth |
| Avg of MAs (Col Q) | Z variable | `mean(MA2, MA3, MA5, MA8, MA13, MA21)` |
| `REL_BREADTH` (Col R) | `Relative_Breadth` | `(Z + Custom_Breadth) / 2` |

---

## Version

v1.7.1 (2026) — Streamlit width fix, status clarity improvements, unified ETF and index breadth tracking.

---

*© 2026 Hemrek Capital*
