import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def load_input_file(file_path):
    if file_path.lower().endswith(".csv"):
        return pd.read_csv(file_path)
    elif file_path.lower().endswith(".xlsx"):
        return pd.read_excel(file_path)
    else:
        raise ValueError("Only CSV and XLSX files are supported.")
    
def preprocess_dataframe(df):
    df.columns = [col.strip() for col in df.columns]

    required_cols = ["Timestamp", "Temperature_C", "ApparentPower_VA"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df["Temperature_C"] = pd.to_numeric(df["Temperature_C"], errors="coerce")
    df["ApparentPower_VA"] = pd.to_numeric(df["ApparentPower_VA"], errors="coerce")

    if "Humidity_%" in df.columns:
        df["Humidity_%"] = pd.to_numeric(df["Humidity_%"], errors="coerce")

    df = df.sort_values("Timestamp").reset_index(drop=True)
    return df
def calculate_cooling_rate(df):
    time_diff_min = df["Timestamp"].diff().dt.total_seconds() / 60.0
    temp_prev = df["Temperature_C"].shift(1)

    df["Cooling_Rate_C_per_min"] = (temp_prev - df["Temperature_C"]) / time_diff_min
    df["Cooling_Rate_C_per_min"] = df["Cooling_Rate_C_per_min"].replace([np.inf, -np.inf], np.nan)

    return df
def calculate_effective_cooling_rate(df):
    df["Effective_Cooling_Rate_C_per_min"] = df["Cooling_Rate_C_per_min"].clip(lower=0)
    return df
def calculate_smart_efficiency_index(df, scale_factor=1000):
    df["Smart_Efficiency_Index"] = np.where(
        df["ApparentPower_VA"] > 0,
        (df["Effective_Cooling_Rate_C_per_min"] / df["ApparentPower_VA"]) * scale_factor,
        np.nan
    )
    return df
def calculate_rolling_metrics(df):
    df["CoolingRate_MA_5"] = df["Effective_Cooling_Rate_C_per_min"].rolling(5, min_periods=1).mean()
    df["Power_MA_5"] = df["ApparentPower_VA"].rolling(5, min_periods=1).mean()
    df["SEI_MA_5"] = df["Smart_Efficiency_Index"].rolling(5, min_periods=1).mean()
    return df
def classify_efficiency(row):
    power = row["ApparentPower_VA"]
    cooling = row["Effective_Cooling_Rate_C_per_min"]
    sei = row["Smart_Efficiency_Index"]
    sei_avg = row["SEI_MA_5"]

    if pd.isna(power) or pd.isna(sei):
        return "Unknown"

    if power < 100:
        return "Idle/Very Low Load"

    if cooling == 0 and power > 500:
        return "Inefficient"

    if sei_avg > 0:
        if sei >= sei_avg * 1.05:
            return "Efficient"
        elif sei >= sei_avg * 0.85:
            return "Moderate"
        else:
            return "Inefficient"

    return "Moderate"
def diagnose_cause(row):
    power = row["ApparentPower_VA"]
    power_avg = row["Power_MA_5"]
    cooling = row["Effective_Cooling_Rate_C_per_min"]
    cooling_avg = row["CoolingRate_MA_5"]
    sei = row["Smart_Efficiency_Index"]
    sei_avg = row["SEI_MA_5"]

    if pd.isna(power) or pd.isna(sei):
        return "Insufficient data"

    if power < 100:
        return "Low-load or idle condition"

    if pd.notna(sei_avg) and sei_avg > 0 and sei >= sei_avg * 0.85:
        return "No major inefficiency detected"

    cooling_drop = pd.notna(cooling_avg) and cooling_avg > 0 and cooling < cooling_avg * 0.85
    power_rise = pd.notna(power_avg) and power_avg > 0 and power > power_avg * 1.10

    if cooling_drop and power_rise:
        return "Cooling rate dropped and apparent power increased"
    elif cooling_drop:
        return "Cooling rate dropped"
    elif power_rise:
        return "Apparent power increased"
    else:
        return "Minor fluctuation or transitional behavior"
def add_trend_status(df):
    trend = []
    for i in range(len(df)):
        if i < 2:
            trend.append("Insufficient history")
            continue

        a = df.loc[i - 2, "Smart_Efficiency_Index"]
        b = df.loc[i - 1, "Smart_Efficiency_Index"]
        c = df.loc[i, "Smart_Efficiency_Index"]

        if pd.isna(a) or pd.isna(b) or pd.isna(c):
            trend.append("Insufficient history")
        elif c > b > a:
            trend.append("Improving")
        elif c < b < a:
            trend.append("Worsening")
        else:
            trend.append("Stable/Fluctuating")

    df["Trend_Status"] = trend
    return df
def recommendation_logic(row):
    status = row["Efficiency_Status"]
    cause = row["Inefficiency_Cause"]
    trend = row["Trend_Status"]
    persistent_warning = row["Persistent_Warning"] if "Persistent_Warning" in row else "No"

    if status == "Efficient":
        return "System is operating efficiently."
    if status == "Moderate":
        return "Performance is acceptable but should be monitored."
    if status == "Idle/Very Low Load":
        return "System appears to be under very low load or idle condition."
    if persistent_warning == "Yes":
        return "Persistent inefficiency detected across multiple cycles. System performance should be inspected."
    if status == "Unknown":
        return "Insufficient data for evaluation."

    if cause == "Cooling rate dropped and apparent power increased":
        if trend == "Worsening":
            return "Combined degradation detected. Efficiency may fall further if this continues."
        return "Cooling is weaker while power draw is increasing."

    if cause == "Cooling rate dropped":
        return "Cooling effectiveness is reduced."

    if cause == "Apparent power increased":
        return "Power consumption increased without matching cooling improvement."

    if cause == "Low-load or idle condition":
        return "Low efficiency here may not indicate a fault."

    return "Monitor the system for further changes."
def predicted_risk(row):
    if row["Efficiency_Status"] == "Inefficient" and row["Trend_Status"] == "Worsening":
        return "High"
    elif row["Efficiency_Status"] == "Inefficient":
        return "Medium"
    elif row["Efficiency_Status"] == "Moderate":
        return "Low"
    else:
        return "Minimal"
def add_persistent_inefficiency(df):
    counts = []
    running_count = 0

    for status in df["Efficiency_Status"]:
        if status == "Inefficient":
            running_count += 1
        else:
            running_count = 0
        counts.append(running_count)

    df["Persistent_Inefficiency_Count"] = counts
    df["Persistent_Warning"] = np.where(
        df["Persistent_Inefficiency_Count"] >= 3,
        "Yes",
        "No"
    )
    return df    
def generate_efficiency_plot(df):
    plt.figure(figsize=(12,6))
    plt.plot(df["Timestamp"], df["Smart_Efficiency_Index"])
    plt.xlabel("Time")
    plt.ylabel("Smart Efficiency Index")
    plt.title("HVAC Efficiency Over Time")
    plt.xticks(rotation=45)
    plt.tight_layout()

    plt.savefig("output_data/efficiency_plot.png")
    plt.close()
def analyze_hvac_file(input_file, output_file):
    df = load_input_file(input_file)
    df = preprocess_dataframe(df)
    df = calculate_cooling_rate(df)
    df = calculate_effective_cooling_rate(df)
    df = calculate_smart_efficiency_index(df)
    df = calculate_rolling_metrics(df)

    df["Efficiency_Status"] = df.apply(classify_efficiency, axis=1)
    df["Inefficiency_Cause"] = df.apply(diagnose_cause, axis=1)
    df = add_trend_status(df) 
    df["Predicted_Risk"] = df.apply(predicted_risk, axis=1)
    df = add_persistent_inefficiency(df)
    df["Recommendation"] = df.apply(recommendation_logic, axis=1)

    if output_file.lower().endswith(".csv"):
        df.to_csv(output_file, index=False)
    elif output_file.lower().endswith(".xlsx"):
        df.to_excel(output_file, index=False)
    else:
        raise ValueError("Output file must be CSV or XLSX.")
    
    generate_efficiency_plot(df)
    print("Analysis complete.")
    print("Output saved to:", output_file)
if __name__ == "__main__":
    input_file = "input_data/live_hvac_data.xlsx"
    output_file = "output_data/hvac_efficiency_output.xlsx"
    analyze_hvac_file(input_file, output_file)                