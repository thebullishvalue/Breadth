"""Vyāpti — breadth-cycle analytics built on the Aarambh oscillators (no UI dependencies)."""

from .pipeline import Analysis, build_analysis, history_start, run

__all__ = ["Analysis", "build_analysis", "history_start", "run"]
__version__ = "3.2.0"
