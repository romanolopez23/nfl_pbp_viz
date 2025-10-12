import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
from PIL import Image
from io import BytesIO

# -----------------------------
# APP CONFIG
# -----------------------------
st.set_page_config(page_title="NFL Play Visualizer", page_icon="🏈", layout="wide")

# Optional: Add small logo at top
logo_path = "nfl_logo.png"
st.sidebar.image(logo_path, width=80)
st.sidebar.title("NFL Play Visualizer")

# -----------------------------
# TEAM LOGOS & COLORS
# -----------------------------
TEAM_INFO = {
    "ARI": {"color": "#97233F", "logo": "ari"},
    "ATL": {"color": "#A71930", "logo": "atl"},
    "BAL": {"color": "#241773", "logo": "bal"},
    "BUF": {"color": "#00338D", "logo": "buf"},
    "CAR": {"color": "#0085CA", "logo": "car"},
    "CHI": {"color": "#0B162A", "logo": "chi"},
    "CIN": {"color": "#FB4F14", "logo": "cin"},
    "CLE": {"color": "#311D00", "logo": "cle"},
    "DAL": {"color": "#003594", "logo": "dal"},
    "DEN": {"color": "#FB4F14", "logo": "den"},
    "DET": {"color": "#0076B6", "logo": "det"},
    "GB": {"color": "#203731", "logo": "gb"},
    "HOU": {"color": "#03202F", "logo": "hou"},
    "IND": {"color": "#002C5F", "logo": "ind"},
    "JAX": {"color": "#006778", "logo": "jax"},
    "KC": {"color": "#E31837", "logo": "kc"},
    "LV": {"color": "#000000", "logo": "lv"},
    "LAC": {"color": "#0080C6", "logo": "lac"},
    "LAR": {"color": "#003594", "logo": "lar"},
    "MIA": {"color": "#008E97", "logo": "mia"},
    "MIN": {"color": "#4F2683", "logo": "min"},
    "NE": {"color": "#002244", "logo": "ne"},
    "NO": {"color": "#D3BC8D", "logo": "no"},
    "NYG": {"color": "#0B2265", "logo": "nyg"},
    "NYJ": {"color": "#125740", "logo": "nyj"},
    "PHI": {"color": "#004C54", "logo": "phi"},
    "PIT": {"color": "#FFB612", "logo": "pit"},
    "SEA": {"color": "#69BE28", "logo": "sea"},
    "SF": {"color": "#AA0000", "logo": "sf"},
    "TB": {"color": "#D50A0A", "logo": "tb"},
    "TEN": {"color": "#4B92DB", "logo": "ten"},
    "WAS": {"color": "#773141", "logo": "wsh"}
}

# -----------------------------
# LOAD SAMPLE DATA (replace with your real dataframe)
# -----------------------------
# Example structure for testing
data = {
    "season": [2024, 2024, 2025, 2025],
    "posteam": ["KC", "BUF", "SF", "DAL"],
    "yardline_100": [80, 50, 25, 40],
    "yards_gained": [20, 15, 40, 5],
    "play_type": ["pass", "rush", "pass", "rush"]
}
df = pd.DataFrame(data)

# -----------------------------
# SIDEBAR FILTERS
# -----------------------------
season = sorted(df["season"].drop_duplicates())
season_choice = st.sidebar.selectbox("Choose Season:", options=season)

filtered_df = df[df["season"] == season_choice]

team_choice = st.sidebar.selectbox("Choose Team:", sorted(filtered_df["posteam"].unique()))

# -----------------------------
# SHOW TEAM LOGO + COLOR
# -----------------------------
if team_choice in TEAM_INFO:
    team_data = TEAM_INFO[team_choice]
    color = team_data["color"]
    logo_slug = team_data["logo"]

    # ESPN logo URL (transparent background)
    logo_url = f"https://a.espncdn.com/i/teamlogos/nfl/500/{logo_slug}.png"

    try:
        response = requests.get(logo_url)
        logo_img = Image.open(BytesIO(response.content))
        st.sidebar.image(logo_img, width=100)
    except:
        st.sidebar.write("🏈 Logo unavailable")

    # Colored banner
    st.sidebar.markdown(
        f"<div style='background-color:{color};padding:8px;border-radius:8px;text-align:center;'>"
        f"<h4 style='color:white;margin:0;'>{team_choice}</h4></div>",
        unsafe_allow_html=True
    )

# -----------------------------
# FIELD / VISUALIZATION
# -----------------------------
st.markdown(f"### {team_choice} Plays in {season_choice} Season")

team_df = filtered_df[filtered_df["posteam"] == team_choice]
team_color = TEAM_INFO.get(team_choice, {}).get("color", "blue")

fig, ax = plt.subplots(figsize=(8, 4))
ax.set_facecolor("#2E8B57")  # field green
ax.scatter(team_df["yardline_100"], team_df["yards_gained"], color=team_color, s=200)

ax.set_xlim(0, 100)
ax.set_ylim(0, 50)
ax.set_xlabel("Yardline (100 = Opponent Goal Line)")
ax.set_ylabel("Yards Gained")
ax.set_title(f"{team_choice} Play Locations", color=team_color)
st.pyplot(fig)

# -----------------------------
# FOOTER
# -----------------------------
st.markdown("---")
st.caption("Data source: nfl_data_py • Visualization: Streamlit + Matplotlib 🏈")
