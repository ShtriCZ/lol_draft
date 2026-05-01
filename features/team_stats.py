import pandas as pd
from utils.patch_utils import get_recent_patches, get_connection

def team_preference_score_v1(team: str, region: str):

    query = """
        SELECT p.champion
FROM player_picks p
JOIN matches m ON p.gameid = m.gameid
WHERE p.teamname = ?
  AND m.league = ?
    """

    conn = get_connection()
    
    df = pd.read_sql_query(query, conn, params=(team, region))

    if df.empty:
        return pd.DataFrame(columns=["champion", "team_score"])

    counts = df["champion"].value_counts().reset_index()
    counts.columns = ["champion", "count"]

    total = counts["count"].sum()
    counts["team_score"] = counts["count"] / total

    return counts[["champion", "team_score"]]

def team_preference_score(champion: str, context, n_patches: int = 3) -> float:
    """
    Conditional team preference:
    Preference pouze v zápasech, kde byl champion dostupný
    (nebanovaný + nefearless).
    """

    if champion in context.fearless_unavailable:
        return 0.0

    conn = get_connection()

    patches = get_recent_patches(context.region, n_patches)

    if not patches:
        return 0.0

    base_weights = [1.0, 0.7, 0.4]
    weights = {
        patch: base_weights[i] if i < len(base_weights) else 0.2
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
            AND p.teamname = ?
            AND p.champion = ?
        WHERE m.league = ?
          AND t.teamname = ?
          AND m.patch IN ({placeholders})
    """

    params = [context.team, champion, context.region, context.team] + patches

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if df.empty:
        return 0.0

    numerator = 0.0
    denominator = 0.0

    for _, row in df.iterrows():

        weight = weights.get(row["patch"], 0.2)

        bans = {row["ban1"], row["ban2"], row["ban3"], row["ban4"], row["ban5"]}

        # champion nebyl banovaný
        if champion not in bans:

            denominator += weight

            # byl picknut
            if pd.notna(row["picked_champion"]):
                numerator += weight

    if denominator == 0:
        return 0.0

    return numerator / denominator