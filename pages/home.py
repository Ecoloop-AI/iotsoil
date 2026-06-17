"""pages/home.py — Main dashboard page"""
from dash import html, dcc
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import data_service as ds
from data_service import PARAMS, C, hex_to_rgba, get_status, soil_health_score
import components as ui

def layout(store):
    latest  = store.get("latest") or {}
    history = store.get("history") or []
    df      = ds.to_df(history)
    score   = soil_health_score(latest)
    alerts  = ds.get_alerts(latest)
    ts      = latest.get("recorded_at", "")
    try:
        ts_fmt = datetime.fromisoformat(ts).strftime("%d %b %Y  %H:%M:%S")
    except Exception:
        ts_fmt = ts or "—"

    # ── history per param for sparklines ──
    spark = {}
    for k in PARAMS:
        spark[k] = df[k].tolist()[-20:] if not df.empty and k in df.columns else []

    # ── alert count badge ──
    crit = sum(1 for a in alerts if a["severity"] == "CRITICAL")
    warn = sum(1 for a in alerts if a["severity"] == "WARNING")

    return html.Div([

        # ── System Banner ──────────────────────────────────────
        html.Div([
            html.Div([
                html.Div([
                    html.Div("SYSTEM OPERATIONAL", style={
                        "fontSize": "10px", "fontWeight": "700",
                        "color": C["green"], "letterSpacing": "2px"}),
                    html.Div(f"Last sync: {ts_fmt}", style={
                        "fontSize": "11px", "color": C["muted"],
                        "fontFamily": "'JetBrains Mono', monospace", "marginTop": "2px"}),
                ]),
            ], style={"display": "flex", "alignItems": "center", "gap": "16px"}),

            html.Div([
                # Alert summary
                html.Div([
                    html.Span(f"■ {crit} CRITICAL", style={
                        "color": C["red"], "fontSize": "11px", "fontWeight": "600",
                        "marginRight": "16px"}),
                    html.Span(f"▲ {warn} WARNING", style={
                        "color": C["yellow"], "fontSize": "11px", "fontWeight": "600"}),
                ]) if (crit + warn) > 0 else html.Div(),
                html.Div([
                    html.Div(style={"width": "8px", "height": "8px",
                                    "borderRadius": "50%", "background": C["green"],
                                    "animation": "pulse 2s infinite"}),
                    html.Span("ESP32_01 ONLINE", style={
                        "fontSize": "11px", "color": C["green"],
                        "fontFamily": "'JetBrains Mono', monospace",
                        "fontWeight": "600", "marginLeft": "8px"}),
                ], style={"display": "flex", "alignItems": "center",
                          "background": "rgba(16,185,129,0.08)",
                          "border": "1px solid rgba(16,185,129,0.25)",
                          "padding": "6px 14px", "borderRadius": "20px",
                          "marginLeft": "16px"}),
            ], style={"display": "flex", "alignItems": "center"}),
        ], style={
            "background": "rgba(15,23,42,0.8)",
            "border": f"1px solid {C['border']}",
            "borderRadius": "12px",
            "padding": "14px 20px",
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "marginBottom": "20px",
        }),

        # ── KPI Cards (7 params) — each card is a clickable link ─
        ui.section_title("Live Sensor Readings"),
        html.Div([
            dcc.Link(
                ui.kpi_card(k, latest.get(k), spark.get(k)),
                href=f"/param/{k}",
                style={"textDecoration": "none", "display": "block"},
                title=f"View {PARAMS[k]['label']} details",
            )
            for k in PARAMS
        ], className="grid-7", style={"marginBottom": "24px"}),

        # ── Overview row 1: trend + health score ───────────────
        ui.section_title("System Overview"),
        html.Div([

            # Multi-trend chart
            html.Div([
                html.Div("Real-Time Parameter Trends", style={
                    "fontSize": "12px", "color": C["muted"], "marginBottom": "12px",
                    "fontWeight": "500", "letterSpacing": "0.5px"}),
                dcc.Graph(
                    figure=ui.multi_trend_chart(df),
                    config={"displayModeBar": False},
                    style={"height": "280px"},
                ),
            ], style={
                "background": "rgba(15,23,42,0.8)", "border": f"1px solid {C['border']}",
                "borderRadius": "14px", "padding": "20px", "flex": "2", "minWidth": "0",
            }),

            # Health score gauge
            html.Div([
                dcc.Graph(
                    figure=ui.health_score_gauge(score),
                    config={"displayModeBar": False},
                    style={"height": "220px"},
                ),
                _score_legend(score),
            ], style={
                "background": "rgba(15,23,42,0.8)", "border": f"1px solid {C['border']}",
                "borderRadius": "14px", "padding": "20px", "flex": "1", "minWidth": "260px",
            }),

        ], style={"display": "flex", "gap": "16px", "marginBottom": "16px"}),

        # ── Overview row 2: radar + daily averages + gauges ────
        html.Div([

            # Radar
            html.Div([
                html.Div("Parameter Balance Radar", style={
                    "fontSize": "12px", "color": C["muted"], "marginBottom": "8px"}),
                dcc.Graph(
                    figure=ui.radar_chart(latest),
                    config={"displayModeBar": False},
                    style={"height": "260px"},
                ),
            ], style={
                "background": "rgba(15,23,42,0.8)", "border": f"1px solid {C['border']}",
                "borderRadius": "14px", "padding": "20px", "flex": "1", "minWidth": "260px",
            }),

            # Moisture & Temp gauges
            html.Div([
                html.Div("Key Gauges", style={
                    "fontSize": "12px", "color": C["muted"], "marginBottom": "12px"}),
                html.Div([
                    dcc.Graph(
                        figure=ui.gauge_chart(
                            latest.get("moisture"), "Moisture", 100, C["blue"], "%"),
                        config={"displayModeBar": False},
                        style={"flex": "1"},
                    ),
                    dcc.Graph(
                        figure=ui.gauge_chart(
                            latest.get("temperature"), "Temperature", 60, "#FF6B6B", "°C"),
                        config={"displayModeBar": False},
                        style={"flex": "1"},
                    ),
                ], style={"display": "flex", "gap": "8px"}),
                html.Div([
                    dcc.Graph(
                        figure=ui.gauge_chart(
                            latest.get("ph"), "pH", 14, C["purple"], ""),
                        config={"displayModeBar": False},
                        style={"flex": "1"},
                    ),
                    dcc.Graph(
                        figure=ui.gauge_chart(
                            latest.get("conductivity"), "EC", 2000, C["yellow"], "µS/cm"),
                        config={"displayModeBar": False},
                        style={"flex": "1"},
                    ),
                ], style={"display": "flex", "gap": "8px"}),
            ], style={
                "background": "rgba(15,23,42,0.8)", "border": f"1px solid {C['border']}",
                "borderRadius": "14px", "padding": "20px", "flex": "1", "minWidth": "280px",
            }),

            # NPK daily bar chart
            html.Div([
                html.Div("NPK Current Levels", style={
                    "fontSize": "12px", "color": C["muted"], "marginBottom": "12px"}),
                dcc.Graph(
                    figure=_npk_bar(latest),
                    config={"displayModeBar": False},
                    style={"height": "260px"},
                ),
            ], style={
                "background": "rgba(15,23,42,0.8)", "border": f"1px solid {C['border']}",
                "borderRadius": "14px", "padding": "20px", "flex": "1", "minWidth": "240px",
            }),

        ], style={"display": "flex", "gap": "16px", "marginBottom": "24px"}),

        # ── Active Alerts strip ─────────────────────────────────
        _alerts_strip(alerts) if alerts else html.Div(),

        # ── Data table ─────────────────────────────────────────
        ui.section_title("Recent Readings"),
        _data_table(history[:10]),

    ])

# ── helpers ──────────────────────────────────────────────────────
def _score_legend(score):
    label = "Excellent" if score >= 80 else "Good" if score >= 60 else \
            "Fair" if score >= 40 else "Poor"
    color = C["green"] if score >= 70 else C["yellow"] if score >= 40 else C["red"]
    items = [
        ("■ Excellent", "≥ 80", C["green"]),
        ("■ Good",      "≥ 60", C["blue"]),
        ("■ Fair",      "≥ 40", C["yellow"]),
        ("■ Poor",      "< 40", C["red"]),
    ]
    return html.Div([
        html.Div(label, style={"fontSize": "18px", "fontWeight": "700",
                               "color": color, "textAlign": "center", "marginBottom": "12px"}),
        html.Div([
            html.Div([
                html.Span(i[0], style={"color": i[2], "fontSize": "10px"}),
                html.Span(i[1], style={"color": C["muted"], "fontSize": "10px",
                                       "marginLeft": "4px"}),
            ]) for i in items
        ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr",
                  "gap": "6px", "padding": "0 8px"}),
    ])

def _npk_bar(latest):
    labels = ["N", "P", "K"]
    vals   = [latest.get("nitrogen", 0), latest.get("phosphorus", 0), latest.get("potassium", 0)]
    colors = [C["green"], "#06B6D4", "#EC4899"]
    fig = go.Figure()
    for l, v, c in zip(labels, vals, colors):
        fig.add_trace(go.Bar(
            x=[l], y=[v or 0], name=l,
            marker_color=c, marker_line_width=0,
            text=[f"{v or 0:.0f}"], textposition="outside",
            textfont=dict(size=11, color=c),
            width=0.5,
        ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False, height=260,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis=dict(showgrid=True, gridcolor="rgba(51,65,85,0.35)",
                   zeroline=False, tickfont=dict(size=9, color=C["muted"])),
        xaxis=dict(showgrid=False, tickfont=dict(size=13, color=C["text"], family="JetBrains Mono")),
        font=dict(family="Inter", color=C["muted"]),
        bargap=0.4,
    )
    return fig

def _alerts_strip(alerts):
    sev_icon = {"CRITICAL": ("■", C["red"]), "WARNING": ("▲", C["yellow"])}
    return html.Div([
        ui.section_title("Active Alerts", html.Span(
            f"{len(alerts)}", style={
                "background": C["red"] if any(a["severity"]=="CRITICAL" for a in alerts) else C["yellow"],
                "color": "#000", "fontSize": "10px", "fontWeight": "700",
                "padding": "2px 8px", "borderRadius": "10px"})),
        html.Div([
            html.Div([
                html.Div([
                    html.Span(sev_icon.get(a["severity"], ("▲", C["yellow"]))[0],
                              style={"color": sev_icon.get(a["severity"], ("▲",C["yellow"]))[1],
                                     "fontSize": "14px", "flexShrink": "0"}),
                    html.Div([
                        html.Div(a["message"], style={
                            "fontSize": "13px", "color": C["text"], "fontWeight": "500"}),
                        html.Div([
                            html.Span(PARAMS.get(a["param"],{}).get("label",""),
                                      style={"color": C["muted"], "fontSize": "11px"}),
                            html.Span(f"  •  {a['value']} {PARAMS.get(a['param'],{}).get('unit','')}",
                                      style={"color": C["muted"], "fontSize": "11px",
                                             "fontFamily": "'JetBrains Mono', monospace"}),
                        ]),
                    ]),
                    html.Span(a["time"], style={
                        "fontSize": "10px", "color": C["muted"],
                        "fontFamily": "'JetBrains Mono', monospace",
                        "marginLeft": "auto"}),
                ], className="alert-row"),
            ]) for a in alerts
        ], style={"background": "rgba(15,23,42,0.8)", "border": f"1px solid {C['border']}",
                  "borderRadius": "12px", "padding": "0 20px",
                  "marginBottom": "24px"}),
    ])

def _data_table(rows):
    if not rows:
        return html.Div("No data", style={"color": C["muted"], "fontSize": "13px"})
    cols = ["recorded_at", "moisture", "temperature", "ph",
            "conductivity", "nitrogen", "phosphorus", "potassium"]
    headers = ["Timestamp", "Moisture %", "Temp °C", "pH",
               "EC µS/cm", "N mg/kg", "P mg/kg", "K mg/kg"]
    return html.Div(
        html.Table([
            html.Thead(html.Tr([
                html.Th(h, style={"padding": "10px 14px", "textAlign": "left",
                                  "color": C["muted"], "fontSize": "10px",
                                  "fontWeight": "600", "letterSpacing": "1.5px",
                                  "textTransform": "uppercase",
                                  "borderBottom": f"1px solid {C['border']}"})
                for h in headers])),
            html.Tbody([
                html.Tr([
                    html.Td(
                        str(row.get(c, "—"))[:19] if c == "recorded_at"
                        else f"{float(row.get(c,0)):.1f}" if row.get(c) is not None else "—",
                        style={"padding": "11px 14px",
                               "borderBottom": f"1px solid rgba(30,41,59,0.5)",
                               "color": C["muted"],
                               "fontSize": "12px",
                               "fontFamily": "'JetBrains Mono', monospace"})
                    for c in cols
                ]) for row in rows
            ]),
        ], style={"width": "100%", "borderCollapse": "collapse"}),
        style={"background": "rgba(15,23,42,0.8)", "border": f"1px solid {C['border']}",
               "borderRadius": "12px", "overflow": "hidden", "overflowX": "auto"})