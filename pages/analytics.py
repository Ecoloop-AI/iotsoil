"""pages/analytics.py — Full analytics page"""
from dash import html, dcc
import plotly.graph_objects as go
import plotly.figure_factory as ff
import pandas as pd
import numpy as np
import data_service as ds
from data_service import PARAMS, C, hex_to_rgba
import components as ui

PARAM_COLORS = {
    "moisture": C["blue"], "temperature": "#FF6B6B",
    "ph": C["purple"], "conductivity": "#F59E0B",
    "nitrogen": C["green"], "phosphorus": "#06B6D4", "potassium": "#EC4899",
}

def layout(store):
    history = store.get("history") or []
    df = ds.to_df(history)

    return html.Div([
        ui.section_title("Historical Trend Analysis"),

        # ── Param selector + time filter ──
        html.Div([
            html.Div([
                html.Label("Parameters", style={"fontSize": "10px", "color": C["muted"],
                                                "letterSpacing": "1px", "marginBottom": "6px",
                                                "display": "block"}),
                dcc.Checklist(
                    id="analytics-params",
                    options=[{"label": html.Span(m["label"], style={"fontSize": "12px",
                              "color": C["muted"], "marginLeft": "6px"}), "value": k}
                             for k, m in PARAMS.items()],
                    value=["moisture", "temperature", "ph"],
                    inline=True,
                    style={"display": "flex", "flexWrap": "wrap", "gap": "16px"},
                    inputStyle={"accentColor": C["blue"]},
                ),
            ], style={"flex": "1"}),
        ], style={
            "background": "rgba(15,23,42,0.8)", "border": f"1px solid {C['border']}",
            "borderRadius": "12px", "padding": "16px 20px", "marginBottom": "16px",
        }),

        # ── Row 1: area trend + histogram ──
        html.Div([
            _panel("Area Trend", dcc.Graph(
                figure=_area_trend(df, ["moisture", "temperature", "ph"]),
                config={"displayModeBar": False}, style={"height": "260px"},
                id="area-trend-chart",
            ), flex=2),
            _panel("Distribution", dcc.Graph(
                figure=_histogram(df),
                config={"displayModeBar": False}, style={"height": "260px"},
            ), flex=1),
        ], style={"display": "flex", "gap": "16px", "marginBottom": "16px"}),

        # ── Row 2: heatmap + box plot ──
        html.Div([
            _panel("Time-of-Day Heatmap — Moisture", dcc.Graph(
                figure=_heatmap(df),
                config={"displayModeBar": False}, style={"height": "260px"},
            ), flex=1),
            _panel("Box Plot — Parameter Spread", dcc.Graph(
                figure=_box_plot(df),
                config={"displayModeBar": False}, style={"height": "260px"},
            ), flex=1),
        ], style={"display": "flex", "gap": "16px", "marginBottom": "16px"}),

        # ── Row 3: scatter + correlation matrix ──
        html.Div([
            _panel("Scatter — Moisture vs Temperature", dcc.Graph(
                figure=_scatter(df),
                config={"displayModeBar": False}, style={"height": "280px"},
            ), flex=1),
            _panel("Correlation Matrix", dcc.Graph(
                figure=_correlation(df),
                config={"displayModeBar": False}, style={"height": "280px"},
            ), flex=1),
        ], style={"display": "flex", "gap": "16px", "marginBottom": "16px"}),

        # ── Row 4: daily averages bar ──
        ui.section_title("Daily Averages"),
        _panel("", dcc.Graph(
            figure=_daily_avg_bar(df),
            config={"displayModeBar": False}, style={"height": "240px"},
        )),
    ])

def _panel(title, content, flex=1):
    return html.Div([
        html.Div(title, style={"fontSize": "12px", "color": C["muted"],
                                "marginBottom": "12px", "fontWeight": "500"}) if title else html.Span(),
        content,
    ], style={
        "background": "rgba(15,23,42,0.8)", "border": f"1px solid {C['border']}",
        "borderRadius": "14px", "padding": "20px", "flex": str(flex), "minWidth": "0",
    })

def _area_trend(df, keys):
    fig = go.Figure()
    if df.empty:
        return fig
    for k in keys:
        if k not in df.columns:
            continue
        color = PARAM_COLORS.get(k, C["blue"])
        fig.add_trace(go.Scatter(
            x=df["recorded_at"], y=df[k],
            name=PARAMS[k]["label"], mode="lines",
            line=dict(color=color, width=2),
            fill="tozeroy", fillcolor=hex_to_rgba(color, 0.07),
        ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=260, margin=dict(l=0, r=0, t=0, b=30),
        showlegend=True, hovermode="x unified",
        legend=dict(orientation="h", y=-0.18, font=dict(size=10, color=C["muted"]),
                    bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(showgrid=False, tickfont=dict(size=9, color=C["muted"])),
        yaxis=dict(showgrid=True, gridcolor="rgba(51,65,85,0.35)",
                   tickfont=dict(size=9, color=C["muted"])),
        font=dict(family="Inter"),
    )
    return fig

def _histogram(df):
    fig = go.Figure()
    if df.empty:
        return fig
    for k in ["moisture", "temperature", "ph"]:
        if k not in df.columns:
            continue
        color = PARAM_COLORS.get(k, C["blue"])
        fig.add_trace(go.Histogram(
            x=df[k], name=PARAMS[k]["label"],
            marker_color=hex_to_rgba(color, 0.7),
            nbinsx=15, opacity=0.8,
        ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        barmode="overlay", height=260, margin=dict(l=0, r=0, t=0, b=0),
        showlegend=True,
        legend=dict(orientation="h", y=-0.18, font=dict(size=10, color=C["muted"]),
                    bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(showgrid=False, tickfont=dict(size=9, color=C["muted"])),
        yaxis=dict(showgrid=True, gridcolor="rgba(51,65,85,0.35)",
                   tickfont=dict(size=9, color=C["muted"])),
        font=dict(family="Inter"),
    )
    return fig

def _heatmap(df):
    fig = go.Figure()
    if df.empty or "moisture" not in df.columns:
        return fig
    df2 = df.copy()
    df2["hour"] = df2["recorded_at"].dt.hour
    df2["date"] = df2["recorded_at"].dt.date
    pivot = df2.pivot_table(index="date", columns="hour",
                            values="moisture", aggfunc="mean")
    fig.add_trace(go.Heatmap(
        z=pivot.values, x=list(pivot.columns), y=[str(d) for d in pivot.index],
        colorscale=[[0, hex_to_rgba(C["blue"], 0.1)],
                    [0.5, C["blue"]], [1, "#FFFFFF"]],
        showscale=True, colorbar=dict(tickfont=dict(size=9, color=C["muted"])),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=260, margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(title=dict(text="Hour of Day", font=dict(size=10, color=C["muted"])),
                   tickfont=dict(size=9, color=C["muted"])),
        yaxis=dict(tickfont=dict(size=9, color=C["muted"])),
        font=dict(family="Inter"),
    )
    return fig

def _box_plot(df):
    fig = go.Figure()
    if df.empty:
        return fig
    for k in ["moisture", "temperature", "ph", "conductivity"]:
        if k not in df.columns:
            continue
        color = PARAM_COLORS.get(k, C["blue"])
        norm = (df[k] - df[k].min()) / (df[k].max() - df[k].min() + 1e-9) * 100
        fig.add_trace(go.Box(
            y=norm, name=PARAMS[k]["label"][:6],
            marker_color=color, line_color=color,
            fillcolor=hex_to_rgba(color, 0.15),
            boxmean=True,
        ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=260, margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        yaxis=dict(showgrid=True, gridcolor="rgba(51,65,85,0.35)",
                   title=dict(text="Normalised (0–100)", font=dict(size=10, color=C["muted"])),
                   tickfont=dict(size=9, color=C["muted"])),
        xaxis=dict(tickfont=dict(size=10, color=C["muted"])),
        font=dict(family="Inter"),
    )
    return fig

def _scatter(df):
    fig = go.Figure()
    if df.empty or "moisture" not in df.columns or "temperature" not in df.columns:
        return fig
    fig.add_trace(go.Scatter(
        x=df["moisture"], y=df["temperature"],
        mode="markers",
        marker=dict(color=df["ph"] if "ph" in df.columns else C["blue"],
                    colorscale="Viridis", size=8, opacity=0.8,
                    showscale=True,
                    colorbar=dict(title="pH", tickfont=dict(size=9, color=C["muted"]))),
        text=df.get("recorded_at", None),
        hovertemplate="Moisture: %{x:.1f}%<br>Temp: %{y:.1f}°C<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=280, margin=dict(l=0, r=60, t=0, b=30),
        xaxis=dict(title=dict(text="Moisture (%)", font=dict(size=10, color=C["muted"])),
                   showgrid=False,
                   tickfont=dict(size=9, color=C["muted"])),
        yaxis=dict(title=dict(text="Temperature (°C)", font=dict(size=10, color=C["muted"])),
                   showgrid=True,
                   gridcolor="rgba(51,65,85,0.35)",
                   tickfont=dict(size=9, color=C["muted"])),
        font=dict(family="Inter"),
    )
    return fig

def _correlation(df):
    keys = [k for k in PARAMS if k in df.columns] if not df.empty else []
    fig = go.Figure()
    if len(keys) < 2:
        return fig
    corr = df[keys].corr().round(2)
    labels = [PARAMS[k]["label"][:8] for k in keys]
    fig.add_trace(go.Heatmap(
        z=corr.values, x=labels, y=labels,
        colorscale=[[0, "#EF4444"], [0.5, "#1E293B"], [1, "#10B981"]],
        zmin=-1, zmax=1,
        text=corr.values.round(2),
        texttemplate="%{text}",
        textfont=dict(size=9),
        showscale=True,
        colorbar=dict(tickfont=dict(size=9, color=C["muted"])),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=280, margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(tickfont=dict(size=9, color=C["muted"])),
        yaxis=dict(tickfont=dict(size=9, color=C["muted"])),
        font=dict(family="Inter"),
    )
    return fig

def _daily_avg_bar(df):
    fig = go.Figure()
    if df.empty:
        return fig
    df2 = df.copy()
    df2["date"] = df2["recorded_at"].dt.date
    for k in ["nitrogen", "phosphorus", "potassium"]:
        if k not in df2.columns:
            continue
        daily = df2.groupby("date")[k].mean().reset_index()
        color = PARAM_COLORS.get(k, C["blue"])
        fig.add_trace(go.Bar(
            x=daily["date"].astype(str), y=daily[k].round(1),
            name=PARAMS[k]["label"],
            marker_color=color, opacity=0.85,
        ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        barmode="group", height=240, margin=dict(l=0, r=0, t=0, b=30),
        showlegend=True,
        legend=dict(orientation="h", y=-0.22, font=dict(size=10, color=C["muted"]),
                    bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(showgrid=False, tickfont=dict(size=9, color=C["muted"])),
        yaxis=dict(showgrid=True, gridcolor="rgba(51,65,85,0.35)",
                   tickfont=dict(size=9, color=C["muted"]),
                   title=dict(text="mg/kg", font=dict(size=10, color=C["muted"]))),
        font=dict(family="Inter"),
    )
    return fig