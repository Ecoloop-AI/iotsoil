"""pages/parameter_detail.py — Detail view for any single parameter"""
from dash import html, dcc
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import data_service as ds
from data_service import PARAMS, C, hex_to_rgba, get_status
import components as ui

def layout(param, store):
    if param not in PARAMS:
        return html.Div("Unknown parameter", style={"color": C["red"]})

    meta    = PARAMS[param]
    history = store.get("history") or []
    latest  = store.get("latest") or {}
    df      = ds.to_df(history)

    val = latest.get(param)
    status, color = get_status(param, float(val) if val is not None else None)

    vals = df[param].dropna() if not df.empty and param in df.columns else pd.Series([])
    mn   = round(vals.min(), 2) if len(vals) else "—"
    mx   = round(vals.max(), 2) if len(vals) else "—"
    avg  = round(vals.mean(), 2) if len(vals) else "—"
    std  = round(vals.std(), 2)  if len(vals) else "—"

    return html.Div([

        # ── Header band ──
        html.Div([
            html.Div([
                html.Div(meta["icon"], style={"fontSize": "36px"}),
                html.Div([
                    html.Div(meta["label"], style={
                        "fontSize": "20px", "fontWeight": "700", "color": C["text"]}),
                    html.Div(f"Unit: {meta['unit']}  •  Range: {meta['min']}–{meta['max']} {meta['unit']}",
                             style={"fontSize": "12px", "color": C["muted"], "marginTop": "4px"}),
                ]),
            ], style={"display": "flex", "alignItems": "center", "gap": "16px"}),

            # Current value hero
            html.Div([
                html.Div(
                    f"{round(float(val), 2) if val is not None else '—'}",
                    style={"fontSize": "48px", "fontWeight": "700",
                           "color": color, "fontFamily": "'JetBrains Mono', monospace",
                           "lineHeight": "1"}),
                html.Div(meta["unit"], style={"fontSize": "16px", "color": C["muted"],
                                              "marginTop": "4px"}),
                html.Div(status.upper(), style={
                    "fontSize": "11px", "fontWeight": "700", "letterSpacing": "2px",
                    "color": color, "marginTop": "6px",
                    "background": hex_to_rgba(color, 0.12),
                    "border": f"1px solid {hex_to_rgba(color, 0.3)}",
                    "padding": "3px 12px", "borderRadius": "20px",
                    "display": "inline-block"}),
            ], style={"textAlign": "right"}),
        ], style={
            "background": f"linear-gradient(135deg, {hex_to_rgba(color, 0.08)}, rgba(15,23,42,0.9))",
            "border": f"1px solid {hex_to_rgba(color, 0.3)}",
            "borderRadius": "16px", "padding": "28px 32px",
            "display": "flex", "justifyContent": "space-between", "alignItems": "center",
            "marginBottom": "24px",
        }),

        # ── Stats row ──
        html.Div([
            _stat("Current", f"{round(float(val),2) if val else '—'}", meta["unit"], color),
            _stat("Minimum", str(mn), meta["unit"], C["blue"]),
            _stat("Maximum", str(mx), meta["unit"], C["red"]),
            _stat("Average", str(avg), meta["unit"], C["green"]),
            _stat("Std Dev", str(std), meta["unit"], C["purple"]),
            _stat("Readings", str(len(vals)), "", C["muted"]),
        ], style={"display": "grid", "gridTemplateColumns": "repeat(6,1fr)",
                  "gap": "12px", "marginBottom": "24px"}),

        # ── Trend + gauge ──
        html.Div([
            html.Div([
                html.Div("Historical Trend", style={
                    "fontSize": "12px", "color": C["muted"], "marginBottom": "12px"}),
                dcc.Graph(
                    figure=_trend(df, param, color),
                    config={"displayModeBar": False},
                    style={"height": "260px"},
                ),
            ], style={
                "background": "rgba(15,23,42,0.8)", "border": f"1px solid {C['border']}",
                "borderRadius": "14px", "padding": "20px", "flex": "3", "minWidth": "0",
            }),
            html.Div([
                dcc.Graph(
                    figure=ui.gauge_chart(
                        float(val) if val else 0,
                        meta["label"], meta["max"], color, meta["unit"]),
                    config={"displayModeBar": False},
                    style={"height": "220px"},
                ),
                _normal_band(meta),
            ], style={
                "background": "rgba(15,23,42,0.8)", "border": f"1px solid {C['border']}",
                "borderRadius": "14px", "padding": "20px", "flex": "1", "minWidth": "240px",
            }),
        ], style={"display": "flex", "gap": "16px", "marginBottom": "16px"}),

        # ── Daily report bar + histogram ──
        html.Div([
            html.Div([
                html.Div("Daily Averages", style={
                    "fontSize": "12px", "color": C["muted"], "marginBottom": "12px"}),
                dcc.Graph(
                    figure=_daily_bar(df, param, color),
                    config={"displayModeBar": False},
                    style={"height": "220px"},
                ),
            ], style={
                "background": "rgba(15,23,42,0.8)", "border": f"1px solid {C['border']}",
                "borderRadius": "14px", "padding": "20px", "flex": "1", "minWidth": "0",
            }),
            html.Div([
                html.Div("Value Distribution", style={
                    "fontSize": "12px", "color": C["muted"], "marginBottom": "12px"}),
                dcc.Graph(
                    figure=_dist(vals, color, meta),
                    config={"displayModeBar": False},
                    style={"height": "220px"},
                ),
            ], style={
                "background": "rgba(15,23,42,0.8)", "border": f"1px solid {C['border']}",
                "borderRadius": "14px", "padding": "20px", "flex": "1", "minWidth": "0",
            }),
        ], style={"display": "flex", "gap": "16px", "marginBottom": "16px"}),

        # ── Anomaly detection ──
        html.Div([
            html.Div("Anomaly Detection (±2σ band)", style={
                "fontSize": "12px", "color": C["muted"], "marginBottom": "12px"}),
            dcc.Graph(
                figure=_anomaly(df, param, color),
                config={"displayModeBar": False},
                style={"height": "220px"},
            ),
        ], style={
            "background": "rgba(15,23,42,0.8)", "border": f"1px solid {C['border']}",
            "borderRadius": "14px", "padding": "20px", "marginBottom": "16px",
        }),

        # ── Raw data table ──
        ui.section_title(f"Recent {meta['label']} Readings"),
        _raw_table(df, param, meta, color),

    ])

# ── helpers ──────────────────────────────────────────────────────
def _stat(label, value, unit, color):
    return html.Div([
        html.Div(f"{value} {unit}".strip(), style={
            "fontSize": "20px", "fontWeight": "700", "color": color,
            "fontFamily": "'JetBrains Mono', monospace", "lineHeight": "1"}),
        html.Div(label, style={"fontSize": "11px", "color": C["muted"],
                               "marginTop": "6px", "letterSpacing": "0.5px"}),
    ], style={
        "background": "rgba(15,23,42,0.8)", "border": f"1px solid {C['border']}",
        "borderTop": f"2px solid {color}",
        "borderRadius": "10px", "padding": "16px",
    })

def _normal_band(meta):
    return html.Div([
        html.Div("Normal Range", style={"fontSize": "11px", "color": C["muted"],
                                        "marginBottom": "10px", "textAlign": "center"}),
        html.Div([
            html.Div([
                html.Span("Low ", style={"color": C["muted"], "fontSize": "11px"}),
                html.Span(f"{meta['lo']} {meta['unit']}",
                          style={"color": C["green"], "fontSize": "13px",
                                 "fontFamily": "'JetBrains Mono', monospace",
                                 "fontWeight": "600"}),
            ]),
            html.Span("—", style={"color": C["muted"]}),
            html.Div([
                html.Span("High ", style={"color": C["muted"], "fontSize": "11px"}),
                html.Span(f"{meta['hi']} {meta['unit']}",
                          style={"color": C["green"], "fontSize": "13px",
                                 "fontFamily": "'JetBrains Mono', monospace",
                                 "fontWeight": "600"}),
            ]),
        ], style={"display": "flex", "justifyContent": "space-between",
                  "alignItems": "center",
                  "background": "rgba(16,185,129,0.06)",
                  "border": "1px solid rgba(16,185,129,0.2)",
                  "borderRadius": "8px", "padding": "10px 14px"}),
    ])

def _trend(df, param, color):
    fig = go.Figure()
    if df.empty or param not in df.columns:
        return fig
    fig.add_trace(go.Scatter(
        x=df["recorded_at"], y=df[param],
        mode="lines+markers",
        line=dict(color=color, width=2),
        marker=dict(size=4, color=color),
        fill="tozeroy", fillcolor=hex_to_rgba(color, 0.07),
        name=PARAMS[param]["label"],
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=260, margin=dict(l=0, r=0, t=0, b=20),
        xaxis=dict(showgrid=False, tickfont=dict(size=9, color=C["muted"])),
        yaxis=dict(showgrid=True, gridcolor="rgba(51,65,85,0.35)",
                   tickfont=dict(size=9, color=C["muted"])),
        font=dict(family="Inter"), showlegend=False, hovermode="x",
    )
    return fig

def _daily_bar(df, param, color):
    fig = go.Figure()
    if df.empty or param not in df.columns:
        return fig
    df2 = df.copy()
    df2["date"] = df2["recorded_at"].dt.date
    daily = df2.groupby("date")[param].mean().reset_index()
    fig.add_trace(go.Bar(
        x=daily["date"].astype(str), y=daily[param].round(2),
        marker_color=color, opacity=0.85,
        marker_line_width=0,
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=220, margin=dict(l=0, r=0, t=0, b=20),
        xaxis=dict(showgrid=False, tickfont=dict(size=9, color=C["muted"])),
        yaxis=dict(showgrid=True, gridcolor="rgba(51,65,85,0.35)",
                   tickfont=dict(size=9, color=C["muted"])),
        font=dict(family="Inter"), showlegend=False,
    )
    return fig

def _dist(vals, color, meta):
    fig = go.Figure()
    if vals.empty:
        return fig
    fig.add_trace(go.Histogram(
        x=vals, nbinsx=20,
        marker_color=hex_to_rgba(color, 0.7),
        marker_line_color=color, marker_line_width=0.5,
    ))
    # normal range vlines
    fig.add_vline(x=meta["lo"], line_dash="dash", line_color=C["green"],
                  annotation_text="Low", annotation_font_size=9,
                  annotation_font_color=C["green"])
    fig.add_vline(x=meta["hi"], line_dash="dash", line_color=C["yellow"],
                  annotation_text="High", annotation_font_size=9,
                  annotation_font_color=C["yellow"])
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=220, margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        xaxis=dict(showgrid=False, tickfont=dict(size=9, color=C["muted"])),
        yaxis=dict(showgrid=True, gridcolor="rgba(51,65,85,0.35)",
                   tickfont=dict(size=9, color=C["muted"])),
        font=dict(family="Inter"),
    )
    return fig

def _anomaly(df, param, color):
    fig = go.Figure()
    if df.empty or param not in df.columns:
        return fig
    s    = df[param].astype(float)
    mu   = s.mean()
    std  = s.std()
    anom = (s - mu).abs() > 2 * std

    fig.add_trace(go.Scatter(
        x=df["recorded_at"], y=s,
        mode="lines", line=dict(color=color, width=1.5), name="Value",
        fill="tozeroy", fillcolor=hex_to_rgba(color, 0.05),
    ))
    # 2σ band
    fig.add_trace(go.Scatter(
        x=list(df["recorded_at"]) + list(df["recorded_at"])[::-1],
        y=[mu + 2*std]*len(df) + [mu - 2*std]*len(df),
        fill="toself", fillcolor=hex_to_rgba(C["green"], 0.06),
        line=dict(color="rgba(0,0,0,0)"), name="±2σ",
    ))
    # anomaly markers
    fig.add_trace(go.Scatter(
        x=df["recorded_at"][anom], y=s[anom],
        mode="markers",
        marker=dict(color=C["red"], size=8, symbol="x"),
        name="Anomaly",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=220, margin=dict(l=0, r=0, t=0, b=20),
        showlegend=True,
        legend=dict(orientation="h", y=-0.22, font=dict(size=10, color=C["muted"]),
                    bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(showgrid=False, tickfont=dict(size=9, color=C["muted"])),
        yaxis=dict(showgrid=True, gridcolor="rgba(51,65,85,0.35)",
                   tickfont=dict(size=9, color=C["muted"])),
        font=dict(family="Inter"),
    )
    return fig

def _raw_table(df, param, meta, color):
    if df.empty or param not in df.columns:
        return html.Div("No data", style={"color": C["muted"]})
    rows = df[["recorded_at", param]].tail(15).iloc[::-1]
    return html.Div(
        html.Table([
            html.Thead(html.Tr([
                html.Th("Timestamp", style={"padding": "10px 14px", "textAlign": "left",
                                            "color": C["muted"], "fontSize": "10px",
                                            "letterSpacing": "1.5px",
                                            "borderBottom": f"1px solid {C['border']}"}),
                html.Th(f"{meta['label']} ({meta['unit']})",
                        style={"padding": "10px 14px", "textAlign": "left",
                               "color": C["muted"], "fontSize": "10px",
                               "letterSpacing": "1.5px",
                               "borderBottom": f"1px solid {C['border']}"}),
                html.Th("Status", style={"padding": "10px 14px", "textAlign": "left",
                                         "color": C["muted"], "fontSize": "10px",
                                         "letterSpacing": "1.5px",
                                         "borderBottom": f"1px solid {C['border']}"}),
            ])),
            html.Tbody([
                html.Tr([
                    html.Td(str(row["recorded_at"])[:19],
                            style={"padding": "11px 14px",
                                   "borderBottom": "1px solid rgba(30,41,59,0.5)",
                                   "color": C["muted"], "fontSize": "11px",
                                   "fontFamily": "'JetBrains Mono', monospace"}),
                    html.Td(f"{round(float(row[param]),2)}",
                            style={"padding": "11px 14px",
                                   "borderBottom": "1px solid rgba(30,41,59,0.5)",
                                   "color": color, "fontSize": "13px",
                                   "fontFamily": "'JetBrains Mono', monospace",
                                   "fontWeight": "600"}),
                    html.Td(
                        html.Span(*get_status(param, float(row[param]))[0:1],
                                  style={"color": get_status(param, float(row[param]))[1],
                                         "fontSize": "10px", "fontWeight": "700"}),
                        style={"padding": "11px 14px",
                               "borderBottom": "1px solid rgba(30,41,59,0.5)"}),
                ]) for _, row in rows.iterrows()
            ]),
        ], style={"width": "100%", "borderCollapse": "collapse"}),
        style={"background": "rgba(15,23,42,0.8)", "border": f"1px solid {C['border']}",
               "borderRadius": "12px", "overflow": "hidden"})
