# app_pages/overview.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from data_loader import load_appliances, load_inventory_snapshot
from utils.helpers import TOOLTIPS, fmt_pct, colored_metric
from config import RISK_BAND_COLORS, RISK_BAND_LEGEND, COLOR_BAD_SOLID, COLOR_NEUTRAL_SOLID


def show():
    st.title("Overview")
    st.caption("What's happening across your installed base right now")

    df = load_appliances()
    inv = load_inventory_snapshot()

    high_risk_pct = (df["Risk_Band"] == "High").mean()
    top10_cutoff = df["Failure_Score_30D"].quantile(0.90)
    top10 = df[df["Failure_Score_30D"] >= top10_cutoff]
    overall_positive_rate = df["Repair_Req_Next_30D"].mean()
    catch_rate = top10["Repair_Req_Next_30D"].sum() / df["Repair_Req_Next_30D"].sum()
    lift = (top10["Repair_Req_Next_30D"].mean() / overall_positive_rate)

    st.markdown(
        f"**Prioritizing your top 10% highest-risk appliances catches "
        f"{fmt_pct(catch_rate)} of appliances that actually need service "
        f"in the next 30 days**, about {lift:.1f}x better than contacting "
        f"customers at random."
    )
    st.caption(
        f"Based on real repair outcomes in this dataset: {top10['Repair_Req_Next_30D'].mean()*100:.1f}% of your "
        f"top-10%-riskiest appliances actually needed a repair, versus {overall_positive_rate*100:.1f}% "
        f"across everyone.",
        help=(
            f"Lift = (repair rate within your top 10% highest-risk appliances) \u00f7 "
            f"(repair rate across everyone) = {top10['Repair_Req_Next_30D'].mean()*100:.1f}% \u00f7 "
            f"{overall_positive_rate*100:.1f}% = {lift:.1f}x. "
            f"Right now, 'top 10%' means a risk score of {top10_cutoff:.2f} or above -- "
            f"this is a percentile cutoff, not a fixed number, so it will shift if the score distribution changes."
        ),
    )

    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        colored_metric("High risk", fmt_pct(high_risk_pct), COLOR_BAD_SOLID, help_text=(
            "Low: below 40% predicted risk. Medium: 40-70%. High: above 70%. "
            "This score is a PREDICTION from a trained model (XGBoost), not a directly observed fact -- "
            "based on each appliance's age, usage, install quality, and repair history. "
            "See About \u2192 Failure Model for the model's real accuracy numbers."
        ))
        st.caption("From the ML model's predictions")
        if st.button("See these appliances \u2192", key="ov_high_risk_link"):
            st.session_state.previous_page = "Overview"
            st.session_state.current_page = "Failure Risk"
            st.rerun()
    with col2:
        st.metric("Total appliances", f"{len(df):,}")
        st.caption("A simple count, all appliances on record")
    with col3:
        below_msl = (inv["Current_SOH"] < inv["MSL"]).sum()
        colored_metric("Parts below safety stock", f"{below_msl} of {len(inv)}", COLOR_BAD_SOLID, help_text=(
            "MSL (minimum stock level) is the safety-stock threshold a part should stay above, given its "
            "typical demand and restock lead time. Both current stock and MSL come from a real day-by-day "
            "simulation of demand and restocking -- not a live warehouse feed. See Inventory & Parts for detail."
        ))
        st.caption("From a simulated day-by-day inventory model")
        if st.button("See inventory details \u2192", key="ov_inv_link"):
            st.session_state.previous_page = "Overview"
            st.session_state.current_page = "Inventory & Parts"
            st.rerun()

    st.markdown("---")
    st.subheader("Risk across your installed base")
    st.caption(
        "Most appliances are Low risk right now. High-risk appliances are the ones worth acting on first. "
        "Every bar here is the model's predicted risk band, not a count of appliances that have actually failed.",
        help=RISK_BAND_LEGEND,
    )

    counts = df["Risk_Band"].value_counts().reindex(["Low", "Medium", "High"]).fillna(0)
    # A single go.Bar trace with per-bar colors, not px.bar's color=
    # (which creates one trace per color -- and in grouped-bar mode,
    # each trace gets a small centering offset meant for when there are
    # multiple bars per category, even when there's only one). That
    # offset is what was pushing each bar away from its own tick label.
    # One trace with a marker_color list has no grouping to offset.
    fig = go.Figure(go.Bar(
        x=counts.index, y=counts.values,
        marker_color=[RISK_BAND_COLORS[c] for c in counts.index],
        width=0.45,
    ))
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)", height=440,
                       yaxis_title="Appliances", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
