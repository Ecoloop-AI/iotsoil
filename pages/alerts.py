"""pages/alerts.py — Alert management page"""
from dash import html, dcc
import plotly.graph_objects as go
from datetime import datetime
import data_service as ds
from data_service import PARAMS, C, hex_to_rgba
import components as ui

SEV_STYLE = {
    "CRITICAL": {"icon": "■", "color": C["red"],    "bg": "rgba(239,68,68,0.08)",   "border": "rgba(239,68,68,0.25)"},
    "WARNING":  {"icon": "▲", "color": C["yellow"], "bg": "rgba(245,158,11,0.08)",  "border": "rgba(245,158,11,0.25)"},
    "INFO":     {"icon": "●", "color": C["blue"],   "bg": "rgba(0,212,255,0.08)",   "border": "rgba(0,212,255,0.25)"},
}

def layout(store):
    latest  = store.get("latest") or {}
    history = store.get("history") or []
    alerts  = ds.get_alerts(latest)
    crit    = [a for a in alerts if a["severity"] == "CRITICAL"]
    warn    = [a for a in alerts if a["severity"] == "WARNING"]

    # build synthetic alert history from all historical rows
    hist_alerts = []
    for row in history:
        for a in ds.get_alerts(row):
            a["recorded_at"] = row.get("recorded_at", "")
            hist_alerts.append(a)
    hist_alerts = hist_alerts[:50]

    return html.Div([

        # ── Summary KPI strip ──
        html.Div([
            _count_card("Active Alerts",   len(alerts), C["blue"]),
            _count_card("Critical",        len(crit),   C["red"]),
            _count_card("Warnings",        len(warn),   C["yellow"]),
            _count_card("Parameters OK",   7 - len({a["param"] for a in alerts}), C["green"]),
        ], style={"display": "grid", "gridTemplateColumns": "repeat(4,1fr)",
                  "gap": "14px", "marginBottom": "24px"}),

        # ── Active alerts + severity chart ──
        html.Div([

            # Active alerts list
            html.Div([
                ui.section_title("Active Alerts"),
                html.Div(
                    [_alert_card(a) for a in alerts] if alerts
                    else [html.Div([
                        html.Div("✓", style={"fontSize": "32px", "color": C["green"]}),
                        html.Div("All parameters within normal range",
                                 style={"color": C["muted"], "fontSize": "13px", "marginTop": "8px"}),
                    ], style={"textAlign": "center", "padding": "40px 0"})],
                    style={"background": "rgba(15,23,42,0.8)",
                           "border": f"1px solid {C['border']}",
                           "borderRadius": "12px", "padding": "0 20px"},
                ),
            ], style={"flex": "2", "minWidth": "0"}),

            # Severity breakdown chart
            html.Div([
                ui.section_title("Severity Breakdown"),
                dcc.Graph(
                    figure=_severity_pie(len(crit), len(warn), 7-len(alerts)),
                    config={"displayModeBar": False},
                    style={"height": "260px"},
                ),
                html.Div([
                    _legend_row("■ Critical", len(crit), C["red"]),
                    _legend_row("▲ Warning",  len(warn),  C["yellow"]),
                    _legend_row("● Normal",   7-len({a["param"] for a in alerts}), C["green"]),
                ], style={"padding": "0 8px"}),
            ], style={
                "background": "rgba(15,23,42,0.8)", "border": f"1px solid {C['border']}",
                "borderRadius": "14px", "padding": "20px", "flex": "1", "minWidth": "240px",
            }),

        ], style={"display": "flex", "gap": "16px", "marginBottom": "24px"}),

        # ── Alert rules reference ──
        ui.section_title("Alert Thresholds"),
        _threshold_table(),

        # ── Alert history ──
        html.Div(style={"height": "24px"}),
        ui.section_title("Alert History"),
        _history_table(hist_alerts),

    ])

def _count_card(label, count, color):
    return html.Div([
        html.Div(str(count), style={
            "fontSize": "40px", "fontWeight": "700",
            "color": color, "fontFamily": "'JetBrains Mono', monospace",
            "lineHeight": "1"}),
        html.Div(label, style={"fontSize": "11px", "color": C["muted"],
                               "marginTop": "6px", "letterSpacing": "0.5px"}),
    ], style={
        "background": "rgba(15,23,42,0.8)", "border": f"1px solid {C['border']}",
        "borderTop": f"2px solid {color}",
        "borderRadius": "12px", "padding": "20px",
    })

def _alert_card(a):
    s = SEV_STYLE.get(a["severity"], SEV_STYLE["WARNING"])
    return html.Div([
        html.Div([
            html.Span(s["icon"], style={"color": s["color"], "fontSize": "16px",
                                        "flexShrink": "0", "marginTop": "2px"}),
            html.Div([
                html.Div([
                    html.Span(a["severity"], style={
                        "fontSize": "10px", "fontWeight": "700",
                        "color": s["color"], "letterSpacing": "1px",
                        "background": s["bg"], "border": f"1px solid {s['border']}",
                        "padding": "2px 8px", "borderRadius": "10px",
                        "marginRight": "8px"}),
                    html.Span(PARAMS.get(a["param"], {}).get("label", a["param"]),
                              style={"fontSize": "11px", "color": C["muted"]}),
                ]),
                html.Div(a["message"], style={
                    "fontSize": "13px", "color": C["text"],
                    "fontWeight": "500", "marginTop": "4px"}),
                html.Div([
                    html.Span("Value: ", style={"color": C["muted"], "fontSize": "11px"}),
                    html.Span(
                        f"{a['value']} {PARAMS.get(a['param'],{}).get('unit','')}",
                        style={"color": s["color"], "fontSize": "11px",
                               "fontFamily": "'JetBrains Mono', monospace",
                               "fontWeight": "600"}),
                ], style={"marginTop": "4px"}),
            ]),
            html.Span(a.get("time", ""), style={
                "fontSize": "10px", "color": C["muted"],
                "fontFamily": "'JetBrains Mono', monospace",
                "marginLeft": "auto", "flexShrink": "0"}),
        ], style={"display": "flex", "gap": "14px", "alignItems": "flex-start"}),
    ], style={
        "padding": "16px 0",
        "borderBottom": f"1px solid rgba(30,41,59,0.5)",
    })

def _severity_pie(crit, warn, ok):
    fig = go.Figure(go.Pie(
        labels=["Critical", "Warning", "Normal"],
        values=[max(crit, 0), max(warn, 0), max(ok, 0)],
        hole=0.65,
        marker=dict(colors=[C["red"], C["yellow"], C["green"]],
                    line=dict(color="#0F172A", width=2)),
        textinfo="none",
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", height=260,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        font=dict(family="Inter"),
        annotations=[dict(
            text=f"{crit+warn}<br><span style='font-size:10px'>issues</span>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=22, color=C["red"] if crit else C["yellow"] if warn else C["green"],
                      family="JetBrains Mono"),
        )],
    )
    return fig

def _legend_row(label, val, color):
    return html.Div([
        html.Span(label, style={"color": color, "fontSize": "12px"}),
        html.Span(str(val), style={"color": C["text"], "fontSize": "13px",
                                   "fontWeight": "600", "marginLeft": "auto",
                                   "fontFamily": "'JetBrains Mono', monospace"}),
    ], style={"display": "flex", "padding": "6px 0",
              "borderBottom": f"1px solid {C['border']}"})

def _threshold_table():
    rules = [
        ("Moisture",      "< 20 %",        "CRITICAL", C["red"]),
        ("Moisture",      "> 80 %",        "WARNING",  C["yellow"]),
        ("pH",            "< 5.5 or > 7.5","WARNING",  C["yellow"]),
        ("Temperature",   "> 40 °C",       "CRITICAL", C["red"]),
        ("Temperature",   "< 5 °C",        "WARNING",  C["yellow"]),
        ("EC",            "> 1500 µS/cm",  "WARNING",  C["yellow"]),
        ("Nitrogen",      "< 20 mg/kg",    "WARNING",  C["yellow"]),
        ("Phosphorus",    "< 10 mg/kg",    "WARNING",  C["yellow"]),
        ("Potassium",     "< 50 mg/kg",    "WARNING",  C["yellow"]),
    ]
    return html.Div(
        html.Table([
            html.Thead(html.Tr([
                html.Th(h, style={"padding": "10px 14px", "textAlign": "left",
                                  "color": C["muted"], "fontSize": "10px",
                                  "letterSpacing": "1.5px", "textTransform": "uppercase",
                                  "borderBottom": f"1px solid {C['border']}"})
                for h in ["Parameter", "Condition", "Severity"]
            ])),
            html.Tbody([
                html.Tr([
                    html.Td(r[0], style={"padding": "11px 14px",
                                         "borderBottom": f"1px solid rgba(30,41,59,0.5)",
                                         "color": C["muted"], "fontSize": "12px"}),
                    html.Td(r[1], style={"padding": "11px 14px",
                                         "borderBottom": f"1px solid rgba(30,41,59,0.5)",
                                         "color": C["text"], "fontSize": "12px",
                                         "fontFamily": "'JetBrains Mono', monospace"}),
                    html.Td(html.Span(r[2], style={
                        "fontSize": "10px", "fontWeight": "700",
                        "color": r[3], "letterSpacing": "1px"}),
                        style={"padding": "11px 14px",
                               "borderBottom": f"1px solid rgba(30,41,59,0.5)"}),
                ]) for r in rules
            ]),
        ], style={"width": "100%", "borderCollapse": "collapse"}),
        style={"background": "rgba(15,23,42,0.8)", "border": f"1px solid {C['border']}",
               "borderRadius": "12px", "overflow": "hidden"})

def _history_table(hist_alerts):
    if not hist_alerts:
        return html.Div("No historical alerts", style={"color": C["muted"], "fontSize": "13px"})
    return html.Div(
        html.Table([
            html.Thead(html.Tr([
                html.Th(h, style={"padding": "10px 14px", "textAlign": "left",
                                  "color": C["muted"], "fontSize": "10px",
                                  "letterSpacing": "1.5px", "textTransform": "uppercase",
                                  "borderBottom": f"1px solid {C['border']}"})
                for h in ["Time", "Parameter", "Severity", "Message", "Value"]
            ])),
            html.Tbody([
                html.Tr([
                    html.Td(str(a.get("recorded_at",""))[:19],
                            style={"padding": "10px 14px",
                                   "borderBottom": f"1px solid rgba(30,41,59,0.5)",
                                   "color": C["muted"], "fontSize": "11px",
                                   "fontFamily": "'JetBrains Mono', monospace"}),
                    html.Td(PARAMS.get(a["param"],{}).get("label", a["param"]),
                            style={"padding": "10px 14px",
                                   "borderBottom": f"1px solid rgba(30,41,59,0.5)",
                                   "color": C["muted"], "fontSize": "12px"}),
                    html.Td(html.Span(a["severity"],
                                      style={"color": SEV_STYLE.get(a["severity"],
                                             SEV_STYLE["WARNING"])["color"],
                                             "fontSize": "10px", "fontWeight": "700",
                                             "letterSpacing": "1px"}),
                            style={"padding": "10px 14px",
                                   "borderBottom": f"1px solid rgba(30,41,59,0.5)"}),
                    html.Td(a["message"],
                            style={"padding": "10px 14px",
                                   "borderBottom": f"1px solid rgba(30,41,59,0.5)",
                                   "color": C["muted"], "fontSize": "12px"}),
                    html.Td(f"{a['value']} {PARAMS.get(a['param'],{}).get('unit','')}",
                            style={"padding": "10px 14px",
                                   "borderBottom": f"1px solid rgba(30,41,59,0.5)",
                                   "color": C["text"], "fontSize": "12px",
                                   "fontFamily": "'JetBrains Mono', monospace"}),
                ]) for a in hist_alerts
            ]),
        ], style={"width": "100%", "borderCollapse": "collapse"}),
        style={"background": "rgba(15,23,42,0.8)", "border": f"1px solid {C['border']}",
               "borderRadius": "12px", "overflow": "hidden", "overflowX": "auto"})
