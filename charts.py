"""Plotly chart builders for the breadth dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

GREEN = "#10b981"
RED = "#ef4444"
GREY = "#888888"
GOLD = "#FFC300"
CYAN = "#06b6d4"
GREEN_FILL = "rgba(16,185,129,0.15)"
RED_FILL = "rgba(239,68,68,0.15)"

OVERSOLD = 0.40
OVERBOUGHT = 0.50
BREADTH_MID = 0.46


def _base_layout(fig: go.Figure, y_title: str, y_range=None) -> go.Figure:
    yaxis = dict(showgrid=True, gridcolor="rgba(42,42,42,0.5)", title=y_title)
    if y_range is not None:
        yaxis["range"] = y_range
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#1A1A1A", height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showgrid=True, gridcolor="rgba(42,42,42,0.5)"),
        yaxis=yaxis, showlegend=False,
        font=dict(family="Inter", color="#EAEAEA"), hovermode="x unified",
    )
    return fig


def _oscillator(df, col, name, mid, above_fill, below_fill, colors, y_title, y_range, hlines=()):
    fig = go.Figure()
    s = df[col]
    baseline = [mid] * len(df)
    for clipped, fill in ((s.clip(lower=mid), above_fill), (s.clip(upper=mid), below_fill)):
        fig.add_trace(go.Scatter(x=df["Date"], y=baseline, line=dict(width=0), hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=df["Date"], y=clipped, fill="tonexty", fillcolor=fill,
                                 line=dict(width=0), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=df["Date"], y=s, mode="lines+markers", name=name,
                             line=dict(color=GOLD, width=2),
                             marker=dict(size=6, color=colors, line=dict(width=0))))
    for y, color in hlines:
        fig.add_hline(y=y, line=dict(color=color, width=1, dash="dash"))
    fig.add_hline(y=mid, line=dict(color="rgba(255,255,255,0.2)", width=1))
    return _base_layout(fig, y_title, y_range)


def _padded_range(s: pd.Series, lo_default: float, hi_default: float, pad: float):
    v_max, v_min = s.max(), s.min()
    hi = float(v_max + pad) if pd.notna(v_max) and v_max > hi_default else hi_default
    lo = float(v_min - pad) if pd.notna(v_min) and v_min < lo_default else lo_default
    return [lo, hi]


def _breadth_colors(s: pd.Series):
    return [GREEN if v < OVERSOLD else RED if v > OVERBOUGHT else GREY for v in s]


def _breadth_oscillator(df, col, name):
    return _oscillator(
        df, col, name, BREADTH_MID, RED_FILL, GREEN_FILL, _breadth_colors(df[col]), name,
        _padded_range(df[col], 0.35, 0.55, 0.05),
        hlines=((OVERBOUGHT, "rgba(239,68,68,0.5)"), (OVERSOLD, "rgba(16,185,129,0.5)")),
    )


def plot_relative_breadth(df):
    return _breadth_oscillator(df, "Relative_Breadth", "Relative Breadth")


def plot_custom_breadth(df):
    return _breadth_oscillator(df, "Custom_Breadth", "Custom Breadth")


def plot_rel_ad_ratio(df):
    s = df["Rel_AD_Ratio"]
    vals = s.dropna()
    if vals.empty:
        y_range = [-0.5, 0.5]
    else:
        pad = max(abs(vals.max()), abs(vals.min()), 0.05) * 0.15
        y_range = [float(vals.min() - pad), float(vals.max() + pad)]
    colors = [GREEN if v > 0 else RED if v < 0 else GREY for v in s]
    return _oscillator(df, "Rel_AD_Ratio", "Rel A/D Ratio", 0.0, GREEN_FILL, RED_FILL,
                       colors, "Rel A/D Ratio", y_range)


def plot_ad_ratio(df):
    s = df["AD_Ratio"]
    colors = [GREEN if v > 1.2 else RED if v < 0.8 else GREY for v in s]
    return _oscillator(df, "AD_Ratio", "Daily ADR", 1.0, GREEN_FILL, RED_FILL, colors,
                       "A/D Ratio", _padded_range(s, 0.5, 1.5, 0.1))


def plot_ad_line(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["AD_Line"], mode="lines", name="A/D Line",
        line=dict(color=CYAN, width=2), fill="tozeroy", fillcolor="rgba(6, 182, 212, 0.1)",
    ))
    return _base_layout(fig, "Cumulative Net Advances")
