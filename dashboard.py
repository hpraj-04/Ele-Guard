import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import os
from streamlit_autorefresh import st_autorefresh

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="EleGuard AI", layout="wide")

# ---------------- CSS STYLE ----------------
st.markdown("""
<style>

#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
header {visibility:hidden;}

.stApp{
background: linear-gradient(135deg,#1e1e24,#2b2b35);
color:#f8fafc;
}

/* Title */
h1{
color:#ffffff;
font-size:42px;
font-weight:700;
}

/* Subheaders */
h2,h3{
color:#ffffff;
}

/* Metric cards */
[data-testid="metric-container"]{
background: rgba(255,255,255,0.08);
border-radius:18px;
padding:20px;
box-shadow:0 10px 25px rgba(0,0,0,0.4);
}

/* Snapshot card */
.snapshot-card{
background:rgba(255,255,255,0.05);
padding:15px;
border-radius:15px;
margin-bottom:20px;
box-shadow:0 8px 20px rgba(0,0,0,0.4);
}

.location-text{
color:#facc15;
font-weight:600;
}

/* Force bright text */
body, p, span, label, div {
    color: #ffffff !important;
}

/* Table styling */
[data-testid="stDataFrame"] {
    background: rgba(255,255,255,0.05);
    border-radius: 12px;
}

a {
    color: #facc15 !important;
    font-weight: 600;
}

</style>
""", unsafe_allow_html=True)

# ---------------- TITLE ----------------
st.title("🐘 EleGuard AI Monitoring Dashboard")

# ---------------- AUTO REFRESH ----------------
st_autorefresh(interval=5000)

# ---------------- CAMERA LOCATION ----------------
latitude = 10.9375
longitude = 76.9558
google_maps_link = f"https://www.google.com/maps?q={latitude},{longitude}"

# ---------------- DATABASE ----------------
conn = sqlite3.connect("elephant.db")
df = pd.read_sql("SELECT * FROM detections ORDER BY id DESC", conn)

# ---------------- DASHBOARD ----------------
if len(df) > 0:

    # ---------- METRICS ----------
    col1, col2, col3 = st.columns(3)

    col1.metric("Total Detections", len(df))

    aggressive = len(df[df["mood"] == "Aggressive"])
    col2.metric("Aggressive Encounters", aggressive)

    col3.metric("Last Mood", df.iloc[0]["mood"])

    st.markdown("---")

    # ---------- PIE CHART ----------
    st.subheader("Elephant Mood Distribution")

    fig = px.pie(
        df,
        names="mood",
        hole=0.6,
        color="mood",
        color_discrete_sequence=["#6ee7b7","#c084fc","#f87171"]
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white")
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ---------- DETECTION RECORDS ----------
    st.subheader("📋 Detection Records")

    display_df = df[["timestamp", "mood"]].copy()
    display_df.index = range(1, len(display_df) + 1)

    st.dataframe(display_df, use_container_width=True, height=300)

    st.markdown("---")

    # ---------- LOCATION ----------
    st.subheader("📍 Latest Elephant Location")

    map_df = pd.DataFrame({
        "lat":[latitude],
        "lon":[longitude]
    })

    st.map(map_df)

    st.markdown(
        f'<p class="location-text">📍 <a href="{google_maps_link}" target="_blank">Open Location in Google Maps</a></p>',
        unsafe_allow_html=True
    )

    st.markdown("---")

    # ---------- SNAPSHOTS ----------
    st.subheader("📷 Elephant Snapshots")

    cols = st.columns(3)

    for i, row in df.iterrows():

        image_path = row["image_path"]

        if os.path.exists(image_path):

            with cols[i % 3]:

                st.markdown('<div class="snapshot-card">', unsafe_allow_html=True)

                st.image(
                    image_path,
                    caption=f"{row['timestamp']} | {row['mood']}",
                    width="stretch"
                )

                st.markdown(
                    f'<p class="location-text">📍 <a href="{google_maps_link}" target="_blank">View Location</a></p>',
                    unsafe_allow_html=True
                )

                st.markdown('</div>', unsafe_allow_html=True)

else:
    st.warning("No elephant detected yet")
