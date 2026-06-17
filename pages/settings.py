"""pages/settings.py — Settings & configuration page"""
from datetime import datetime
from dash import html, dcc, callback, Output, Input, State, ALL
import data_service as ds
from data_service import PARAMS, C
import components as ui

def layout():
    thresholds = ds.get_thresholds()   # current saved (or default) values
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
                _threshold_row(k, meta, thresholds.get(k, meta)) for k, meta in PARAMS.items()
            ]),
            html.Div([
                html.Button("Save Thresholds", id="save-thresholds-btn",
                            n_clicks=0, className="iot-btn"),
                html.Div(id="save-status", style={"fontSize": "12px",
                                                   "color": C["green"],
                                                   "marginLeft": "14px"}),
            ], style={"display": "flex", "alignItems": "center", "marginTop": "16px"}),
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

def _threshold_row(key, meta, current):
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
            dcc.Input(
                id={"type": "thresh-lo", "param": key},
                value=current["lo"], type="number", step=0.1,
                style={**_input_style, "width": "100px"},
                className="iot-input"),
        ], style={"marginRight": "16px"}),
        html.Div([
            html.Label("High warning", style=_label_style),
            dcc.Input(
                id={"type": "thresh-hi", "param": key},
                value=current["hi"], type="number", step=0.1,
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

# ── Save Thresholds callback ─────────────────────────────────────
# Pattern-matching State (ALL) reads every low/high input on the page in
# one shot, regardless of how many parameters PARAMS contains, and writes
# them through data_service.set_thresholds(), which persists to disk and
# busts the threshold cache. The next sensor-store refresh (or any
# get_status/get_alerts call) immediately sees the new values.
@callback(
    Output("save-status", "children"),
    Input("save-thresholds-btn", "n_clicks"),
    State({"type": "thresh-lo", "param": ALL}, "value"),
    State({"type": "thresh-lo", "param": ALL}, "id"),
    State({"type": "thresh-hi", "param": ALL}, "value"),
    prevent_initial_call=True,
)
def save_thresholds(n_clicks, lo_values, lo_ids, hi_values):
    new_values = {}
    for lo_id, lo_val, hi_val in zip(lo_ids, lo_values, hi_values):
        if lo_val is None or hi_val is None:
            continue
        param = lo_id["param"]
        if float(lo_val) >= float(hi_val):
            return f"⚠ {param.title()}: low warning must be less than high warning — not saved"
        new_values[param] = {"lo": lo_val, "hi": hi_val}
    ds.set_thresholds(new_values)
    return f"✓ Saved at {datetime.now().strftime('%H:%M:%S')} — now live on the dashboard"
