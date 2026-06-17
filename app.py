"""
app.py — SoilSense IIoT Dashboard entry point
Run: python app.py  →  http://localhost:8050
"""
import dash
from dash import dcc, html, Input, Output, State, callback
from datetime import datetime
import data_service as ds
from data_service import C

app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    title="SoilSense IIoT",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server

import pages.home            as home_page
import pages.analytics       as analytics_page
import pages.reports         as reports_page
import pages.alerts          as alerts_page
import pages.settings        as settings_page
import pages.parameter_detail as param_page

NAV = [
    ("/",                    "⬡",  "Dashboard",   "MAIN"),
    ("/analytics",           "◈",  "Analytics",   None),
    ("/reports",             "▦",  "Reports",     None),
    ("/alerts",              "◉",  "Alerts",      None),
    ("/param/moisture",      "◌",  "Moisture",    "PARAMETERS"),
    ("/param/temperature",   "◌",  "Temperature", None),
    ("/param/ph",            "◌",  "Soil pH",     None),
    ("/param/conductivity",  "◌",  "EC",          None),
    ("/param/nitrogen",      "◌",  "Nitrogen",    None),
    ("/param/phosphorus",    "◌",  "Phosphorus",  None),
    ("/param/potassium",     "◌",  "Potassium",   None),
    ("/settings",            "◧",  "Settings",    "SYSTEM"),
]

def sidebar():
    items = []
    for href, icon, label, section in NAV:
        if section:
            items.append(html.Div(section, style={
                "fontSize": "9px", "fontWeight": "700", "letterSpacing": "2px",
                "color": "#334155", "padding": "16px 20px 6px",
            }))
        items.append(dcc.Link(
            html.Div([
                html.Span(icon, style={"fontSize": "13px", "width": "18px",
                                       "textAlign": "center", "flexShrink": "0",
                                       "color": "#475569"}),
                html.Span(label, style={"fontSize": "13px", "fontWeight": "500"}),
            ], className="nav-item"),
            href=href, style={"textDecoration": "none"},
        ))
    return html.Div([
        html.Div([
            html.Div([
                html.Div("⬡", style={"fontSize": "22px", "color": C["blue"]}),
                html.Div("⬡", style={"fontSize": "14px", "color": C["blue"],
                                     "opacity": "0.5", "marginLeft": "-8px", "marginTop": "4px"}),
            ], style={"display": "flex"}),
            html.Div([
                html.Div("SOILSENSE", style={"fontSize": "12px", "fontWeight": "700",
                                              "color": C["text"], "letterSpacing": "3px"}),
                html.Div("IIoT PLATFORM v2", style={"fontSize": "8px", "color": "#334155",
                                                     "letterSpacing": "2px"}),
            ]),
        ], style={"display": "flex", "alignItems": "center", "gap": "10px",
                  "padding": "22px 20px 18px", "borderBottom": f"1px solid {C['border']}",
                  "marginBottom": "4px"}),
        html.Div(items),
        html.Div([
            html.Div([
                html.Div(style={"width": "7px", "height": "7px", "borderRadius": "50%",
                                "background": C["green"], "animation": "pulse 2s infinite",
                                "flexShrink": "0"}),
                html.Div([
                    html.Div("ESP32_01", style={"fontSize": "11px", "color": C["green"],
                                                "fontFamily": "'JetBrains Mono', monospace",
                                                "fontWeight": "600"}),
                    html.Div("Dr Hullash Collabrated with ecoloop.in ", style={"fontSize": "9px", "color": "#334155",
                                                   "fontFamily": "'JetBrains Mono', monospace"}),
                ]),
            ], style={"display": "flex", "alignItems": "center", "gap": "8px"}),
        ], style={"position": "absolute", "bottom": "20px", "left": "0", "right": "0",
                  "padding": "0 16px"}),
    ], style={"width": "210px", "minHeight": "100vh", "background": "#0A0F1E",
              "borderRight": f"1px solid {C['border']}", "position": "fixed",
              "top": "0", "left": "0", "zIndex": "200",
              "overflowY": "auto", "overflowX": "hidden"})

def topbar():
    return html.Div([
        html.Div(id="page-title", style={"fontSize": "15px", "fontWeight": "600",
                                          "color": C["text"], "letterSpacing": "0.5px"}),
        html.Div([
            html.Div(id="live-clock", style={"fontSize": "12px",
                "fontFamily": "'JetBrains Mono', monospace",
                "color": "#475569", "marginRight": "20px"}),
            html.Div([
                html.Div(style={"width": "6px", "height": "6px", "borderRadius": "50%",
                                "background": C["green"], "animation": "pulse 2s infinite"}),
                html.Span("LIVE DATA", style={"fontSize": "10px", "fontWeight": "700",
                                               "color": C["green"], "letterSpacing": "1.5px",
                                               "marginLeft": "6px"}),
            ], style={"display": "flex", "alignItems": "center",
                      "background": "rgba(16,185,129,0.08)",
                      "border": "1px solid rgba(16,185,129,0.25)",
                      "padding": "5px 14px", "borderRadius": "20px"}),
        ], style={"display": "flex", "alignItems": "center"}),
    ], style={"height": "56px", "background": "#080E1C",
              "borderBottom": f"1px solid {C['border']}",
              "display": "flex", "alignItems": "center",
              "justifyContent": "space-between", "padding": "0 28px",
              "position": "fixed", "top": "0", "left": "210px", "right": "0",
              "zIndex": "199"})

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Interval(id="clock-interval", interval=1000,  n_intervals=0),
    dcc.Interval(id="data-interval",  interval=30000, n_intervals=0),
    dcc.Store(id="sensor-store"),
    sidebar(),
    topbar(),
    html.Div(id="page-content", style={
        "marginLeft": "210px", "marginTop": "56px",
        "minHeight": "calc(100vh - 56px)",
        "background": C["bg"], "padding": "24px 28px",
    }),
], style={"fontFamily": "'Inter', sans-serif", "background": C["bg"]})

@callback(Output("live-clock", "children"), Input("clock-interval", "n_intervals"))
def tick(_):
    return datetime.now().strftime("%Y-%m-%d  %H:%M:%S")

@callback(Output("sensor-store", "data"), Input("data-interval", "n_intervals"))
def refresh(_):
    return {"latest": ds.fetch_latest(), "history": ds.fetch_history(100)}

@callback(
    Output("page-content", "children"),
    Output("page-title",   "children"),
    Input("url",           "pathname"),
    State("sensor-store",  "data"),
)
def route(path, store):
    store = store or {"latest": None, "history": []}
    if not path or path == "/":
        return home_page.layout(store), "Dashboard Overview"
    if path == "/analytics":
        return analytics_page.layout(store), "Analytics"
    if path == "/reports":
        return reports_page.layout(store), "Reports"
    if path == "/alerts":
        return alerts_page.layout(store), "Alert Management"
    if path == "/settings":
        return settings_page.layout(), "Settings"
    if path and path.startswith("/param/"):
        param = path.split("/param/")[1]
        label = ds.PARAMS.get(param, {}).get("label", param.title())
        return param_page.layout(param, store), f"⬡ {label}"
    return html.Div("Page not found", style={"color": C["muted"]}), "404"

@callback(
    Output("page-content", "children", allow_duplicate=True),
    Input("sensor-store",  "data"),
    State("url",           "pathname"),
    prevent_initial_call=True,
)
def live_home(store, path):
    if path in (None, "/"):
        return home_page.layout(store or {})
    return dash.no_update

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True,port=5000)
