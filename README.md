# VYĀPTI

**व्याप्ति · Market Breadth | @thebullishvalue**

*Vyāpti* means pervasion: how far something extends through the whole. Breadth measures exactly that, namely how far a move has spread through an index's members. In Nyāya logic, vyāpti is also the invariable relation that licenses an inference from evidence, which is the system's other half: the record that says whether a reading has ever meant anything before you lean on it.

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

## The interface

The interface is the @thebullishvalue family's (Tattva, Arthagati, Pragyam). Its UI layer (`ui/theme.css`, `ui/theme.py`, `ui/components.py`, `ui/format.py`) is adopted whole from Arthagati, so Breadth reads as one more instrument from the same terminal:

- **"Graphite" design language:** Inter for prose, JetBrains Mono for every figure.
- **Semantic colour only:** green is long, red is short, amber is caution, cobalt is the system.
- **Flat panels**, with **Paper (light)** and **Slate (dark)** appearances. The light theme is a token swap, not a second stylesheet.

**Shell (identical on every page):** ticker tape (the index and every sector's equal-weighted level) → command bar (instrument · zone, index level and change, Relative Breadth, record, last crossing, window, as-of, freshness chip) → notice rail (caveats such as substitute constituents, no index price or missing prices).

**Rail:** brand → Market (universe, index) → Record (history to judge against, as-of date) → Session (Run, Refresh data, Start over) → Appearance. Global controls live in the rail; the chart window lives in the header of the chart it reframes.

**Pages.** Each follows the house reading order: TRUST → ANCHOR → STATE → DETAIL → EVENTS.

| Group | Page | Contents |
|---|---|---|
| Engine | **Breadth Engine** (leads) | The Read (state, record, five evidence rows) · Breadth Oscillators (Relative & Custom Breadth with the index on the second axis, Relative A/D Ratio, A/D ratio, A/D line) · Window Statistics · The Reading · Crossing Log |
| Engine | Record | Zone Record cards · By Zone · By Crossing · Oversold Episodes |
| Engine | Sectors | Sector Zones · weekly sector heatmap · Sector Readings · Constituents |
| System | Data | Coverage · Daily Breadth with CSV export |
| System | Method | Counting · The Oscillators · Reads · The Record — rendered from the engine's own constants |

The Read follows Tattva's anatomy:

1. One statement: the Relative Breadth zone.
2. Whether that zone's record in this index supports leaning on it (better / about / worse than normal, or no record).
3. Five evidence rows: Relative Breadth, direction, momentum, the latest session and the breadth trend. Each bar places its reading in its own history. Evidence is shown, never added into a score.

**Colour carries a claim.** Green marks the oversold zone, the reading whose record has mattered. Overbought has no record of mattering, so it is drawn in neutral slate rather than a warning colour.

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
| `app.py` | Shell: rail, run, tape, command bar, notice rail, navigation, footer |
| `config.py` | Product identity, chart windows, record options |
| `ui/theme.css`, `ui/theme.py`, `ui/components.py`, `ui/format.py` | The family's shared UI layer (vendored from Arthagati) |
| `ui/verdict.py` | The Read card's content, built from an analysis (pure) |
| `ui/charts.py` | The engine stack and sector heatmap, in the family's chart grammar |
| `ui/tabs/` | Landing, Breadth Engine, Record, Sectors, Data, Method |
| `cli.py` | The same reading as text or JSON, optional CSV |
| `breadth/indicators.py` | Oscillators, zone, direction, momentum, A/D-line trend, sector and stock snapshots |
| `breadth/study.py` | Episodes, zone and crossing evidence, verdict |
| `breadth/narrative.py` | The reading and "what would change it" text |
| `breadth/pipeline.py` | `run()` / `build_analysis()`: everything in one call |
| `breadth/universe.py` | Universes, constituents, sectors, index tickers |
| `breadth/data.py` | Yahoo download, live-session append, currency inversion |
| `tests/` | 55 offline tests (network mocked, synthetic market generator) |

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

**v3.2.0 (2026)**: Renamed Market Breadth → Vyāpti.

**v3.1.0 (2026)**: The family interface. Adopted the shared UI layer of Tattva, Arthagati and Pragyam: the Graphite design system with Paper/Slate appearances, tape / command bar / notice rail shell, `st.navigation` pages in house reading order, Tattva's read card, panel-anchored chart windows, the institutional table, and the family landing page.

**v3.0.0 (2026)**: Rebuilt around the Aarambh oscillators. The zone is the headline; direction, momentum and the A/D-line trend support it. Evidence uses only real-time information and is sized by episode. A plain-language reading with "what would change it" replaces the indicator dashboard. Sectors are read with the same oscillator. An as-of date allows historical replay.

v2.0.0: Institutional indicator set (superseded; see the audit above). v1.9.0: Correctness audit.

---

*© 2026 Vyāpti · @thebullishvalue*
