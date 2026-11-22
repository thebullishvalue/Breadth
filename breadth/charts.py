"""Plotly chart builders. Every function takes the windowed panel (Date index)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .signals import SIGNAL_BY_KEY

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
        fig.add_trace(go.Scatter(x=df.index, y=baseline, line=dict(width=0), hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=df.index, y=clipped, fill="tonexty", fillcolor=fill,
                                 line=dict(width=0), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=df.index, y=s, mode="lines+markers", name=name,
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
        x=df.index, y=df["AD_Line"], mode="lines", name="A/D Line",
        line=dict(color=CYAN, width=2), fill="tozeroy", fillcolor="rgba(6, 182, 212, 0.1)",
    ))
    return _base_layout(fig, "Cumulative Net Advances")


# ══════════════════════════════════════════════════════════════════════════════
# INSTITUTIONAL VIEWS
# ══════════════════════════════════════════════════════════════════════════════

AMBER = "#f59e0b"
PURPLE = "#a78bfa"
REGIME_BANDS = [  # (lo, hi, fill)
    (70, 100, "rgba(16,185,129,0.20)"),
    (55, 70, "rgba(16,185,129,0.09)"),
    (30, 45, "rgba(239,68,68,0.09)"),
    (0, 30, "rgba(239,68,68,0.20)"),
]
EVENT_STYLE = {
    "bullish": dict(symbol="triangle-up", color=GREEN),
    "bearish": dict(symbol="triangle-down", color=RED),
}


def _dark(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#1A1A1A", height=height,
        margin=dict(l=10, r=10, t=30, b=10), font=dict(family="Inter", color="#EAEAEA"),
        hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(42,42,42,0.5)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(42,42,42,0.5)")
    return fig


def plot_overview(view: pd.DataFrame, price: pd.Series, events: dict, price_label: str) -> go.Figure:
    """Benchmark with signal markers (top) over the Health Score with regime bands (bottom)."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.6, 0.4], vertical_spacing=0.04)
    p = price.reindex(view.index)
    fig.add_trace(go.Scatter(x=view.index, y=p, name=price_label, line=dict(color=GOLD, width=2)), 1, 1)
    for key, flags in events.items():
        f = flags.reindex(view.index).fillna(False).astype(bool)
        if not f.any():
            continue
        sd = SIGNAL_BY_KEY[key]
        style = EVENT_STYLE.get(sd.bias, dict(symbol="circle", color=GREY))
        fig.add_trace(go.Scatter(
            x=view.index[f], y=p[f], mode="markers", name=sd.label,
            marker=dict(size=11, line=dict(width=1, color="#0F0F0F"), **style),
        ), 1, 1)
    fig.add_trace(go.Scatter(x=view.index, y=view["Health_Score"], name="Health Score",
                             line=dict(color=CYAN, width=2)), 2, 1)
    # Shapes must follow the trace: Plotly skips subplots that are still empty.
    for lo, hi, fill in REGIME_BANDS:
        fig.add_hrect(y0=lo, y1=hi, fillcolor=fill, line_width=0, layer="below", row=2, col=1)
    fig.update_yaxes(title_text=price_label, row=1, col=1)
    fig.update_yaxes(title_text="Health (0-100)", range=[0, 100], row=2, col=1)
    return _dark(fig, 560)


def plot_participation(view: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for w, color in ((20, GREY), (50, GOLD), (200, CYAN)):
        fig.add_trace(go.Scatter(x=view.index, y=view[f"Pct_Above_{w}"], name=f"% above {w}-DMA",
                                 line=dict(color=color, width=2 if w != 20 else 1)))
    for y, c in ((80, "rgba(239,68,68,0.5)"), (50, "rgba(255,255,255,0.2)"), (20, "rgba(16,185,129,0.5)")):
        fig.add_hline(y=y, line=dict(color=c, width=1, dash="dash" if y != 50 else "solid"))
    fig.update_yaxes(title_text="% of constituents", range=[0, 100])
    return _dark(fig, 380)


def plot_highs_lows(view: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=view.index, y=view["New_Highs"], name="New 52W highs", marker_color=GREEN))
    fig.add_trace(go.Bar(x=view.index, y=-view["New_Lows"], name="New 52W lows", marker_color=RED,
                         customdata=view["New_Lows"], hovertemplate="%{customdata}"))
    fig.add_trace(go.Scatter(x=view.index, y=view["NH_NL"].rolling(10, min_periods=1).mean(),
                             name="Net (10-session avg)", line=dict(color=GOLD, width=2)))
    fig.update_layout(barmode="relative")
    fig.update_yaxes(title_text="Count")
    return _dark(fig, 360)


def plot_mcclellan(view: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    osc = view["McClellan_Osc"]
    fig.add_trace(go.Bar(x=view.index, y=osc, name="McClellan Oscillator",
                         marker_color=[GREEN if v > 0 else RED for v in osc]), secondary_y=False)
    fig.add_trace(go.Scatter(x=view.index, y=view["McClellan_Sum"], name="Summation Index (window)",
                             line=dict(color=PURPLE, width=2)), secondary_y=True)
    fig.update_yaxes(title_text="Oscillator (ratio-adjusted)", secondary_y=False)
    fig.update_yaxes(title_text="Summation", tickformat=",.0f", secondary_y=True, showgrid=False)
    return _dark(fig, 380)


def plot_volume_breadth(view: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    ratio = view["UpDown_Value_Ratio"]
    fig.add_trace(go.Bar(x=view.index, y=ratio, name="Up/Down traded value",
                         marker_color=[GREEN if v > 1 else RED for v in ratio.fillna(1)]), secondary_y=False)
    trin = view["TRIN"].rolling(10, min_periods=1).mean()
    fig.add_trace(go.Scatter(x=view.index, y=trin, name="TRIN (10-session avg)",
                             line=dict(color=AMBER, width=2)), secondary_y=True)
    fig.add_hline(y=1.0, line=dict(color="rgba(255,255,255,0.3)", width=1))
    ticks = [0.1, 0.25, 0.5, 1, 2, 4, 10]
    fig.update_yaxes(title_text="Up / Down value", type="log", tickvals=ticks, ticktext=[f"{t:g}" for t in ticks],
                     secondary_y=False)
    fig.update_yaxes(title_text="TRIN", tickformat=".2f", secondary_y=True, showgrid=False)
    return _dark(fig, 360)


def plot_sector_heatmap(history: pd.DataFrame, freq: str = "W-FRI") -> go.Figure:
    """Sectors x weeks heatmap of % members above 50-DMA."""
    h = history.resample(freq).last().dropna(how="all")
    order = h.iloc[-1].sort_values().index if len(h) else h.columns
    h = h[order]
    fig = go.Figure(go.Heatmap(
        z=h.T.to_numpy(), x=h.index, y=list(h.columns), zmin=0, zmax=100,
        colorscale=[[0, RED], [0.5, "#2A2A2A"], [1, GREEN]],
        colorbar=dict(title="% > 50DMA"), hovertemplate="%{y}<br>%{x|%d %b %Y}: %{z:.0f}%<extra></extra>",
    ))
    return _dark(fig, max(300, 26 * len(h.columns) + 80))


def plot_regime_returns(table: pd.DataFrame, horizon: int = 21) -> go.Figure:
    col = f"Avg {horizon}D %"
    colors = [GREEN if v > 0 else RED for v in table[col].fillna(0)]
    fig = go.Figure(go.Bar(x=table["Regime"], y=table[col], marker_color=colors,
                           text=[f"n={n}" for n in table["Sessions"]], textposition="outside"))
    fig.update_yaxes(title_text=f"Avg forward {horizon}-session return %")
    return _dark(fig, 340)
