import json
from pathlib import Path

import pandas as pd
import streamlit as st

EXCEL_PATH = Path.home() / "sensor_readingsC.xlsx"
BASELINE_JSON_PATH = Path.home() / "baseline_config.json"
SHEET_NAME = "Readings"

st.set_page_config(
    page_title="HVAC Adaptive AI Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- AUTO REFRESH --------------------
st.sidebar.title("Dashboard Controls")
auto_refresh = st.sidebar.checkbox("Auto refresh", value=True)
refresh_seconds = st.sidebar.slider("Refresh every (seconds)", 2, 30, 5)

if auto_refresh:
    st.markdown(
        f"""
        <script>
            setTimeout(function(){{
                window.location.reload();
            }}, {refresh_seconds * 1000});
        </script>
        """,
        unsafe_allow_html=True,
    )

# -------------------- LOADERS --------------------
@st.cache_data(ttl=2)
def load_data():
    if not EXCEL_PATH.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=2)
def load_baseline():
    if not BASELINE_JSON_PATH.exists():
        return {}
    try:
        with open(BASELINE_JSON_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def fmt(value, decimals=2, suffix=""):
    if pd.isna(value) or value is None:
        return "--"
    try:
        return f"{float(value):.{decimals}f}{suffix}"
    except Exception:
        return str(value)


# -------------------- HEADER --------------------
st.title("HVAC Adaptive AI Dashboard")
st.caption("Real-time site-adaptive HVAC efficiency and anomaly monitoring")

df = load_data()
baseline = load_baseline()

if df.empty:
    st.warning("No data found yet. Run the live HVAC adaptive AI script first.")
    st.stop()

# -------------------- PREP DATA --------------------
if "Timestamp" in df.columns:
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")

df = df.sort_values("Timestamp")
latest = df.iloc[-1]

# Optional numeric conversion for safety
numeric_cols = [
    "Temperature_C",
    "Humidity_%",
    "ApparentPower_VA",
    "Smart_Efficiency_Index",
    "Deviation_Score",
    "Cooling_Rate_C_per_min",
    "Effective_Cooling_Rate_C_per_min",
]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# -------------------- TOP STATUS BANNER --------------------
ai_status = str(latest.get("Adaptive_AI_Status", "--"))
anomaly_flag = str(latest.get("Anomaly_Flag", "--"))
risk = str(latest.get("Predicted_Risk", "--"))
recommendation = str(latest.get("Recommendation", "No recommendation available"))

if anomaly_flag == "Yes":
    st.error(
        f"AI Status: {ai_status} | Anomaly Flag: {anomaly_flag} | Risk: {risk}"
    )
elif "Moderate" in ai_status:
    st.warning(
        f"AI Status: {ai_status} | Anomaly Flag: {anomaly_flag} | Risk: {risk}"
    )
else:
    st.success(
        f"AI Status: {ai_status} | Anomaly Flag: {anomaly_flag} | Risk: {risk}"
    )

# -------------------- KPI ROW 1 --------------------
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Mode", str(latest.get("Mode", "--")))
k2.metric("Temperature (°C)", fmt(latest.get("Temperature_C"), 2))
k3.metric("Humidity (%)", fmt(latest.get("Humidity_%"), 2))
k4.metric("Power (VA)", fmt(latest.get("ApparentPower_VA"), 2))
k5.metric("SEI", fmt(latest.get("Smart_Efficiency_Index"), 3))

# -------------------- KPI ROW 2 --------------------
k6, k7, k8, k9, k10 = st.columns(5)
k6.metric("Cooling Rate (°C/min)", fmt(latest.get("Cooling_Rate_C_per_min"), 3))
k7.metric("Effective Cooling", fmt(latest.get("Effective_Cooling_Rate_C_per_min"), 3))
k8.metric("Deviation Score", fmt(latest.get("Deviation_Score"), 3))
k9.metric("Efficiency Status", str(latest.get("Efficiency_Status", "--")))
k10.metric("Trend", str(latest.get("Trend_Status", "--")))

# -------------------- RECOMMENDATION + INTERPRETATION --------------------
left_box, right_box = st.columns([1.3, 1])

with left_box:
    st.subheader("Recommendation")
    st.info(recommendation)

with right_box:
    st.subheader("Current Interpretation")
    st.write(f"**Cause:** {latest.get('Inefficiency_Cause', '--')}")
    st.write(f"**Persistent Warning:** {latest.get('Persistent_Warning', '--')}")
    st.write(f"**Persistent Inefficiency Count:** {latest.get('Persistent_Inefficiency_Count', '--')}")
    st.write(f"**Persistent Anomaly Count:** {latest.get('Persistent_Anomaly_Count', '--')}")

# -------------------- BASELINE PANEL --------------------
st.subheader("Learned Site Baseline")

if baseline:
    b1, b2, b3, b4, b5 = st.columns(5)
    b1.metric("Baseline Temp Mean", fmt(baseline.get("temperature_mean"), 2))
    b2.metric("Baseline Humidity Mean", fmt(baseline.get("humidity_mean"), 2))
    b3.metric("Baseline Power Mean", fmt(baseline.get("power_mean"), 2))
    b4.metric("Baseline Cooling Mean", fmt(baseline.get("cooling_mean"), 3))
    b5.metric("Baseline SEI Mean", fmt(baseline.get("sei_mean"), 3))
    st.caption(f"Calibrated at: {baseline.get('calibrated_at', '--')}")
else:
    st.warning("Baseline has not been learned yet. Calibration may still be running.")

# -------------------- SUMMARY METRICS --------------------
st.subheader("Session Summary")

summary1, summary2, summary3, summary4, summary5 = st.columns(5)

total_rows = len(df)

anomaly_count = 0
if "Anomaly_Flag" in df.columns:
    anomaly_count = (df["Anomaly_Flag"].astype(str) == "Yes").sum()

avg_power = df["ApparentPower_VA"].dropna().mean() if "ApparentPower_VA" in df.columns else None
avg_temp = df["Temperature_C"].dropna().mean() if "Temperature_C" in df.columns else None
avg_sei = df["Smart_Efficiency_Index"].dropna().mean() if "Smart_Efficiency_Index" in df.columns else None
max_dev = df["Deviation_Score"].dropna().max() if "Deviation_Score" in df.columns else None

summary1.metric("Rows Logged", total_rows)
summary2.metric("Total AI Anomalies", int(anomaly_count))
summary3.metric("Average Power", fmt(avg_power, 2))
summary4.metric("Average SEI", fmt(avg_sei, 3))
summary5.metric("Max Deviation Score", fmt(max_dev, 3))

# -------------------- CHARTS --------------------
st.subheader("Live Charts")

c1, c2 = st.columns(2)

with c1:
    if "Temperature_C" in df.columns:
        st.write("Temperature vs Time")
        temp_df = df[["Timestamp", "Temperature_C"]].dropna()
        if not temp_df.empty:
            st.line_chart(temp_df.set_index("Timestamp"))

with c2:
    if "ApparentPower_VA" in df.columns:
        st.write("Apparent Power vs Time")
        power_df = df[["Timestamp", "ApparentPower_VA"]].dropna()
        if not power_df.empty:
            st.line_chart(power_df.set_index("Timestamp"))

c3, c4 = st.columns(2)

with c3:
    if "Smart_Efficiency_Index" in df.columns:
        st.write("SEI vs Time")
        sei_df = df[["Timestamp", "Smart_Efficiency_Index"]].dropna()
        if not sei_df.empty:
            st.line_chart(sei_df.set_index("Timestamp"))

with c4:
    if "Deviation_Score" in df.columns:
        st.write("Deviation Score vs Time")
        dev_df = df[["Timestamp", "Deviation_Score"]].dropna()
        if not dev_df.empty:
            st.line_chart(dev_df.set_index("Timestamp"))

# -------------------- EXTRA CHARTS --------------------
st.subheader("Additional Performance Charts")

c5, c6 = st.columns(2)

with c5:
    if "Cooling_Rate_C_per_min" in df.columns:
        st.write("Cooling Rate vs Time")
        cool_df = df[["Timestamp", "Cooling_Rate_C_per_min"]].dropna()
        if not cool_df.empty:
            st.line_chart(cool_df.set_index("Timestamp"))

with c6:
    if "Effective_Cooling_Rate_C_per_min" in df.columns:
        st.write("Effective Cooling Rate vs Time")
        eff_df = df[["Timestamp", "Effective_Cooling_Rate_C_per_min"]].dropna()
        if not eff_df.empty:
            st.line_chart(eff_df.set_index("Timestamp"))

# -------------------- LATEST LOG TABLE --------------------
st.subheader("Latest Logged Data")

show_cols = [
    "Timestamp",
    "Mode",
    "Temperature_C",
    "Humidity_%",
    "ApparentPower_VA",
    "Cooling_Rate_C_per_min",
    "Smart_Efficiency_Index",
    "Deviation_Score",
    "Adaptive_AI_Status",
    "Anomaly_Flag",
    "Efficiency_Status",
    "Recommendation",
]

existing_show_cols = [c for c in show_cols if c in df.columns]

with st.expander("Show latest 20 rows"):
    st.dataframe(df[existing_show_cols].tail(20), use_container_width=True)

# -------------------- FOOTER --------------------
st.caption(
    "Approach 4: Site-adaptive AI with local baseline learning, deviation scoring, "
    "HVAC efficiency interpretation, and live dashboard visualization."
)