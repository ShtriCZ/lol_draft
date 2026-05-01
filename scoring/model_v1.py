import pandas as pd

from features.global_stats import global_pick_rate_weighted
from features.team_stats import team_preference_score_v1
from features.player_stats import player_preference_score
from model.draft_engine import get_available_champions

def recommend_champions_v1(context, top_n=10):

    region = context.region
    team = context.team
    player = context.player

    all_champions = context.all_champions
    banned = context.banned_champions
    picked = context.allied_picks
    fearless_unavailable = context.fearless_unavailable

    # 1️⃣ Dostupní championi
    available_champs = get_available_champions(
        all_champions=all_champions,
        banned=banned,
        picked=picked,
        fearless_unavailable=fearless_unavailable
    )

    # 2️⃣ Meta
    meta_df = global_pick_rate_weighted(region)

    # 3️⃣ Team preference
    team_df = team_preference_score_v1(team, region)

    # 4️⃣ Player preference
    player_df = player_preference_score(player, region)

    # 5️⃣ Sloučení
    df = pd.DataFrame({"champion": available_champs})

    df = df.merge(meta_df, on="champion", how="left")
    df = df.merge(team_df, on="champion", how="left")
    df = df.merge(player_df, on="champion", how="left")

    df = df.fillna(0)

    df["score"] = (
        0.5 * df["meta_score"] +
        0.3 * df["team_score"] +
        0.2 * df["player_score"]
    )

    df = df.sort_values("score", ascending=False)

    return df.head(top_n)