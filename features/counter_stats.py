import pandas as pd
from utils.patch_utils import get_connection

def get_counter_score(champion: str, enemy_picks: list, region: str) -> float:
    """
    Vypočítá Counter koeficient (F7) proti nepřátelskému týmu.
    """
    if not enemy_picks:
        return 0.5

    conn = get_connection()
    wr_list = []

    for enemy in enemy_picks:
        # Hledáme hry, kde náš tým vyhrál (result=1) a měl 'champion', 
        # zatímco soupeř měl 'enemy'. 
        # POZNÁMKA: Musíme joinovat team_drafts t1 (náš) a team_drafts t2 (soupeř)
        query = """
            SELECT AVG(t1.result) as wr, COUNT(*) as cnt
            FROM team_drafts t1
            JOIN team_drafts t2 ON t1.gameid = t2.gameid AND t1.side != t2.side
            JOIN matches m ON t1.gameid = m.gameid
            WHERE m.league = ?
              AND (t1.pick1=? OR t1.pick2=? OR t1.pick3=? OR t1.pick4=? OR t1.pick5=?)
              AND (t2.pick1=? OR t2.pick2=? OR t2.pick3=? OR t2.pick4=? OR t2.pick5=?)
        """
        params = [region, champion, champion, champion, champion, champion, 
                  enemy, enemy, enemy, enemy, enemy]
        
        df = pd.read_sql_query(query, conn, params=params)
        
        if not df.empty and df['cnt'].iloc[0] > 0:
            wr = df['wr'].iloc[0]
            cnt = df['cnt'].iloc[0]
            smoothed_wr = (wr * cnt + 0.5 * 5) / (cnt + 5)
            wr_list.append(smoothed_wr)

    conn.close()
    return sum(wr_list) / len(wr_list) if wr_list else 0.5