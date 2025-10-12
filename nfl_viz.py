import streamlit as st
import pandas as pd
import os
import urllib.request
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
import matplotlib.patches as patches
import numpy as np
import textwrap
import nfl_data_py as nfl
import requests
from PIL import Image
from io import BytesIO

# -----------------------------
# APP HEADER
# -----------------------------
logo_path = "nfl_logo.png"
st.sidebar.image(logo_path, width=80)

# -----------------------------
# TEAM COLORS AND LOGOS
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
# LOAD DATA
# -----------------------------
pbp = nfl.import_pbp_data([2024, 2025], downcast=True, cache=False, alt_path=None)
df = pd.DataFrame(pbp)

df['yardline_100'] = 120 - df['yardline_100'] - 10
df['xreception'] = df['yardline_100'] + df['air_yards']
df['xend'] = df['yardline_100'] + df['air_yards'] + df['yards_after_catch']
df['xend_rush'] = df['yardline_100'] + df['rushing_yards']

df.loc[
    (df['play_type'] == 'pass') &
    (df['touchdown'] == 1.0) &
    (df['interception'] == 1),
    'play_type'
] = 'pass intercepted'

df = df[((df['play_type'] == 'run') | (df['play_type'] == 'pass') | (df['play_type'] == 'pass intercepted')) & (df['touchdown'] == 1.0)]

# -----------------------------
# STREAMLIT FILTERS
# -----------------------------
season = sorted(df['season'].drop_duplicates(), reverse=True)
season_choice = st.sidebar.selectbox('Choose Season:', options=season)
df = df[df['season'] == season_choice]

play_type = sorted(df['play_type'].drop_duplicates())
play_type_choice = st.sidebar.selectbox('Choose Play Type:', options=play_type)
df = df[df['play_type'] == play_type_choice]

team = sorted(df['posteam'].drop_duplicates())
team_choice = st.sidebar.selectbox('Choose Team:', options=team)
df = df[df['posteam'] == team_choice]

# -----------------------------
# SHOW TEAM LOGO & COLOR
# -----------------------------
if team_choice in TEAM_INFO:
    color = TEAM_INFO[team_choice]['color']
    logo_code = TEAM_INFO[team_choice]['logo']
    logo_url = f"https://a.espncdn.com/i/teamlogos/nfl/500/{logo_code}.png"

    try:
        response = requests.get(logo_url)
        logo_img = Image.open(BytesIO(response.content))
        st.sidebar.image(logo_img, width=100)
    except:
        st.sidebar.write("🏈 Logo unavailable")

    st.sidebar.markdown(
        f"<div style='background-color:{color};padding:8px;border-radius:6px;text-align:center;'>"
        f"<h4 style='color:white;margin:0;'>{team_choice}</h4></div>",
        unsafe_allow_html=True
    )

# -----------------------------
# PLAYER FILTERS
# -----------------------------
if play_type_choice == 'run':
    rusher = df['rusher_player_name'].drop_duplicates()
    rusher_choice = st.sidebar.selectbox('Choose Rusher:', options=rusher)
    df = df[df['rusher_player_name'] == rusher_choice]
    currentplayer = rusher_choice
elif play_type_choice in ['pass', 'pass intercepted']:
    passer = df['passer'].drop_duplicates()
    passer_choice = st.sidebar.selectbox('Choose Passer:', options=passer)
    df = df[df['passer'] == passer_choice]
    currentplayer = passer_choice

Game_ID = df['game_id'].drop_duplicates()
Game_ID_choice = st.sidebar.selectbox('Choose Game ID:', options=Game_ID)
df = df[df['game_id'] == Game_ID_choice]

play_id = df['play_id'].drop_duplicates()
play_id_choice = st.sidebar.selectbox('Choose Play_id:', options=play_id)
df = df[df['play_id'] == play_id_choice]

df = df[['game_id', 'play_id', 'play_type', 'home_team', 'away_team', 'game_date',
         'receiver', 'rusher', 'passer', 'ydstogo', 'down', 'posteam', 'yardline_100',
         'xreception', 'xend', 'desc', 'yards_gained', 'air_yards', 'yards_after_catch',
         'xend_rush', 'interception', 'return_yards', 'interception_player_name']]

home_team = df['home_team'].iloc[0]
away_team = df['away_team'].iloc[0]
game_date = df['game_date'].iloc[0]
desc = df['desc'].iloc[0]
receiver = df['receiver'].iloc[0]
ydstogo = df['ydstogo'].iloc[0]
down = df['down'].iloc[0]
xend = df['xend'].iloc[0]
xreception = df['xreception'].iloc[0]
yards_after_catch = df['yards_after_catch'].iloc[0]
interception = df['interception'].iloc[0]
return_yards = df['return_yards'].iloc[0]
interception_player_name = df['interception_player_name'].iloc[0]

# -----------------------------
# FIELD DRAW FUNCTION
# -----------------------------
def create_football_field(linenumbers=True, endzones=True, highlight_line_number=85,
                          highlight_line=False, highlight_first_down_line=False,
                          yards_to_go=10, figsize=(12, 6.33)):

    rect = patches.Rectangle((0, 0), 120, 53.3, linewidth=0.1,
                             edgecolor='r', facecolor='darkgreen', zorder=0)
    fig, ax = plt.subplots(1, figsize=figsize)
    ax.add_patch(rect)

    plt.plot([10, 10, 110, 110, 10], [0, 53.3, 53.3, 0, 0], color='white')

    if endzones:
        team_color = TEAM_INFO.get(team_choice, {}).get("color", "blue")
        ez1 = patches.Rectangle((0, 0), 10, 53.3, facecolor=team_color, alpha=0.2, zorder=0)
        ez2 = patches.Rectangle((110, 0), 10, 53.3, facecolor=team_color, alpha=0.2, zorder=0)
        ax.add_patch(ez1)
        ax.add_patch(ez2)

    plt.xlim(0, 120)
    plt.ylim(-5, 58.3)
    plt.axis('off')
    return fig, ax

# -----------------------------
# VISUALIZATION
# -----------------------------
fig, ax = create_football_field(highlight_line=True,
                                highlight_line_number=df['yardline_100'].iloc[0],
                                highlight_first_down_line=True,
                                yards_to_go=df['ydstogo'].iloc[0])

team_color = TEAM_INFO.get(team_choice, {}).get("color", "orange")

plt.scatter(df['yardline_100'], np.full(len(df), 26.65), color=team_color, s=400)

if play_type_choice == 'pass':
    plt.scatter(df['xreception'], np.full(len(df), 26.65), label="xreception", marker='x', s=400, color=team_color)
elif play_type_choice == 'pass intercepted':
    plt.scatter(df['xreception'], np.full(len(df), 26.65), label="xreception", marker='x', s=400, color='purple')

# Arrows
for i in range(len(df)):
    if play_type_choice == 'run':
        plt.arrow(df['yardline_100'].iloc[i], 26.65,
                  df['xend_rush'].iloc[i] - df['yardline_100'].iloc[i], 0,
                  head_width=2, head_length=3, width=1, fc='orange', ec='orange')
    elif play_type_choice == 'pass' and df['yards_after_catch'].iloc[i] > 0:
        plt.arrow(df['xreception'].iloc[i], 26.65,
                  df['xend'].iloc[i] - df['xreception'].iloc[i], 0,
                  head_width=2, head_length=3, width=0.7, fc='orange', ec='orange')
    elif play_type_choice == 'pass intercepted' and df['interception'].iloc[i] == 1.0:
        plt.arrow(df['xreception'].iloc[i], 26.65,
                  -df['return_yards'].iloc[i], 0,
                  head_width=2, head_length=3, width=0.7, fc='purple', ec='purple')

# Title
wrapped_desc = textwrap.fill(desc, width=40)
if play_type_choice == 'run':
    currenttitle = f"{away_team} at {home_team} on {game_date}\nRusher: {currentplayer}\nDown: {down} - Yards to Go: {ydstogo}\n\n{wrapped_desc}"
elif play_type_choice == 'pass intercepted' and interception == 1.0:
    currenttitle = f"{away_team} at {home_team} on {game_date}\n{currentplayer} Intercepted by {interception_player_name}\nDown: {down} - Yards to Go: {ydstogo}\n\n{wrapped_desc}"
else:
    currenttitle = f"{away_team} at {home_team} on {game_date}\n{currentplayer} to {receiver}\nDown: {down} - Yards to Go: {ydstogo}\n\n{wrapped_desc}"

plt.title(currenttitle, fontsize=24)
st.pyplot(fig, use_container_width=True)
