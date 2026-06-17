"""
data_service.py  —  All API calls + in-process TTL cache.

Cache strategy:
  • fetch_latest()   → cached 30 s  (live KPI cards)
  • fetch_history()  → cached 60 s  (charts / sparklines)
  • fetch_all()      → cached 5 min (reports — heavy call, rarely changes)

No extra libraries — uses a plain dict + datetime comparison.
"""

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

def cache_info():
    """Return human-readable cache status (useful for debugging)."""
    now = datetime.now()
    with _lock:
        return {k: f"expires in {int((v['expires']-now).total_seconds())}s"
                for k, v in _cache.items() if now < v["expires"]}

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
    if value is None:
        return "unknown", C["muted"]
    m   = PARAMS.get(key, {})
    lo, hi = m.get("lo", 0), m.get("hi", 9999)
    if lo <= value <= hi:
        return "Normal", C["green"]
    gap = (hi - lo) * 0.2
    if (lo - gap) <= value < lo or hi < value <= (hi + gap):
        return "Warning", C["yellow"]
    return "Critical", C["red"]

def soil_health_score(row):
    if not row:
        return 0
    scores = []
    for key in PARAMS:
        val = row.get(key)
        if val is None:
            continue
        m    = PARAMS[key]
        mid  = (m["lo"] + m["hi"]) / 2
        span = (m["hi"] - m["lo"]) / 2
        score = max(0, 100 - abs(float(val) - mid) / span * 50)
        scores.append(min(100, score))
    return round(sum(scores) / len(scores), 1) if scores else 0

# ── Alert engine ─────────────────────────────────────────────────

ALERT_RULES = [
    ("moisture",     lambda v: v < 20,   "CRITICAL", "Moisture critically low — risk of crop stress"),
    ("moisture",     lambda v: v > 80,   "WARNING",  "Moisture too high — waterlogging risk"),
    ("ph",           lambda v: v < 5.5,  "WARNING",  "pH too acidic — nutrient lock-out likely"),
    ("ph",           lambda v: v > 7.5,  "WARNING",  "pH too alkaline — limits phosphorus uptake"),
    ("temperature",  lambda v: v > 40,   "CRITICAL", "Soil temperature critical — root damage risk"),
    ("temperature",  lambda v: v < 5,    "WARNING",  "Soil temperature low — microbial activity reduced"),
    ("conductivity", lambda v: v > 1500, "WARNING",  "EC high — possible salt accumulation"),
    ("nitrogen",     lambda v: v < 20,   "WARNING",  "Nitrogen deficiency detected"),
    ("phosphorus",   lambda v: v < 10,   "WARNING",  "Phosphorus deficiency detected"),
    ("potassium",    lambda v: v < 50,   "WARNING",  "Potassium deficiency detected"),
]

def get_alerts(row):
    if not row:
        return []
    from datetime import datetime as _dt
    now    = _dt.now().strftime("%H:%M:%S")
    alerts = []
    for key, fn, severity, msg in ALERT_RULES:
        val = row.get(key)
        if val is not None:
            try:
                if fn(float(val)):
                    alerts.append({"param": key, "severity": severity,
                                   "message": msg, "value": val, "time": now})
            except Exception:
                pass
    return alerts