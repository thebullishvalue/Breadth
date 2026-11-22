"""Headless breadth report, for cron jobs and quick terminal checks.

    python cli.py --universe "India Indexes" --index "NIFTY 500"
    python cli.py --universe "US Indexes" --index "S&P 500" --years 5 --csv sp500.csv --json
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys

import pandas as pd

from breadth import run
from breadth.signals import SIGNAL_BY_KEY, recent_events
from breadth.universe import UNIVERSE_KINDS

SNAPSHOT_FIELDS = ["Advances", "Declines", "AD_Ratio", "Pct_Above_20", "Pct_Above_50", "Pct_Above_200",
                   "New_Highs", "New_Lows", "NH_NL", "McClellan_Osc", "Custom_Breadth", "Relative_Breadth",
                   "Health_Score", "Regime", "Tactical", "Coverage"]


def _clean(v):
    if isinstance(v, (float, int)) and pd.isna(v):
        return None
    return round(float(v), 4) if isinstance(v, float) else (int(v) if hasattr(v, "item") else v)


def main(argv=None) -> int:
    today = datetime.date.today()
    ap = argparse.ArgumentParser(description="Market breadth report")
    ap.add_argument("--universe", default=UNIVERSE_KINDS[0], choices=UNIVERSE_KINDS)
    ap.add_argument("--index", default="NIFTY 500", help="Index name (ignored for Commodities/Currency)")
    ap.add_argument("--start", type=datetime.date.fromisoformat, default=today - datetime.timedelta(days=180))
    ap.add_argument("--end", type=datetime.date.fromisoformat, default=today)
    ap.add_argument("--years", type=int, default=3, help="History used for the signal study")
    ap.add_argument("--csv", help="Write the windowed breadth panel to this CSV path")
    ap.add_argument("--json", action="store_true", help="Print a JSON snapshot instead of text")
    args = ap.parse_args(argv)

    index = args.index if args.universe in UNIVERSE_KINDS[:2] else None
    a = run(args.universe, index, args.start, args.end, args.years)
    if a is None:
        print("No usable sessions in the selected window.", file=sys.stderr)
        return 1

    if args.csv:
        a.view.to_csv(args.csv)

    signals = [{"signal": SIGNAL_BY_KEY[k].label, "bias": SIGNAL_BY_KEY[k].bias, "date": str(d.date()),
                "sessions_ago": ago} for k, d, ago in recent_events(a.events)]
    if args.json:
        print(json.dumps({
            "universe": a.universe.name, "asof": str(a.asof.date()), "reference": a.price_source,
            "snapshot": {f: _clean(a.last[f]) for f in SNAPSHOT_FIELDS},
            "recent_signals": signals,
        }, indent=2))
    else:
        print(f"{a.universe.name} — breadth as of {a.asof:%d %b %Y} ({a.universe.source})")
        for line in a.note:
            print(" • " + re.sub(r"\*\*(.+?)\*\*", r"\1", line))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
