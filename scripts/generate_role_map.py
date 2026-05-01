import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path("data/lol_draft.db")

def generate_role_map():
    conn = sqlite3.connect(DB_PATH)
    
    # SQL dotaz, který spočítá výskyty šampiona na každé pozici
    query = """
        SELECT 
            champion, 
            position, 
            COUNT(*) as play_count
        FROM player_picks
        GROUP BY champion, position
    """
    
    df = pd.read_sql_query(query, conn)
    
    # Výpočet procentuálního zastoupení role pro každého šampiona
    total_counts = df.groupby('champion')['play_count'].transform('sum')
    df['percentage'] = df['play_count'] / total_counts
    
    # Vytvoření tabulky v DB
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS champion_roles")
    cursor.execute("""
        CREATE TABLE champion_roles (
            champion TEXT,
            position TEXT,
            percentage REAL,
            play_count INTEGER
        )
    """)
    
    df.to_sql("champion_roles", conn, if_exists="append", index=False)
    
    # Přidání indexu pro rychlé hledání
    cursor.execute("CREATE INDEX idx_champ_role ON champion_roles(champion)")
    
    conn.commit()
    conn.close()
    print("✅ Mapa rolí šampionů byla úspěšně vygenerována.")

if __name__ == "__main__":
    generate_role_map()