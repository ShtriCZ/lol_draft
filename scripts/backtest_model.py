import sqlite3
import pandas as pd
from scoring.model_v2_5 import recommend_champions_v2_5
from main import DraftContext # Předpokládám, že DraftContext máš v main.py nebo jinde

import sqlite3
import pandas as pd
from main import DraftContext
from scoring.model_v2_5 import recommend_champions_v2_5

def run_backtest(limit=10):
    conn = sqlite3.connect("data/lol_draft.db")
    
    # Načteme data: zápas, tým, hráče a co reálně picknul
    # Filtrujeme na Blue side a pick1 (B1), což je nejčistší test mety a preferencí
    query = """
        SELECT 
            m.gameid, 
            m.league, 
            p.teamname, 
            p.playername, 
            p.champion as real_pick
        FROM matches m
        JOIN player_picks p ON m.gameid = p.gameid
        WHERE p.side = 'Blue' AND p.position = 'mid' 
        LIMIT ?
    """
    test_data = pd.read_sql_query(query, conn, params=(limit,))
    
    # Seznam všech šampionů pro model
    all_champs = pd.read_sql_query("SELECT DISTINCT champion FROM champion_roles", conn)['champion'].tolist()
    
    top_1_hits = 0
    top_5_hits = 0

    print(f"{'TEAM & PLAYER':<35} | {'REAL PICK':<12} | {'MODEL TOP 5 RECOMMENDATIONS'}")
    print("-" * 110)

    for idx, row in test_data.iterrows():
        # 1. Načtení reálných banů pro tuto hru
        bans_query = f"""
            SELECT ban1, ban2, ban3, ban4, ban5 
            FROM team_drafts 
            WHERE gameid = '{row['gameid']}'
        """
        bans_df = pd.read_sql_query(bans_query, conn)
        if not bans_df.empty:
            # .values.flatten() udělá z tabulky banů jeden dlouhý seznam, .tolist() ho převede na list
            real_bans = [b for b in bans_df.values.flatten() if b and b != '']
            
        # 2. Příprava kontextu s reálnými daty o týmu a hráči
        context = DraftContext(
            region=row['league'],
            all_champions=all_champs,
            allied_picks=[], 
            enemy_picks=[],
            banned_champions=real_bans,
            fearless_unavailable=[],
            team=row['teamname'],
            player=row['playername'],
            game_number=1
        )
        
        # 3. Získání doporučení od modelu v2.5
        recs = recommend_champions_v2_5(context, top_n=5)
        
        real_pick = row['real_pick']
        recommended_list = []
        rec_str = ""

        if not recs.empty:
            recommended_list = recs['champion'].tolist()
            # Formátování výstupu: Šampion (skóre)
            rec_str = ", ".join([f"{r['champion']} ({r['score']})" for _, r in recs.iterrows()])
        else:
            rec_str = "ŽÁDNÁ DOPORUČENÍ"

        # 4. Vyhodnocení úspěšnosti
        is_top1 = False
        if recommended_list and real_pick == recommended_list[0]:
            is_top1 = True
            top_1_hits += 1
            
        is_top5 = False
        if real_pick in recommended_list:
            is_top5 = True
            top_5_hits += 1

        # 5. Výpis řádku
        status = "✅" if is_top5 else "❌"
        line_info = f"{row['teamname']} ({row['playername']})"
        print(f"{line_info[:35]:<35} | {real_pick:<12} | {status} {rec_str}")

    print("-" * 110)
    print(f"VÝSLEDKY: Top 1 Accuracy: {(top_1_hits/limit)*100:.1f}% | Top 5 Accuracy: {(top_5_hits/limit)*100:.1f}%")
    conn.close()

if __name__ == "__main__":
    # Spustíme test na 15 hrách
    run_backtest(limit=15)