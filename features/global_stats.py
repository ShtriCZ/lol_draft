import pandas as pd
from utils.patch_utils import *

def global_pick_rate_weighted(region: str, n_patches: int = 3) -> pd.DataFrame:
    """
    Vážený pick rate podle posledních N patchů.
    """

    conn = get_connection()

    patches = get_recent_patches(region, n_patches)

    if not patches:
        return pd.DataFrame(columns=["champion", "score"])

    # vytvoření váh
    weights = {}
    base_weights = [1.0, 0.7, 0.4]

    for i, patch in enumerate(patches):
        weights[patch] = base_weights[i] if i < len(base_weights) else 0.2

    placeholders = ",".join(["?"] * len(patches))

    query = f"""
    SELECT p.champion, m.patch
    FROM player_picks p
    JOIN matches m ON p.gameid = m.gameid
    WHERE m.league = ?
    AND m.patch IN ({placeholders})
    """

    params = [region] + patches
    df = pd.read_sql_query(query, conn, params=params)

    conn.close()

    if df.empty:
        return pd.DataFrame(columns=["champion", "score"])

    # přidání váhy
    df["weight"] = df["patch"].map(weights)

    # agregace
    scores = (
        df.groupby("champion")["weight"]
        .sum()
        .reset_index()
    )

    total_weight = df["weight"].sum()
    scores["score"] = scores["weight"] / total_weight

    return scores.sort_values(by="score", ascending=False)

def global_ban_rate_weighted(region: str, n_patches: int = 3) -> pd.DataFrame:
    """
    Vážený ban rate podle posledních N patchů.
    """

    conn = get_connection()

    patches = get_recent_patches(region, n_patches)

    if not patches:
        return pd.DataFrame(columns=["champion", "score"])

    base_weights = [1.0, 0.7, 0.4]
    weights = {
        patch: base_weights[i] if i < len(base_weights) else 0.2
        for i, patch in enumerate(patches)
    }

    placeholders = ",".join(["?"] * len(patches))

    query = f"""
    SELECT m.patch, t.ban1, t.ban2, t.ban3, t.ban4, t.ban5
    FROM team_drafts t
    JOIN matches m ON t.gameid = m.gameid
    WHERE m.league = ?
    AND m.patch IN ({placeholders})
    """

    params = [region] + patches
    df = pd.read_sql_query(query, conn, params=params)

    conn.close()

    if df.empty:
        return pd.DataFrame(columns=["champion", "score"])

    # transformace do long form
    bans = df.melt(
        id_vars=["patch"],
        value_vars=["ban1", "ban2", "ban3", "ban4", "ban5"],
        value_name="champion"
    )

    bans = bans.dropna(subset=["champion"])

    bans["weight"] = bans["patch"].map(weights)

    scores = (
        bans.groupby("champion")["weight"]
        .sum()
        .reset_index()
    )

    total_weight = bans["weight"].sum()
    scores["score"] = scores["weight"] / total_weight

    return scores.sort_values(by="score", ascending=False)