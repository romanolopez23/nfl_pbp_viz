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

#import data
pbp = nfl.import_pbp_data([2024])
#create df
df = pd.DataFrame(pbp)

# Update yardline_100
df['yardline_100'] = 120 - df['yardline_100'] - 10
# Calculate xreception
df['xreception'] = df['yardline_100'] + df['air_yards']
# Calculate xend
df['xend'] = df['yardline_100'] + df['air_yards'] + df['yards_after_catch']

#filter and show data
df = df[(df['play_type'] == 'pass') & (df['touchdown'] == 1.0)]


#streamlit filters

passer = df['passer'].drop_duplicates()
passer_choice = st.sidebar.selectbox(
    'Choose Passer:', options=passer)
df = df[(df['passer'] == passer_choice)]

pd.set_option('display.max_columns', None)
df


Game_ID = df['game_id'].drop_duplicates()
Game_ID_choice = st.sidebar.selectbox(
    'Choose Game ID:', options=Game_ID)
df = df[(df['game_id'] == Game_ID_choice)]

play_id = df['play_id'].drop_duplicates()
play_id_choice = st.sidebar.selectbox(
    'Choose Play_id:', options=play_id)
df = df[(df['play_id'] == play_id_choice)]



df = df[['game_id', 'play_id', 'home_team', 'away_team', 'game_date', \
        'receiver', 'passer', 'ydstogo', 'down', 'posteam', 'yardline_100', \
        'xreception', 'xend', 'desc', 'yards_gained', 'air_yards', 'yards_after_catch',\
            ]]
df

# Assign variables
home_team = df['home_team'].iloc[0]
away_team = df['away_team'].iloc[0] 
game_date = df['game_date'].iloc[0]
desc = df['desc'].iloc[0]
receiver = df['receiver'].iloc[0]
ydstogo = df['ydstogo'].iloc[0]
down = df['down'].iloc[0]


def create_football_field(linenumbers=True,
                          endzones=True,
                          highlight_line_number=85,
                          highlight_line=False,
                          highlight_first_down_line=False,
                          yards_to_go=10,
                          highlighted_name='Line of Scrimmage',
                          fifty_is_los=False,
                          figsize=(12, 6.33)):
    """
    Function that plots the football field for viewing plays.
    Allows for showing or hiding endzones.
    """
    rect = patches.Rectangle((0, 0), 120, 53.3, linewidth=0.1,
                             edgecolor='r', facecolor='darkgreen', zorder=0)

    fig, ax = plt.subplots(1, figsize=figsize)
    ax.add_patch(rect)

    plt.plot([10, 10, 10, 20, 20, 30, 30, 40, 40, 50, 50, 60, 60, 70, 70, 80,
              80, 90, 90, 100, 100, 110, 110, 120, 0, 0, 120, 120],
             [0, 0, 53.3, 53.3, 0, 0, 53.3, 53.3, 0, 0, 53.3, 53.3, 0, 0, 53.3,
              53.3, 0, 0, 53.3, 53.3, 0, 0, 53.3, 53.3, 53.3, 0, 0, 53.3],
             color='white')

    if fifty_is_los:
        plt.plot([60, 60], [0, 53.3], color='gold')
        plt.text(62, 50, '<- Player Yardline at Snap', color='gold')
        
    # Endzones
    if endzones:
        ez1 = patches.Rectangle((0, 0), 10, 53.3,
                                linewidth=0.1,
                                edgecolor='r',
                                facecolor='blue',
                                alpha=0.2,
                                zorder=0)
        ez2 = patches.Rectangle((110, 0), 120, 53.3,
                                linewidth=0.1,
                                edgecolor='r',
                                facecolor='blue',
                                alpha=0.2,
                                zorder=0)
        ax.add_patch(ez1)
        ax.add_patch(ez2)

    plt.xlim(0, 120)
    plt.ylim(-5, 58.3)
    plt.axis('off')

    if linenumbers:
        for x in range(20, 110, 10):
            numb = x
            if x > 50:
                numb = 120 - x
            plt.text(x, 5, str(numb - 10),
                     horizontalalignment='center',
                     fontsize=20,
                     color='white')
            plt.text(x - 0.95, 53.3 - 5, str(numb - 10),
                     horizontalalignment='center',
                     fontsize=20,
                     color='white', rotation=180)

    if endzones:
        hash_range = range(11, 110)
    else:
        hash_range = range(1, 120)

    for x in hash_range:
        ax.plot([x, x], [0.4, 0.7], color='white')
        ax.plot([x, x], [53.0, 52.5], color='white')
        ax.plot([x, x], [22.91, 23.57], color='white')
        ax.plot([x, x], [29.73, 30.39], color='white')

    if highlight_line:
        hl = highlight_line_number
        plt.plot([hl, hl], [0, 53.3], color='yellow')
        
    if highlight_first_down_line:
        fl = hl + yards_to_go
        plt.plot([fl, fl], [0, 53.3], color='yellow')
        
    return fig, ax


df = pd.DataFrame(df)  # Ensure your df is defined
for team in df['posteam'].unique():
    team_data = df[df['posteam'] == team]

# Display the football field
fig, ax = create_football_field(
    linenumbers=True,
    endzones=True,
    highlight_line=True,
    highlight_line_number=team_data['yardline_100'].iloc[0],  # Using the first value for highlighting
    highlight_first_down_line=True,
    yards_to_go=team_data['ydstogo'].iloc[0]  # Using the first value for highlighting
)

# Create the scatter plot for xpass
for team in df['posteam'].unique():
    team_data = df[df['posteam'] == team]
    plt.scatter(team_data['yardline_100'], np.full(len(team_data), 26.65), label=f"{team} yardline_100", marker='o', s=200)

# Create the scatter plot for air_yards
plt.scatter(team_data['xreception'], np.full(len(team_data), 26.65), label=f"{team} xreception", marker='x', s=200)

# Add arrows from xreception to xend
for i in range(len(team_data)):
    plt.arrow(
        team_data['xreception'].iloc[i],
        26.65,
        team_data['xend'].iloc[i] - team_data['xreception'].iloc[i],  # Arrow length in x direction
        0,  # Arrow length in y direction (0 since we're on a constant y-level)
        head_width=0.5,  # Width of the arrow head
        head_length=0.5,  # Length of the arrow head
        fc='orange',  # Fill color for the arrow head
        ec='orange'   # Edge color for the arrow head
    )

wrapped_desc = textwrap.fill(desc, width=40)

# Set the title
plt.title(
    f"{away_team} at {home_team} on {game_date}\n"
    f"{passer_choice} to {receiver}\n"
    f"Down: {down} - Yards to Go: {ydstogo}\n\n\n" 
    f"{wrapped_desc}", 
    fontsize=24
)


# Display the figure in Streamlit
st.pyplot(fig)
