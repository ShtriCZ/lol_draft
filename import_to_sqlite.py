import pandas as pd
import sqlite3
from pathlib import Path

DB_PATH = Path("data/lol_draft.db")
CSV_PATH = Path("data/raw/2026_LoL_esports_match_data_from_OraclesElixir.csv")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

ALLOWED_LEAGUES = {
    "LEC",
    "LCK",
    "LPL",
    "LCS",
    "WLD's",
    "MSI",
    "FST",
    "EWC",
    "LTA",
    "LTA N",
    "LTA S",
}

def create_tables():
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS matches (
        gameid TEXT PRIMARY KEY,
        league TEXT,
        year INTEGER,
        split TEXT,
        game INTEGER,
        patch TEXT,
        date TEXT,
        gamelength INTEGER
    );

    CREATE TABLE IF NOT EXISTS team_drafts (
        gameid TEXT,
        side TEXT,
        teamname TEXT,
        teamid TEXT,
        firstPick INTEGER,
        ban1 TEXT, ban2 TEXT, ban3 TEXT, ban4 TEXT, ban5 TEXT,
        pick1 TEXT, pick2 TEXT, pick3 TEXT, pick4 TEXT, pick5 TEXT,
        result INTEGER,
        PRIMARY KEY (gameid, side)
    );

    CREATE TABLE IF NOT EXISTS player_picks (
        gameid TEXT,
        playerid TEXT,
        playername TEXT,
        position TEXT,
        side TEXT,
        teamname TEXT,
        teamid TEXT,
        champion TEXT,
        PRIMARY KEY (gameid, playerid)
    );
    """)

def import_matches(df):
    matches = df[[
        "gameid", "league", "year", "split",
        "game", "patch", "date", "gamelength"
    ]].drop_duplicates("gameid")

    matches.to_sql(
        "matches",
        conn,
        if_exists="append",
        index=False
    )

def import_team_drafts(df):
    teams = df[df["position"] == "team"][[
        "gameid", "side", "teamname", "teamid", "firstPick",
        "ban1", "ban2", "ban3", "ban4", "ban5",
        "pick1", "pick2", "pick3", "pick4", "pick5",
        "result"
    ]]

    teams.to_sql(
        "team_drafts",
        conn,
        if_exists="append",
        index=False
    )

def import_player_picks(df):
    players = df[df["position"] != "team"][[
        "gameid", "playerid", "playername",
        "position", "side",
        "teamname", "teamid",
        "champion"
    ]]

    players.to_sql(
        "player_picks",
        conn,
        if_exists="append",
        index=False
    )

def main():
    df = pd.read_csv(CSV_PATH)
    # Filtrace pouze na vybrané ligy
    df = df[df["league"].isin(ALLOWED_LEAGUES)].copy()

    create_tables()
    import_matches(df)
    import_team_drafts(df)
    import_player_picks(df)

    conn.commit()
    conn.close()

    print("✅ SQLite databáze úspěšně aktualizována")

if __name__ == "__main__":
    main()
