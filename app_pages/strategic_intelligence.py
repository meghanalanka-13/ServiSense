# app_pages/strategic_intelligence.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_loader import load_repair_events
from config import COLOR_GOOD_SOLID, COLOR_BAD_SOLID, COLOR_NEUTRAL_SOLID, COLOR_BAD
from utils.helpers import colored_metric

CITY_COORDS = {
    "Delhi": (28.7041, 77.1025), "Mumbai": (19.0760, 72.8777),
    "Kolkata": (22.5726, 88.3639), "Chennai": (13.0827, 80.2707),
    "Bengaluru": (12.9716, 77.5946), "Ahmedabad": (23.0225, 72.5714),
    "Hyderabad": (17.3850, 78.4867),
}


def _trend(current: float, prior: float, up_is_bad: bool):
    """A REAL arrow, computed from an actual trailing-12-months vs
    prior-12-months comparison -- not decorative. Direction/color depend
    on whether an increase is good or bad for that specific metric."""
    if abs(current - prior) < 1e-9:
        return "\u2192", COLOR_NEUTRAL_SOLID
    went_up = current > prior
    bad = went_up if up_is_bad else not went_up
    arrow = "\u2191" if went_up else "\u2193"
    return arrow, (COLOR_BAD_SOLID if bad else COLOR_GOOD_SOLID)


def show():
    st.title("Strategic Intelligence")
    st.caption("The business-level view: service quality and where your volume actually is")

    events = load_repair_events()

    latest_date = events["Complaint_Raised_Date"].max()
    last_12mo = events[events["Complaint_Raised_Date"] > latest_date - pd.Timedelta(days=365)]
    prior_12mo = events[
        (events["Complaint_Raised_Date"] <= latest_date - pd.Timedelta(days=365))
        & (events["Complaint_Raised_Date"] > latest_date - pd.Timedelta(days=730))
    ]

    def _rate(df, status_check):
        return status_check(df).mean() if len(df) else 0.0

    repeat_now = _rate(last_12mo, lambda d: d["Resolution_Status"] == "Pending Follow-up")
    repeat_prior = _rate(prior_12mo, lambda d: d["Resolution_Status"] == "Pending Follow-up")
    fv_now = _rate(last_12mo, lambda d: d["Resolution_Status"].isin(["Fixed", "Part Replaced"]))
    fv_prior = _rate(prior_12mo, lambda d: d["Resolution_Status"].isin(["Fixed", "Part Replaced"]))
    stockout_now = _rate(last_12mo, lambda d: d["Stockout_At_Time_Of_Repair"])
    stockout_prior = _rate(prior_12mo, lambda d: d["Stockout_At_Time_Of_Repair"])

    repeat_arrow, repeat_color = _trend(repeat_now, repeat_prior, up_is_bad=True)
    fv_arrow, fv_color = _trend(fv_now, fv_prior, up_is_bad=False)
    stockout_arrow, stockout_color = _trend(stockout_now, stockout_prior, up_is_bad=True)

    st.caption(
        f"Arrows compare the trailing 12 months ({last_12mo['Complaint_Raised_Date'].min().date()} to "
        f"{latest_date.date()}) against the 12 months before that."
    )

    # Overall (all-time, whole dataset) rates -- what the tooltips explain against
    overall_repeat_event = (events["Resolution_Status"] == "Pending Follow-up").mean()
    overall_repeat_appliance = (
        events.groupby("Appliance_ID")["Resolution_Status"]
        .apply(lambda s: (s == "Pending Follow-up").any()).mean()
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        colored_metric("Repeat visit rate (per visit)", f"{repeat_now*100:.1f}%", repeat_color, repeat_arrow, help_text=(
            f"Of every repair VISIT (not appliance), the share that ended in 'Pending Follow-up'. "
            f"An operational metric: of the jobs technicians do, how often do they need to come back? "
            f"Shown here: trailing 12 months. All-time average across the full dataset: {overall_repeat_event*100:.1f}%."
        ))
    with col2:
        colored_metric("First-visit resolution rate", f"{fv_now*100:.1f}%", fv_color, fv_arrow, help_text=(
            "Share of repairs fully resolved (Fixed or Part Replaced) in one visit, trailing 12 months. Higher is better."
        ))
    with col3:
        colored_metric("Stock-out rate", f"{stockout_now*100:.1f}%", stockout_color, stockout_arrow, help_text=(
            "Share of repairs where the needed part was genuinely out of stock at the time, trailing 12 months. "
            "Lower is better. Note: in this dataset, a stockout is specifically what CAUSES a 'Pending Follow-up' "
            "status, so this number and the repeat visit rate move together by construction, not coincidence."
        ))

    st.markdown("---")
    col4, col5 = st.columns(2)
    with col4:
        st.metric("Repeat rate (per appliance, all-time)", f"{overall_repeat_appliance*100:.1f}%")
        st.caption(
            "A different question from the metric above",
            help=(
                f"Of the 200,000 unique APPLIANCES (not visits), the share that has EVER had at least one "
                f"'Pending Follow-up' visit in its history. A customer-experience metric: of everyone we've "
                f"ever serviced, what share has had at least one bad visit? This is naturally higher than the "
                f"per-visit rate ({overall_repeat_event*100:.1f}%) since an appliance with several visits only "
                f"needs ONE of them to go badly to count here. No year-over-year arrow -- this is a cumulative, "
                f"all-time figure, not a rate for a specific period."
            ),
        )
    with col5:
        cost_per_visit = st.number_input("Assumed cost per repeat visit (\u20b9)", min_value=0, value=800, step=100)
        repeat_count = (events["Resolution_Status"] == "Pending Follow-up").sum()
        est_cost = repeat_count * cost_per_visit
        st.metric("Est. cost of repeat visits (all-time)", f"\u20b9{est_cost:,.0f}",
                  help="Repeat-visit count (all-time, per-visit basis) multiplied by the cost you enter above. "
                       "Not a bookkeeping figure, plug in your own real number.")

    st.markdown("---")
    st.subheader("Where your complaint volume is")
    st.caption("Marker size = total repair volume in that city, across the full history.")

    by_city = events.groupby("City").size().reset_index(name="Volume")
    by_city["lat"] = by_city["City"].map(lambda c: CITY_COORDS[c][0])
    by_city["lon"] = by_city["City"].map(lambda c: CITY_COORDS[c][1])

    fig = go.Figure(go.Scattermap(
        lat=by_city["lat"], lon=by_city["lon"],
        mode="markers+text",
        marker=dict(size=by_city["Volume"] / by_city["Volume"].max() * 40 + 10, color=COLOR_BAD),
        text=by_city["City"], textposition="top center",
        hovertext=by_city.apply(lambda r: f"{r['City']}: {r['Volume']:,} repairs", axis=1),
        hoverinfo="text",
    ))
    fig.update_layout(
        map=dict(style="open-street-map", center=dict(lat=22, lon=80), zoom=3.6),
        height=480, margin=dict(l=0, r=0, t=0, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        by_city[["City", "Volume"]].sort_values("Volume", ascending=False)
        .rename(columns={"Volume": "Total repairs"}),
        hide_index=True, use_container_width=True,
    )
