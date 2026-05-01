import pandas as pd
from features.global_stats import global_pick_rate_weighted, global_ban_rate_weighted
from features.team_stats import team_preference_score
from features.player_stats import player_preference_score
from features.synergy_stats import get_synergy_score
from features.counter_stats import get_counter_score
from model.draft_engine import get_available_champions

def recommend_champions_v2(context, weights=None, top_n=10):
    """
    Implementace S(C) = w1*F1 + w2*F2 + w3*F3 + w4*F4 + w5*F6 + w6*F7
    """
    # Výchozí váhy
    if weights is None:
        weights = {
            "global_pick": 0.2,   # F1
            "global_ban": 0.1,    # F2
            "team_pref": 0.15,    # F3
            "player_pref": 0.15,  # F4
            "synergy": 0.2,       # F6
            "counter": 0.2        # F7
        }

    # 1. Získání dostupných šampionů
    available_champs = get_available_champions(
        all_champions=context.all_champions,
        banned=context.banned_champions,
        picked=context.allied_picks + context.enemy_picks,
        fearless_unavailable=context.fearless_unavailable
    )

    # 2. Načtení hromadných dat pro Metu (aby se nevolalo v cyklu)
    meta_picks = global_pick_rate_weighted(context.region)
    meta_bans = global_ban_rate_weighted(context.region)

    results = []

    for champion in available_champs:
        # F1 & F2 (Global)
        f1 = meta_picks.loc[meta_picks['champion'] == champion, 'score'].values[0] if champion in meta_picks['champion'].values else 0
        f2 = meta_bans.loc[meta_bans['champion'] == champion, 'score'].values[0] if champion in meta_bans['champion'].values else 0
        
        # F3 (Team)
        f3 = team_preference_score(champion, context)
        
        # F4 (Player)
        f4 = player_preference_score(champion, context)
        
        # F6 (Synergy)
        f6 = get_synergy_score(champion, context.allied_picks, context.region)
        
        # F7 (Counter)
        f7 = get_counter_score(champion, context.enemy_picks, context.region)

        # Finální výpočet skóre S(C)
        final_score = (
            weights["global_pick"] * f1 +
            weights["global_ban"] * f2 +
            weights["team_pref"] * f3 +
            weights["player_pref"] * f4 +
            weights["synergy"] * f6 +
            weights["counter"] * f7
        )

        results.append({
            "champion": champion,
            "score": round(final_score, 4),
            "meta_val": round(f1 + f2, 4),
            "pref_val": round(f3 + f4, 4),
            "strategic_val": round(f6 + f7, 4) # Základ pro Wildcard
        })

    df = pd.DataFrame(results).sort_values(by="score", ascending=False)
    return df.head(top_n)