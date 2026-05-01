import pandas as pd
from pathlib import Path

# =========================
# Pevně dané cesty
# =========================
INPUT_CSV_PATH = Path("data/raw/2026_LoL_esports_match_data_from_OraclesElixir.csv")
OUTPUT_CSV_PATH = Path("data/processed/filtered_matches.csv")

# =========================
# Požadované sloupce
# =========================
REQUIRED_COLUMNS = [
    "gameid",
    "league",
    "year",
    "split",
    "game",
    "patch",
    "side",
    "position",
    "playername",
    "playerid",
    "teamname",
    "teamid",
    "firstPick",
    "champion",
    "ban1",
    "ban2",
    "ban3",
    "ban4",
    "ban5",
    "pick1",
    "pick2",
    "pick3",
    "pick4",
    "pick5",
    "result"
]

# =========================
# Povolené ligy
# =========================
ALLOWED_LEAGUES = [
    "LEC",
    "LCK",
    "LPL",
    "LCS",
    "WLD's",
    "MSI",
    "FST",
    "EWC",
    "LTA N",
    "LTA S",
    "LTA"
]

def main():
    print("Načítám CSV soubor...")
    df = pd.read_csv(INPUT_CSV_PATH)

    print(f"Původní počet řádků: {len(df)}")

    # -------------------------
    # Filtrace lig
    # -------------------------
    df = df[df["league"].isin(ALLOWED_LEAGUES)]

    print(f"Po filtraci lig: {len(df)}")

    # -------------------------
    # Filtrace sloupců
    # -------------------------
    missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_columns:
        raise ValueError(f"CSV neobsahuje požadované sloupce: {missing_columns}")

    df = df[REQUIRED_COLUMNS]

    # -------------------------
    # Uložení výsledku
    # -------------------------
    OUTPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_CSV_PATH, index=False)

    print("Hotovo ✅")
    print(f"Výsledný soubor uložen do: {OUTPUT_CSV_PATH}")
    print(f"Počet řádků ve výsledku: {len(df)}")


if __name__ == "__main__":
    main()