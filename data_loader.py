# data_loader.py
# ============================================================
# Every page reads data through this module. Loading is cached
# (@st.cache_data) so the ~230MB of underlying CSVs are read from disk
# once per app session, not once per page click.
# ============================================================

import json
import pandas as pd
import streamlit as st
from pathlib import Path
from config import DATA_DIR, RISK_BAND_LOW_MAX, RISK_BAND_HIGH_MIN

DATA_PATH = Path(DATA_DIR)


def _risk_band(score: float) -> str:
    if score < RISK_BAND_LOW_MAX:
        return "Low"
    if score < RISK_BAND_HIGH_MIN:
        return "Medium"
    return "High"


@st.cache_data(show_spinner="Loading appliance data...")
def load_appliances() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH / "appliances_scored.csv.gz", parse_dates=[
        "Install_Date", "Last_Service_Date", "Last_PM_Date", "Next_PM_Due_Date"
    ])
    df["Risk_Band"] = df["Failure_Score_30D"].apply(_risk_band)
    df["Risk_Band_90D"] = df["Failure_Score_90D"].apply(_risk_band)
    return df


@st.cache_data(show_spinner="Loading inventory data...")
def load_inventory_snapshot() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH / "inventory_snapshot.csv")


@st.cache_data(show_spinner="Loading inventory history...")
def load_inventory_ledger() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH / "inventory_ledger.csv.gz", parse_dates=["Date"])


@st.cache_data
def load_stockout_days() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH / "stockout_days.csv", parse_dates=["Date"])


@st.cache_data(show_spinner="Loading repair history...")
def load_repair_events() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH / "repair_events.csv.gz", parse_dates=["Complaint_Raised_Date"])


@st.cache_data
def load_forecast_by_appliance_type() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH / "forecast_by_appliance_type.csv", parse_dates=["Month"])


@st.cache_data
def load_forecast_by_part() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH / "forecast_by_part.csv", parse_dates=["Month"])


@st.cache_data
def load_cross_dependency_results() -> dict:
    with open(DATA_PATH / "cross_dependency_results.json") as f:
        return json.load(f)


@st.cache_data
def load_seasonal_strength() -> dict:
    with open(DATA_PATH / "seasonal_decomposition_strength.json") as f:
        return json.load(f)


@st.cache_data
def load_model_metrics() -> dict:
    with open(DATA_PATH / "model_metrics.json") as f:
        return json.load(f)


@st.cache_data
def load_feature_importance(window: str = "30D") -> pd.DataFrame:
    return pd.read_json(DATA_PATH / f"feature_importance_{window}.json")
