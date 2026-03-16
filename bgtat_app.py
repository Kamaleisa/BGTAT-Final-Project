# Bespoke Gas Turbine Analysis Tool (BGTAT)
# M.Sc Capstone Project-Kamaleldin Eisa -March 2026

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import logging

# Hide the "No runtime found" warning for a cleaner notebook experience
logging.getLogger("streamlit.runtime.caching.cache_data_api").setLevel(logging.ERROR)

# ==========================================
# 1. FRAME CONFIGURATIONS 
# ==========================================

FRAME_CONFIGS = {
    "Frame 5": {
        "Base_MW": 33.0, 
        "TC_Count": 18, 
        "Swirl_Coeff": 0.02, 
        "Min_Swirl": 10
    },
    "Frame 6B": {
        "Base_MW": 45.0, 
        "TC_Count": 24, 
        "Swirl_Coeff": 0.025, 
        "Min_Swirl": 12
    },
    "Frame 7E": {
        "Base_MW": 85.0, 
        "TC_Count": 24, 
        "Swirl_Coeff": 0.028, 
        "Min_Swirl": 14
    },
    "Frame 9E": {
        "Base_MW": 132.0,  # Correctly matched to your 127.8MW data
        "TC_Count": 31, 
        "Swirl_Coeff": 0.03, 
        "Min_Swirl": 15
    }
}
# ==========================================
# 2. AUTO-DETECTION LOGIC
# ==========================================
def auto_detect_frame(df):
    """
    Automatically selects the frame based on the maximum power in the data.
    """
    # Using strip() just in case there are hidden spaces in your CSV headers
    max_p = df['Power Output (MW)'].max()
    
    if max_p > 100:
        return "Frame 9E"
    elif max_p > 60:
        return "Frame 7E"
    elif max_p > 35:
        return "Frame 6B"
    else:
        return "Frame 5"

# ==========================================
# 3. CORE PHYSICS & DIAGNOSTIC FUNCTIONS
# ==========================================

def calculate_swirl_angle(load_pct, config):
    """Exponential decay model for GE Exhaust Swirl."""
    base_swirl = 45.0
    min_swirl = config['Min_Swirl']
    k = config['Swirl_Coeff']
    return (base_swirl - min_swirl) * np.exp(-k * load_pct) + min_swirl

def simulate_thermocouples(avg_temp, fault_type, tc_count):
    """Synthesizes individual TC readings."""
    base_readings = np.random.normal(avg_temp, 1.5, tc_count)
    if fault_type == 1:
        fault_idx = np.random.randint(0, tc_count)
        base_readings[fault_idx] -= np.random.uniform(40, 75)
    return base_readings

def calculate_spreads(tc_readings):
    """Calculates GE-standard Spread 1, 2, and 3."""
    sorted_tc = np.sort(tc_readings)
    sp1 = sorted_tc[-1] - sorted_tc[0]
    sp2 = sorted_tc[-1] - sorted_tc[1]
    sp3 = sorted_tc[-1] - ((sorted_tc[0] + sorted_tc[1]) / 2)
    return sp1, sp2, sp3

def auto_detect_frame(df):
    """Heuristic identification of the turbine frame."""
    max_p = df['Power Output (MW)'].max()
    if max_p > 100: return "Frame 9E"
    elif max_p > 60: return "Frame 7E"
    elif max_p > 35: return "Frame 6B"
    else: return "Frame 5"

# ==========================================
# 4. DATA & INTERFACE
# ==========================================
st.set_page_config(page_title="BGTAT Frame Investigator", layout="wide")
st.title("🛠️ Bespoke Gas Turbine Analysis Tool (BGTAT)")

# Loading your dataset

@st.cache_data
def load_and_init_data():
    # Fixed the double C:\ and added the closing quote
    path = r'C:\Users\Acer\OneDrive\Documents\gas_turbine_fault_detection.csv' 
    
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        # Check if the file name has that extra space we saw earlier
        df = pd.read_csv(path.replace('.csv', ' .csv'))
        
    df.columns = df.columns.str.strip()
    return df
df = load_and_init_data()

# --- Auto Detection Layer ---
detected_name = auto_detect_frame(df)

st.sidebar.header("Investigation Parameters")
selected_frame = st.sidebar.selectbox(
    "Select Turbine Frame", 
    list(FRAME_CONFIGS.keys()), 
    index=list(FRAME_CONFIGS.keys()).index(detected_name)
)
config = FRAME_CONFIGS[selected_frame]

record_idx = st.sidebar.slider("Select Operational Cycle", 0, len(df)-1, 100)
row = df.iloc[record_idx]

# --- Core Calculations ---
load_pct = min(100.0, (row['Power Output (MW)'] / config['Base_MW']) * 100)
swirl_angle = calculate_swirl_angle(load_pct, config)
tc_readings = simulate_thermocouples(row['Exhaust Gas Temperature (°C)'], row['Fault'], config['TC_Count'])
sp1, sp2, sp3 = calculate_spreads(tc_readings)

# ==========================================
# 5. DASHBOARD & ALERTS
# ==========================================
LIMIT = 45.0
col1, col2, col3, col4 = st.columns(4)

col1.metric("Load Status", f"{load_pct:.1f}%")
col2.metric("Swirl Angle", f"{swirl_angle:.1f}°")

def get_alert(val):
    return (f"⚠️ +{val-LIMIT:.1f} HIGH", "inverse") if val > LIMIT else ("✅ Nominal", "normal")

msg1, clr1 = get_alert(sp1)
col3.metric("Spread 1", f"{sp1:.1f} °C", delta=msg1, delta_color=clr1)

msg2, clr2 = get_alert(sp2)
col4.metric("Spread 2", f"{sp2:.1f} °C", delta=msg2, delta_color=clr2)

st.markdown("---")

# --- Visuals ---
v_left, v_right = st.columns(2)
with v_left:
    st.subheader("Exhaust Thermal Profile (Swirl-Adjusted)")
    thetas = np.linspace(0, 360, config['TC_Count'], endpoint=False)
    # Rotating the plot by the swirl angle to show 'Physical Burner Origin'
    thetas_swirled = (thetas + swirl_angle) % 360 
    fig_polar = go.Figure(go.Scatterpolar(
        r=tc_readings, theta=thetas_swirled, fill='toself', marker=dict(color='orange')
    ))
    st.plotly_chart(fig_polar, use_container_width=True)

with v_right:
    st.subheader("Design Swirl Curve (Exponential Decay)")
    l_range = np.linspace(0, 110, 50)
    s_curve = [calculate_swirl_angle(l, config) for l in l_range]
    fig_curve = px.line(x=l_range, y=s_curve, labels={'x':'Load %', 'y':'Swirl Angle'})
    fig_curve.add_scatter(x=[load_pct], y=[swirl_angle], mode='markers', marker=dict(size=12, color='red'), name='Current State')
    st.plotly_chart(fig_curve, use_container_width=True)

# --- Final Diagnostic Log ---
if sp1 > LIMIT:
    st.error(f"🚨 **Fault Detected:** Spread {sp1:.1f}°C exceeds {LIMIT}°C limit. Suspected fuel nozzle clogs.")
    st.info(f"**Maintenance Hint:** Inspect burners {swirl_angle:.0f}° counter-swirl from the thermocouple cold-spot.")
else:
    st.success(f"🟢 **Healthy:** Turbine {selected_frame} is within safe thermal gradients.")




