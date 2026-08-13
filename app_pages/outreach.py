# app_pages/outreach.py
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from data_loader import load_appliances
from config import COLOR_GOOD, COLOR_NEUTRAL


def show():
    st.title("Customer Outreach")
    st.caption("Proactively reach customers before they call you, pick the risk level worth reaching out at")

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

    threshold = st.slider(
        "Minimum risk score to include in outreach", 0.0, 1.0, 0.5, 0.01,
        help="Customers whose appliance scores at or above this get included in the outreach list.",
    )
    st.caption("Slide to adjust the risk % threshold.")

    reached = scoped[scoped["Failure_Score_30D"] >= threshold]
    pct_reached = len(reached) / len(scoped) if len(scoped) else 0

    st.markdown("---")
    scope_label = " / ".join([x for x in [type_filter, city_filter] if x != "All"]) or "your full installed base"
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric(f"Customers reached ({scope_label})", f"{len(reached):,}")
    with col_b:
        st.metric("Share of this scope reached", f"{pct_reached*100:.1f}%")

    with st.expander("See the detailed risk distribution behind this number"):
        st.caption("Where your current threshold sits relative to the full risk distribution for this scope.")
        scores = scoped["Failure_Score_30D"]

        # One consistent set of bins across the WHOLE range, then color
        # each bar by threshold -- two separately-binned histograms (one
        # per side of the threshold) would each pick their own bin width
        # from their own data range, producing mismatched-width bars that
        # visually collide right at the threshold boundary.
        nbins = 40
        bin_edges = np.linspace(0, 1, nbins + 1)
        counts, _ = np.histogram(scores, bins=bin_edges)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        bin_width = bin_edges[1] - bin_edges[0]
        bar_colors = [COLOR_GOOD if c >= threshold else COLOR_NEUTRAL for c in bin_centers]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=bin_centers, y=counts, marker_color=bar_colors, width=bin_width * 0.95,
        ))
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)", height=320,
                           xaxis_title="Risk score", yaxis_title="Appliances", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Customers to contact")

    display_cols = ["Appliance_ID", "Brand", "Appliance_Type", "City", "Failure_Score_30D", "Last_Part_Category_Used", "Days_Since_Last_Service"]
    display = reached.sort_values("Failure_Score_30D", ascending=False)[display_cols].head(200).rename(columns={
        "Appliance_ID": "ID", "Appliance_Type": "Type", "Failure_Score_30D": "Risk score",
        "Last_Part_Category_Used": "Likely part at risk", "Days_Since_Last_Service": "Days since last visit",
    })
    st.dataframe(
        display.style.format({"Risk score": "{:.3f}", "Days since last visit": "{:.0f}"}),
        hide_index=True, use_container_width=True, height=320,
    )
    st.caption(f"Showing the top 200 of {len(reached):,} customers, by risk score.")
    st.download_button(
        "Download full outreach list (CSV)",
        reached[display_cols].to_csv(index=False),
        file_name=f"outreach_list_{threshold}.csv",
    )

    st.markdown("---")
    st.subheader("Sample message")
    if len(reached) > 0:
        sample = display.iloc[0]
        st.markdown(
            f"> Hi! Based on your {sample['Brand']} {sample['Type']}'s usage pattern, "
            f"we'd recommend a preventive check soon to avoid an unexpected breakdown. "
            f"Would you like to schedule a visit?"
        )
    else:
        st.info("No customers at this threshold/scope. Try lowering the threshold or widening the filters.")
