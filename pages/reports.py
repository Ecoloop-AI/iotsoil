"""
pages/reports.py
Old UI style + latest fast logic:
  - fetch_all() with 5-min TTL cache (no repeated HTTP calls)
  - Pure-Python date filter (works regardless of API support)
  - Table capped at 200 rows for fast render (download gets all)
  - dcc.Loading spinner so UI never looks frozen
  - CSV & Excel reuse same cached data (no double HTTP request)
"""
from dash import html, dcc, callback, Output, Input, State, no_update, ctx
import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta
import data_service as ds
from data_service import PARAMS, C, hex_to_rgba
import components as ui

# ── colour map ───────────────────────────────────────────────────
PARAM_COLORS = {
    "moisture":     C["blue"],
    "temperature":  "#FF6B6B",
    "ph":           C["purple"],
    "conductivity": "#F59E0B",
    "nitrogen":     C["green"],
    "phosphorus":   "#06B6D4",
    "potassium":    "#EC4899",
}

_CARD = {
    "background": "rgba(15,23,42,0.8)",
    "border":     f"1px solid {C['border']}",
    "borderRadius": "14px",
    "padding":    "20px 24px",
}
_LBL = {
    "fontSize": "10px", "color": C["muted"], "letterSpacing": "1px",
    "textTransform": "uppercase", "marginBottom": "6px", "display": "block",
}

# ════════════════════════════════════════════════════════════════
#  LAYOUT
# ════════════════════════════════════════════════════════════════
def layout(store):
    today    = date.today()
    week_ago = today - timedelta(days=7)

    # fetch_all is TTL-cached (5 min) — fast after first call.
    # This gives true oldest/newest dates from the full dataset.
    all_rows = ds.fetch_all(limit=2000)
    df_all   = ds.to_df(all_rows)

    if not df_all.empty:
        d_min = df_all["recorded_at"].min().date()
        d_max = df_all["recorded_at"].max().date()
        count = len(df_all)
    else:
        d_min, d_max = week_ago, today
        count = 0

    param_options = [
        {"label": html.Span(
            [html.Span(PARAMS[k]["icon"], style={"marginRight": "6px"}),
             PARAMS[k]["label"]],
            style={"display": "flex", "alignItems": "center",
                   "fontSize": "13px", "color": C["muted"]}),
         "value": k}
        for k in PARAMS
    ]

    return html.Div([

        # ── KPI summary strip (fast — from cache) ─────────────
        html.Div([
            _info_card("Total Records",  str(count),         C["blue"]),
            _info_card("Date Oldest",    str(d_min),         C["muted"]),
            _info_card("Date Newest",    str(d_max),         C["muted"]),
            _info_card("Parameters",     "7 channels",       C["green"]),
        ], style={"display": "grid", "gridTemplateColumns": "repeat(4,1fr)",
                  "gap": "14px", "marginBottom": "24px"}),

        # ── Filter panel ───────────────────────────────────────
        ui.section_title("Filter & Selection"),
        html.Div([
            html.Div([
                html.Label(f"From date  (earliest: {d_min})", style=_LBL),
                dcc.DatePickerSingle(
                    id="report-date-from",
                    date=str(d_min),
                    # NO min/max_date_allowed — user can pick any date freely
                    display_format="DD MMM YYYY",
                    first_day_of_week=1,
                    style={"width": "100%"},
                    className="iot-datepicker",
                ),
            ], style={"flex": "1", "minWidth": "160px"}),

            html.Div([
                html.Label(f"To date  (latest: {d_max})", style=_LBL),
                dcc.DatePickerSingle(
                    id="report-date-to",
                    date=str(d_max),
                    # NO min/max_date_allowed — user can pick any date freely
                    display_format="DD MMM YYYY",
                    first_day_of_week=1,
                    style={"width": "100%"},
                    className="iot-datepicker",
                ),
            ], style={"flex": "1", "minWidth": "160px"}),

            html.Div([
                html.Label("Parameters", style=_LBL),
                dcc.Dropdown(
                    id="report-params",
                    options=param_options,
                    value=["moisture", "temperature", "ph"],
                    multi=True,
                    placeholder="Select parameters...",
                    style={
                        "background": "#0A1628",
                        "border": f"1px solid {C['border']}",
                        "borderRadius": "8px",
                        "color": C["text"],
                        "fontSize": "13px",
                    },
                    className="iot-dropdown",
                ),
            ], style={"flex": "3", "minWidth": "260px"}),

            html.Div([
                html.Label("\u00a0", style=_LBL),
                html.Button("▶  Apply Filter", id="btn-apply-report",
                            n_clicks=0, className="iot-btn",
                            style={"width": "100%", "padding": "10px 0"}),
            ], style={"flex": "1", "minWidth": "130px"}),

            html.Div([
                html.Label("\u00a0", style=_LBL),
                html.Button("↺  Reset", id="btn-reset-report",
                            n_clicks=0, className="iot-btn",
                            style={"width": "100%", "padding": "10px 0",
                                   "background": "rgba(51,65,85,0.6)"}),
            ], style={"flex": "1", "minWidth": "100px"}),

        ], style={**_CARD, "display": "flex", "gap": "16px",
                  "flexWrap": "wrap", "alignItems": "flex-end",
                  "marginBottom": "20px"}),

        # ── Results — spinner wraps so UI never looks frozen ───
        dcc.Loading(
            id="report-loading",
            type="circle",
            color=C["blue"],
            children=html.Div(
                id="report-results",
                children=html.Div(
                    "Select a date range and click ▶ Apply Filter.",
                    style={"color": C["muted"], "fontSize": "13px", "padding": "20px 0"},
                ),
            ),
        ),

        # ── Export ─────────────────────────────────────────────
        html.Div(style={"height": "20px"}),
        ui.section_title("Export  ← respects current filter"),
        html.Div([
            html.Button("⬇  Download CSV", id="btn-csv", n_clicks=0,
                        className="iot-btn", style={"marginRight": "12px"}),
            html.Button("⬇  Download Excel", id="btn-excel", n_clicks=0,
                        className="iot-btn",
                        style={"background": "linear-gradient(135deg,#10B981,#065F46)"}),
            html.Span("  Downloads use the same data as the table above",
                      style={"fontSize": "11px", "color": C["muted"],
                             "marginLeft": "14px", "fontStyle": "italic"}),
            dcc.Download(id="download-csv"),
            dcc.Download(id="download-excel"),
            # lightweight store — only holds filter params, NOT the data
            dcc.Store(id="report-filter-store",
                      data={"from": str(d_min), "to": str(d_max),
                            "params": ["moisture", "temperature", "ph"]}),
        ], style={**_CARD, "display": "flex", "alignItems": "center",
                  "flexWrap": "wrap", "gap": "8px"}),
    ])

# ════════════════════════════════════════════════════════════════
#  PRIVATE HELPERS
# ════════════════════════════════════════════════════════════════
def _info_card(label, val, color):
    return html.Div([
        html.Div(val, style={"fontSize": "20px", "fontWeight": "700",
                              "color": color,
                              "fontFamily": "'JetBrains Mono', monospace"}),
        html.Div(label, style={"fontSize": "11px", "color": C["muted"],
                               "marginTop": "6px"}),
    ], style={
        "background": "rgba(15,23,42,0.8)", "border": f"1px solid {C['border']}",
        "borderTop": f"2px solid {color}",
        "borderRadius": "12px", "padding": "18px 20px",
    })

def _apply_filter(df, params, date_from, date_to):
    """Pure-Python date filter — always correct, no API dependency."""
    if df.empty:
        return pd.DataFrame()
    out = df.copy()
    try:
        if date_from:
            out = out[out["recorded_at"].dt.date >= pd.to_datetime(date_from).date()]
        if date_to:
            out = out[out["recorded_at"].dt.date <= pd.to_datetime(date_to).date()]
    except Exception:
        pass
    return out.reset_index(drop=True)

def _trend_chart(df, params):
    fig = go.Figure()
    base = dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=300, margin=dict(l=10, r=10, t=10, b=40),
        font=dict(family="Inter"),
        xaxis=dict(showgrid=False, tickfont=dict(size=9, color=C["muted"]),
                   tickformat="%d %b %H:%M", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(51,65,85,0.35)",
                   tickfont=dict(size=9, color=C["muted"]), zeroline=False),
    )
    if df.empty or not params:
        fig.update_layout(**base,
            annotations=[dict(
                text="No data — adjust the date range or parameter selection",
                xref="paper", yref="paper", x=0.5, y=0.5,
                showarrow=False, font=dict(size=13, color=C["muted"]))])
        return fig

    for k in params:
        if k not in df.columns:
            continue
        color = PARAM_COLORS.get(k, C["blue"])
        fig.add_trace(go.Scatter(
            x=df["recorded_at"], y=df[k].astype(float),
            name=f"{PARAMS[k]['icon']} {PARAMS[k]['label']} ({PARAMS[k]['unit']})",
            mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=4, color=color),
            fill="tozeroy",
            fillcolor=hex_to_rgba(color, 0.06),
            hovertemplate=(
                f"<b>{PARAMS[k]['label']}</b><br>"
                "%{x|%Y-%m-%d %H:%M}<br>"
                f"%{{y:.2f}} {PARAMS[k]['unit']}<extra></extra>"
            ),
        ))

    fig.update_layout(
        **base,
        showlegend=True,
        legend=dict(orientation="h", y=-0.2,
                    font=dict(size=11, color=C["muted"]),
                    bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=C["surface"], bordercolor=C["border"],
                        font=dict(size=11, color=C["text"])),
    )
    return fig

def _data_table(df, params, max_rows=200):
    """Renders latest max_rows for speed; download callback gets all rows."""
    if df.empty:
        return html.Div("No records in selected range.",
                        style={"color": C["muted"], "fontSize": "13px",
                               "padding": "20px"})

    show_cols  = ["recorded_at"] + [p for p in params if p in df.columns]
    col_labels = {"recorded_at": "Timestamp"}
    col_labels.update({k: f"{PARAMS[k]['label']} ({PARAMS[k]['unit']})"
                       for k in PARAMS})

    total = len(df)
    disp  = df[show_cols].iloc[::-1].head(max_rows)

    th_style = {
        "padding": "10px 14px", "textAlign": "left",
        "color": C["muted"], "fontSize": "10px",
        "letterSpacing": "1.5px", "textTransform": "uppercase",
        "borderBottom": f"1px solid {C['border']}",
        "whiteSpace": "nowrap", "background": "#080E1C",
        "position": "sticky", "top": "0", "zIndex": "1",
    }

    def td_cell(val, col):
        color = (PARAM_COLORS.get(col, C["muted"])
                 if col != "recorded_at" else C["muted"])
        try:
            text = (str(val)[:19] if col == "recorded_at"
                    else f"{float(val):.2f}" if val is not None else "—")
        except Exception:
            text = "—"
        return html.Td(text, style={
            "padding": "10px 14px",
            "borderBottom": f"1px solid rgba(30,41,59,0.4)",
            "color": color, "fontSize": "12px",
            "fontFamily": "'JetBrains Mono', monospace",
            "whiteSpace": "nowrap",
        })

    note = html.Div(
        f"Showing latest {max_rows} of {total} records — use Download for full data",
        style={"fontSize": "10px", "color": C["muted"],
               "padding": "8px 14px",
               "borderBottom": f"1px solid {C['border']}",
               "fontStyle": "italic"}
    ) if total > max_rows else html.Div()

    return html.Div([
        note,
        html.Div(
            html.Table([
                html.Thead(html.Tr([
                    html.Th(col_labels.get(c, c), style=th_style)
                    for c in show_cols
                ])),
                html.Tbody([
                    html.Tr([td_cell(row[c], c) for c in show_cols])
                    for _, row in disp.iterrows()
                ]),
            ], style={"width": "100%", "borderCollapse": "collapse"}),
            style={"overflowX": "auto", "maxHeight": "400px", "overflowY": "auto"},
        ),
    ], style={"border": f"1px solid {C['border']}", "borderRadius": "12px",
              "overflow": "hidden"})

def _summary_strip(df, params):
    if df.empty:
        return html.Div()
    items = [
        ("Records",  str(len(df)),                       C["blue"]),
        ("From",     str(df["recorded_at"].min())[:10],  C["muted"]),
        ("To",       str(df["recorded_at"].max())[:10],  C["muted"]),
        ("Days",     str((df["recorded_at"].max()
                          - df["recorded_at"].min()).days + 1), C["purple"]),
    ]
    for k in params:
        if k in df.columns:
            avg = df[k].astype(float).mean()
            items.append((
                f"Avg {PARAMS[k]['label'][:7]}",
                f"{avg:.1f} {PARAMS[k]['unit']}",
                PARAM_COLORS.get(k, C["blue"]),
            ))
    return html.Div([
        html.Div([
            html.Div(v, style={"fontSize": "16px", "fontWeight": "700",
                               "color": c,
                               "fontFamily": "'JetBrains Mono', monospace",
                               "lineHeight": "1.2"}),
            html.Div(lbl, style={"fontSize": "9px", "color": C["muted"],
                                 "marginTop": "4px", "letterSpacing": "0.5px",
                                 "textTransform": "uppercase"}),
        ], style={"background": "rgba(10,15,30,0.7)",
                  "border": f"1px solid {C['border']}",
                  "borderTop": f"2px solid {c}",
                  "borderRadius": "8px", "padding": "12px 14px",
                  "flex": "1", "minWidth": "110px"})
        for lbl, v, c in items
    ], style={"display": "flex", "gap": "10px",
              "flexWrap": "wrap", "marginBottom": "16px"})

def _build_results(df, params, date_from, date_to):
    filtered = _apply_filter(df, params, date_from, date_to)
    return html.Div([
        _summary_strip(filtered, params),

        html.Div([
            html.Div([
                html.Span("Parameter Trend",
                          style={"fontSize": "12px", "color": C["muted"],
                                 "fontWeight": "500"}),
                html.Span(f"  {len(filtered)} data points",
                          style={"fontSize": "11px", "color": C["dim"],
                                 "marginLeft": "10px",
                                 "fontFamily": "'JetBrains Mono', monospace"}),
            ], style={"marginBottom": "12px"}),
            dcc.Graph(
                figure=_trend_chart(filtered, params),
                config={"displayModeBar": True,
                        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                        "displaylogo": False},
                style={"height": "300px"},
            ),
        ], style={**_CARD, "marginBottom": "16px"}),

        ui.section_title(
            f"Data Table — {len(filtered)} records"
            + (f"  ({date_from} → {date_to})" if date_from else "")
        ),
        _data_table(filtered, params),
    ])

# ════════════════════════════════════════════════════════════════
#  CALLBACKS
# ════════════════════════════════════════════════════════════════

@callback(
    Output("report-results",      "children"),
    Output("report-filter-store", "data"),
    Input("btn-apply-report",     "n_clicks"),
    Input("btn-reset-report",     "n_clicks"),
    State("report-date-from",     "date"),
    State("report-date-to",       "date"),
    State("report-params",        "value"),
    prevent_initial_call=True,
)
def apply_filter(_, __, date_from, date_to, params):
    today    = str(date.today())
    week_ago = str(date.today() - timedelta(days=7))

    if ctx.triggered_id == "btn-reset-report":
        date_from = week_ago
        date_to   = today
        params    = ["moisture", "temperature", "ph"]

    fd     = (date_from or week_ago)[:10]
    td     = (date_to   or today)[:10]
    params = params or list(PARAMS.keys())

    # fetch_all() has 5-min TTL cache — fast after first call
    df    = ds.to_df(ds.fetch_all(limit=2000))
    store = {"from": fd, "to": td, "params": params}

    # guard: if user picked dates outside the data range, show helpful message
    if not df.empty:
        db_min = str(df["recorded_at"].min().date())
        db_max = str(df["recorded_at"].max().date())
        if fd > db_max or td < db_min:
            msg = html.Div([
                html.Div("⚠ No data in selected range",
                         style={"fontSize": "14px", "fontWeight": "600",
                                "color": C["yellow"], "marginBottom": "8px"}),
                html.Div(
                    f"Your selection: {fd} → {td}",
                    style={"fontSize": "12px", "color": C["muted"],
                           "fontFamily": "'JetBrains Mono',monospace"}),
                html.Div(
                    f"Data available: {db_min} → {db_max}",
                    style={"fontSize": "12px", "color": C["green"],
                           "fontFamily": "'JetBrains Mono',monospace",
                           "marginTop": "4px"}),
            ], style={"padding": "24px", "background": "rgba(245,158,11,0.06)",
                      "border": f"1px solid rgba(245,158,11,0.25)",
                      "borderRadius": "12px"})
            return msg, store

    return _build_results(df, params, fd, td), store


@callback(
    Output("download-csv",    "data"),
    Input("btn-csv",          "n_clicks"),
    State("report-filter-store", "data"),
    prevent_initial_call=True,
)
def download_csv(n, store):
    if not n:
        return no_update
    store  = store or {}
    # reuses cached data — no second HTTP call
    df     = ds.to_df(ds.fetch_all(limit=2000))
    params = store.get("params") or list(PARAMS.keys())
    filt   = _apply_filter(df, params,
                           store.get("from"), store.get("to"))
    if filt.empty:
        return no_update
    cols = ["recorded_at"] + [p for p in params if p in filt.columns]
    return dcc.send_data_frame(
        filt[cols].to_csv,
        f"soil_{store.get('from')}_to_{store.get('to')}.csv",
        index=False,
    )


@callback(
    Output("download-excel",  "data"),
    Input("btn-excel",        "n_clicks"),
    State("report-filter-store", "data"),
    prevent_initial_call=True,
)
def download_excel(n, store):
    if not n:
        return no_update
    store  = store or {}
    df     = ds.to_df(ds.fetch_all(limit=2000))
    params = store.get("params") or list(PARAMS.keys())
    filt   = _apply_filter(df, params,
                           store.get("from"), store.get("to"))
    if filt.empty:
        return no_update
    cols = ["recorded_at"] + [p for p in params if p in filt.columns]
    return dcc.send_data_frame(
        filt[cols].to_excel,
        f"soil_{store.get('from')}_to_{store.get('to')}.xlsx",
        sheet_name="SoilReport", index=False,
    )