# utils/helpers.py
# ============================================================
# Shared formatting + tooltip text. Every page pulls explanations from
# here so the same concept is worded identically everywhere it appears,
# rather than being re-explained slightly differently on each page.
# ============================================================

TOOLTIPS = {
    "failure_score": "Model-estimated chance this appliance needs a repair soon. Based on age, usage, past repairs, and installation quality.",
    "failure_score_60d": "Chance of needing a repair in the next 30 days, the near-term, dispatch-relevant view.",
    "failure_score_90d": "Chance of needing a repair in the next 90 days, a medium-term planning view.",
    "risk_band": "Low: below 40% chance. Medium: 40-70%. High: above 70%.",
    "prev_repair_count": "How many times this appliance has needed service before.",
    "failure_velocity": "Past repairs per year of the appliance's life, a rough pace-of-breakdown indicator.",
    "current_soh": "Current stock on hand for this part, from a real day-by-day simulation of demand and restocking, not a live warehouse feed.",
    "msl": "Minimum stock level, the safety-stock threshold this part should stay above given its typical demand and restock lead time.",
    "stockout": "A day where demand for this part exceeded what was in stock.",
    "pm_priority": "Combines how soon maintenance is due with how risky the appliance currently is. Higher score means service it sooner.",
    "cross_dependency_lift": "How much more likely the second part is to fail, given the first part already failed on this same appliance, compared to appliances where it didn't.",
    "outreach_threshold": "Only appliances at or above this risk score get included in the outreach list.",
    "forecast_confidence": "The shaded band shows the range the model expects the real number to fall within, based on how much this series has varied historically.",
    "seasonal_strength": "How much of this appliance type's ups and downs are explained by the time of year, versus random variation. Near 0 means no real seasonal pattern.",
}


def fmt_pct(x: float, decimals: int = 1) -> str:
    return f"{x * 100:.{decimals}f}%"


def fmt_currency_inr(x: float) -> str:
    if x >= 1_00_00_000:
        return f"\u20b9{x/1_00_00_000:.2f} Cr"
    if x >= 1_00_000:
        return f"\u20b9{x/1_00_000:.2f} L"
    return f"\u20b9{x:,.0f}"


def risk_band_label(score: float) -> str:
    from config import RISK_BAND_LOW_MAX, RISK_BAND_HIGH_MIN
    if score < RISK_BAND_LOW_MAX:
        return "Low"
    if score < RISK_BAND_HIGH_MIN:
        return "Medium"
    return "High"


def colored_metric(label: str, value: str, color: str, arrow: str = "", help_text: str = ""):
    """A metric-like display with a colored value -- st.metric doesn't
    support custom value coloring, so this uses styled markdown instead,
    kept visually close to a native metric (small muted label, large
    value) for consistency with the rest of the app."""
    import streamlit as st
    title_attr = help_text.replace('"', "'") if help_text else ""
    arrow_html = f'<span style="font-size:1.3rem;">{arrow}</span> ' if arrow else ""
    st.markdown(
        f'<div title="{title_attr}">'
        f'<div style="color:#6B6B68;font-size:0.85rem;margin-bottom:0.15rem;">{label}</div>'
        f'<div style="color:{color};font-size:2.1rem;font-weight:600;line-height:1.2;">{arrow_html}{value}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
