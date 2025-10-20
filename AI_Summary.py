import streamlit as st
import nfl_data_py as nfl
import pandas as pd
import google.genai as genai
from google.genai import types
import re

# --- Helper to remove emojis or non-ASCII characters ---
def clean_text(text):
    return re.sub(r'[^\x00-\x7F]+', '', text)

# --- Page title ---
st.title("🏈 AI-Powered NFL Game Summary Generator (Google Gemini)")

# --- Sidebar configuration ---
with st.sidebar:
    st.header("Configuration")
    api_key = st.secrets["GEMINI_API_KEY"]
    model_name = st.selectbox(
        "Select Model:",
        ["gemini-2.5-flash", "gemini-2.5-pro"],
        index=0
    )

if not api_key:
    st.warning("Please enter your Gemini API key in the sidebar.")
    st.stop()

client = genai.Client(api_key=api_key)
season = 2025

# --- Load entire season once ---
@st.cache_data
def load_season_data(season):
    pbp = nfl.import_pbp_data([season], downcast=True, cache=False)
    return pbp

pbp_data = load_season_data(season)

# --- Sidebar: Select week ---
available_weeks = sorted(pbp_data["week"].dropna().unique())
selected_week = st.sidebar.selectbox("📅 Select Week:", available_weeks, index=0)

# Filter data for selected week
week_data = pbp_data[pbp_data["week"] == selected_week]

if week_data.empty:
    st.warning(f"No data found for Week {selected_week} in {season}.")
    st.stop()

# --- Calculate pass attempts ---
week_data["pass_attempts"] = (
    ((week_data["pass"] == 1.0) & 
     (week_data["sack"] != 1.0) & 
     (week_data["play_type"] != "run") &
     (week_data["two_point_attempt"] != 1.0) & 
     ((week_data["play_type"] != "no_play") |
      ((week_data["play_type"] == "no_play") & (week_data['penalty_team'] == week_data['posteam']))))
).astype(int)

# --- Calculate incomplete passes ---
week_data["pass_incomplete"] = (
    ((week_data["pass"] == 1.0) & 
     (week_data["sack"] != 1.0) & 
     (week_data["play_type"] != "run") &
     (week_data["two_point_attempt"] != 1.0) & 
     ((week_data["play_type"] != "no_play") |
      ((week_data["play_type"] == "no_play") & (week_data['penalty_team'] == week_data['posteam'])))) &
    ((week_data["incomplete_pass"] == 1.0) | (week_data["interception"] == 1.0))
).astype(int)

# --- Calculate pass yards ---
week_data["pass_yards"] = week_data["yards_gained"].where(
    (week_data["pass"] == 1)
    & (week_data["sack"] != 1)
    & (week_data["play_type"] != "no_play")
    & (week_data["pass_attempts"] == 1),
    0
)

# --- Aggregate stats per team for each game ---
game_stats_per_team = (
    week_data.groupby(["game_id", "game_stadium", "posteam", "home_team", "away_team"])
    .agg(
        total_plays=("play_id", "count"),
        total_yards=("yards_gained", "sum"),
        pass_yards=("pass_yards", "sum"),
        pass_plays=("pass_attempts", "sum"),
        rush_plays=("rush", "sum"),
        total_home_score=("total_home_score", "max"),
        total_away_score=("total_away_score", "max"),
        interceptions=("interception", "sum"),
        fourth_down_converted=("fourth_down_converted", "sum"),
        fourth_down_failed=("fourth_down_failed", "sum"),
        sacks=("sack", "sum"),
        incomplete_passes=("pass_incomplete", "sum")
    )
    .reset_index()
)

# --- Display game stats table ---
st.subheader(f"📊 Week {selected_week} Game Stats (Per Team)")
st.dataframe(game_stats_per_team[[
    "game_id", "home_team", "away_team", "posteam",
    "total_plays", "total_yards", "pass_yards", "pass_plays", "incomplete_passes", "rush_plays",
    "total_home_score", "total_away_score", "interceptions", "fourth_down_converted",
    "fourth_down_failed", "sacks", "game_stadium"
]])

# --- Prepare single row per game ---
def get_game_row(game_id):
    game = game_stats_per_team[game_stats_per_team["game_id"] == game_id]
    if len(game) != 2:
        return None

    home = game[game["posteam"] == game.iloc[0]["home_team"]].iloc[0]
    away = game[game["posteam"] == game.iloc[0]["away_team"]].iloc[0]

    return {
        "game_id": game_id,
        "game_stadium": home["game_stadium"],
        "home_team": home["home_team"],
        "away_team": away["away_team"],
        "home_total_yards": home["total_yards"],
        "away_total_yards": away["total_yards"],
        "total_home_score": home["total_home_score"],
        "total_away_score": away["total_away_score"],
        "home_sacks": home["sacks"],
        "away_sacks": away["sacks"]
    }

# --- Cached AI Summary Function ---
@st.cache_data(show_spinner=False)
def generate_game_summary_cached(model_name, game_row):
    prompt = f"""
    Write a short NFL game summary (4-5 sentences) for {game_row['away_team']} vs {game_row['home_team']}.
    Final score: {game_row['away_team']} {game_row['total_away_score']} - {game_row['home_team']} {game_row['total_home_score']}.
    Mention yards, sacks, and stadium ({game_row['game_stadium']}). 
    Make it concise, funny, and natural. If the Chargers are involved, roast Jim Harbaugh.
    """
    try:
        response = client.models.generate_content(model=model_name, contents=prompt)
        return clean_text(response.text)
    except Exception as e:
        return f"Error generating summary: {str(e)}"

# --- Game selection ---
st.sidebar.subheader("🏈 Select a Game")
game_ids = sorted(week_data["game_id"].unique())
selected_game_id = st.sidebar.selectbox("Choose Game:", game_ids)

# --- Generate Summary Button ---
generate_button = st.button("🧠 Generate AI Summary")

# Placeholder for summary
summary_placeholder = st.empty()

# --- Handle click ---
if generate_button:
    summary_placeholder.empty()
    game_row = get_game_row(selected_game_id)
    if game_row:
        with st.spinner("Generating summary..."):
            summary = generate_game_summary_cached(model_name, game_row)
        summary_placeholder.markdown(summary)
    else:
        summary_placeholder.warning("Game data incomplete.")
