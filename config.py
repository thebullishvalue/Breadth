"""Vyāpti — product identity and the UI's shared settings.

The single source the UI layer (ui/theme.py, ui/components.py) reads its name,
version and chart windows from, the same contract as the rest of the
@thebullishvalue family.
"""

from breadth import __version__

VERSION = f"v{__version__}"
PRODUCT_NAME = "Vyāpti"
COMPANY = "@thebullishvalue"

#: The product mark, split where the accent starts (see render_nav_brand).
MARK_HEAD, MARK_TAIL = "VYAP", "TI"
SANSKRIT = "व्याप्ति"           # vyāpti — pervasion; in Nyāya, the relation that licenses an inference
TAGLINE = "व्याप्ति · Market Breadth"

#: Chart windows offered in each page's primary chart panel (calendar days).
#: The engine always computes on the full history; these only frame the plots.
TIMEFRAMES: dict[str, int | None] = {
    "1W": 7,
    "1M": 30,
    "3M": 90,
    "6M": 180,
    "YTD": None,
    "1Y": 365,
    "2Y": 730,
    "5Y": 1825,
    "MAX": None,
}
DEFAULT_TIMEFRAME = "6M"

#: Years of history the record is judged on, offered in the rail.
EVIDENCE_YEARS = {"3 years": 3, "5 years": 5, "10 years": 10}
DEFAULT_EVIDENCE = "5 years"

#: Sessions old before the command bar's freshness chip turns to a warning.
STALE_DATA_DAYS = 4
