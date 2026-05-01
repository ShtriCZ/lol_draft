import sqlite3
import pandas as pd
from draft_manager import DraftSession, SeriesManager

DB_PATH = "data/lol_draft.db"

def get_game_flow(gameid, conn):
    query = f"SELECT * FROM team_drafts WHERE gameid = '{gameid}'"
    df = pd.read_sql_query(query, conn)
    if 'side' in df.columns: df['side'] = df['side'].str.lower()
    
    blue_rows = df[df['side'] == 'blue']
    red_rows = df[df['side'] == 'red']
    if blue_rows.empty or red_rows.empty: return None

    b, r = blue_rows.iloc[0], red_rows.iloc[0]
    # Vrátíme i jména týmů pro logování
    teams = {'blue': b['teamname'], 'red': r['teamname']}
    
    flow = [
        ('ban', 'blue', b['ban1']), ('ban', 'red', r['ban1']),
        ('ban', 'blue', b['ban2']), ('ban', 'red', r['ban2']),
        ('ban', 'blue', b['ban3']), ('ban', 'red', r['ban3']),
        ('pick', 'blue', b['pick1']), ('pick', 'red', r['pick1']),
        ('pick', 'red', r['pick2']), ('pick', 'blue', b['pick2']),
        ('pick', 'blue', b['pick3']), ('pick', 'red', r['pick3']),
        ('ban', 'red', r['ban4']), ('ban', 'blue', b['ban4']),
        ('ban', 'red', r['ban5']), ('ban', 'blue', b['ban5']),
        ('pick', 'red', r['pick4']), ('pick', 'blue', b['pick4']),
        ('pick', 'blue', b['pick5']), ('pick', 'red', r['pick5'])
    ]
    return flow, teams

def run_validation(game_ids):
    conn = sqlite3.connect(DB_PATH)
    all_results = []

    for g_id in game_ids:
        # Načtení info o zápasu
        match_info = pd.read_sql_query(f"SELECT patch, league, split FROM matches WHERE gameid='{g_id}'", conn)
        patch = match_info.iloc[0]['patch'] if not match_info.empty else "???"
        league = match_info.iloc[0]['league'] if not match_info.empty else "???"
        
        res = get_game_flow(g_id, conn)
        if not res: continue
        flow, teams = res

        query_fp = f"SELECT firstPick FROM team_drafts WHERE gameid='{g_id}' AND LOWER(side)='blue'"
        fp_res = pd.read_sql_query(query_fp, conn)
        blue_fp = fp_res.iloc[0]['firstPick'] if not fp_res.empty else 1
        
        # SeriesManager s reálnou ligou a týmy
        manager = SeriesManager(region=league, my_team=teams['blue'], enemy_team=teams['red'], format_bo=5)
        session = manager.start_new_game(my_side='blue', has_first_pick=(blue_fp == 1))
        
        print(f"\n{'='*90}")
        print(f"LIGA: {league:6} | PATCH: {patch:6} | {teams['blue']} vs {teams['red']} ({g_id})")
        print(f"{'='*90}")

        hits = {"gameid": g_id, "league": league, "patch": patch, "total_picks": 0, "top1": 0, "top3": 0, "top5": 0}

        for action_type, side, real_champ in flow:
            if not real_champ or real_champ == 'None': continue

            if action_type == 'pick':
                # Zjistíme, co si systém myslí, že zbývá za role
                occupied = session.get_occupied_roles(side="allied" if session.is_my_turn() else "enemy")
                all_roles = ['top', 'jungle', 'mid', 'adc', 'support']
                missing_roles = [r for r in all_roles if r not in occupied]
                
                recs = session.get_recommendations()
                top_list = recs['champion'].tolist() if (recs is not None and not recs.empty) else []
                
                print(f"KROK {session.current_step:2} | SIDE: {side.upper():4} | CHYBÍ ROLE: {missing_roles}")
                print(f"  REAL: {real_champ:15} | TOP 5 REC: {top_list[:5]}")
                
                hits["total_picks"] += 1
                real_norm = "".join(filter(str.isalnum, real_champ.lower()))
                top_norm = ["".join(filter(str.isalnum, str(c).lower())) for c in top_list]
                
                if real_norm in top_norm:
                    rank = top_norm.index(real_norm) + 1
                    if rank == 1: hits["top1"] += 1
                    if rank <= 3: hits["top3"] += 1
                    if rank <= 5: hits["top5"] += 1
                    print(f"    >>> ZÁSAH na pozici: {rank}")
                else:
                    if not top_list:
                        print(f"    [!!!] CHYBA: Algoritmus vrátil prázdný seznam pro role {missing_roles}")
                    else:
                        print(f"    --- MIMO")

            session.add_action(real_champ)

        all_results.append(hits)
        
    conn.close()
    return pd.DataFrame(all_results)

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    # Změna: Bereme náhodné hry, aby se test nerypoval pořád v těch stejných 20
    query = "SELECT DISTINCT gameid FROM team_drafts ORDER BY RANDOM() LIMIT 5"
    sample_games = pd.read_sql_query(query, conn)['gameid'].tolist()
    conn.close()

    results = run_validation(sample_games)
    print("\n\nSUMMARY:")
    print(results)