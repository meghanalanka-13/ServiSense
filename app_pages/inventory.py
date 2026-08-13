# app_pages/inventory.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from data_loader import (
    load_repair_events, load_forecast_by_appliance_type, load_forecast_by_part,
    load_inventory_snapshot, load_appliances,
)
from config import COLOR_GOOD, COLOR_BAD, COLOR_NEUTRAL, COLOR_TEXT, COLOR_GOOD_SOLID, COLOR_BAD_SOLID, COLOR_NEUTRAL_SOLID, STOCK_HEALTH_LEGEND
from utils.helpers import colored_metric


def _stock_health(row):
    ratio = row["Current_SOH"] / row["MSL"] if row["MSL"] > 0 else 1
    if ratio < 0.5:
        return "Critical"
    if ratio < 1.0:
        return "Low"
    if ratio < 1.5:
        return "Safe"
    return "Overstock"


def show():
    prev = st.session_state.get("previous_page")
    if prev and prev != "Inventory & Parts":
        if st.button(f"\u2190 Back to {prev}", key="inv_back_link"):
            st.session_state.current_page = prev
            st.session_state.previous_page = None
            st.rerun()

    st.title("Inventory & Parts")
    st.caption("Forecasted demand, real stock levels, and whether technicians are already feeling it")

    events = load_repair_events()
    forecast_type = load_forecast_by_appliance_type()
    forecast_part = load_forecast_by_part()
    snap = load_inventory_snapshot()

    appliance_types = ["All"] + sorted(events["Appliance_Type"].unique().tolist())
    selected_type = st.selectbox("Appliance type", appliance_types)

    st.markdown("---")
    label = selected_type if selected_type != "All" else "all appliance types"
    st.subheader(f"Complaint volume: history and forecast \u2014 {label}")
    st.caption("The forecast is a real SARIMA model fit to this appliance type's own repair history."
               + (" 'All' sums each type's independent forecast, an approximation, not a jointly-fit model." if selected_type == "All" else ""))

    if selected_type == "All":
        history = (
            events.assign(Month=lambda d: d["Complaint_Raised_Date"].dt.to_period("M").dt.to_timestamp())
            .groupby("Month").size().reset_index(name="Complaints")
        )
        fc = forecast_type.groupby("Month").agg({"Forecast_Complaints": "sum", "Lo95": "sum", "Hi95": "sum"}).reset_index()
    else:
        history = (
            events[events["Appliance_Type"] == selected_type]
            .assign(Month=lambda d: d["Complaint_Raised_Date"].dt.to_period("M").dt.to_timestamp())
            .groupby("Month").size().reset_index(name="Complaints")
        )
        fc = forecast_type[forecast_type["Appliance_Type"] == selected_type]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=history["Month"], y=history["Complaints"], mode="lines",
                              name="History", line=dict(color=COLOR_TEXT)))
    fig.add_trace(go.Scatter(x=fc["Month"], y=fc["Forecast_Complaints"], mode="lines+markers",
                              name="Forecast", line=dict(color=COLOR_GOOD, dash="dash")))
    fig.add_trace(go.Scatter(
        x=pd.concat([fc["Month"], fc["Month"][::-1]]),
        y=pd.concat([fc["Hi95"], fc["Lo95"][::-1]]),
        fill="toself", fillcolor="rgba(70,130,180,0.15)", line=dict(width=0), mode="lines",
        name="80% confidence", showlegend=True,
    ))
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)", height=380,
                       legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("What that means for parts", help="Expected repairs needing each part, next month, allocated from the forecast above using each part's real historical share of repairs.")
    st.caption("Allocated from the forecast above using each part's real historical share of repairs.")

    if selected_type == "All":
        next_month_parts = (
            forecast_part.sort_values("Month").groupby("Part_Category_Needed").first().reset_index()
            .sort_values("Forecast_Demand", ascending=False)
        )
    else:
        next_month_parts = (
            forecast_part[forecast_part["Appliance_Type"] == selected_type]
            .sort_values("Month").groupby("Part_Category_Needed").first().reset_index()
            .sort_values("Forecast_Demand", ascending=False)
        )
    top3 = next_month_parts.head(3)
    cols_top3 = st.columns(3)
    for col, (_, row) in zip(cols_top3, top3.iterrows()):
        col.metric(row["Part_Category_Needed"], f"{row['Forecast_Demand']:.0f}")

    with st.expander(f"See all {len(next_month_parts)} parts"):
        st.dataframe(
            next_month_parts[["Part_Category_Needed", "Forecast_Demand"]]
            .rename(columns={"Part_Category_Needed": "Part", "Forecast_Demand": "Forecast demand, next month"})
            .style.format({"Forecast demand, next month": "{:.0f}"}),
            hide_index=True, use_container_width=True, height=min(38 * (len(next_month_parts) + 1), 400),
        )

    st.markdown("---")
    st.subheader("Risk-adjusted forecast")
    st.caption(
        "This is the hierarchical calculation: SARIMA's total forecast (pure time-series, no idea which "
        "specific appliances are risky) scaled down to just the share currently scoring at or above your "
        "threshold, then allocated across parts using THAT group's own part history, not the full "
        "population's. Set the threshold to something like 'only hold stock for High risk' and see what "
        "that implies for next month specifically."
    )

    risk_threshold = st.slider(
        "Minimum risk score to include", 0.0, 1.0, 0.7, 0.01,
        help="Only appliances scoring at or above this are counted below.",
        key="inv_risk_threshold",
    )

    appliances = load_appliances()
    type_scoped_appliances = appliances if selected_type == "All" else appliances[appliances["Appliance_Type"] == selected_type]
    scoped_appliances = type_scoped_appliances[type_scoped_appliances["Failure_Score_30D"] >= risk_threshold]
    scoped_with_part = scoped_appliances[scoped_appliances["Last_Part_Category_Used"] != "N/A"]

    risk_share = len(scoped_appliances) / len(type_scoped_appliances) if len(type_scoped_appliances) else 0

    if selected_type == "All":
        base_forecast_next_month = forecast_type.sort_values("Month").groupby("Appliance_Type").first()["Forecast_Complaints"].sum()
    else:
        base_forecast_next_month = fc.sort_values("Month")["Forecast_Complaints"].iloc[0]

    risk_adjusted_total = base_forecast_next_month * risk_share

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        st.metric("Appliances at/above threshold", f"{len(scoped_appliances):,}")
        st.caption(f"{risk_share*100:.1f}% of {'this type' if selected_type != 'All' else 'installed base'}")
    with col_r2:
        st.metric("Base forecast, next month", f"{base_forecast_next_month:.0f}",
                  help="SARIMA's total forecast for next month, before any risk filtering.")
    with col_r3:
        st.metric("Risk-adjusted forecast", f"{risk_adjusted_total:.0f}",
                  help=f"Base forecast \u00d7 risk share = {base_forecast_next_month:.0f} \u00d7 {risk_share:.3f} = {risk_adjusted_total:.1f}. "
                       f"Assumes the current risk composition holds into next month, a reasonable approximation, not a certainty.")

    if len(scoped_with_part) == 0:
        st.info("No appliances meet this threshold with a recorded part history. Try lowering it.")
    else:
        part_share = scoped_with_part["Last_Part_Category_Used"].value_counts(normalize=True)
        part_demand = (part_share * risk_adjusted_total).round(0).astype(int).reset_index()
        part_demand.columns = ["Part", "Risk-adjusted demand, next month"]

        top3_risk = part_demand.head(3)
        cols_top3_risk = st.columns(3)
        for col, (_, row) in zip(cols_top3_risk, top3_risk.iterrows()):
            col.metric(row["Part"], f"{row['Risk-adjusted demand, next month']:,}")

        with st.expander(f"See all {len(part_demand)} parts"):
            st.dataframe(
                part_demand,
                hide_index=True, use_container_width=True, height=min(38 * (len(part_demand) + 1), 400),
            )
            st.caption(f"Based on {len(scoped_with_part):,} currently-flagged appliances with a recorded part history.")

    st.markdown("---")
    st.subheader("Current stock health")
    st.caption("From a real day-by-day simulation of demand and restocking, not a live warehouse feed.")

    snap = snap.copy()
    snap["Health"] = snap.apply(_stock_health, axis=1)
    health_counts = snap["Health"].value_counts().reindex(["Critical", "Low", "Safe", "Overstock"]).fillna(0)

    cols2 = st.columns(4)
    band_colors = {"Critical": COLOR_BAD_SOLID, "Low": COLOR_BAD_SOLID, "Safe": COLOR_GOOD_SOLID, "Overstock": COLOR_NEUTRAL_SOLID}
    for col, band in zip(cols2, ["Critical", "Low", "Safe", "Overstock"]):
        with col:
            colored_metric(band, str(int(health_counts[band])), band_colors[band])
    st.caption(STOCK_HEALTH_LEGEND)

    st.markdown("---")
    st.subheader("Purchase suggestions")
    city_filter_purchase = st.selectbox(
        "City", ["All"] + sorted(snap["City"].unique().tolist()), key="purchase_city_filter",
    )
    shortage_scope = snap if city_filter_purchase == "All" else snap[snap["City"] == city_filter_purchase]
    shortage = shortage_scope[shortage_scope["Required"] > 0].sort_values("Required", ascending=False)

    if len(shortage) == 0:
        st.info("Nothing currently below safety stock for this filter.")
    else:
        top3_shortage = shortage.head(3)
        cols_top3_shortage = st.columns(3)
        for col, (_, row) in zip(cols_top3_shortage, top3_shortage.iterrows()):
            col.metric(f"{row['Part_Category_Needed']} ({row['City']})", f"{row['Required']:.0f}",
                       help="Units to order to get back to safety stock level.")

        with st.expander(f"See all {len(shortage)} part/city combinations below safety stock"):
            st.dataframe(
                shortage[["Part_Category_Needed", "City", "Current_SOH", "MSL", "Required"]]
                .rename(columns={"Part_Category_Needed": "Part", "Current_SOH": "In stock", "MSL": "Safety level", "Required": "Need to order"}),
                hide_index=True, use_container_width=True, height=min(38 * (len(shortage) + 1), 450),
            )

    st.markdown("---")
    st.subheader("Field reports vs. simulated stock across cities")
    st.caption(
        "For each part: how often technicians have reported waiting on it in the past, compared to how "
        "many cities are showing it Critical or Low in stock right now. One honest caveat: stock is a "
        "shared pool across every appliance type that uses the same part (e.g. PCB is used by several "
        "types), so filtering below scopes the historical side, but current stock always reflects all "
        "types combined, since that's how the underlying inventory actually works."
    )

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        agree_type_filter = st.selectbox(
            "Appliance type", ["All"] + sorted(events["Appliance_Type"].unique().tolist()),
            key="agree_type_filter",
        )
    with col_f2:
        agree_city_filter = st.selectbox(
            "City", ["All"] + sorted(events["City"].unique().tolist()),
            key="agree_city_filter",
        )

    events_scoped = events if agree_type_filter == "All" else events[events["Appliance_Type"] == agree_type_filter]
    if agree_city_filter != "All":
        events_scoped = events_scoped[events_scoped["City"] == agree_city_filter]
    relevant_parts = sorted(events_scoped["Part_Category_Needed"].unique().tolist())

    snap_scoped = snap if agree_city_filter == "All" else snap[snap["City"] == agree_city_filter]

    stockout_rate_by_part = (
        events_scoped.groupby("Part_Category_Needed")["Stockout_At_Time_Of_Repair"]
        .mean().reset_index().rename(columns={"Stockout_At_Time_Of_Repair": "rate"})
    )
    cities_tracked = snap_scoped.groupby("Part_Category_Needed").size().rename("total_cities")
    cities_low_crit = (
        snap_scoped[snap_scoped["Health"].isin(["Critical", "Low"])]
        .groupby("Part_Category_Needed").size().rename("low_crit_cities")
    )

    compare = (
        stockout_rate_by_part.set_index("Part_Category_Needed")
        .join(cities_tracked).join(cities_low_crit)
        .fillna(0).reset_index()
    )
    compare = compare[compare["Part_Category_Needed"].isin(relevant_parts)].sort_values("rate", ascending=False)

    if len(compare) == 0:
        st.info("No parts found for this filter.")
    else:
        table = compare.copy()
        table["Historical stockout rate"] = (table["rate"] * 100).round(1)
        col_label = "Critical/Low now" if agree_city_filter != "All" else "Cities Critical/Low"
        table[col_label] = (
            table["low_crit_cities"].astype(int).astype(str) + " of " + table["total_cities"].astype(int).astype(str)
        )
        table = table.rename(columns={"Part_Category_Needed": "Part"})[
            ["Part", "Historical stockout rate", col_label]
        ]

        top3_field = table.head(3)
        cols_top3_field = st.columns(3)
        for col, (_, row) in zip(cols_top3_field, top3_field.iterrows()):
            col.metric(row["Part"], f"{row['Historical stockout rate']:.1f}%", help=f"{col_label}: {row[col_label]}")

        with st.expander(f"See all {len(table)} parts"):
            st.dataframe(
                table.style.format({"Historical stockout rate": "{:.1f}%"}),
                hide_index=True, use_container_width=True, height=min(38 * (len(table) + 1), 740),
            )
