import pandas as pd
from utils.patch_utils import get_connection

def get_synergy_score(champion: str, allied_picks: list, region: str) -> float:
    """
    Vypočítá synergický koeficient (F6) jako průměrný Win Rate 
    šampiona se stávajícími spojenci.
    """
    if not allied_picks:
        return 0.5  # Neutrální hodnota (50% WR)

    conn = get_connection()
    wr_list = []

    for ally in allied_picks:
        # Hledáme hry, kde byli oba šampioni v týmu (nezáleží na pozici)
        query = """
            SELECT AVG(result) as wr, COUNT(*) as cnt
            FROM team_drafts t
            JOIN matches m ON t.gameid = m.gameid
            WHERE m.league = ? 
              AND (
                (pick1=? OR pick2=? OR pick3=? OR pick4=? OR pick5=?) AND
                (pick1=? OR pick2=? OR pick3=? OR pick4=? OR pick5=?)
              )
        """
        params = [region, champion, champion, champion, champion, champion, 
                  ally, ally, ally, ally, ally]
        
        df = pd.read_sql_query(query, conn, params=params)
        
        # Bayesian Smoothing (pokud je málo her, táhneme to k 0.5)
        # Tím eliminujeme 100% WR z jedné náhodné hry
        if not df.empty and df['cnt'].iloc[0] > 0:
            wr = df['wr'].iloc[0]
            cnt = df['cnt'].iloc[0]
            smoothed_wr = (wr * cnt + 0.5 * 5) / (cnt + 5)
            wr_list.append(smoothed_wr)

    conn.close()
    
    if not wr_list:
        return 0.5
        
    return sum(wr_list) / len(wr_list)