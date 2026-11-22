"""Market Breadth — institutional breadth analytics engine (no UI dependencies)."""

from .pipeline import Analysis, build_analysis, history_start, run

__all__ = ["Analysis", "build_analysis", "history_start", "run"]
__version__ = "2.0.0"
