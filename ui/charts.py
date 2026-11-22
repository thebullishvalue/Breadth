"""Breadth figures, drawn in the family's chart grammar (ui.theme).

Conventions shared with Arthagati's engine stack:
  * the instrument (Relative Breadth) is the accent line; Custom Breadth, its
    faster companion, is the info colour;
  * the index rides on the oscillator pane's SECONDARY axis, dimmed slate — it
    is the reference the oscillator is read against, not a competing series;
  * colour carries a claim: green marks the oversold zone, whose record is the
    one that has mattered; the overbought line is neutral slate because, on
    its own, it has not;
  * hairlines sit exactly on the row boundaries.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from breadth.indicators import MIDLINE, OVERBOUGHT, OVERSOLD
from ui.theme import chart_color, chart_layout, chart_rgba, grid_rgba, style_axes, style_secondary_axis

ROWS = [0.42, 0.18, 0.18, 0.22]


def _hairlines(fig: go.Figure, heights: list[float]) -> None:
    cum = 1.0
    for h in heights[:-1]:
        cum -= h
        fig.add_shape(type="line", xref="paper", yref="paper", x0=0, y0=cum, x1=1, y1=cum,
                      line=dict(color=grid_rgba(0.07), width=1))


def engine_stack(view: pd.DataFrame, price: pd.Series, price_label: str, events: dict) -> go.Figure:
    """Relative & Custom Breadth (index on the second axis) · Relative A/D Ratio · A/D ratio · A/D line."""
    x = view.index
    accent, info, slate = chart_color("accent"), chart_color("cyan"), chart_color("slate")
    long_c = chart_color("emerald")
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.035, row_heights=ROWS,
                        specs=[[{"secondary_y": True}], [{}], [{}], [{}]])

    # Row 1 — the instrument, with the index as its reference.
    fig.add_trace(go.Scattergl(x=x, y=price.reindex(x), mode="lines", name=price_label,
                               line=dict(color=chart_rgba("slate", 0.55), width=1.0)),
                  row=1, col=1, secondary_y=True)
    fig.add_trace(go.Scattergl(x=x, y=view["Custom_Breadth"], mode="lines", name="Custom Breadth",
                               line=dict(color=info, width=1.1)), row=1, col=1, secondary_y=False)
    fig.add_trace(go.Scattergl(x=x, y=view["Relative_Breadth"], mode="lines", name="Relative Breadth",
                               line=dict(color=accent, width=1.8)), row=1, col=1, secondary_y=False)
    rb = view["Relative_Breadth"]
    for key, symbol, name in (("OS_IN", "triangle-down", "Turned oversold"),
                              ("OS_OUT", "triangle-up", "Climbed out of oversold")):
        flags = events.get(key)
        if flags is None:
            continue
        hit = flags.reindex(x).fillna(False).to_numpy(dtype=bool)
        if hit.any():
            fig.add_trace(go.Scatter(x=x[hit], y=rb[hit], mode="markers", name=name,
                                     marker=dict(symbol=symbol, size=9, color=long_c)),
                          row=1, col=1, secondary_y=False)

    # Row 2 — Relative A/D Ratio (daily momentum of the A/D ratio).
    rel = view["Rel_AD_Ratio"]
    fig.add_trace(go.Bar(x=x, y=rel, name="Relative A/D Ratio", showlegend=False,
                         marker_color=[chart_rgba("emerald", 0.75) if v > 0 else chart_rgba("rose", 0.75)
                                       for v in rel.fillna(0)]), row=2, col=1)

    # Row 3 — A/D ratio per session, on a log scale centred on 1.
    adr = view["AD_Ratio"].clip(lower=0.05)
    fig.add_trace(go.Bar(x=x, y=np.log10(adr), name="A/D ratio", showlegend=False,
                         customdata=view["AD_Ratio"], hovertemplate="%{customdata:.2f}",
                         marker_color=[chart_rgba("emerald", 0.6) if v > 1 else chart_rgba("rose", 0.6)
                                       for v in adr]), row=3, col=1)
    fig.add_trace(go.Scattergl(x=x, y=np.log10(view["ADR_MA10"].clip(lower=0.05)), mode="lines",
                               name="A/D 10-session avg", customdata=view["ADR_MA10"],
                               hovertemplate="%{customdata:.2f}", line=dict(color=slate, width=1.2)),
                  row=3, col=1)

    # Row 4 — the A/D line against its 50-session average (the longer trend).
    fig.add_trace(go.Scattergl(x=x, y=view["AD_Line_MA50"], mode="lines", name="A/D line 50-session avg",
                               line=dict(color=slate, width=1.1, dash="dot")), row=4, col=1)
    fig.add_trace(go.Scattergl(x=x, y=view["AD_Line"], mode="lines", name="A/D line",
                               line=dict(color=info, width=1.5)), row=4, col=1)

    # Zone bands and lines — after the traces (Plotly skips subplots that are still empty).
    lo = min(0.30, float(np.nanmin(view[["Relative_Breadth", "Custom_Breadth"]].to_numpy())) - 0.02)
    hi = max(0.62, float(np.nanmax(view[["Relative_Breadth", "Custom_Breadth"]].to_numpy())) + 0.02)
    fig.add_hrect(y0=lo, y1=OVERSOLD, fillcolor=chart_rgba("emerald", 0.08), line_width=0, layer="below",
                  row=1, col=1, secondary_y=False)
    fig.add_hline(y=OVERSOLD, line_color=chart_rgba("emerald", 0.55), line_width=1, row=1, col=1,
                  secondary_y=False)
    fig.add_hline(y=OVERBOUGHT, line_color=chart_rgba("slate", 0.55), line_width=1, line_dash="dot",
                  row=1, col=1, secondary_y=False)
    fig.add_hline(y=MIDLINE, line_color=grid_rgba(0.08), line_width=1, row=1, col=1, secondary_y=False)
    fig.add_hline(y=0, line_color=grid_rgba(0.11), line_width=1, row=2, col=1)
    fig.add_hline(y=0, line_color=grid_rgba(0.11), line_width=1, row=3, col=1)

    fig.update_layout(**chart_layout(height=860, show_legend=True), bargap=0.15)
    style_axes(fig, y_title="Breadth", y_range=[lo, hi], row=1, col=1, secondary_y=False)
    style_secondary_axis(fig, title=price_label, tickformat=",.0f", row=1, col=1)
    fig.update_yaxes(autorange=True, row=1, col=1, secondary_y=True)
    style_axes(fig, y_title="Rel A/D", row=2, col=1)
    ticks = [0.1, 0.25, 0.5, 1, 2, 4, 10]
    style_axes(fig, y_title="A/D ratio", row=3, col=1)
    fig.update_yaxes(tickvals=np.log10(ticks), ticktext=[f"{t:g}" for t in ticks], row=3, col=1)
    style_axes(fig, y_title="A/D line", row=4, col=1)
    _hairlines(fig, ROWS)
    return fig


def sector_heatmap(frame: pd.DataFrame) -> go.Figure:
    """Weekly Relative Breadth by sector. Green where a sector was oversold; no colour claim above it."""
    zmin, zmax = 0.30, 0.62
    pos = lambda v: (v - zmin) / (zmax - zmin)  # noqa: E731
    scale = [[0, chart_color("emerald")], [pos(OVERSOLD), chart_rgba("emerald", 0.35)],
             [pos(OVERSOLD) + 0.001, chart_rgba("slate", 0.10)], [1, chart_rgba("slate", 0.75)]]
    fig = go.Figure(go.Heatmap(
        z=frame.T.to_numpy(), x=frame.index, y=list(frame.columns), zmin=zmin, zmax=zmax, colorscale=scale,
        colorbar=dict(title=dict(text="RB", font=dict(size=10)), tickvals=[0.30, OVERSOLD, OVERBOUGHT, 0.60],
                      tickfont=dict(size=9, family="JetBrains Mono, monospace"), thickness=10),
        customdata=np.round(frame.T.to_numpy(), 3),
        hovertemplate="%{y}<br>week to %{x|%d %b %Y}: %{customdata}<extra></extra>",
    ))
    fig.update_layout(**chart_layout(height=max(320, 22 * frame.shape[1] + 90), show_legend=False))
    style_axes(fig)
    fig.update_yaxes(showgrid=False, zeroline=False, tickfont=dict(size=9))
    fig.update_xaxes(showgrid=False)
    return fig
