import pandas as pd
from pathlib import Path

INPUT_CSV_PATH = Path("data/processed/filtered_matches.csv")

OUTPUT_DIR = Path("data/processed/split")
MATCHES_CSV = OUTPUT_DIR / "matches.csv"
TEAM_DRAFTS_CSV = OUTPUT_DIR / "team_drafts.csv"
PLAYER_PICKS_CSV = OUTPUT_DIR / "player_picks.csv"


def main():
    df = pd.read_csv(INPUT_CSV_PATH, dtype=str)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ================= MATCHES =================
    matches = (
        df[
            ["gameid", "league", "year", "split", "game", "patch", "result"]
        ]
        .drop_duplicates(subset=["gameid"])
        .reset_index(drop=True)
    )
    matches.to_csv(MATCHES_CSV, index=False)

    # ================= TEAM DRAFTS =================
    team_rows = df[df["position"] == "team"]

    team_drafts = (
        team_rows[
            [
                "gameid",
                "teamid",
                "teamname",
                "side",
                "firstPick",
                "ban1",
                "ban2",
                "ban3",
                "ban4",
                "ban5",
                "pick1",
                "pick2",
                "pick3",
                "pick4",
                "pick5"
            ]
        ]
        .drop_duplicates(subset=["gameid", "teamid"])
        .reset_index(drop=True)
    )
    team_drafts.to_csv(TEAM_DRAFTS_CSV, index=False)

    # ================= PLAYER PICKS =================
    player_rows = df[df["position"] != "team"]

    player_picks = (
        player_rows[
            [
                "gameid",
                "teamid",
                "teamname",
                "playerid",
                "playername",
                "position",
                "champion"
            ]
        ]
        .reset_index(drop=True)
    )
    player_picks.to_csv(PLAYER_PICKS_CSV, index=False)

    print("✅ Hotovo")


if __name__ == "__main__":
    main()
