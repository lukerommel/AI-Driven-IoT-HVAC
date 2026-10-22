import streamlit as st
import pandas as pd
from pathlib import Path
from streamlit_autorefresh import st_autorefresh

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="HVAC Adaptive AI Live Dashboard",
    layout="wide"
)

# =========================================================
# AUTO REFRESH
# =========================================================
st_autorefresh(interval=2000, key="hvac_refresh")

# =========================================================
# FILE PATHS
# =========================================================
PROJECT_DIR = Path("/home/team8/Desktop/Project/Approach_4_Adaptive_AI")
INPUT_DATA_DIR = PROJECT_DIR / "input_data"

CSV_PATH = INPUT_DATA_DIR / "live_hvac_data.csv"
EXCEL_PATH = INPUT_DATA_DIR / "live_hvac_data.xlsx"

# =========================================================
# LOAD DATA
# =========================================================
def load_data():
    try:
        if CSV_PATH.exists():
            return pd.read_csv(CSV_PATH)
        if EXCEL_PATH.exists():
            return pd.read_excel(EXCEL_PATH)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

df = load_data()

st.title("HVAC Adaptive AI Live Dashboard")

if df.empty:
    st.warning("No live data found yet. Start the logger first.")
    st.stop()

# =========================================================
# CLEAN DATA
# =========================================================
df.columns = [str(c).strip() for c in df.columns]
df = df.tail(300).copy()

numeric_cols = [
    "Temperature_C",
    "Humidity_%",
    "A0_Voltage_V",
    "Vrms_ADC",
    "Mains_Vrms_Est",
    "A1_Current_V",
    "Irms_A",
    "ApparentPower_VA",
    "Cooling_Rate_C_per_min",
    "Effective_Cooling_Rate_C_per_min",
    "Smart_Efficiency_Index",
    "CoolingRate_MA_5",
    "Power_MA_5",
    "SEI_MA_5",
    "Baseline_Temp_Mean",
    "Baseline_Humidity_Mean",
    "Baseline_Power_Mean",
    "Baseline_Cooling_Mean",
    "Baseline_SEI_Mean",
]

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

if "Timestamp" in df.columns:
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")

# =========================================================
# HELPERS
# =========================================================
def current_value(col_name):
    if col_name in df.columns and not df.empty:
        return df.iloc[-1][col_name]
    return None

def current_text(col_name):
    if col_name in df.columns and not df.empty:
        val = df.iloc[-1][col_name]
        if pd.isna(val):
            return None
        return str(val)
    return None

def display_value(val, fmt="{:.2f}"):
    if pd.isna(val):
        return "—"
    try:
        return fmt.format(val)
    except Exception:
        return str(val)

# =========================================================
# CURRENT ROW VALUES
# =========================================================
mode_val = current_text("Mode")
temp_val = current_value("Temperature_C")
hum_val = current_value("Humidity_%")
vrms_val = current_value("Mains_Vrms_Est")
irms_val = current_value("Irms_A")
power_val = current_value("ApparentPower_VA")
cool_val = current_value("Cooling_Rate_C_per_min")
eff_cool_val = current_value("Effective_Cooling_Rate_C_per_min")
sei_val = current_value("Smart_Efficiency_Index")
sei_ma_val = current_value("SEI_MA_5")

status_val = current_text("Efficiency_Status")
cause_val = current_text("Inefficiency_Cause")
trend_val = current_text("Trend_Status")
persistent_warning_val = current_text("Persistent_Warning")
recommendation_val = current_text("Recommendation")
risk_val = current_text("Predicted_Risk")

# =========================================================
# FRESHNESS
# =========================================================
last_time = current_value("Timestamp") if "Timestamp" in df.columns else None

if last_time is not None and not pd.isna(last_time):
    now = pd.Timestamp.now()
    age_sec = (now - last_time).total_seconds()

    if age_sec <= 6:
        st.success(f"Live feed active • last update {int(age_sec)} sec ago")
    elif age_sec <= 15:
        st.warning(f"Live feed slightly delayed • last update {int(age_sec)} sec ago")
    else:
        st.error(f"No recent sensor update • last update {int(age_sec)} sec ago")

    st.caption(f"Last updated: {last_time}")
else:
    st.warning("Timestamp not available.")

# =========================================================
# LIVE INTERPRETATION MESSAGE
# =========================================================
if mode_val == "CALIBRATION":
    st.info("Calibration in progress: learning a site-specific baseline.")
elif pd.isna(power_val):
    st.error("Current row has incomplete power/voltage data.")
elif pd.isna(sei_val) and not pd.isna(power_val):
    st.warning("Power is available, but SEI is not yet valid. Cooling trend window is still stabilizing.")
elif sei_val == 0:
    st.info("SEI is currently zero because the measured cooling trend over the active window is very small.")
elif status_val == "Idle/Very Low Load":
    st.info("System is under very low load or idle condition.")
elif status_val == "Efficient":
    st.success("System is operating efficiently.")
elif status_val == "Moderate":
    st.warning("System is operating with moderate efficiency.")
elif status_val == "Inefficient":
    st.error("System is showing inefficient behavior.")

# =========================================================
# TOP METRICS
# =========================================================
r1 = st.columns(4)
r2 = st.columns(4)
r3 = st.columns(3)

with r1[0]:
    st.metric("Mode", mode_val if mode_val is not None else "—")
with r1[1]:
    st.metric("Temperature (°C)", display_value(temp_val, "{:.2f}"))
with r1[2]:
    st.metric("Humidity (%)", display_value(hum_val, "{:.2f}"))
with r1[3]:
    st.metric("Power (VA)", display_value(power_val, "{:.2f}"))

with r2[0]:
    st.metric("Voltage (V)", display_value(vrms_val, "{:.2f}"))
with r2[1]:
    st.metric("Current (A)", display_value(irms_val, "{:.3f}"))
with r2[2]:
    st.metric("Cooling Rate", display_value(cool_val, "{:.3f}"))
with r2[3]:
    st.metric("Effective Cooling", display_value(eff_cool_val, "{:.3f}"))

with r3[0]:
    st.metric("SEI", display_value(sei_val, "{:.3f}"))
with r3[1]:
    st.metric("SEI (MA-5)", display_value(sei_ma_val, "{:.3f}"))
with r3[2]:
    st.metric("Status", status_val if status_val is not None else "—")

# =========================================================
# STATUS DETAILS
# =========================================================
if cause_val is not None:
    st.write(f"**Cause:** {cause_val}")

if trend_val is not None:
    st.write(f"**Trend:** {trend_val}")

if persistent_warning_val is not None:
    st.write(f"**Persistent Warning:** {persistent_warning_val}")

if risk_val is not None:
    st.write(f"**Predicted Risk:** {risk_val}")

if recommendation_val is not None:
    st.success(f"Recommendation: {recommendation_val}")

# =========================================================
# CHARTS
# =========================================================
st.subheader("Live Trends")

if "Timestamp" in df.columns:
    chart_df = df.dropna(subset=["Timestamp"]).copy()
    chart_df = chart_df.set_index("Timestamp")

    if "Temperature_C" in chart_df.columns:
        st.markdown("**Temperature Trend**")
        st.line_chart(chart_df[["Temperature_C"]], height=220)

    if "Humidity_%" in chart_df.columns:
        st.markdown("**Humidity Trend**")
        st.line_chart(chart_df[["Humidity_%"]], height=220)

    if "ApparentPower_VA" in chart_df.columns:
        st.markdown("**Power Trend**")
        st.line_chart(chart_df[["ApparentPower_VA"]], height=220)

    if "Cooling_Rate_C_per_min" in chart_df.columns:
        temp_chart = chart_df.copy()
        temp_chart.loc[temp_chart["Cooling_Rate_C_per_min"].abs() > 5, "Cooling_Rate_C_per_min"] = pd.NA
        st.markdown("**Cooling Rate Trend**")
        st.line_chart(temp_chart[["Cooling_Rate_C_per_min"]], height=220)

    sei_cols = [c for c in ["Smart_Efficiency_Index", "SEI_MA_5"] if c in chart_df.columns]
    if sei_cols:
        st.markdown("**SEI Trend**")
        st.line_chart(chart_df[sei_cols], height=220)
else:
    st.warning("No timestamp column found, so time-based charts cannot be plotted.")

# =========================================================
# DATA QUALITY
# =========================================================
st.subheader("Data Quality Check")

dq1, dq2, dq3 = st.columns(3)

with dq1:
    temp_missing = df["Temperature_C"].isna().sum() if "Temperature_C" in df.columns else "N/A"
    hum_missing = df["Humidity_%"].isna().sum() if "Humidity_%" in df.columns else "N/A"
    st.write(f"Missing Temperature rows: {temp_missing}")
    st.write(f"Missing Humidity rows: {hum_missing}")

with dq2:
    sei_missing = df["Smart_Efficiency_Index"].isna().sum() if "Smart_Efficiency_Index" in df.columns else "N/A"
    cool_missing = df["Cooling_Rate_C_per_min"].isna().sum() if "Cooling_Rate_C_per_min" in df.columns else "N/A"
    st.write(f"Missing SEI rows: {sei_missing}")
    st.write(f"Missing Cooling rows: {cool_missing}")

with dq3:
    if "ApparentPower_VA" in df.columns:
        low_load_rows = (df["ApparentPower_VA"] < 20).sum()
        st.write(f"Low-load rows (<20 VA): {low_load_rows}")
    else:
        st.write("Low-load rows (<20 VA): N/A")

# =========================================================
# LATEST RECORDS
# =========================================================
st.subheader("Latest Records")
st.dataframe(df.tail(20), use_container_width=True)