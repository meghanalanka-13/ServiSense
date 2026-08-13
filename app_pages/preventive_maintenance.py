# app_pages/preventive_maintenance.py
import streamlit as st
import pandas as pd
from data_loader import load_appliances
from config import RISK_BAND_LEGEND

PRIORITY_FORMULA_HELP = (
    "Priority Score = 0.5 x (how soon it's due, ranked) + 0.5 x (risk score, ranked). "
    "Higher score means visit sooner."
)


def show():
    st.title("Preventive Maintenance")
    st.caption("Which appliances to visit next, and why they're ranked that way")

    df = load_appliances()

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        type_filter = st.selectbox("Appliance type", ["All"] + sorted(df["Appliance_Type"].unique().tolist()))
    with col_f2:
        city_filter = st.selectbox("City", ["All"] + sorted(df["City"].unique().tolist()))

    scoped = df.copy()
    if type_filter != "All":
        scoped = scoped[scoped["Appliance_Type"] == type_filter]
    if city_filter != "All":
        scoped = scoped[scoped["City"] == city_filter]

    window_days = st.slider("Show appliances due within (days)", 7, 90, 30)

    st.markdown("---")

    due_soon = scoped[scoped["Days_To_Next_PM"] <= window_days].copy()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(f"Due within {window_days} days", f"{len(due_soon):,}")
    with col2:
        overdue = (scoped["Days_To_Next_PM"] < 0).sum()
        st.metric("Already overdue", f"{overdue:,}")
    with col3:
        high_risk_due = (due_soon["Risk_Band"] == "High").sum() if len(due_soon) else 0
        st.metric("Of those, High risk", f"{high_risk_due:,}", help=RISK_BAND_LEGEND)

    st.markdown("---")
    st.subheader("Prioritized visit list", help=PRIORITY_FORMULA_HELP)
    st.markdown(
        "Ranked by a **priority score** combining how soon maintenance is due "
        "with how risky the appliance currently is."
    )

    if len(due_soon) == 0:
        st.info("No appliances fall within this window. Try widening the slider or filters.")
        return

    due_soon["due_rank"] = due_soon["Days_To_Next_PM"].rank(ascending=True, pct=True)
    due_soon["risk_rank"] = due_soon["Failure_Score_30D"].rank(ascending=False, pct=True)
    due_soon["Priority_Score"] = round(1 - (0.5 * due_soon["due_rank"] + 0.5 * due_soon["risk_rank"]), 3)

    display = due_soon.sort_values("Priority_Score", ascending=False).head(25)[[
        "Appliance_ID", "Appliance_Type", "Brand", "City", "Days_To_Next_PM",
        "Failure_Score_30D", "Risk_Band", "Priority_Score",
    ]].rename(columns={
        "Appliance_ID": "ID", "Days_To_Next_PM": "Days until due",
        "Failure_Score_30D": "Risk score", "Risk_Band": "Risk",
        "Appliance_Type": "Type", "Priority_Score": "Priority",
    })

    st.dataframe(
        display.style.format({"Risk score": "{:.2f}", "Priority": "{:.2f}"}),
        hide_index=True, use_container_width=True,
    )

    st.caption(f"Showing the top 25 of {len(due_soon):,} appliances due within {window_days} days, by priority.", help=RISK_BAND_LEGEND)

    st.markdown("---")
    st.subheader("Sample outreach message")
    sample = display.iloc[0]
    days_val = sample["Days until due"]
    day_word = "day" if days_val == 1 else "days"
    st.markdown(
        f"> Hi! Your {sample['Brand']} {sample['Type']} is due for preventive "
        f"maintenance in {days_val} {day_word}. We can schedule a quick check "
        f"to help avoid an unexpected breakdown."
    )
