from features.global_stats import (
    global_pick_rate_weighted,
    global_ban_rate_weighted
)
from model.draft_context import DraftContext
from features.team_stats import team_preference_score
from scoring.model_v1 import recommend_champions_v1
import pandas as pd
from utils.patch_utils import get_connection
from scoring.model_v2 import recommend_champions_v2

def main():
    
    region = "LCK"

    print("=== GLOBAL PICK RATE ===")
    picks = global_pick_rate_weighted(region, n_patches=3)
    print(picks.head(10))

    print("\n=== GLOBAL BAN RATE ===")
    bans = global_ban_rate_weighted(region, n_patches=3)
    print(bans.head(10))

    context = DraftContext(
        region="LCK",
        team="T1",
        player=None,
        all_champions= load_all_champions(),   # komplet seznam ze DB
        allied_picks=[],
        enemy_picks=[],
        banned_champions=[],
        fearless_unavailable=[],
        game_number=1
    )

    score = team_preference_score("Azir", context)
    
    print("Team preference:", score)
    context = DraftContext(
        region= "LEC",
        team= "G2 Esports",
        player= "Caps",
        all_champions= load_all_champions(),   # komplet seznam ze DB
        banned_champions= ["Azir", "Orianna"],
        allied_picks= ["Vi", "Jinx"],
        fearless_unavailable= ["Ahri"],
        enemy_picks=[],
        game_number=1
    )

    #result = recommend_champions_v1(context, top_n=10)

    #print(result)
    
    context = DraftContext(
    region="LEC",
    team="G2 Esports",
    player="Caps",
    all_champions=load_all_champions(),
    allied_picks=["Vi", "Rell"], # Máme silný engage
    enemy_picks=["Jayce"],       # Soupeř má squishy poke top/mid
    banned_champions=["Azir", "Orianna", "Tristana"],
    fearless_unavailable=[],
    game_number=1
    )

    recommendations = recommend_champions_v2(context)
    print(recommendations)

def load_all_champions():    
    conn = get_connection()
    query = "SELECT DISTINCT champion FROM player_picks"
    df = pd.read_sql_query(query, conn)
    return df["champion"].tolist()

if __name__ == "__main__":
    main()