"""Plotly figures. One colour language throughout:

    green  = oversold zone (Relative Breadth < 0.40) / positive momentum
    amber  = overbought zone (Relative Breadth > 0.50)
    red    = negative momentum
    gold   = Relative Breadth, cyan = Custom Breadth
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .indicators import MIDLINE, OVERBOUGHT, OVERSOLD

GREEN = "#10b981"
AMBER = "#f59e0b"
RED = "#ef4444"
GREY = "#888888"
GOLD = "#FFC300"
CYAN = "#06b6d4"
TEXT = "#EAEAEA"
OS_FILL = "rgba(16,185,129,0.14)"
OB_FILL = "rgba(245,158,11,0.07)"
OB_SHADE = "rgba(245,158,11,0.045)"   # lighter on the price pane, where overbought can cover most sessions
ZONE_COLOR = {"OVERSOLD": GREEN, "NEUTRAL": GREY, "OVERBOUGHT": AMBER}


def _style(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#1A1A1A", height=height,
        margin=dict(l=10, r=10, t=30, b=10), font=dict(family="Inter", color=TEXT), hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(42,42,42,0.5)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(42,42,42,0.5)")
    return fig


def _zone_segments(zone: pd.Series):
    """(start, end, zone) runs of consecutive sessions in the same zone."""
    if zone.empty:
        return []
    run = (zone != zone.shift()).cumsum()
    return [(g.index[0], g.index[-1], g.iloc[0]) for _, g in zone.groupby(run)]


def plot_cycle(view: pd.DataFrame, price: pd.Series, price_label: str) -> go.Figure:
    """Index with zone shading, the two breadth oscillators with zone bands, and A/D momentum."""
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.40, 0.38, 0.22], vertical_spacing=0.035)
    p = price.reindex(view.index)
    fig.add_trace(go.Scatter(x=view.index, y=p, name=price_label, line=dict(color=TEXT, width=1.8)), 1, 1)
    fig.add_trace(go.Scatter(x=view.index, y=view["Relative_Breadth"], name="Relative Breadth",
                             line=dict(color=GOLD, width=2.6)), 2, 1)
    fig.add_trace(go.Scatter(x=view.index, y=view["Custom_Breadth"], name="Custom Breadth",
                             line=dict(color=CYAN, width=1.3)), 2, 1)
    rel = view["Rel_AD_Ratio"]
    fig.add_trace(go.Bar(x=view.index, y=rel, name="Relative A/D Ratio",
                         marker_color=[GREEN if v > 0 else RED for v in rel.fillna(0)]), 3, 1)

    # Shapes after traces: Plotly skips subplots that are still empty.
    for start, end, z in _zone_segments(view["Zone"]):
        if z != "NEUTRAL":
            fig.add_vrect(x0=start - pd.Timedelta(hours=12), x1=end + pd.Timedelta(hours=12), line_width=0,
                          fillcolor=OS_FILL if z == "OVERSOLD" else OB_SHADE, layer="below", row=1, col=1)
    lo = min(0.30, float(view[["Relative_Breadth", "Custom_Breadth"]].min().min()) - 0.02)
    hi = max(0.62, float(view[["Relative_Breadth", "Custom_Breadth"]].max().max()) + 0.02)
    fig.add_hrect(y0=lo, y1=OVERSOLD, fillcolor=OS_FILL, line_width=0, layer="below", row=2, col=1)
    fig.add_hrect(y0=OVERBOUGHT, y1=hi, fillcolor=OB_FILL, line_width=0, layer="below", row=2, col=1)
    fig.add_hline(y=OVERSOLD, line=dict(color=GREEN, width=1, dash="dash"), row=2, col=1)
    fig.add_hline(y=OVERBOUGHT, line=dict(color=AMBER, width=1, dash="dash"), row=2, col=1)
    fig.add_hline(y=MIDLINE, line=dict(color="rgba(255,255,255,0.15)", width=1), row=2, col=1)
    fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.25)", width=1), row=3, col=1)

    fig.update_yaxes(title_text=price_label, row=1, col=1)
    fig.update_yaxes(title_text="Breadth", range=[lo, hi], row=2, col=1)
    fig.update_yaxes(title_text="A/D momentum", row=3, col=1)
    return _style(fig, 720)


def plot_ad_ratio(view: pd.DataFrame) -> go.Figure:
    """Daily A/D ratio around 1.0 with its 10-session average."""
    s = view["AD_Ratio"]
    colors = [GREEN if v > 1.2 else RED if v < 0.8 else GREY for v in s]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=view.index, y=s - 1, base=1, name="A/D ratio", marker_color=colors,
                         customdata=s, hovertemplate="%{customdata:.2f}"))
    fig.add_trace(go.Scatter(x=view.index, y=view["ADR_MA10"], name="10-session average",
                             line=dict(color=GOLD, width=2)))
    fig.add_hline(y=1.0, line=dict(color="rgba(255,255,255,0.3)", width=1))
    ticks = [0.1, 0.25, 0.5, 1, 2, 4, 10]
    fig.update_yaxes(title_text="Advancers ÷ decliners", type="log", tickvals=ticks,
                     ticktext=[f"{t:g}" for t in ticks])
    return _style(fig, 340)


def plot_ad_line(view: pd.DataFrame) -> go.Figure:
    """Cumulative net advances with its 50-session average (the longer breadth trend)."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=view.index, y=view["AD_Line"], name="A/D line",
                             line=dict(color=CYAN, width=2), fill="tozeroy", fillcolor="rgba(6,182,212,0.08)"))
    fig.add_trace(go.Scatter(x=view.index, y=view["AD_Line_MA50"], name="50-session average",
                             line=dict(color=GREY, width=1.5, dash="dot")))
    fig.update_yaxes(title_text="Cumulative net advances")
    return _style(fig, 340)


def plot_sector_heatmap(sector_osc: dict, start, end) -> go.Figure:
    """Weekly Relative Breadth by sector, coloured by zone."""
    frame = pd.DataFrame({s: o["Relative_Breadth"] for s, o in sector_osc.items()})
    frame = frame.loc[pd.Timestamp(start):pd.Timestamp(end)].resample("W-FRI").last().dropna(how="all")
    if frame.empty:
        return _style(go.Figure(), 300)
    # Highest latest reading at the bottom, so oversold sectors sit at the top (as in the sector table).
    frame = frame[frame.iloc[-1].sort_values(ascending=False).index]
    zmin, zmax = 0.30, 0.62
    pos = lambda v: (v - zmin) / (zmax - zmin)  # noqa: E731
    scale = [[0, GREEN], [pos(OVERSOLD), "rgba(16,185,129,0.35)"], [pos(OVERSOLD) + 0.001, "#2A2A2A"],
             [pos(OVERBOUGHT), "#2A2A2A"], [pos(OVERBOUGHT) + 0.001, "rgba(245,158,11,0.35)"], [1, AMBER]]
    fig = go.Figure(go.Heatmap(
        z=frame.T.to_numpy(), x=frame.index, y=list(frame.columns), zmin=zmin, zmax=zmax, colorscale=scale,
        colorbar=dict(title="Relative<br>Breadth", tickvals=[0.30, OVERSOLD, OVERBOUGHT, 0.60]),
        hovertemplate="%{y}<br>week to %{x|%d %b %Y}: %{z:.3f}<extra></extra>",
    ))
    return _style(fig, max(320, 24 * frame.shape[1] + 90))
