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
st.title("AI-Powered NFL Game Summary Generator (Google Gemini)")

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
week = 1

@st.cache_data
def load_week_data(season, week):
    pbp = nfl.import_pbp_data([season], downcast=True, cache=False)
    return pbp[pbp["week"] == week]

# --- Load Week 1 data ---
week_data = load_week_data(season, week)

if week_data.empty:
    st.warning(f"No data found for Week {week} in {season}.")
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
    (week_data["pass"] == 1) &
    (week_data["sack"] != 1) &
    (week_data["play_type"] != "no_play") &
    (week_data["pass_attempts"] == 1),
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
        #game_stadium=("game_stadium", "first")  # Preserve stadium name
    )
    .reset_index()
)

# --- Display game stats table ---
st.subheader("📊 Game Stats Table (per team)")
st.dataframe(game_stats_per_team[[
    "game_id", "home_team", "away_team", "posteam",
    "total_plays", "total_yards", "pass_yards", "pass_plays", "incomplete_passes", "rush_plays",
    "total_home_score", "total_away_score", "interceptions", "fourth_down_converted",
    "fourth_down_failed", "sacks", "game_stadium"
]])

# --- Prepare a single row per game with home/away stats ---
def get_game_row(game_id):
    game = game_stats_per_team[game_stats_per_team["game_id"] == game_id]
    if len(game) != 2:
        return None  # Skip if data is incomplete

    home = game[game["posteam"] == game.iloc[0]["home_team"]].iloc[0]
    away = game[game["posteam"] == game.iloc[0]["away_team"]].iloc[0]

    return {
        "game_id": game_id,
        "game_stadium": home["game_stadium"],
        "home_team": home["home_team"],
        "away_team": away["away_team"],
        "home_total_plays": home["total_plays"],
        "home_total_yards": home["total_yards"],
        "home_pass_plays": home["pass_plays"],
        "home_rush_plays": home["rush_plays"],
        "away_total_plays": away["total_plays"],
        "away_total_yards": away["total_yards"],
        "away_pass_plays": away["pass_plays"],
        "away_rush_plays": away["rush_plays"],
        "total_home_score": home["total_home_score"],
        "total_away_score": away["total_away_score"],
        "home_interceptions": home["interceptions"],
        "away_interceptions": away["interceptions"],
        "home_fourth_down_converted": home["fourth_down_converted"],
        "away_fourth_down_converted": away["fourth_down_converted"],
        "home_fourth_down_failed": home["fourth_down_failed"],
        "away_fourth_down_failed": away["fourth_down_failed"],
        "home_sacks": home["sacks"],
        "away_sacks": away["sacks"],
        "home_incomplete_passes": home["incomplete_passes"],
        "away_incomplete_passes": away["incomplete_passes"]
    }

# --- Generate enhanced AI summary ---
def generate_game_summary(row):
    prompt = f"""
    Write a short NFL game summary (4-5 sentences) for {row['away_team']} vs {row['home_team']}.
    Include the final score ({row['away_team']} {row['total_away_score']} - {row['home_team']} {row['total_home_score']}).
    Provide key offensive and defensive stats for both teams:

    {row['home_team']}: 
    {row['home_total_plays']} total plays, 
    {row['home_total_yards']} total yards, 
    {row['home_pass_plays']} passing plays, 
    {row['home_rush_plays']} rushing plays, 
    {row['home_interceptions']} interceptions,
    {row['home_fourth_down_converted']} fourth down converted,
    {row['home_fourth_down_failed']} fourth down failed,
    {row['home_sacks']} sacks,
    {row['home_incomplete_passes']} incomplete passes.

    {row['away_team']}: 
    {row['away_total_plays']} total plays, 
    {row['away_total_yards']} total yards, 
    {row['away_pass_plays']} passing plays, 
    {row['away_rush_plays']} rushing plays, 
    {row['away_interceptions']} interceptions,
    {row['away_fourth_down_converted']} fourth down converted,
    {row['away_fourth_down_failed']} fourth down failed,
    {row['away_sacks']} sacks,
    {row['away_incomplete_passes']} incomplete passes.

    Highlight which team dominated the passing or rushing game. Mention pass completion percentage. And the stadium name: {row['game_stadium']}.
    Make it funny.
    Do not use emojis.
    """
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return clean_text(response.text)
    except Exception as e:
        return f"Error generating summary: {str(e)}"

# --- Game selection filter ---
with st.sidebar.subheader("🏈 Select a Game to Generate AI Summary"):
    game_ids = week_data["game_id"].unique()
    selected_game_id = st.selectbox("Choose game_id:", game_ids)

game_row = get_game_row(selected_game_id)
if game_row:
    st.subheader(f"🏈 AI Summary: {game_row['away_team']} at {game_row['home_team']}")
    st.write(generate_game_summary(game_row))
else:
    st.warning("Game data is incomplete.")
