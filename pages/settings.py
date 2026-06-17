"""pages/settings.py — Settings & configuration page"""
from dash import html, dcc
from data_service import PARAMS, C
import components as ui

def layout():
    return html.Div([
        ui.section_title("System Configuration"),

        # ── Connection settings ──
        html.Div([
            html.Div("API Connection", style={"fontSize": "14px", "fontWeight": "600",
                                              "color": C["text"], "marginBottom": "16px"}),
            html.Div([
                html.Div([
                    html.Label("API Endpoint URL", style=_label_style),
                    dcc.Input(value="https://ecoloop.in/soil_api/get_soil.php",
                              style=_input_style, className="iot-input"),
                ], style={"flex": "2", "minWidth": "0"}),
                html.Div([
                    html.Label("Refresh Interval (s)", style=_label_style),
                    dcc.Input(value="30", type="number", min=5, max=300,
                              style=_input_style, className="iot-input"),
                ], style={"flex": "1"}),
                html.Div([
                    html.Label("History Limit", style=_label_style),
                    dcc.Input(value="100", type="number", min=10, max=1000,
                              style=_input_style, className="iot-input"),
                ], style={"flex": "1"}),
            ], style={"display": "flex", "gap": "16px"}),
        ], style=_card_style, className="kpi-card"),

        html.Div(style={"height": "16px"}),

        # ── Alert thresholds ──
        html.Div([
            html.Div("Alert Thresholds", style={"fontSize": "14px", "fontWeight": "600",
                                                 "color": C["text"], "marginBottom": "16px"}),
            html.Div([
                _threshold_row(k, meta) for k, meta in PARAMS.items()
            ]),
            html.Button("Save Thresholds", className="iot-btn",
                        style={"marginTop": "16px"}),
        ], style=_card_style, className="kpi-card"),

        html.Div(style={"height": "16px"}),

        # ── System info ──
        html.Div([
            html.Div("System Information", style={"fontSize": "14px", "fontWeight": "600",
                                                   "color": C["text"], "marginBottom": "16px"}),
            html.Div([
                _info_row("Platform",      "Python Dash + Plotly"),
                _info_row("Sensor",        "7-in-1 Soil Sensor (RS485 Modbus)"),
                _info_row("Controller",    "ESP32"),
                _info_row("Protocol",      "HTTP POST → cPanel MySQL"),
                _info_row("Data Host",     "ecoloop.in"),
                _info_row("Dashboard Ver", "2.0.0"),
            ]),
        ], style=_card_style, className="kpi-card"),

    ])

# ── helpers ──────────────────────────────────────────────────────
_label_style = {
    "fontSize": "10px", "color": C["muted"], "letterSpacing": "1px",
    "marginBottom": "6px", "display": "block", "textTransform": "uppercase",
}
_input_style = {
    "background": "#0A1628", "border": f"1px solid {C['border']}",
    "color": C["text"], "borderRadius": "8px", "padding": "8px 12px",
    "fontSize": "13px", "fontFamily": "'JetBrains Mono', monospace",
    "width": "100%",
}
_card_style = {
    "background": "linear-gradient(135deg, rgba(30,41,59,0.9), rgba(15,23,42,0.95))",
    "border": f"1px solid {C['border']}",
    "borderRadius": "16px", "padding": "24px", "marginBottom": "0",
}

def _threshold_row(key, meta):
    return html.Div([
        html.Div([
            html.Span(meta["icon"], style={"fontSize": "16px", "marginRight": "10px"}),
            html.Span(meta["label"], style={"fontSize": "13px", "color": C["text"],
                                            "fontWeight": "500", "minWidth": "130px"}),
            html.Span(meta["unit"], style={"fontSize": "11px", "color": C["muted"],
                                           "minWidth": "60px"}),
        ], style={"display": "flex", "alignItems": "center", "flex": "1"}),
        html.Div([
            html.Label("Low warning", style=_label_style),
            dcc.Input(value=meta["lo"], type="number", step=0.1,
                      style={**_input_style, "width": "100px"},
                      className="iot-input"),
        ], style={"marginRight": "16px"}),
        html.Div([
            html.Label("High warning", style=_label_style),
            dcc.Input(value=meta["hi"], type="number", step=0.1,
                      style={**_input_style, "width": "100px"},
                      className="iot-input"),
        ]),
    ], style={"display": "flex", "alignItems": "center", "padding": "12px 0",
              "borderBottom": f"1px solid rgba(30,41,59,0.5)"})

def _info_row(label, value):
    return html.Div([
        html.Span(label, style={"fontSize": "12px", "color": C["muted"],
                                "minWidth": "160px", "display": "inline-block"}),
        html.Span(value, style={"fontSize": "12px", "color": C["text"],
                                "fontFamily": "'JetBrains Mono', monospace"}),
    ], style={"padding": "10px 0", "borderBottom": f"1px solid rgba(30,41,59,0.5)"})
