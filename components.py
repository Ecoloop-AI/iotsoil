"""
components.py — Reusable UI building blocks
"""
from dash import html, dcc
import plotly.graph_objects as go
import numpy as np
from data_service import PARAMS, C, hex_to_rgba, get_status, soil_health_score

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=C["muted"]),
    margin=dict(l=0, r=0, t=0, b=0),
    showlegend=False,
    xaxis=dict(showgrid=False, zeroline=False, showline=False,
               tickfont=dict(size=9, color=C["muted"])),
    yaxis=dict(showgrid=True, gridcolor="rgba(51,65,85,0.4)", zeroline=False,
               showline=False, tickfont=dict(size=9, color=C["muted"])),
)

def card(children, style=None, className=""):
    base = {
        "background": "linear-gradient(135deg, rgba(30,41,59,0.9), rgba(15,23,42,0.95))",
        "border": f"1px solid {C['border']}",
        "borderRadius": "16px",
        "padding": "20px",
        "position": "relative",
        "overflow": "hidden",
    }
    if style:
        base.update(style)
    return html.Div(children, style=base, className=f"kpi-card {className}")

def section_title(text, extra=None):
    return html.Div([
        html.Span(text, style={"fontSize": "11px", "fontWeight": "600",
                               "letterSpacing": "2px", "color": C["muted"],
                               "textTransform": "uppercase"}),
        html.Div(style={"flex": "1", "height": "1px",
                        "background": f"linear-gradient(90deg, {C['border']}, transparent)"}),
        extra or html.Span(),
    ], style={"display": "flex", "alignItems": "center", "gap": "12px", "marginBottom": "16px"})

def status_badge(status, color):
    cls = {"Normal": "badge-normal", "Warning": "badge-warning",
           "Critical": "badge-critical"}.get(status, "badge-warning")
    return html.Span(status.upper(), className=f"badge {cls}")

def sparkline(values, color):
    if not values or len(values) < 2:
        values = [0, 0]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=values, mode="lines",
        line=dict(color=color, width=1.5),
        fill="tozeroy",
        fillcolor=hex_to_rgba(color, 0.08),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=C["muted"]),
        showlegend=False,
        height=40,
        xaxis=dict(visible=False, showgrid=False, zeroline=False),
        yaxis=dict(visible=False, showgrid=False, zeroline=False),
        margin=dict(l=0, r=0, t=0, b=0),
    )
    return dcc.Graph(figure=fig, config={"displayModeBar": False},
                     style={"height": "40px"})

def kpi_card(key, value, history_vals=None):
    meta = PARAMS[key]
    status, color = get_status(key, value)
    pct = 0
    if value is not None:
        span = meta["max"] - meta["min"]
        pct = max(0, min(100, (float(value) - meta["min"]) / span * 100))

    display_val = "—"
    if value is not None:
        display_val = f"{round(float(value), 2 if key=='ph' else 1)}"

    # Ring — CSS conic-gradient trick (works in all Dash versions, no SVG needed)
    # conic-gradient draws the arc; a smaller inner circle creates the donut hole
    bg_color   = "#1E293B"          # track colour
    arc_deg    = round(pct / 100 * 360, 1)
    ring = html.Div([
        # Outer ring (conic-gradient arc)
        html.Div(style={
            "width": "64px", "height": "64px", "borderRadius": "50%",
            "background": (
                f"conic-gradient({color} 0deg {arc_deg}deg, {bg_color} {arc_deg}deg 360deg)"
            ),
            "display": "flex", "alignItems": "center", "justifyContent": "center",
            "flexShrink": "0",
            "transition": "background 0.8s ease",
        }, children=[
            # Inner circle (creates donut hole) + icon
            html.Div(meta["icon"], style={
                "width": "44px", "height": "44px", "borderRadius": "50%",
                "background": "#0A0F1E",
                "display": "flex", "alignItems": "center", "justifyContent": "center",
                "fontSize": "18px", "lineHeight": "1",
            }),
        ]),
    ], style={"flexShrink": "0"})

    return card(html.Div([
        # Top row: icon ring + value
        html.Div([
            ring,
            html.Div([
                html.Div(display_val, style={
                    "fontSize": "28px", "fontWeight": "700",
                    "color": color, "lineHeight": "1",
                    "fontFamily": "'JetBrains Mono', monospace",
                }),
                html.Div(meta["unit"], style={"fontSize": "11px", "color": C["muted"],
                                              "marginTop": "2px"}),
            ]),
        ], style={"display": "flex", "alignItems": "center", "gap": "14px", "marginBottom": "12px"}),

        # Label + badge
        html.Div([
            html.Div(meta["label"], style={"fontSize": "12px", "color": C["muted"],
                                           "fontWeight": "500"}),
            status_badge(status, color),
        ], style={"display": "flex", "justifyContent": "space-between",
                  "alignItems": "center", "marginBottom": "10px"}),

        # Sparkline
        sparkline(history_vals or [], color),

        # Accent bar
        html.Div(style={
            "position": "absolute", "top": "0", "left": "0", "width": f"{pct}%",
            "height": "2px", "background": color,
            "transition": "width 1s ease", "borderRadius": "2px 0 0 0",
        }),
    ]))

def gauge_chart(value, title, max_val, color, unit=""):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value or 0,
        number={"suffix": f" {unit}", "font": {"size": 26, "color": C["text"],
                                                "family": "JetBrains Mono"}},
        title={"text": title, "font": {"size": 12, "color": C["muted"]}},
        gauge={
            "axis": {"range": [0, max_val], "tickwidth": 0,
                     "tickcolor": C["border"], "tickfont": {"size": 9, "color": C["muted"]}},
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, max_val * 0.5],  "color": hex_to_rgba(color, 0.07)},
                {"range": [max_val * 0.5, max_val * 0.8], "color": hex_to_rgba(color, 0.14)},
                {"range": [max_val * 0.8, max_val],       "color": hex_to_rgba(color, 0.22)},
            ],
            "threshold": {"line": {"color": color, "width": 2},
                          "thickness": 0.8, "value": value or 0},
        },
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter"), height=200,
        margin=dict(l=20, r=20, t=30, b=10),
    )
    return fig

def health_score_gauge(score):
    color = C["green"] if score >= 70 else C["yellow"] if score >= 40 else C["red"]
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        delta={"reference": 70, "font": {"size": 12}},
        number={"suffix": "/100", "font": {"size": 32, "color": color,
                                            "family": "JetBrains Mono"}},
        title={"text": "SOIL HEALTH SCORE", "font": {"size": 11, "color": C["muted"]}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 0,
                     "tickfont": {"size": 9, "color": C["muted"]}},
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0,  40], "color": hex_to_rgba(C["red"],    0.12)},
                {"range": [40, 70], "color": hex_to_rgba(C["yellow"], 0.12)},
                {"range": [70, 100],"color": hex_to_rgba(C["green"],  0.12)},
            ],
        },
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter"), height=220,
        margin=dict(l=20, r=20, t=30, b=10),
    )
    return fig

def radar_chart(row):
    keys = list(PARAMS.keys())
    vals = []
    for k in keys:
        v = row.get(k, 0) if row else 0
        m = PARAMS[k]
        pct = max(0, min(100, (float(v or 0) - m["min"]) / (m["max"] - m["min"]) * 100))
        vals.append(pct)
    vals.append(vals[0])
    labels = [PARAMS[k]["label"] for k in keys] + [PARAMS[keys[0]]["label"]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals, theta=labels, fill="toself",
        fillcolor=hex_to_rgba(C["blue"], 0.12),
        line=dict(color=C["blue"], width=2),
        marker=dict(color=C["blue"], size=6),
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 100],
                            tickfont=dict(size=8, color=C["muted"]),
                            gridcolor=C["border"], linecolor=C["border"]),
            angularaxis=dict(tickfont=dict(size=9, color=C["muted"]),
                             gridcolor=C["border"], linecolor=C["border"]),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        height=260,
        margin=dict(l=40, r=40, t=20, b=20),
        font=dict(family="Inter", color=C["muted"]),
    )
    return fig

def multi_trend_chart(df):
    fig = go.Figure()
    param_colors = {
        "moisture": C["blue"], "temperature": "#FF6B6B",
        "ph": C["purple"], "conductivity": "#F59E0B",
        "nitrogen": C["green"], "phosphorus": "#06B6D4", "potassium": "#EC4899",
    }
    if df is None or df.empty:
        fig.update_layout(**PLOTLY_LAYOUT, height=280)
        return fig
    for key, color in param_colors.items():
        if key not in df.columns:
            continue
        fig.add_trace(go.Scatter(
            x=df["recorded_at"], y=df[key],
            name=PARAMS[key]["label"],
            mode="lines",
            line=dict(color=color, width=1.5),
            opacity=0.85,
        ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=C["muted"]),
        margin=dict(l=0, r=0, t=0, b=0),
        height=280,
        showlegend=True,
        legend=dict(orientation="h", y=-0.15, font=dict(size=10, color=C["muted"]),
                    bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(showgrid=False, tickfont=dict(size=9, color=C["muted"]),
                   tickformat="%H:%M"),
        yaxis=dict(showgrid=True, gridcolor="rgba(51,65,85,0.35)",
                   tickfont=dict(size=9, color=C["muted"])),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=C["surface"], bordercolor=C["border"],
                        font=dict(size=11, color=C["text"])),
    )
    return fig