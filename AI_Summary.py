import streamlit as st
import nfl_data_py as nfl
import pandas as pd
import google.genai as genai
from google.genai import types
import re
import time

# --- Helper to remove emojis or non-ASCII characters ---
def clean_text(text):
    return re.sub(r'[^\x00-\x7F]+', '', text)

# --- Page title ---
st.title("🏈 NFL Game AI Summary Generator")

# --- Sidebar configuration ---
with st.sidebar:
    st.header("Configuration")
    api_key = st.secrets["GEMINI_API_KEY"]
    model_name = st.selectbox(
        "🤖 Select Model:",
        ["gemini-2.5-flash", "gemini-2.5-pro"],
        index=0
    )

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

# --- Toggle table visibility ---
#if "show_table" not in st.session_state:
   # st.session_state.show_table = True  # default is visible

#toggle_table = st.button("📊 Show/Hide Game Stats Table")
#if toggle_table:
   # st.session_state.show_table = not st.session_state.show_table

# --- Display table only if flag is True ---
#if st.session_state.show_table:
   # st.subheader(f"📊 Week {selected_week} Game Stats (Per Team)")
   # st.dataframe(game_stats_per_team[[
     #   "game_id", "home_team", "away_team", "posteam",
      #  "total_plays", "total_yards", "pass_yards", "pass_plays", "incomplete_passes", "rush_plays",
       # "total_home_score", "total_away_score", "interceptions", "fourth_down_converted",
       # "fourth_down_failed", "sacks", "game_stadium"
   # ]])


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
    Do not use emojis.
    If the Chargers (LAC) are involved, roast Jim Harbaugh about the game cheating scandals he had at Michigan.
    """
    try:
        response = client.models.generate_content(model=model_name, contents=prompt)
        return clean_text(response.text)
    except Exception as e:
        return f"Error generating summary: {str(e)}"

# --- Game selection ---
game_ids = sorted(week_data["game_id"].unique())
selected_game_id = st.sidebar.selectbox("🏈 Select a Game", game_ids)

# --- Generate Summary Button ---
generate_button = st.button("🧠 Generate AI Summary")

# Placeholder for summary
summary_placeholder = st.empty()

# --- Handle click with typing effect ---
if generate_button:
    summary_placeholder.empty()
    game_row = get_game_row(selected_game_id)
    if game_row:
        with st.spinner("AI is typing..."):
            summary = generate_game_summary_cached(model_name, game_row)
            displayed_text = ""
            for char in summary:
                displayed_text += char
                summary_placeholder.markdown(displayed_text)
                time.sleep(0.015)  # keep typing effect
    else:
        summary_placeholder.warning("Game data incomplete.")
