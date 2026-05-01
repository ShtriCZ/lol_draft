import sqlite3
import pandas as pd
from draft_manager import SeriesManager

DB_PATH = "data/lol_draft.db"

def get_all_series_data():
    conn = sqlite3.connect(DB_PATH)
    # Načteme vše a převedeme side na lowercase pro jistotu
    query = """
        SELECT m.gameid, m.league, m.game, m.date, td.teamname, LOWER(td.side) as side, 
               td.ban1, td.ban2, td.ban3, td.ban4, td.ban5,
               td.pick1, td.pick2, td.pick3, td.pick4, td.pick5
        FROM matches m
        JOIN team_drafts td ON m.gameid = td.gameid
        ORDER BY m.league, m.date ASC, m.game ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        return []

    # Seskupíme řádky podle gameid (vždycky by tam měly být 2 - Blue a Red)
    game_groups = df.groupby('gameid')
    
    all_series = []
    current_series = []
    last_league = None

    # Seřadíme unikátní hry podle ligy a data, abychom mohli detekovat série
    unique_games = df[['gameid', 'league', 'game', 'date']].drop_duplicates().sort_values(['league', 'date'])

    for _, g_info in unique_games.iterrows():
        g_id = g_info['gameid']
        game_num = g_info['game']
        league = g_info['league']
        
        # Pokud je game == 1, uzavřeme starou sérii a začneme novou
        if game_num == 1:
            if len(current_series) > 1:
                all_series.append(current_series)
            current_series = []
        
        # Vytáhneme oba řádky (týmy) pro tuto hru
        game_pair = game_groups.get_group(g_id)
        
        # Kontrola, jestli máme v datech oba týmy
        if len(game_pair) == 2:
            current_series.append(game_pair)
        else:
            print(f"Varování: Hra {g_id} v lize {league} má nekompletní data (chybí tým). Přeskakuji.")

    # Přidání poslední série
    if len(current_series) > 1:
        all_series.append(current_series)
        
    return all_series

def run_series_validation():
    all_series = get_all_series_data()
    print(f"Nalezeno {len(all_series)} validních sérií (Bo3/Bo5).")

    # Statistiky rozdělené podle čísla hry v sérii
    # Klíč: číslo hry (1, 2, 3, 4, 5), Hodnota: stejný stats slovník jako minule
    game_stats = {}

    draft_steps = [
        ('ban', 'blue', 'ban1'), ('ban', 'red', 'ban1'), ('ban', 'blue', 'ban2'),
        ('ban', 'red', 'ban2'), ('ban', 'blue', 'ban3'), ('ban', 'red', 'ban3'),
        ('pick', 'blue', 'pick1'), ('pick', 'red', 'pick1'), ('pick', 'red', 'pick2'),
        ('pick', 'blue', 'pick2'), ('pick', 'blue', 'pick3'), ('pick', 'red', 'pick3'),
        ('ban', 'red', 'ban4'), ('ban', 'blue', 'ban4'), ('ban', 'red', 'ban5'),
        ('ban', 'blue', 'ban5'), ('pick', 'red', 'pick4'), ('pick', 'blue', 'pick4'),
        ('pick', 'blue', 'pick5'), ('pick', 'red', 'pick5')
    ]

    for series in all_series:
        try:
            g1 = series[0]
            league = g1['league'].iloc[0]
            blue_rows = g1[g1['side'] == 'blue']
            red_rows = g1[g1['side'] == 'red']
            
            if blue_rows.empty or red_rows.empty: continue
                
            blue_team = blue_rows.iloc[0]['teamname']
            red_team = red_rows.iloc[0]['teamname']
            
            manager = SeriesManager(region=league, my_team=blue_team, enemy_team=red_team)

            for game_df in series:
                game_num = int(game_df['game'].iloc[0])
                
                # Inicializace statistik pro konkrétní číslo hry, pokud ještě neexistuje
                if game_num not in game_stats:
                    game_stats[game_num] = {
                        "pick_total": 0, "pick_top1": 0, "pick_top5": 0,
                        "ban_total": 0, "ban_top1": 0, "ban_top5": 0
                    }

                session = manager.start_new_game(my_side='blue', has_first_pick=True)

                for action_type, side, key in draft_steps:
                    team_data = game_df[game_df['side'] == side]
                    if team_data.empty: continue
                    
                    real_champ = team_data.iloc[0][key]
                    if not real_champ or real_champ in ['None', '']:
                        session.current_step += 1
                        continue

                    recs = session.get_recommendations()
                    top_list = recs['champion'].tolist() if (recs is not None and not recs.empty) else []
                    
                    prefix = "pick_" if action_type == 'pick' else "ban_"
                    game_stats[game_num][f"{prefix}total"] += 1
                    
                    if real_champ in top_list:
                        rank = top_list.index(real_champ) + 1
                        if rank == 1: game_stats[game_num][f"{prefix}top1"] += 1
                        if rank <= 5: game_stats[game_num][f"{prefix}top5"] += 1

                    session.add_action(real_champ)
        except Exception as e:
            continue

    # FINÁLNÍ VÝPIS
    print("\n" + "="*70)
    print(f"{'HRA':<6} | {'TYP':<5} | {'TOP 1':<10} | {'TOP 5':<10} | {'CELKEM'}")
    print("-"*70)
    
    for g_num in sorted(game_stats.keys()):
        s = game_stats[g_num]
        for cat in ["pick", "ban"]:
            total = s[f"{cat}_total"]
            if total > 0:
                t1_pc = (s[f"{cat}_top1"] / total) * 100
                t5_pc = (s[f"{cat}_top5"] / total) * 100
                name = f"Hra {g_num}" if cat == "pick" else ""
                print(f"{name:<6} | {cat:<5} | {t1_pc:>5.1f}%     | {t5_pc:>5.1f}%     | {total}")
        print("-"*70)

if __name__ == "__main__":
    run_series_validation()