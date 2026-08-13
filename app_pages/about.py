# app_pages/about.py
import streamlit as st
import pandas as pd
import plotly.express as px
from config import COLOR_GOOD
from data_loader import (
    load_model_metrics, load_seasonal_strength, load_cross_dependency_results,
    load_appliances, load_forecast_by_appliance_type, load_feature_importance,
)

FEATURE_LABELS = {
    "Appliance_Age_Yrs": "Appliance age",
    "Usage_Intensity": "Usage intensity",
    "Cumulative_Usage_Hours": "Total hours used",
    "Ambient_Humidity": "Ambient humidity",
    "Water_Hardness_TDS": "Water hardness",
    "Voltage_Stability_Index": "Voltage stability",
    "Cooling_Efficiency_Score": "Cooling efficiency",
    "Dust_Exposure_Level": "Dust exposure",
    "Prev_Repair_Count": "Past repair count",
    "Failure_Velocity": "Pace of past breakdowns",
    "Days_Since_Last_Service": "Days since last service",
    "Days_To_Next_PM": "Days to next scheduled maintenance",
    "PM_Due_Next_14D": "Maintenance due within 14 days",
    "AMC_Status": "Under AMC contract",
    "Net_Profit": "Net profit potential",
}
CATEGORICAL_PREFIX_LABELS = {
    "Last_Part_Category_Used": "Part needed",
    "Last_Complaint_Text_History": "Complaint",
    "Last_Root_Cause_Tag": "Root cause",
    "Last_Resolution_Status": "Last resolution",
    "Appliance_Type": "Appliance type",
    "Brand": "Brand",
    "City": "City",
    "Installation_Quality": "Install quality",
    "Warranty_Status": "Warranty",
}


def _readable_feature(raw_name: str) -> str:
    for key, label in FEATURE_LABELS.items():
        if raw_name == key:
            return label
    for prefix in sorted(CATEGORICAL_PREFIX_LABELS, key=len, reverse=True):
        if raw_name.startswith(prefix + "_"):
            value = raw_name[len(prefix) + 1:].replace("_", " ")
            return f"{CATEGORICAL_PREFIX_LABELS[prefix]}: {value}"
    return raw_name.replace("_", " ")


SECTIONS = ["Dataset", "Failure Model", "Forecasting", "Cross-Dependencies", "Recommender", "Roadmap"]


def show():
    st.title("About this tool")
    st.caption("Technical documentation, methodology, and honest limitations.")

    # A session-state-driven radio, not st.tabs(). st.tabs() has known
    # cross-version inconsistencies in how it persists the active tab
    # across reruns (older Streamlit can silently reset to the first tab
    # the instant any widget inside a tab triggers a rerun -- exactly
    # what a 30D/90D toggle does). A plain radio, tracked explicitly in
    # session_state, behaves identically on every Streamlit version.
    if "about_section" not in st.session_state:
        st.session_state.about_section = SECTIONS[0]
    section = st.radio("Section", SECTIONS, horizontal=True, label_visibility="collapsed", key="about_section")

    if section == "Dataset":
        st.subheader("How this dataset was generated")
        st.markdown("""
        - **200,000 synthetic appliances**: 6 types, 7 Indian cities, 5.7 years of simulated repair history (2021 to 2026).
        - **Every seasonal pattern is sourced, not invented**: AC and refrigerator compressor stress from summer heat,
          water heater stress from winter demand, water purifier's two-peak pattern (monsoon sediment plus summer TDS load).
          Microwave deliberately shows no seasonality, an honest control case, not an oversight.
        - **Real inventory simulation**: stock levels come from an actual day-by-day (s,S) reorder policy driven by
          real generated demand, not a random number dressed up as one.
        - **Cross-part dependencies are real, not decorative**: a documented failure cascade, such as a failing
          condenser coil raising compressor risk, actually generates a real chance of a follow-up event in the
          data, not just a citation sitting next to unrelated numbers.
        - **Target definition**: `Repair_Req_Next_30D` and `90D` use a genuine backtest split. Features come only
          from events before a reference date, and the target checks for a real event strictly after it. No leakage
          by construction.
        """)
        df = load_appliances()
        st.metric("Appliances with zero prior service history", f"{(df['Prev_Repair_Count']==0).sum():,} of {len(df):,}")

    elif section == "Failure Model":
        st.subheader("Model evaluation")

        st.markdown("**A note on reading these numbers**")
        st.caption(
            "ROC-AUC's random baseline is always 0.5, regardless of class balance. PR-AUC's random baseline "
            "is the positive rate itself, so comparing a PR-AUC number to the '0.7 is good' rule (a "
            "ROC-AUC heuristic) is comparing two different scales."
        )

        metrics = load_model_metrics()
        window = st.radio("Window", ["30D", "90D"], horizontal=True, key="about_model_window")
        m = metrics[f"Repair_Req_Next_{window}"]

        col1, col2, col3 = st.columns(3)
        col1.metric("ROC-AUC", m["roc_auc"])
        col2.metric("PR-AUC", m["pr_auc"], f"baseline {m['pr_auc_baseline']}")
        col3.metric("PR-AUC lift over baseline", f"{m['pr_auc_lift_over_baseline']}x")

        st.markdown("**Confusion matrix** (held-out test set)")
        cm = m["confusion_matrix"]
        cm_df = pd.DataFrame(cm, index=["Actual: No", "Actual: Yes"], columns=["Predicted: No", "Predicted: Yes"])
        st.dataframe(cm_df)

        st.caption(
            f"Trained on {m['train_rows']:,} rows, tested on {m['test_rows']:,}. "
            f"scale_pos_weight={m['scale_pos_weight_used']} to counter the {m['positive_rate']*100:.1f}% positive rate."
        )

        st.markdown("---")
        st.markdown("**Leakage check**: an automated single-feature AUC scan ran against every numeric feature "
                    "before this model was trusted. No feature exceeded 0.85 AUC alone, so no leakage was detected.")

        st.markdown("---")
        st.subheader("What drives the model")
        st.caption("The features with the strongest influence on a given appliance's risk score.")
        fi = load_feature_importance(window)
        fi["label"] = fi["feature"].apply(_readable_feature)
        fi_top = fi.drop_duplicates("label").head(8).sort_values("importance")
        fig_fi = px.bar(fi_top, x="importance", y="label", orientation="h",
                        labels={"importance": "Relative influence", "label": ""})
        fig_fi.update_traces(marker_color=COLOR_GOOD)
        fig_fi.update_layout(plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)", height=350)
        st.plotly_chart(fig_fi, use_container_width=True)

    elif section == "Forecasting":
        st.subheader("Seasonal decomposition strength")
        st.caption("Verified before committing to SARIMA's seasonal terms, not assumed just because seasonality was designed in.")
        strength = load_seasonal_strength()
        strength_df = pd.DataFrame(list(strength.items()), columns=["Appliance Type", "Seasonal Strength"]).sort_values(
            "Seasonal Strength", ascending=False)
        fig = px.bar(strength_df, x="Appliance Type", y="Seasonal Strength")
        fig.update_traces(marker_color=COLOR_GOOD)
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)", height=300)
        st.plotly_chart(fig, use_container_width=True)

        lowest = strength_df.iloc[-1]
        st.caption(
            f"{lowest['Appliance Type']} scores lowest ({lowest['Seasonal Strength']:.3f}) in this run. "
            f"Microwave has no designed weather mechanism at all, so it should always land among the weakest "
            f"regardless of exact rank, worth checking it never scores anywhere near AC's level."
        )

        st.markdown("---")
        fc = load_forecast_by_appliance_type()
        orders = fc[["Appliance_Type", "Model_Order"]].drop_duplicates()
        zero_seasonal = orders[orders["Model_Order"].str.contains(r"\(0, 0, 0, 12\)")]["Appliance_Type"].tolist()
        if zero_seasonal:
            st.markdown(
                f"**Cross-validated a second way**: `auto_arima`'s own AIC-based model selection independently "
                f"agreed on some appliances. It chose zero seasonal terms for "
                f"**{', '.join(zero_seasonal)}** in this run, without being told to."
            )
        else:
            st.markdown(
                "**Cross-validated a second way**: `auto_arima`'s own AIC-based model selection gave every "
                "appliance type at least one real seasonal term in this run, consistent with the seasonal "
                "strength chart above showing every type registering some real signal."
            )
        with st.expander("See the actual chosen order per appliance type"):
            st.dataframe(orders, hide_index=True, use_container_width=True)

    elif section == "Cross-Dependencies":
        st.subheader("Sourced cross-part dependency edges")
        st.caption(
            "Structure (which parts connect) comes from real repair-industry sources, found by direct search, "
            "not general reasoning. Parameters (how strong each link is) are learned from this dataset via a "
            "real Bayesian network (pgmpy), not hand-tuned."
        )
        cross_deps = load_cross_dependency_results()
        for atype, edges in cross_deps.items():
            with st.expander(f"{atype} ({len(edges)} edges)"):
                for e in edges:
                    st.markdown(f"**{e['part_a']} \u2192 {e['part_b']}**: lift {e['lift']}x "
                               f"({e['p_b_given_a_failed']*100:.0f}% vs {e['p_b_given_a_ok']*100:.0f}%)")
                    st.caption(e["mechanism"])

    elif section == "Recommender":
        st.subheader("How Technician Support works")
        st.markdown("""
        Free-text queries are matched against real historical technician notes using **TF-IDF and cosine similarity**,
        a classic, fully offline semantic-search technique. No API key, no cost, no external dependency.

        **A known, real limitation, found during testing**: TF-IDF has no concept of synonyms or world knowledge.
        A query using a word that never appears anywhere in the notes corpus, such as "hissing", gets zero signal for
        that word and falls back to matching on whatever other words happen to overlap, which can produce a
        less relevant match than the same query phrased with more common vocabulary. This is a real, demonstrated
        gap, not a hypothetical one, and it is the specific thing a real language model would close (see Roadmap).
        """)

    elif section == "Roadmap":
        st.subheader("Planned enhancements")
        st.markdown("""
        - **AI-API-based recommender** (e.g. Claude): would close the TF-IDF vocabulary gap above and support
          real follow-up conversation. Deliberately not built yet, since the investment pays off once there's real
          production interest and scale to justify it, not before. Would be retrieval-grounded (only synthesizes
          from real retrieved cases, never invents a diagnosis) with hardcoded hazard-term safety rules that
          fire regardless of model output.
        - **IoT and real-time sensor data**: would replace usage-intensity proxies with actual telemetry (cycle
          counts, runtime temperatures) from connected appliances, and would let the cross-dependency analysis
          move from replacement-record correlation to physical precursor signal.
        - **Age and usage-adjusted hazard-ratio cross-dependency model**: the current lift numbers don't control for
          shared root causes, such as appliance age driving both parts' failure independently. A Cox proportional
          hazards approach would isolate the genuine cascade effect from this confound.
        - **Real deployment requirements**: authentication (a Partner Portal login already exists in the parent
          site), a real database instead of CSV files, and hosting. This is a demo-stage prototype, not a
          production system, and shouldn't be mistaken for one.
        """)
