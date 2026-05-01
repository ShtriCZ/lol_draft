import pandas as pd
from utils.patch_utils import get_recent_patches, get_connection


def player_preference_score(champion: str, context, n_patches: int = 5) -> float:
    """
    Conditional player preference:
    Preference hráče pouze v zápasech,
    kde byl champion dostupný.
    """

    # Pokud champion není dostupný kvůli fearless
    if champion in context.fearless_unavailable:
        return 0.0

    # Pokud není definován hráč
    if not context.player:
        return 0.0

    conn = get_connection()

    patches = get_recent_patches(context.region, n_patches)

    if not patches:
        return 0.0

    base_weights = [1.0, 0.85, 0.7, 0.55, 0.4]
    weights = {
        patch: base_weights[i] if i < len(base_weights) else 0.3
        for i, patch in enumerate(patches)
    }

    placeholders = ",".join(["?"] * len(patches))

    query = f"""
        SELECT 
            m.patch,
            p.champion AS picked_champion,
            t.ban1, t.ban2, t.ban3, t.ban4, t.ban5
        FROM matches m
        JOIN team_drafts t ON m.gameid = t.gameid
        LEFT JOIN player_picks p 
            ON m.gameid = p.gameid 
            AND p.playername = ?
            AND p.champion = ?
        WHERE m.league = ?
          AND p.playername = ?
          AND m.patch IN ({placeholders})
    """

    params = [
        context.player,
        champion,
        context.region,
        context.player
    ] + patches

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if df.empty:
        return 0.0

    numerator = 0.0
    denominator = 0.0

    for _, row in df.iterrows():

        weight = weights.get(row["patch"], 0.3)

        bans = {row["ban1"], row["ban2"], row["ban3"], row["ban4"], row["ban5"]}

        if champion not in bans:

            denominator += weight

            if pd.notna(row["picked_champion"]):
                numerator += weight

    if denominator == 0:
        return 0.0

    return numerator / denominator