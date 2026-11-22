# MARKET BREADTH

**Advance-Decline Intelligence | Hemrek Capital**

A breadth monitor for Indian and US equity indexes, commodity futures and currencies. It answers four questions a desk asks every morning:

1. **Is the market healthy underneath?** Structural participation: how many constituents are in uptrends, and are they making new highs or new lows?
2. **Is breadth stretched right now?** Tactical oscillators and momentum.
3. **Has anything fired?** Breadth thrusts, washouts, overbought/oversold crossings, and divergences between price and participation.
4. **Does any of it matter?** Each signal and regime comes with the benchmark's forward returns in this universe, compared with the unconditional baseline.

Built with Streamlit and Plotly. Prices from Yahoo Finance; constituents from NSE and Wikipedia.

---

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py                      # dashboard
python cli.py --index "NIFTY 500"         # headless desk note (cron-friendly)
python cli.py --universe "US Indexes" --index "S&P 500" --years 5 --json --csv sp500.csv
```

Python 3.10+.

---

## The dashboard

**Header**: regime and tactical pills, any signal that fired in the last 5 sessions, six KPI cards (Health Score, % > 50-DMA, % > 200-DMA, Net New Highs, McClellan Oscillator, A/D Ratio), and a generated **Desk Note**. The note states the current reading, what this regime has historically been followed by in this universe, and any active signals.

| Tab | Contents |
|---|---|
| Overview | Benchmark with signal markers above the Health Score with regime bands |
| Participation | % above 20/50/200-DMA; 52-week new highs vs new lows |
| Momentum | McClellan Oscillator & Summation Index; up/down traded value & TRIN; cumulative A/D line |
| Oscillators | Relative Breadth, Relative A/D Ratio, Custom Breadth, A/D Ratio (the original Aarambh set) |
| Sectors | Per-sector participation table and a weekly sector × time heatmap of % above 50-DMA |
| Signal Study | Forward 5/10/21/63-session benchmark returns after each signal (average, hit rate, edge vs baseline) and by health regime |
| Constituents | Per-stock snapshot: 1D/21D change, trend position, distance from 52-week high, filterable by sector |
| Data | Coverage and missing symbols, constituent source, survivorship note, full breadth matrix with CSV export |

Results persist across reruns. The CSV export does not reset the page.

---

## Methodology

### Counting rules

- An asset counts on a session only if it **actually printed** that day. The previous close is carried across gaps of up to 2 sessions (a holiday on one exchange), but a missing print is never counted as "unchanged".
- Sessions where fewer than max(10, 50% of the universe) assets reported are dropped.
- All indicators are computed on the full downloaded history (study period plus a 400-calendar-day warm-up) and only then cut to the display window. A reading on a given date doesn't depend on which window you picked.

### Structural health

| Component | Definition |
|---|---|
| % above 50-DMA | Share of eligible constituents closing above their own 50-session SMA |
| % above 200-DMA | Same, 200-session SMA |
| 52W score | `50 + 2.5 × (new highs − new lows) / eligible × 100`, clipped to 0–100. Net ±20% of the universe at 52-week extremes saturates it. Small counts (2 highs vs 0 lows) barely move it. |

**Health Score** = mean of the three (0–100). The 20-DMA reading is shown but deliberately excluded because it is tactical and makes the score whipsaw.

| Regime | Health Score |
|---|---|
| STRONG | ≥ 70 |
| HEALTHY | 55 – 70 |
| NEUTRAL | 45 – 55 |
| WEAK | 30 – 45 |
| WASHOUT | < 30 |

### Tactical and momentum

**Custom Breadth**: an EMA of `x = A / (A + D)` (0.5 on sessions with no directional moves), seeded with the first full 10-session SMA, `C = 2 / (10 + 1)`:
```
BREADTH(t) = BREADTH(t−1) + C × (x(t) − BREADTH(t−1))
```
This is the same series Zweig used for his breadth thrust.

**Relative Breadth**: `(Z + Custom_Breadth) / 2`, where `Z` is the mean of the 2, 3, 5, 8, 13 and 21-session SMAs of Custom Breadth. Tactical state: **OVERSOLD** < 0.40, **OVERBOUGHT** > 0.50.

**Relative A/D Ratio**: `(d + mean(SMA₂(d), SMA₃(d), SMA₅(d))) / 2`, where `d` is the daily change in the A/D ratio.

**McClellan Oscillator** (ratio-adjusted, so it is comparable across universe sizes): `RANA = 1000 × (A − D) / (A + D)`, then `EMA₀.₁₀(RANA) − EMA₀.₀₅(RANA)`. The **Summation Index** is its running total from the start of the display window.

**Up/Down traded value**: price × volume summed over advancers vs decliners. Traded value rather than share count, so share price doesn't distort it. **TRIN** = `(A / D) / (up value / down value)`. It isn't available for spot FX, which has no volume.

**A/D Ratio** = A / D (A when D = 0). **A/D Line**: cumulative net advances from the window start.

### Signals

Each signal is debounced: an event within 10 sessions of the previous one is ignored.

| Signal | Bias | Rule |
|---|---|---|
| Breadth Thrust | Bullish | Custom Breadth crosses above 0.615 having been below 0.40 within the last 10 sessions (Zweig) |
| Relative Breadth Oversold | Bullish | Relative Breadth crosses below 0.40 |
| Relative Breadth Overbought | Bearish | Relative Breadth crosses above 0.50 |
| Participation Washout | Bullish | % above 50-DMA crosses below 15% |
| Bearish Divergence | Bearish | Benchmark at a 63-session high while % above 50-DMA is ≥ 15 pts below its own 63-session high |
| Bullish Divergence | Bullish | Benchmark at a 63-session low while % above 50-DMA is ≥ 15 pts above its own 63-session low |

### Signal study

For every event, the benchmark's return over the next 5, 10, 21 and 63 sessions is computed. The table reports the average, the hit rate (% positive) and the **edge** (average minus the average over all sessions). Rows with fewer than 5 events are flagged. The regime study groups every session by its health regime and reports the 21-session forward return.

**Read it as evidence, not proof:**
- **Survivorship bias.** History is computed on *today's* constituents, so names that were removed or delisted are missing.
- **Overlap.** Forward windows of nearby events overlap, so the observations are not independent.
- **Small samples.** Small samples are noisy. The study history is selectable (1/3/5/10 years) in the sidebar.

---

## Universes

| Universe | Constituents | Reference series |
|---|---|---|
| India | 16 NIFTY indexes from the NSE index files (with industry). If NSE is down, Wikipedia is used for NIFTY 50/NEXT 50/100/500; other indexes fall back to a flagged 26-stock large-cap list. | Yahoo index (e.g. `^NSEI`, `^CRSLDX`); NIFTY MIDCAP 100, SMLCAP 100 and MEDIA have no usable Yahoo history and use the equal-weight composite |
| US | S&P 500, Dow Jones, NASDAQ 100 from Wikipedia (with GICS/ICB sectors); the Dow has a built-in fallback | `^GSPC`, `^DJI`, `^NDX` |
| Commodities | 24 futures in 6 groups (precious, industrial, energy, grains, softs, livestock) | Equal-weight composite |
| Currency (vs USD) | 16 currencies. USD-quoted pairs are inverted so an advance always means the currency **rose against USD**; high breadth = broad dollar weakness. Crosses are excluded because their direction has no common reference. | Equal-weight composite |

If a benchmark download fails, the equal-weight composite is used automatically, and the UI says which series is in use.

Caching: constituents 1 hour, prices 5 minutes. Failures are never cached.

---

## Project layout

| Path | Purpose |
|---|---|
| `app.py` | Streamlit UI and caching |
| `cli.py` | Headless report (text or JSON, optional CSV) |
| `breadth/universe.py` | Universes, constituent scraping, sectors, benchmarks |
| `breadth/data.py` | Yahoo download, field extraction, live-session append, FX inversion |
| `breadth/indicators.py` | Breadth panel, health/tactical classification, per-asset snapshot, sector aggregation |
| `breadth/signals.py` | Signal definitions, event detection, desk note |
| `breadth/study.py` | Forward-return event and regime studies |
| `breadth/pipeline.py` | `run()` / `build_analysis()`: everything above in one call |
| `breadth/charts.py` | Plotly figures |
| `assets/style.css` | Hemrek design system |
| `tests/` | 51 offline tests (network mocked, synthetic market generator) |

### Development

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
```

CI (GitHub Actions) runs lint and tests on Python 3.10 and 3.13 on every push.

---

## Aarambh spreadsheet correspondence

| Spreadsheet Column | App Column | Formula |
|---|---|---|
| `A/(A+D)` (Col C) | Derived internally | `Advances / (Advances + Declines)` |
| `BREADTH` (Col J) | `Custom_Breadth` | EMA of A/(A+D), smoothing constant `2/(10+1)` |
| 2D–21D MAs (Cols K–P) | Intermediate | Fibonacci-period SMAs of Custom Breadth |
| Avg of MAs (Col Q) | Z | `mean(MA2, MA3, MA5, MA8, MA13, MA21)` |
| `REL_BREADTH` (Col R) | `Relative_Breadth` | `(Z + Custom_Breadth) / 2` |

---

## Version

**v2.0.0 (2026)**: Institutional rebuild. Structural Health Score and regimes; trend participation (20/50/200-DMA); 52-week highs/lows; ratio-adjusted McClellan Oscillator and Summation Index; value-weighted up/down breadth and TRIN; benchmark overlay; Zweig thrust, washout and divergence signals; forward-return signal and regime studies; sector breadth and rotation heatmap; constituent snapshot; generated desk note; USD-oriented currency breadth; headless CLI; engine split into the `breadth` package.

v1.9.0: Correctness audit (stale-price counting, EMA alignment, warm-up, scrapers, caching, TLS).

---

*© 2026 Hemrek Capital*
