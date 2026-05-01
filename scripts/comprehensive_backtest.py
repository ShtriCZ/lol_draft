import sqlite3
import pandas as pd
from main import DraftContext
from scoring.model_v2_5 import recommend_champions_v2_5, recommend_bans_v2_5

def run_comprehensive_backtest(limit=100, cfg=None):
    """
    cfg: Slovník s váhami pro jednotlivé fáze. 
    Pokud je None, použijí se defaultní hodnoty.
    """
    conn = sqlite3.connect("data/lol_draft.db")
    
    # SQL dotaz (league je v matches, gameid propojuje vše)
    query = """
        SELECT 
            p.gameid, m.league, p.teamname, p.playername, p.champion as real_pick,
            m.game as game_number, td.firstPick, p.position
        FROM player_picks p
        JOIN matches m ON p.gameid = m.gameid
        JOIN team_drafts td ON p.gameid = td.gameid AND p.teamname = td.teamname
        WHERE p.champion IS NOT NULL
        LIMIT ?
    """
    data = pd.read_sql_query(query, conn, params=(limit,))
    all_champs = pd.read_sql_query("SELECT DISTINCT champion FROM champion_roles", conn)['champion'].tolist()

    stats = {
        "bans_ph1": {"hits": 0, "total": 0},
        "bans_ph2": {"hits": 0, "total": 0},
        "power_picks": {"hits": 0, "total": 0},
        "counter_picks": {"hits": 0, "total": 0}
    }

    # Defaultní váhy pokud nejsou dodány (pro normální běh)
    if cfg is None:
        cfg = {
            "w_ban1": [0.9, 0.1], 
            "w_ban2": [0.5, 0.4, 0.1],
            "w_pick_early": {"meta": 0.3, "pref": 0.6, "strategic": 0.1},
            "w_pick_late": {"meta": 0.2, "pref": 0.6, "strategic": 0.2}
        }

    for idx, row in data.iterrows():
        # --- POMOCNÁ DATA ---
        enemy_query = f"SELECT teamname FROM team_drafts WHERE gameid = '{row['gameid']}' AND teamname != '{row['teamname']}'"
        enemy_res = pd.read_sql_query(enemy_query, conn)
        enemy_team = enemy_res.iloc[0]['teamname'] if not enemy_res.empty else "Unknown"

        my_bans_query = f"SELECT ban1, ban2, ban3, ban4, ban5 FROM team_drafts WHERE gameid = '{row['gameid']}' AND teamname = '{row['teamname']}'"
        my_bans_res = pd.read_sql_query(my_bans_query, conn)
        real_ph1 = [b for b in my_bans_res.iloc[0][['ban1', 'ban2', 'ban3']].tolist() if b] if not my_bans_res.empty else []
        real_ph2 = [b for b in my_bans_res.iloc[0][['ban4', 'ban5']].tolist() if b] if not my_bans_res.empty else []

        # --- TESTOVÁNÍ S VÁHAMI Z CFG ---
        
        # 1. BANS Phase 1
        ctx_ph1 = DraftContext(region=row['league'], all_champions=all_champs, allied_picks=[], enemy_picks=[],
                               banned_champions=[], fearless_unavailable=[], team=enemy_team, player="Unknown",
                               game_number=row['game_number'], has_first_pick=bool(row['firstPick']))
        # Předáváme váhy do funkce (nutno upravit i funkci v model_v2_5.py)
        rec_ph1 = recommend_bans_v2_5(ctx_ph1, phase=1, top_n=5, weights=cfg["w_ban1"])['champion'].tolist()
        if any(b in real_ph1 for b in rec_ph1): stats["bans_ph1"]["hits"] += 1
        stats["bans_ph1"]["total"] += 1

        # 2. BANS Phase 2
        # (Zde by se měly doplnit i allied_early/enemy_early picky jako minule)
        ctx_ph2 = DraftContext(region=row['league'], all_champions=all_champs, allied_picks=[], enemy_picks=[],
                               banned_champions=real_ph1, fearless_unavailable=[], team=enemy_team, player="Unknown",
                               game_number=row['game_number'], has_first_pick=bool(row['firstPick']))
        rec_ph2 = recommend_bans_v2_5(ctx_ph2, phase=2, top_n=5, weights=cfg["w_ban2"])['champion'].tolist()
        if any(b in real_ph2 for b in rec_ph2): stats["bans_ph2"]["hits"] += 1
        stats["bans_ph2"]["total"] += 1

        # 3. PICKS (Early vs Late)
        ctx_pick = DraftContext(region=row['league'], all_champions=all_champs, allied_picks=[], enemy_picks=[],
                                banned_champions=real_ph1+real_ph2, fearless_unavailable=[], 
                                team=row['teamname'], player=row['playername'],
                                game_number=row['game_number'], has_first_pick=bool(row['firstPick']))
        
        is_early = (row['firstPick'] == 1 or row['position'] in ['JNG', 'ADC'])
        p_weights = cfg["w_pick_early"] if is_early else cfg["w_pick_late"]
        
        recs = recommend_champions_v2_5(ctx_pick, top_n=5, weights=p_weights)['champion'].tolist()
        
        if is_early:
            if row['real_pick'] in recs: stats["power_picks"]["hits"] += 1
            stats["power_picks"]["total"] += 1
        else:
            if row['real_pick'] in recs: stats["counter_picks"]["hits"] += 1
            stats["counter_picks"]["total"] += 1

    conn.close()
    return stats

if __name__ == "__main__":
    run_comprehensive_backtest(limit=20, cfg=None)