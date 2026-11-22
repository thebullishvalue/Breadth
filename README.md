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

Running sum of net advances (Advances − Declines), starting from the first session of the selected window. Used for divergence detection: index rising while ADL falls signals weakening participation, and vice versa.

### 3. Custom Breadth Oscillator

An EMA-smoothed signal derived from the normalized advance ratio. The computation pipeline:

```
Step 1:  x = A / (A + D)                         # bounded [0, 1]; 0.5 when A + D = 0
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

### 5. Relative A/D Ratio

A momentum-of-breadth signal:

```
Step 1:  d = AD_Ratio(t) - AD_Ratio(t-1)
Step 2:  M = mean(SMA(d, 2), SMA(d, 3), SMA(d, 5))
Step 3:  REL_AD_RATIO = (d + M) / 2
```

Positive values mean breadth is improving; negative values mean it is deteriorating.

---

## Supported Universes

| Universe | Indexes / Assets |
|----------|-----------------|
| **India** | NIFTY 50, NIFTY NEXT 50, NIFTY 100, NIFTY 200, NIFTY 500, NIFTY MIDCAP 50/100, NIFTY SMLCAP 100, NIFTY BANK, AUTO, FIN SERVICE, FMCG, IT, MEDIA, METAL, PHARMA |
| **US** | S&P 500, DOW JONES, NASDAQ 100 |
| **Commodities** | 24 futures — Gold, Silver, Crude Oil WTI/Brent, Natural Gas, Copper, Corn, Wheat, Soybeans, Coffee, Cotton, and more |
| **Currencies** | 24 FX pairs — EUR/USD, GBP/USD, USD/JPY, USD/INR, and more |

Constituent lists are fetched live from NSE India (niftyindices.com) and Wikipedia. If NSE is unreachable, Wikipedia is used for NIFTY 50, NIFTY NEXT 50, NIFTY 100 and NIFTY 500. Other Indian indexes then fall back to a built-in list of large caps, and the app warns that the results do not represent the selected index. The Dow Jones has a built-in fallback list; S&P 500 and NASDAQ 100 report an error instead of guessing.

---

## Data Pipeline

```
NSE CSV / Wikipedia Scrape / Hardcoded Tickers
                    │
                    ▼
          yfinance Download
   (start − 120 calendar days warm-up)
                    │
                    ▼
        Live Intraday Append
     (if end date is today and
      today's bar is missing)
                    │
                    ▼
       Close Matrix Assembly
   (tz-normalised, de-duplicated dates)
                    │
                    ▼
        Pct Change → A/D/U Count
 (only assets that printed that day; prior
  close carried over ≤ 2-session gaps;
  sessions where < max(10, 50%) of the
  universe reported are dropped)
                    │
                    ▼
    ADR, ADL, Custom Breadth,
    Relative Breadth Computation
                    │
                    ▼
     Date Window Filter → Display
```

All indicators are computed over the full warm-up history and only then trimmed to the selected window, so values inside the window don't depend on where the download started.

Data is cached with a 5-minute TTL for price data and a 1-hour TTL for constituent lists. Failed fetches are never cached.

---

## Dashboard Layout

**Sidebar** — Universe selection (India / US / Commodities / Currency), index picker, date range, and the RUN ANALYSIS trigger.

**Metric Cards** — Snapshot date, A/D Ratio with sentiment label, Advances count, Declines count, and Net Advances with directional coloring.

Results stay on screen across reruns, for example after clicking the CSV export.

**Time Series Analytics Tab:**
- Relative Breadth Oscillator — bi-color gradient fill with Fibonacci MA smoothing
- Relative A/D Ratio — ADR momentum
- Custom Breadth Oscillator — EMA-smoothed signal with oversold/overbought zones
- A/D Ratio Oscillator — raw daily ADR with bullish/bearish gradient
- Cumulative A/D Line — area chart of net advance accumulation

**Raw Data Matrix Tab** — Full historical breadth table with CSV export.

**Last Session Movers Tab** — Per-constituent price and % change for the latest session, sorted from best to worst.

All charts use Plotly with the Hemrek dark theme (background `#0F0F0F`, accent `#FFC300`, green `#10b981`, red `#ef4444`).

---

## Installation & Usage

### Requirements

- Python 3.10+
- Dependencies listed in `requirements.txt`

### Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

### Development

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
```

CI (GitHub Actions) runs lint and tests on Python 3.10 and 3.13 on every push.

### Project Layout

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI, design-system CSS, caching |
| `engine.py` | Universes, constituent fetching, price download, breadth computation (no Streamlit dependency) |
| `charts.py` | Plotly chart builders |
| `tests/` | Unit tests for the engine and charts (offline, network mocked) |
| `.streamlit/config.toml` | Server settings and dark theme matching the custom CSS |

---

## Aarambh Spreadsheet Correspondence

The system replicates the computations from the Aarambh master spreadsheet:

| Spreadsheet Column | App Column | Formula |
|---|---|---|
| `A/(A+D)` (Col C) | Derived internally | `Advances / (Advances + Declines)` |
| `BREADTH` (Col J) | `Custom_Breadth` | EMA of A/(A+D) with smoothing constant `2/(10+1)` |
| 2D–21D MAs (Cols K–P) | Intermediate | Fibonacci-period SMAs of Custom Breadth |
| Avg of MAs (Col Q) | Z variable | `mean(MA2, MA3, MA5, MA8, MA13, MA21)` |
| `REL_BREADTH` (Col R) | `Relative_Breadth` | `(Z + Custom_Breadth) / 2` |

---

## Version

v1.9.0 (2026) — Correctness audit: stale prices no longer counted as "unchanged", EMA alignment fixed when sessions are dropped, longer indicator warm-up, A/D line anchored to the window start, repaired Dow/NASDAQ-100/NIFTY 500 constituent scraping, failures no longer cached, TLS verification restored, results persist across reruns, new movers tab, tests and CI.

---

*© 2026 Hemrek Capital*
