# app_pages/failure_risk.py
import streamlit as st
import plotly.express as px
import pandas as pd
from data_loader import load_appliances
from utils.helpers import TOOLTIPS, fmt_pct
from config import RISK_BAND_COLORS, COLOR_NEUTRAL, COLOR_BAD, RISK_BAND_LEGEND


def show():
    prev = st.session_state.get("previous_page")
    if prev and prev != "Failure Risk":
        if st.button(f"\u2190 Back to {prev}", key="fr_back_link"):
            st.session_state.current_page = prev
            st.session_state.previous_page = None
            st.rerun()

    st.title("Failure Risk")
    st.caption("Which appliances are likely to need service soon, and why")

    df = load_appliances()

    window = st.radio("Prediction window", ["30 days", "90 days"], horizontal=True, label_visibility="collapsed")
    score_col = "Failure_Score_30D" if window == "30 days" else "Failure_Score_90D"
    band_col = "Risk_Band" if window == "30 days" else "Risk_Band_90D"

    st.markdown("---")
    st.subheader("Set your own risk threshold")
    st.caption("Set your own cutoff below, since what counts as significant depends on your own capacity and risk tolerance.")

    type_filter = st.selectbox("Appliance type", ["All"] + sorted(df["Appliance_Type"].unique().tolist()), key="fr_threshold_type_filter")
    scoped_df = df if type_filter == "All" else df[df["Appliance_Type"] == type_filter]

    threshold = st.slider(
        "Minimum risk score to flag", 0.0, 1.0, 0.5, 0.01,
        help="Appliances scoring at or above this get included in the list below.",
    )
    st.caption("Slide to adjust the risk % threshold.")

    flagged = scoped_df[scoped_df[score_col] >= threshold].sort_values(score_col, ascending=False)
    pct_flagged = len(flagged) / len(scoped_df) if len(scoped_df) else 0

    scope_label = type_filter if type_filter != "All" else "installed base"
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Appliances flagged", f"{len(flagged):,}")
        st.caption(f"{pct_flagged*100:.1f}% of {scope_label}")
    with col_b:
        actual_positive_rate = flagged["Repair_Req_Next_30D" if window == "30 days" else "Repair_Req_Next_90D"].mean() if len(flagged) else 0
        st.metric("Of those, actually needed service", f"{actual_positive_rate*100:.1f}%",
                  help="Of the appliances this threshold flags, the share that genuinely went on to need a repair.")

    if len(flagged) == 0:
        st.info("No appliances meet this threshold for this appliance type. Try lowering it or widening the filter.")
    else:
        display_cols = ["Appliance_ID", "Appliance_Type", "Brand", "City", "Appliance_Age_Yrs", score_col, band_col]
        flagged_display = flagged[display_cols].head(200).rename(columns={
            "Appliance_ID": "ID", "Appliance_Type": "Type", "Appliance_Age_Yrs": "Age (yrs)",
            score_col: "Risk score", band_col: "Band",
        })
        st.dataframe(
            flagged_display.style.format({"Age (yrs)": "{:.1f}", "Risk score": "{:.3f}"}),
            hide_index=True, use_container_width=True, height=320,
        )
        st.caption(f"Showing the top 200 of {len(flagged):,} flagged appliances, by risk score.", help=RISK_BAND_LEGEND)
        st.download_button(
            "Download full flagged list (CSV)",
            flagged[display_cols].to_csv(index=False),
            file_name=f"flagged_appliances_{window.replace(' ', '')}_{threshold}.csv",
        )

    st.markdown("---")
    st.subheader(f"Risk by appliance type ({window})")
    st.caption("Each bar shows the mix of Low/Medium/High risk within that appliance type.", help=RISK_BAND_LEGEND)

    grp = df.groupby(["Appliance_Type", band_col]).size().reset_index(name="count")
    totals = grp.groupby("Appliance_Type")["count"].transform("sum")
    grp["pct"] = grp["count"] / totals * 100

    fig = px.bar(
        grp, x="Appliance_Type", y="pct", color=band_col,
        color_discrete_map=RISK_BAND_COLORS,
        category_orders={band_col: ["Low", "Medium", "High"]},
        labels={"pct": "Share of appliances (%)", "Appliance_Type": ""},
    )
    fig.update_layout(barmode="stack", plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)",
                       legend_title="", height=400, bargap=0.4)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Complaint phrases")
    st.caption("Filter to see which complaints matter most for a specific type or city. "
               "Aggregating across all types can mix very different risk profiles together.")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        type_filter = st.selectbox("Appliance type", ["All"] + sorted(df["Appliance_Type"].unique().tolist()), key="complaint_type_filter")
    with col_f2:
        city_filter = st.selectbox("City", ["All"] + sorted(df["City"].unique().tolist()), key="complaint_city_filter")

    valid = df[df["Last_Complaint_Text_History"] != "No prior service on record"]
    if type_filter != "All":
        valid = valid[valid["Appliance_Type"] == type_filter]
    if city_filter != "All":
        valid = valid[valid["City"] == city_filter]

    if len(valid) == 0:
        st.info("No records found for this filter combination.")
        return

    phrase_stats = (
        valid.groupby("Last_Complaint_Text_History")
        .agg(occurrences=("Appliance_ID", "count"), avg_risk=(score_col, "mean"))
        .reset_index()
        .sort_values("occurrences", ascending=False)
    )

    most_common = phrase_stats.iloc[0]
    highest_risk = phrase_stats.sort_values("avg_risk", ascending=False).iloc[0]

    st.markdown(
        f"**Your most common complaint is '{most_common['Last_Complaint_Text_History']}'**, "
        f"while **your highest-risk complaint is '{highest_risk['Last_Complaint_Text_History']}'** "
        f"(avg. risk score {highest_risk['avg_risk']:.2f})."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**What customers report most**")
        top_common = phrase_stats.sort_values("occurrences", ascending=False).head(8).sort_values("occurrences")
        fig3 = px.bar(top_common, x="occurrences", y="Last_Complaint_Text_History", orientation="h",
                      labels={"occurrences": "Occurrences", "Last_Complaint_Text_History": ""})
        fig3.update_traces(marker_color=COLOR_NEUTRAL)
        fig3.update_layout(plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)", height=350)
        st.plotly_chart(fig3, use_container_width=True)
    with col2:
        st.markdown("**What actually signals risk**")
        top_risk = phrase_stats.sort_values("avg_risk", ascending=False).head(8).sort_values("avg_risk")
        fig4 = px.bar(top_risk, x="avg_risk", y="Last_Complaint_Text_History", orientation="h",
                      labels={"avg_risk": "Average risk score", "Last_Complaint_Text_History": ""})
        fig4.update_traces(marker_color=COLOR_BAD)
        fig4.update_layout(plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)", height=350)
        st.plotly_chart(fig4, use_container_width=True)
