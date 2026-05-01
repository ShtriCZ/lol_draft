import pandas as pd
import sqlite3


def get_connection():
    return sqlite3.connect("data/lol_draft.db")


def get_recent_patches(region: str, n: int = 3) -> list[str]:
    """
    Vrátí posledních N unikátních patchů
    pro daný region.
    """

    conn = get_connection()

    query = """
        SELECT DISTINCT patch
        FROM matches
        WHERE league = ?
        ORDER BY year DESC, split DESC, game DESC
    """

    df = pd.read_sql_query(query, conn, params=[region])
    conn.close()

    return df["patch"].head(n).tolist()