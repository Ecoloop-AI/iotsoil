"""
data_service.py  —  All API calls + in-process TTL cache.

Cache strategy:
  • fetch_latest()   → cached 30 s  (live KPI cards)
  • fetch_history()  → cached 60 s  (charts / sparklines)
  • fetch_all()      → cached 5 min (reports — heavy call, rarely changes)
  • get_thresholds() → cached 5 s   (alert/warning thresholds, see below)

No extra libraries — uses a plain dict + datetime comparison.
"""

import os
import json
import requests
import pandas as pd
import threading
from datetime import datetime, timedelta

API_URL = "https://ecoloop.in/soil_api/get_soil.php"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

# ── Parameter metadata ───────────────────────────────────────────
# "lo"/"hi" here are only the DEFAULT thresholds (used the very first time
# the app runs, before anyone has saved anything on the Settings page).
# Once a user saves thresholds, the live values come from get_thresholds()
# below — never read PARAMS[...]["lo"/"hi"] directly elsewhere in the app.
PARAMS = {
    "moisture":     {"label": "Soil Moisture",  "unit": "%",     "min": 0,   "max": 100,  "lo": 20,  "hi": 80,   "icon": "💧"},
    "temperature":  {"label": "Temperature",    "unit": "°C",    "min": 0,   "max": 60,   "lo": 10,  "hi": 40,   "icon": "🌡"},
    "ph":           {"label": "Soil pH",        "unit": "pH",    "min": 0,   "max": 14,   "lo": 5.5, "hi": 7.5,  "icon": "⚗"},
    "conductivity": {"label": "Conductivity",   "unit": "µS/cm", "min": 0,   "max": 2000, "lo": 100, "hi": 1500, "icon": "⚡"},
    "nitrogen":     {"label": "Nitrogen",       "unit": "mg/kg", "min": 0,   "max": 200,  "lo": 20,  "hi": 150,  "icon": "🌿"},
    "phosphorus":   {"label": "Phosphorus",     "unit": "mg/kg", "min": 0,   "max": 200,  "lo": 10,  "hi": 100,  "icon": "🔬"},
    "potassium":    {"label": "Potassium",      "unit": "mg/kg", "min": 0,   "max": 300,  "lo": 50,  "hi": 200,  "icon": "🌾"},
}

# ── Colour tokens ────────────────────────────────────────────────
C = {
    "bg":      "#0F172A", "surface": "#1E293B", "surface2": "#0A1628",
    "border":  "#334155", "blue":    "#00D4FF",  "green":    "#10B981",
    "yellow":  "#F59E0B", "red":     "#EF4444",  "purple":   "#8B5CF6",
    "text":    "#E2E8F0", "muted":   "#64748B",  "dim":      "#334155",
}

def hex_to_rgba(h, a):
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{a})"

# ════════════════════════════════════════════════════════════════
#  TTL Cache  (thread-safe, no extra dependencies)
# ════════════════════════════════════════════════════════════════
_cache: dict = {}
_lock  = threading.Lock()

def _get(key):
    """Return cached value if still fresh, else None."""
    with _lock:
        entry = _cache.get(key)
        if entry and datetime.now() < entry["expires"]:
            return entry["value"]
    return None

def _set(key, value, ttl_seconds):
    with _lock:
        _cache[key] = {
            "value":   value,
            "expires": datetime.now() + timedelta(seconds=ttl_seconds),
        }

def _invalidate_key(key):
    with _lock:
        _cache.pop(key, None)

def cache_info():
    """Return human-readable cache status (useful for debugging)."""
    now = datetime.now()
    with _lock:
        return {k: f"expires in {int((v['expires']-now).total_seconds())}s"
                for k, v in _cache.items() if now < v["expires"]}

# ════════════════════════════════════════════════════════════════
#  Alert / warning thresholds — single source of truth
# ════════════════════════════════════════════════════════════════
# Render's free-tier filesystem resets on every spin-down/redeploy, so we
# DON'T store thresholds in a local file. Instead they're saved through two
# small PHP endpoints on your existing cPanel hosting (same host as
# get_soil.php) — that storage is permanent and free.
#
#   GET  THRESHOLDS_GET_URL   → returns the saved JSON ({} if none yet)
#   POST THRESHOLDS_SAVE_URL  → body: {"<param>": {"lo":.., "hi":..}, ..., "key": SECRET}
#
# get_thresholds() is still cached 5 s (re-using the TTL cache above) so a
# page that calls it many times per render doesn't hammer the cPanel host.
THRESHOLDS_GET_URL  = "https://ecoloop.in/soil_api/get_thresholds.php"
THRESHOLDS_SAVE_URL = "https://ecoloop.in/soil_api/save_thresholds.php"

# Must exactly match $SECRET in save_thresholds.php on cPanel.
# Better: set this as a Render environment variable instead of hardcoding it.
THRESHOLDS_SECRET = os.environ.get("THRESHOLDS_SECRET", "change-this-to-something-only-you-know")

def _read_thresholds_remote():
    try:
        r = requests.get(THRESHOLDS_GET_URL, headers=HEADERS, timeout=8)
        r.raise_for_status()
        return r.json() or {}
    except Exception as e:
        print(f"[thresholds] remote read failed: {e}")
        return {}

def get_thresholds():
    """Current {param: {"lo":.., "hi":..}} — defaults merged with any saved overrides."""
    cached = _get("thresholds")
    if cached is not None:
        return cached
    saved = _read_thresholds_remote()
    result = {}
    for key, meta in PARAMS.items():
        override = saved.get(key, {})
        result[key] = {
            "lo": override.get("lo", meta["lo"]),
            "hi": override.get("hi", meta["hi"]),
        }
    _set("thresholds", result, 5)
    return result

def set_thresholds(new_values: dict):
    """
    Persist new lo/hi thresholds via the cPanel endpoint.
    new_values = {param: {"lo": x, "hi": y}, ...}
    Called by the Settings page "Save Thresholds" button.
    """
    current = get_thresholds()
    for key, vals in new_values.items():
        if key not in PARAMS:
            continue
        lo = vals.get("lo", current[key]["lo"])
        hi = vals.get("hi", current[key]["hi"])
        current[key] = {"lo": float(lo), "hi": float(hi)}
    try:
        payload = dict(current)
        payload["key"] = THRESHOLDS_SECRET
        r = requests.post(THRESHOLDS_SAVE_URL, json=payload, headers=HEADERS, timeout=8)
        r.raise_for_status()
        print(f"[thresholds] saved to cPanel: {list(new_values.keys())}")
    except Exception as e:
        print(f"[thresholds] remote save failed: {e}")
    _invalidate_key("thresholds")  # next get_thresholds() re-fetches immediately
    return current

# ════════════════════════════════════════════════════════════════
#  API helpers
# ════════════════════════════════════════════════════════════════

def _get_json(params, timeout=10):
    r = requests.get(API_URL, params=params, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.json().get("data", [])

# ── Public fetch functions ───────────────────────────────────────

def fetch_latest(ttl=30):
    """Single most-recent row. Cached 30 s."""
    key = "latest"
    hit = _get(key)
    if hit is not None:
        return hit
    try:
        data = _get_json({"latest": 1}, timeout=8)
        result = data[0] if data else None
        _set(key, result, ttl)
        print(f"[cache] fetch_latest — API call, TTL {ttl}s")
        return result
    except Exception as e:
        print(f"[fetch_latest] {e}")
        return None

def fetch_history(limit=200, ttl=60):
    """Recent N rows for charts/sparklines. Cached 60 s."""
    key = f"history_{limit}"
    hit = _get(key)
    if hit is not None:
        return hit
    try:
        data = _get_json({"limit": limit}, timeout=12)
        _set(key, data, ttl)
        print(f"[cache] fetch_history({limit}) — API call, TTL {ttl}s")
        return data
    except Exception as e:
        print(f"[fetch_history] {e}")
        return []

def fetch_all(limit=2000, ttl=300):
    """All records for reporting. Cached 5 minutes — avoids repeated heavy calls."""
    key = f"all_{limit}"
    hit = _get(key)
    if hit is not None:
        return hit
    try:
        data = _get_json({"limit": limit}, timeout=25)
        _set(key, data, ttl)
        print(f"[cache] fetch_all({limit}) — API call, TTL {ttl}s")
        return data
    except Exception as e:
        print(f"[fetch_all] {e}")
        return []

def invalidate():
    """Force-clear the cache (call after a manual refresh button)."""
    with _lock:
        _cache.clear()
    print("[cache] invalidated")

# ── DataFrame helper ─────────────────────────────────────────────

def to_df(rows):
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["recorded_at"] = pd.to_datetime(df["recorded_at"])
    for p in PARAMS:
        if p in df.columns:
            df[p] = pd.to_numeric(df[p], errors="coerce")
    return df.sort_values("recorded_at").reset_index(drop=True)

# ── Status helpers ───────────────────────────────────────────────

def get_status(key, value):
    """Normal / Warning / Critical — always evaluated against the CURRENT
    saved thresholds, so this updates the moment Settings are saved."""
    if value is None:
        return "unknown", C["muted"]
    th = get_thresholds().get(key, {})
    lo, hi = th.get("lo", 0), th.get("hi", 9999)
    if lo <= value <= hi:
        return "Normal", C["green"]
    gap = (hi - lo) * 0.2
    if (lo - gap) <= value < lo or hi < value <= (hi + gap):
        return "Warning", C["yellow"]
    return "Critical", C["red"]

def soil_health_score(row):
    if not row:
        return 0
    thresholds = get_thresholds()
    scores = []
    for key in PARAMS:
        val = row.get(key)
        if val is None:
            continue
        th = thresholds.get(key, {})
        lo, hi = th.get("lo"), th.get("hi")
        if lo is None or hi is None or hi == lo:
            continue
        mid  = (lo + hi) / 2
        span = (hi - lo) / 2
        score = max(0, 100 - abs(float(val) - mid) / span * 50)
        scores.append(min(100, score))
    return round(sum(scores) / len(scores), 1) if scores else 0

# ── Alert engine ─────────────────────────────────────────────────
# Each rule says: for this param, "low" means below the current lo threshold
# (or "high" means above the current hi threshold). No hardcoded numbers —
# everything reads from get_thresholds(), so saved Settings changes flow
# straight through to alerts. (Previously these numbers were hardcoded and
# disconnected from PARAMS — e.g. temperature low fired at <5 even though
# PARAMS said lo=10. That inconsistency is now gone by construction.)
ALERT_RULES = [
    ("moisture",     "low",  "CRITICAL", "Moisture critically low — risk of crop stress"),
    ("moisture",     "high", "WARNING",  "Moisture too high — waterlogging risk"),
    ("ph",           "low",  "WARNING",  "pH too acidic — nutrient lock-out likely"),
    ("ph",           "high", "WARNING",  "pH too alkaline — limits phosphorus uptake"),
    ("temperature",  "high", "CRITICAL", "Soil temperature critical — root damage risk"),
    ("temperature",  "low",  "WARNING",  "Soil temperature low — microbial activity reduced"),
    ("conductivity", "high", "WARNING",  "EC high — possible salt accumulation"),
    ("nitrogen",     "low",  "WARNING",  "Nitrogen deficiency detected"),
    ("phosphorus",   "low",  "WARNING",  "Phosphorus deficiency detected"),
    ("potassium",    "low",  "WARNING",  "Potassium deficiency detected"),
]

def get_alerts(row):
    if not row:
        return []
    now = datetime.now().strftime("%H:%M:%S")
    thresholds = get_thresholds()
    alerts = []
    for key, bound, severity, msg in ALERT_RULES:
        val = row.get(key)
        if val is None:
            continue
        th = thresholds.get(key, {})
        lo, hi = th.get("lo"), th.get("hi")
        try:
            v = float(val)
            breached = (
                (bound == "low"  and lo is not None and v < lo) or
                (bound == "high" and hi is not None and v > hi)
            )
            if breached:
                alerts.append({"param": key, "severity": severity,
                               "message": msg, "value": val, "time": now})
        except Exception:
            pass
    return alerts
