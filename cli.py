"""Headless breadth reading, for scheduled jobs and quick terminal checks.

    python cli.py --index "NIFTY 500"
    python cli.py --universe "US Indexes" --index "S&P 500" --years 10 --json --csv sp500.csv
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys

import pandas as pd

from breadth import run
from breadth.narrative import ZONE_LABEL
from breadth.study import CROSSING_TEXT
from breadth.universe import UNIVERSE_KINDS

FIELDS = ["Advances", "Declines", "AD_Ratio", "Custom_Breadth", "Relative_Breadth", "Rel_AD_Ratio", "Zone",
          "Direction", "Momentum", "Breadth_Trend"]


def _plain(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"\1", text)


def _clean(v):
    if isinstance(v, float):
        return None if pd.isna(v) else round(v, 4)
    return int(v) if hasattr(v, "item") and float(v).is_integer() else v


def main(argv=None) -> int:
    today = datetime.date.today()
    ap = argparse.ArgumentParser(description="Vyāpti — market breadth reading")
    ap.add_argument("--universe", default=UNIVERSE_KINDS[0], choices=UNIVERSE_KINDS)
    ap.add_argument("--index", default="NIFTY 500", help="Index name (ignored for Commodities/Currency)")
    ap.add_argument("--asof", type=datetime.date.fromisoformat, default=today)
    ap.add_argument("--days", type=int, default=182, help="Calendar days of daily figures for --csv")
    ap.add_argument("--years", type=int, default=5, help="History used to judge each reading")
    ap.add_argument("--csv", help="Write the daily figures to this CSV path")
    ap.add_argument("--json", action="store_true", help="Print JSON instead of text")
    args = ap.parse_args(argv)

    index = args.index if args.universe in UNIVERSE_KINDS[:2] else None
    a = run(args.universe, index, args.asof - datetime.timedelta(days=args.days), args.asof, args.years)
    if a is None:
        print("No usable sessions in the selected period.", file=sys.stderr)
        return 1
    if args.csv:
        a.view.to_csv(args.csv)

    if args.json:
        print(json.dumps({
            "universe": a.universe.name, "asof": str(a.asof.date()), "zone": a.zone,
            "versus_normal": a.verdict.label, "verdict": a.verdict.sentence,
            "latest": {f: _clean(a.last[f]) for f in FIELDS},
            "recent_crossings": [{"what": CROSSING_TEXT[k], "sessions_ago": ago} for k, ago in a.recent],
            "reading": [_plain(p) for p in a.reading],
            "watch": [_plain(w) for w in a.watch],
        }, indent=2))
    else:
        print(f"{a.universe.name}: breadth is {ZONE_LABEL[a.zone].upper()} as of {a.asof:%d %b %Y}")
        print(f"\n{a.verdict.sentence}\n")
        for p in a.reading:
            print(_plain(p) + "\n")
        print("What would change it:")
        for w in a.watch:
            print(" • " + _plain(w))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
