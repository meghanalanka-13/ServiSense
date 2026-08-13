# config.py
# ============================================================
# ServiSense Configuration
# Single source of truth for colors, paths, and thresholds.
# Change DATA_DIR to point at a different data-engine export set.
# ============================================================

DATA_DIR = "data"

# ---- Palette: monochrome base + exactly two directional chart colors ----
# Everything outside charts stays black/white/cream/gray. Inside charts,
# red = worse/rising-bad, blue = better/falling-good. Translucent fills
# (not solid), matching the Mimic/ClinIQ reference style -- softer, less
# "muddy," coral/steelblue rather than a flat brick red.
COLOR_BG = "#F7F5F1"
COLOR_SURFACE = "#FFFFFF"
COLOR_TEXT = "#1A1A1A"
COLOR_TEXT_MUTED = "#6B6B68"
COLOR_BORDER = "#E4E1D9"
COLOR_ACCENT_DARK = "#0D0D0D"   # for buttons/highlights, still monochrome

COLOR_BAD = "rgba(240, 30, 44, 0.75)"      # translucent red (#f01e2c) -- rising risk, worse outcome
COLOR_GOOD = "rgba(70, 130, 180, 0.75)"    # translucent steelblue -- falling risk, better outcome
COLOR_NEUTRAL = "rgba(156, 154, 148, 0.7)"  # translucent gray -- a "medium"/unclassified band

# Solid (non-translucent) versions, for places like sample-message quotes
# or borders where a flat fill still reads better than a translucent one.
COLOR_BAD_SOLID = "#f01e2c"
COLOR_GOOD_SOLID = "#4682B4"
COLOR_NEUTRAL_SOLID = "#9C9A94"

# Risk band -> color mapping (used consistently everywhere a risk band is shown)
RISK_BAND_COLORS = {
    "Low": COLOR_GOOD,
    "Medium": COLOR_NEUTRAL,
    "High": COLOR_BAD,
}

# ---- Risk thresholds ----
RISK_BAND_LOW_MAX = 0.4
RISK_BAND_HIGH_MIN = 0.7

# Reusable legend text -- show this wherever Low/Medium/High risk bands
# appear, so the cutoffs are never left unexplained.
RISK_BAND_LEGEND = (
    f"Low: below {int(RISK_BAND_LOW_MAX*100)}% risk score. "
    f"Medium: {int(RISK_BAND_LOW_MAX*100)}-{int(RISK_BAND_HIGH_MIN*100)}%. "
    f"High: {int(RISK_BAND_HIGH_MIN*100)}% or above."
)

# Inventory stock-health bands work on a different scale (current stock
# as a ratio of the safety-stock level, MSL) -- a separate legend so it's
# never confused with the risk-score bands above.
STOCK_HEALTH_LEGEND = (
    "Critical: stock below 50% of the safety level (MSL). Low: 50-100%. "
    "Safe: 100-150%. Overstock: above 150%."
)

# ---- Preventive maintenance ----
PM_INTERVAL_DAYS = {
    "Refrigerator": 365, "Washing Machine": 270, "Water Purifier": 180,
    "Water Heater": 365, "Microwave": 365, "AC": 180,
}

# ---- Outreach defaults ----
DEFAULT_OUTREACH_THRESHOLD = 0.5

# ---- App metadata ----
APP_TITLE = "ServiSense"
APP_TAGLINE = "The intelligence layer behind Co-Repairs"
