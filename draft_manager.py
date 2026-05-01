import os
import json
import pandas as pd
import sqlite3
from scoring.model_v2_5 import recommend_champions_v2_5, recommend_bans_v2_5
import datetime
import copy

DRAFT_ORDER = [
    ('ban', 'blue'), ('ban', 'red'), ('ban', 'blue'), ('ban', 'red'), ('ban', 'blue'), ('ban', 'red'),
    ('pick', 'blue'), ('pick', 'red'), ('pick', 'red'), ('pick', 'blue'), ('pick', 'blue'), ('pick', 'red'),
    ('ban', 'red'), ('ban', 'blue'), ('ban', 'red'), ('ban', 'blue'),
    ('pick', 'red'), ('pick', 'blue'), ('pick', 'blue'), ('pick', 'red')
]

class DraftContext:
    """Pomocná třída, kterou tvoje modely očekávají jako vstup"""
    def __init__(self, region, allied_picks, enemy_picks, banned_champions, 
                 team, player, has_first_pick, current_step, all_champions=None):
        self.region = region
        self.allied_picks = allied_picks
        self.enemy_picks = enemy_picks
        self.banned_champions = banned_champions
        self.fearless_unavailable = []  # Pro základní verzi prázdné
        self.team = team
        self.player = player
        self.game_number = 1  # Výchozí hodnota
        self.has_first_pick = has_first_pick
        self.current_step = current_step
        self.all_champions = all_champions or []

class DraftSession:
    def __init__(self, region, my_team, enemy_team, my_side, has_first_pick, fearless_history=[], db_path="data/lol_draft.db"):
        self.db_path = db_path
        self.region = region
        self.my_team = my_team
        self.enemy_team = enemy_team
        self.my_side = my_side
        self.has_first_pick = has_first_pick
        
        self.allied_picks = []
        self.enemy_picks = []
        self.allied_bans = []
        self.enemy_bans = []
        self.bans = []
        self.draft_history = []
        self._roles_cache = {}
        
        if self.has_first_pick:
            self.starting_side = self.my_side
        else:
            self.starting_side = 'red' if self.my_side == 'blue' else 'blue'
            
        self.current_step = 0
        self.steps = self._generate_draft_steps()
        
        # Načtení seznamu všech šampionů pro model
        self.all_champs = self._load_all_champions()
        
        self.fearless_history = fearless_history
        # Do seznamu zakázaných šampionů pro tento draft přidej ty z minula
        self.unavailable_champs = set(self.fearless_history)

    def _generate_draft_steps(self):
        # 1. Vezmeme tvou základní šablonu (kde blue začíná banem i pickem)
        # DRAFT_ORDER by mělo vypadat jako: [('ban', 'blue'), ('ban', 'red'), ...]
        template = copy.deepcopy(DRAFT_ORDER)
    
        # Kdo reálně začíná?
        if self.has_first_pick:
            starting_side = self.my_side
        else:
            starting_side = 'red' if self.my_side == 'blue' else 'blue'

        # Pokud má začínat RED, prohodíme barvy v celém draftu
        if starting_side == 'red':
            new_steps = []
            for action_type, side in template:
                new_side = 'red' if side == 'blue' else 'blue'
                new_steps.append({'type': action_type, 'side': new_side})
            return new_steps

        # Pokud začíná BLUE, stačí jen převést formát na slovníky
        return [{'type': t, 'side': s} for t, s in template]

    # V draft_manager.py (třída DraftSession)
    def is_my_turn(self):
        # Standardní pořadí picků (0-19)
        # Modrá (Side 1): 0, 1, 2, 3, 4, 5 (Bany), pak 6 (Pick), 9-10, 13-14, 17, 18
        # Červená (Side 2): ... atd.

        # Jednodušší je podívat se, jak se střídají týmy v tvém poli 'steps' 
        # (pokud ho máš definované), nebo použít tuhle logiku:

        # Definice kroků, kdy vybírá Side 1 (Modrá)
        side1_steps = [0, 2, 4, 6, 9, 10, 13, 15, 17, 18]
        # Definice kroků, kdy vybírá Side 2 (Červená)
        side2_steps = [1, 3, 5, 7, 8, 11, 12, 14, 16, 19]

        if self.my_side == "blue":
            return self.current_step in side1_steps
        else:
            return self.current_step in side2_steps
    
    def get_unavailable_champions(self):
        """Vrátí množinu všech šampionů, kteří už nemohou být vybráni."""
        # Spojíme všechny bany, picky a případně historii Fearless draftu
        unavailable = set()
        unavailable.update(self.allied_bans)
        unavailable.update(self.enemy_bans)
        unavailable.update(self.allied_picks)
        unavailable.update(self.enemy_picks)

        # Pokud máš Fearless mode, přidej i historii předchozích her
        if hasattr(self, 'fearless_history') and self.fearless_history:
            unavailable.update(self.fearless_history)

        return unavailable

    def get_current_step(self):
        """Vrátí slovník s informacemi o aktuálním kroku (strana a typ)"""
        if self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None

    def _load_all_champions(self):
        json_path = os.path.join("data", "champion_list.json")
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                champs = json.load(f)
                return sorted(champs)
        except Exception as e:
            print(f"Chyba při načítání JSONu: {e}. Nouzově beru data z DB.")
            # Fallback na DB, aby aplikace nespadla, když JSON chybí
            return self._load_from_db_fallback()

    def _load_from_db_fallback(self):
        import sqlite3
        import pandas as pd
        conn = sqlite3.connect(self.db_path)
        query = "SELECT DISTINCT champion FROM champion_roles"
        champs = pd.read_sql_query(query, conn)['champion'].tolist()
        conn.close()
        return sorted(champs)

    def add_action(self, champion_name):
        step_data = self.get_current_step()
        if not step_data: return False

        side = step_data['side']
        action_type = step_data['type']
        is_allied = (side == self.my_side)

        if champion_name in self.draft_history:
            return False

        self.draft_history.append(champion_name)

        # Klíčové rozdělení - musí být striktní!
        if action_type == 'ban':
            self.bans.append(champion_name)  # PŘIDAT TENTO ŘÁDEK - plní společný seznam
            if is_allied:
                self.allied_bans.append(champion_name)
            else:
                self.enemy_bans.append(champion_name)
        elif action_type == 'pick':
            if is_allied:
                self.allied_picks.append(champion_name)
            else:
                self.enemy_picks.append(champion_name)

        self.current_step += 1
        return True
    
    def get_next_action_info(self):
        """Vrátí info pro UI z upravených kroků, ne z globální konstanty."""
        if self.current_step < len(self.steps): # Používáme self.steps!
            step = self.steps[self.current_step]
            action = step['type']
            side = step['side']
            
            who = "VÁŠ TÝM" if side == self.my_side else "SOUPEŘ"
            return f"{who} - {action.upper()}"
        return "KONEC DRAFTU"

    def is_ban_phase(self):
        """
        Určuje, zda se zrovna banuje. 
        Standardní draft: 6 banů na začátku (3+3), pak picky, pak 4 bany (2+2)
        Zjednodušeno pro UI:
        """
        # Tohle si můžeš upravit podle přesného pořadí kroků draftu (0-19)
        ban_steps = [0, 1, 2, 3, 4, 5, 12, 13, 14, 15] 
        return self.current_step in ban_steps

    def get_recommendations(self, current_player_name="Unknown"):
        ctx = DraftContext(
            region=self.region,
            allied_picks=self.allied_picks,
            enemy_picks=self.enemy_picks,
            banned_champions=self.all_bans, 
            team=self.my_team,
            player=current_player_name,
            has_first_pick=self.has_first_pick,
            current_step=self.current_step,
            all_champions=self.all_champs
        )

        if self.is_ban_phase():
            recs = recommend_bans_v2_5(ctx, phase=(1 if self.current_step < 10 else 2))
        else:
            recs = recommend_champions_v2_5(ctx)
    
        final_recs = []
        unavailable = self.all_unavailable
        my_occupied = self.get_occupied_roles(side="allied")
        enemy_occupied = self.get_occupied_roles(side="enemy")
        
        if self.is_my_turn():
            occupied = self.get_occupied_roles(side="allied")
        else:
            occupied = self.get_occupied_roles(side="enemy")

        def is_valid_recommendation(champ_name, champ_roles):
            """Dynamický filtr pro picky i bany střídající strany"""
            # 1. Šampion nesmí být v draftu (picky/bany/fearless)
            if champ_name in unavailable: 
                return False
        
            is_my_turn = self.is_my_turn()
        
            # 2. Logika pro PICKOVÁNÍ
            if not self.is_ban_phase():
                # Pokud vybírám JÁ, nekoukám na role, co už MÁM.
                # Pokud vybírá ENEMY, nekoukám na role, co už mají ONI.
                occupied_to_check = self.get_occupied_roles(side="allied" if is_my_turn else "enemy")
                return any(pos for pos in champ_roles if pos not in occupied_to_check)
        
            # 3. Logika pro BANTOVÁNÍ
            else:
                # Fáze 1 (prvních 6 banů): Tady se role tolik neřeší (banují se OP šampioni)
                if self.current_step < 6:
                    return True
                    
                # Fáze 2 (Bany po prvních pickách):
                # Tady chceme banovat to, co DRUHÝ tým ještě NEMÁ picknuté.
                if is_my_turn:
                    # Já banuju proti ENEMY (chci banovat to, co jim chybí)
                    target_occupied = self.get_occupied_roles(side="enemy")
                else:
                    # Enemy banuje proti MNĚ (chce banovat to, co chybí mně)
                    target_occupied = self.get_occupied_roles(side="allied")
        
                # Ban dává smysl, pokud šampion může jít na linku, která u soupeře/mě ještě není obsazená
                can_hurt_other_team = any(pos for pos in champ_roles if pos not in target_occupied)
                return can_hurt_other_team

        # 2. Zpracování doporučení od modelu
        if recs is not None and not recs.empty:
            for _, row in recs.iterrows():
                champ = row['champion']
                roles = self.get_champion_roles(champ)

                if is_valid_recommendation(champ, roles):
                    target = [r for r in roles if r not in occupied][0] if not self.is_ban_phase() else "BAN"
                    final_recs.append({'champion': champ, 'score': row['score'], 'roles': roles, 'target': target})

                # ZMĚNA: Tady dej třeba 15, v GUI se i tak zobrazí jen první 3
                if len(final_recs) >= 15: break 

        # 3. FALLBACK
        if len(final_recs) < 15:
            for champ in self.all_champs:
                if len(final_recs) >= 15: break

        # 3. FALLBACK
        if len(final_recs) < 5:
            for champ in self.all_champs:
                if len(final_recs) >= 5: break
                if any(r['champion'] == champ for r in final_recs): continue

                roles = self.get_champion_roles(champ)
                if is_valid_recommendation(champ, roles):
                    target = [r for r in roles if r not in occupied][0] if not self.is_ban_phase() else "BAN"
                    final_recs.append({'champion': champ, 'score': 0.0, 'roles': roles, 'target': target})

        return pd.DataFrame(final_recs).reset_index(drop=True)
    
    def get_champion_roles(self, champ_name):
        if champ_name in self._roles_cache:
            return self._roles_cache[champ_name]

        try:
            conn = sqlite3.connect(self.db_path)
            # 1. Vytáhneme pozici i četnost (např. počet her na dané pozici)
            query = "SELECT position, play_count FROM champion_roles WHERE champion = ?"
            res = pd.read_sql_query(query, conn, params=(champ_name,))
            conn.close()

            if res.empty:
                return []

            # 2. Výpočet procentuálního zastoupení
            total_games = res['play_count'].sum()
            res['percentage'] = res['play_count'] / total_games

            # 3. LOGIKA FILTROVÁNÍ:
            # Pokud má nejhranější role víc než 95 %, vezmeme jen tu jednu (není to flex)
            top_role_row = res.loc[res['percentage'].idxmax()]

            if top_role_row['percentage'] >= 0.95:
                roles = [top_role_row['position']]
            else:
                # Jinak je to flex - vezmeme všechny role, co mají alespoň 5 %
                roles = res[res['percentage'] >= 0.05]['position'].tolist()

            self._roles_cache[champ_name] = roles 
            return roles
        except Exception as e:
            print(f"Chyba při zjišťování rolí pro {champ_name}: {e}")
            return []

    def get_occupied_roles(self, side="allied"):
        picks = self.allied_picks if side == "allied" else self.enemy_picks
        occupied = set()

        # Seřadíme picky tak, aby šampioni s jednou rolí (např. ADC) 
        # obsadili linku jako první, a flexi až pak.
        sorted_picks = sorted(picks, key=lambda c: len(self.get_champion_roles(c)))

        for champ in sorted_picks:
            positions = self.get_champion_roles(champ)
            # Najdeme první pozici šampiona, která ještě není v týmu obsazená
            for p in positions:
                if p not in occupied:
                    occupied.add(p)
                    break # Šampion obsadil jednu linku, jdeme na dalšího
        return occupied
    
    
    def export_log(self):
        """Bod C: Export dat pro diplomku"""
        filename = f"draft_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"DRAFT LOG: {self.my_team} vs {self.enemy_team}\n")
            f.write(f"Region: {self.region}, Side: {self.my_side}\n")
            f.write("-" * 30 + "\n")
            f.write(f"Bans: {', '.join(self.bans)}\n")
            f.write(f"Allied Picks: {', '.join(self.allied_picks)}\n")
            f.write(f"Enemy Picks: {', '.join(self.enemy_picks)}\n")
        print(f"Log uložen do {filename}")
        
    def get_champion_role(self, champ_name):
        # Tohle by mělo sahat do tvé tabulky champion_roles
        conn = sqlite3.connect(self.db_path)
        query = "SELECT position FROM champion_roles WHERE champion = ?"
        res = pd.read_sql_query(query, conn, params=(champ_name,))
        conn.close()
        return res['position'].tolist() if not res.empty else []
        
    @property
    def all_bans(self):
        """Vrátí spojený seznam všech banů (vlastních i soupeřových)"""
        return self.allied_bans + self.enemy_bans

    @property
    def all_unavailable(self):
        """Vrátí vše, co už nemůže být vybráno (bany + picky + fearless historie)"""
        return self.all_bans + self.allied_picks + self.enemy_picks + self.fearless_history
class SeriesManager:
    def __init__(self, region, my_team, enemy_team, format_bo=1):
        self.region = region
        self.my_team = my_team
        self.enemy_team = enemy_team
        self.format_bo = format_bo # 1, 3, nebo 5
        self.games_history = []
        self.fearless_unavailable = set()
        self.current_game_num = 1
        self.games_played = 0
        self.scores = {"blue": 0, "red": 0}

    def start_new_game(self, my_side, has_first_pick):
        self.games_played += 1
        return DraftSession(
            region=self.region,
            my_team=self.my_team,
            enemy_team=self.enemy_team,
            my_side=my_side,
            has_first_pick=has_first_pick,
            fearless_history=list(self.games_history)
        )

    def is_series_over(self):
        """Vrátí True, pokud série dosáhla maximálního počtu her."""
        # Např. v Bo3 je max 3 hry, v Bo5 max 5 her
        if self.games_played >= self.format_bo:
            return True
        
        # Volitelně: Můžeš přidat logiku pro vítězství (např. 2-0 v Bo3)
        # wins_needed = (self.format_bo // 2) + 1
        # if self.scores["blue"] >= wins_needed or self.scores["red"] >= wins_needed:
        #     return True

        return False
    
    def finish_game(self, allied_picks, enemy_picks):
        # Přidání šampionů do celkové historie série (fearless_unavailable)
        # Použijeme list, který předáváme do DraftSession jako fearless_history
        self.games_history.extend(allied_picks)
        self.games_history.extend(enemy_picks)

        #self.games_played += 1
        #self.current_game_num += 1