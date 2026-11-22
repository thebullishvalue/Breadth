# MARKET BREADTH

**Advance-Decline Intelligence | Hemrek Capital**

Reads an index's breadth cycle with the Aarambh oscillators and answers three questions, in this order:

1. **Where is breadth?** Oversold, neutral or overbought, from the Relative Breadth oscillator.
2. **Which way is it moving?** Custom Breadth against Relative Breadth, confirmed or not by the Relative A/D Ratio.
3. **What has that meant?** What the index did next, every previous time breadth was here, compared with any other month.

The page then says what would change the reading, how far away that is in oscillator units, and what happened the previous times it did.

Built with Streamlit and Plotly. Prices from Yahoo Finance; constituents from NSE and Wikipedia.

---

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py                                  # dashboard
python cli.py --index "NIFTY 500"                     # the same reading in the terminal
python cli.py --universe "US Indexes" --index "S&P 500" --years 10 --json --csv sp500.csv
```

Python 3.10+.

---

## The page

**Top (always visible)**
- **Breadth is …**: the zone, the Relative Breadth value and what the zone means.
- **What this has meant for the index**: Better than normal / About normal / Worse than normal / Too few cases, with the figures behind it.
- **The reading**: where breadth is (including how unusual today's level is and any line crossed in the last two weeks), which way it is moving, whether momentum agrees, the latest session, and the longer A/D-line trend.
- **What would change it**: the next decisive moves, their distance in oscillator units, and what followed them before.

**Tabs**

| Tab | Question it answers |
|---|---|
| Breadth Cycle | How did we get here? Index shaded by zone, Relative and Custom Breadth with the zone lines, Relative A/D Ratio, daily A/D ratio, A/D line with its 50-session average |
| What History Says | How reliable is the reading? Results by zone, by line crossing, and every oversold episode |
| Sectors | Where is breadth coming from? The same oscillator per sector, a weekly sector heatmap, and stock drill-down |
| Data & Method | What is this based on? Coverage, sources, oscillator definitions, daily figures with CSV export |

Sidebar: market, **as of** date (read breadth as it stood on any past day), chart period, and how much history to judge against (3 / 5 / 10 years).

---

## The oscillators

Each session, every constituent that traded is counted as advancing, declining or unchanged. A constituent that didn't trade is not counted (its previous close is carried across gaps of up to 2 sessions). Sessions where fewer than max(10, 50% of the universe) reported are dropped.

| Oscillator | Definition | Role |
|---|---|---|
| A/D Ratio | A / D (A when D = 0) | Today's session |
| Custom Breadth | EMA of A/(A+D), `C = 2/(10+1)`, seeded with the first 10-session SMA | Fast breadth line |
| Relative Breadth | `(Z + Custom Breadth) / 2`, Z = mean of its 2, 3, 5, 8, 13, 21-session SMAs | **Zone:** oversold < 0.40, overbought > 0.50 |
| Relative A/D Ratio | `(d + mean(SMA₂(d), SMA₃(d), SMA₅(d))) / 2`, d = daily change in A/D Ratio | Momentum confirmation (3-session average sign) |
| A/D Line | Cumulative net advances | Longer trend: above or below its 50-session average |

**Direction** is *improving* when Custom Breadth is above Relative Breadth and *deteriorating* when below. A gap of at least 0.005 is needed to flip it, so a tiny crossing doesn't flicker the reading.

Colours: **green** = oversold (and positive momentum), **amber** = overbought, **red** = negative momentum, **gold** = Relative Breadth, **cyan** = Custom Breadth.

---

## How "what it has meant" is worked out

- **Zones:** every session in the history is grouped by its zone, and the index's return over the next 21 and 63 sessions is measured.
- **Crossings:** measured from the day Relative Breadth crossed 0.40 or 0.50. A repeat crossing within 10 sessions isn't counted again.
- **Sample size** is stated in *separate episodes*: zone stretches less than 10 sessions apart count as one. Sessions inside one episode aren't independent evidence. Fewer than 5 episodes → "too few cases".
- **Verdict** compares the one-month figures with all sessions in the same history:
  - **Better than normal:** average at least 0.5 points higher *and* hit rate at least 3 points higher, or average at least 1.5 points higher.
  - **Worse than normal:** the mirror image.
  - **About normal:** anything else.
- **No look-ahead.** Every figure uses only what was known on the day.
- **Limits.** History uses today's index members, so names that have since left the index are missing (survivorship bias). Past patterns are evidence, not a guarantee.

---

## Why it is built this way (audit of v2.0, Nov 2026)

v2.0 surrounded the oscillators with a composite Health Score, McClellan, TRIN, % above moving averages, new highs/lows and a signal table. Checked against five years of NIFTY 500 and S&P 500 data:

- **The Health Score's labels were contradicted by its own evidence.** "Washout" (shown red) was followed by the *best* month in both markets (+4.0% / +5.2%, 82–83% up). "Healthy" (shown green) was among the worst. Removed.
- **The Relative Breadth oversold zone holds up in both markets.** Oversold sessions: NIFTY 500 +2.3% one month later (68% up), S&P 500 +3.4% (77% up), against about +1.1% (62–66%) normally. The system is built on this.
- **Overbought is not a sell signal.** Overbought sessions and crossings performed about like any other time. Relative Breadth was above 0.50 on 50% (NIFTY 500) to 67% (S&P 500) of sessions, so the 0.50 line is crossed 10 or more times a year. The page says so rather than treating every crossing as news.
- **Short-term direction flips every 4–5 sessions,** so it is commentary, not the headline.
- The other v2.0 indicators either duplicated the oscillators (McClellan is also an EMA spread of net advances) or added jargon without changing the reading. They were removed. The zone is the headline, and the remaining reads support it.

---

## Universes

| Universe | Constituents | Compared with |
|---|---|---|
| India | 16 NIFTY indexes from the NSE index files. If NSE is down: Wikipedia for NIFTY 50/NEXT 50/100/500; other indexes fall back to a flagged large-cap list. | The index on Yahoo (e.g. `^NSEI`, `^CRSLDX`). NIFTY MIDCAP 100, SMLCAP 100 and MEDIA have no usable Yahoo history and use an equal-weighted basket of constituents. |
| US | S&P 500, Dow Jones, NASDAQ 100 from Wikipedia (the Dow has a built-in fallback) | `^GSPC`, `^DJI`, `^NDX` |
| Commodities | 24 futures in 6 groups | Equal-weighted basket |
| Currency (vs USD) | 16 currencies, all measured against USD (USD-quoted pairs inverted); crosses excluded | Equal-weighted basket |

Sector breadth uses NSE industries, GICS/ICB sectors from Wikipedia, or the commodity/currency groups. Only sectors with at least 5 members are shown.

Caching: constituents 1 hour, prices 5 minutes. Failures are never cached.

---

## Project layout

| Path | Purpose |
|---|---|
| `app.py` | Streamlit page |
| `cli.py` | The same reading as text or JSON, optional CSV |
| `breadth/indicators.py` | Oscillators, zone, direction, momentum, A/D-line trend, sector and stock snapshots |
| `breadth/study.py` | Episodes, zone and crossing evidence, verdict |
| `breadth/narrative.py` | The reading and "what would change it" text |
| `breadth/pipeline.py` | `run()` / `build_analysis()`: everything in one call |
| `breadth/universe.py` | Universes, constituents, sectors, index tickers |
| `breadth/data.py` | Yahoo download, live-session append, currency inversion |
| `breadth/charts.py` | Plotly figures |
| `assets/style.css` | Hemrek design system |
| `tests/` | 49 offline tests (network mocked, synthetic market generator) |

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

**v3.0.0 (2026)**: Rebuilt around the Aarambh oscillators. The zone is the headline; direction, momentum and the A/D-line trend support it. Evidence uses only real-time information and is sized by episode. A plain-language reading with "what would change it" replaces the indicator dashboard. Sectors are read with the same oscillator. An as-of date allows historical replay.

v2.0.0: Institutional indicator set (superseded; see the audit above). v1.9.0: Correctness audit.

---

*© 2026 Hemrek Capital*
