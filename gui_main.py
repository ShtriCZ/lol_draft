import customtkinter as ctk
import sqlite3
import pandas as pd
from PIL import Image
import os

from gui_draft import DraftScreen
from draft_manager import DraftSession, SeriesManager
        
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("LoL Draft Analyzer - Diplomacy Edition")
        self.geometry("1200x750")

        # Databáze
        self.db_path = "data/lol_draft.db"
        
        self.title("LoL Draft Tool")
        # Nastaví minimální šířku a výšku (uprav podle svého monitoru)
        self.minsize(1200, 800)
        
        # Inicializace stavu
        
        self.series_fearless_history = []
        self.selected_league = ctk.StringVar(value="LEC")
        self.selected_series = ctk.StringVar(value="Bo1")
        self.series_manager = None # Vytvoříme ho až při startu
        
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)
        self.image_cache = {}
        
        self.show_main_menu()

    def start_new_draft(self, my_side, has_first):
        # Při vytváření nové session jí předáme nasbíranou historii
        self.current_session = DraftSession(
            "EUW", "Team A", "Team B", 
            my_side, has_first, 
            fearless_history=self.series_fearless_history
        )
        self.show_draft_screen()

    def confirm_next_game(self, my_side, has_first):
        """Tato část patří do potvrzovacího tlačítka v tvém dialogu"""
        # 1. SeriesManager vytvoří novou instanci DraftSession se starými bany
        new_session = self.series_manager.start_new_game(
            my_side=my_side, 
            has_first_pick=has_first
        )
        
        # 2. Předáme novou session do hlavní aplikace
        self.app.current_session = new_session
        
        # 3. Znovu načteme obrazovku draftu (tím se vyresetuje UI a načte nová session)
        self.app.show_draft_screen()
        
    def show_main_menu(self):
        """Úvodní obrazovka s výběrem ligy a týmů"""
        for child in self.container.winfo_children():
            child.destroy()

        frame = ctk.CTkFrame(self.container)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(frame, text="Draft Analysis Setup", font=("Roboto", 24, "bold")).pack(pady=20)

        # 1. Výběr Ligy
        ctk.CTkLabel(frame, text="Vyber ligu:").pack()
        leagues = ["LEC", "LCS", "LPL", "LCK"]
        self.league_menu = ctk.CTkOptionMenu(frame, values=leagues, variable=self.selected_league, command=self.update_teams)
        self.league_menu.pack(pady=10)

        # 2. Výběr Týmů (Dva sloupce)
        team_frame = ctk.CTkFrame(frame)
        team_frame.pack(pady=20)

        ctk.CTkLabel(team_frame, text="Tým 1 (Váš)").grid(row=0, column=0, padx=20)
        self.team1_menu = ctk.CTkOptionMenu(team_frame, values=[])
        self.team1_menu.grid(row=1, column=0, padx=20, pady=10)

        ctk.CTkLabel(team_frame, text="Tým 2 (Soupeř)").grid(row=0, column=1, padx=20)
        self.team2_menu = ctk.CTkOptionMenu(team_frame, values=[])
        self.team2_menu.grid(row=1, column=1, padx=20, pady=10)

        # 3. Formát série
        ctk.CTkLabel(frame, text="Formát série:").pack()
        ctk.CTkSegmentedButton(frame, values=["Bo1", "Bo3", "Bo5"], variable=self.selected_series).pack(pady=10)

        # Start button
        ctk.CTkButton(frame, text="ZAČÍT DRAFT", fg_color="green", hover_color="darkgreen", 
                      command=self.start_draft_session).pack(pady=30)

        # Prvotní načtení týmů
        self.update_teams(self.selected_league.get())

    def update_teams(self, league_name):
        """Načte týmy z DB podle vybrané ligy"""
        # Musíme propojit tabulky matches (kde je league) a team_drafts
        conn = sqlite3.connect(self.db_path)
        query = f"""
            SELECT DISTINCT td.teamname 
            FROM team_drafts td
            JOIN matches m ON td.gameid = m.gameid
            WHERE m.league = '{league_name}'
            ORDER BY td.teamname ASC
        """
        teams = pd.read_sql_query(query, conn)['teamname'].tolist()
        conn.close()

        self.team1_menu.configure(values=teams)
        self.team1_menu.set(teams[0] if teams else "")
        self.team2_menu.configure(values=teams)
        self.team2_menu.set(teams[1] if len(teams) > 1 else "")
        
    def get_players_for_team(self, team_name):
        """Načte unikátní hráče a jejich pozice pro daný tým"""
        conn = sqlite3.connect(self.db_path)
        # Hledáme hráče, kteří za ten tým reálně hráli
        query = f"""
            SELECT DISTINCT playername, position 
            FROM player_picks 
            WHERE teamname = ?
            ORDER BY CASE position 
                WHEN 'TOP' THEN 1 WHEN 'JNG' THEN 2 WHEN 'MID' THEN 3 
                WHEN 'ADC' THEN 4 WHEN 'SUP' THEN 5 END
        """
        df = pd.read_sql_query(query, conn, params=(team_name,))
        conn.close()
        return df

    def start_draft_session(self):
        """Příprava dat před přepnutím na lobby"""
        t1 = self.team1_menu.get()
        t2 = self.team2_menu.get()
        league = self.selected_league.get()
        bo_format = int(self.selected_series.get().replace("Bo", "")) # "Bo3" -> 3

        self.series_manager = SeriesManager(
            region=league, 
            my_team=t1, 
            enemy_team=t2, 
            format_bo=bo_format
        )

        # Načtení soupisek (to už tam máš)
        self.roster_t1 = self.get_players_for_team(t1)
        self.roster_t2 = self.get_players_for_team(t2)
        
        self.show_lobby()

    def show_lobby(self):
        for child in self.container.winfo_children():
            child.destroy()
            
        lobby_frame = ctk.CTkFrame(self.container)
        lobby_frame.pack(pady=20, padx=20, fill="both", expand=True)
        
        ctk.CTkLabel(lobby_frame, text="Příprava hry - Sestavy týmů", font=("Roboto", 20, "bold")).pack(pady=10)
        
        settings_frame = ctk.CTkFrame(lobby_frame, fg_color="transparent")
        settings_frame.pack(pady=10)

        # Výběr Blue Side
        ctk.CTkLabel(settings_frame, text="Kdo má First Pick?").grid(row=0, column=0, padx=20)
        self.side_var = ctk.StringVar(value="team1")
        ctk.CTkRadioButton(settings_frame, text=self.team1_menu.get(), variable=self.side_var, value="team1").grid(row=1, column=0)
        ctk.CTkRadioButton(settings_frame, text=self.team2_menu.get(), variable=self.side_var, value="team2").grid(row=2, column=0)

        # Výběr First Picku
        # ctk.CTkLabel(settings_frame, text="Kdo má First Pick?").grid(row=0, column=1, padx=20)
        # self.fp_var = ctk.StringVar(value="team1")
        # ctk.CTkRadioButton(settings_frame, text=self.team1_menu.get(), variable=self.fp_var, value="team1").grid(row=1, column=1)
        # ctk.CTkRadioButton(settings_frame, text=self.team2_menu.get(), variable=self.fp_var, value="team2").grid(row=2, column=1)
        
        # --- SESTAVY ---
        lists_frame = ctk.CTkFrame(lobby_frame, fg_color="transparent")
        lists_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Tým 1
        t1_f = ctk.CTkFrame(lists_frame)
        t1_f.pack(side="left", fill="both", expand=True, padx=10)
        ctk.CTkLabel(t1_f, text=self.team1_menu.get(), text_color="cyan").pack()
        for _, p in self.roster_t1.iterrows():
            ctk.CTkLabel(t1_f, text=f"{p['position']}: {p['playername']}").pack(anchor="w", padx=20)

        # Tým 2
        t2_f = ctk.CTkFrame(lists_frame)
        t2_f.pack(side="right", fill="both", expand=True, padx=10)
        ctk.CTkLabel(t2_f, text=self.team2_menu.get(), text_color="red").pack()
        for _, p in self.roster_t2.iterrows():
            ctk.CTkLabel(t2_f, text=f"{p['position']}: {p['playername']}").pack(anchor="w", padx=20)

        ctk.CTkButton(lobby_frame, text="POTVRDIT A ZAČÍT DRAFT", fg_color="green",
                      command=self.final_start_confirm).pack(pady=20)
        
    def final_start_confirm(self):
        # 1. Kdo je na jaké straně?
        # is_t1_blue je True, pokud uživatel zvolil pro Tým 1 modrou stranu
        is_t1_blue = (self.side_var.get() == "team1")

        blue_team_name = self.team1_menu.get() if is_t1_blue else self.team2_menu.get()
        red_team_name = self.team2_menu.get() if is_t1_blue else self.team1_menu.get()

        # 2. Určení strany uživatele ('my_side')
        # Pokud hraješ za Tým 1 a ten je Blue, tvoje strana je 'blue'
        my_side = 'blue' if is_t1_blue else 'red'

        # 3. Kdo má First Pick? 
        # Vynutíme logiku: Blue Side == First Pick (has_first_pick = True)
        # has_first se předává do SeriesManager.start_new_game a říká, 
        # jestli tvoje strana (my_side) má začínat.

        if my_side == 'blue':
            has_first = True
        else:
            has_first = False

        # Volitelný log pro kontrolu v konzoli
        print(f"DEBUG: Startuju draft. Side: {my_side}, Has FP: {has_first}")

        # Následuje tvůj kód pro otevření okna draftu...
        # self.launch_draft_window(my_side, has_first, blue_team_name, red_team_name)

        # 3. Uložíme si názvy týmů a soupisky pro UI draftu
        self.blue_team = blue_team_name
        self.red_team = red_team_name
        self.blue_roster = self.roster_t1 if is_t1_blue else self.roster_t2
        self.red_roster = self.roster_t2 if is_t1_blue else self.roster_t1

        self.show_draft_screen(side=my_side, has_first=has_first)
        
    def get_champion_image(self, champ_name, size=(60, 60)):
        # 1. Vyčištění jména pro název souboru
        # "Dr. Mundo" -> "DrMundo", "Kai'Sa" -> "KaiSa"
        clean_name = champ_name.replace(" ", "").replace("'", "").replace("&", "").replace("Willump","")

        # 2. Kontrola cache
        cache_key = f"{clean_name}_{size[0]}"
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]

        # 3. Cesta k souboru (používáme clean_name)
        img_path = os.path.join("assets", "champions", f"{clean_name}_0.jpg")

        try:
            if not os.path.exists(img_path):
                # Pokud obrázek neexistuje, zkusíme najít aspoň placeholder
                print(f"Obrázek nenalezen: {img_path}")
                return None

            pil_img = Image.open(img_path)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
            self.image_cache[cache_key] = ctk_img
            return ctk_img
        except Exception as e:
            print(f"Chyba při načítání obrázku {champ_name}: {e}")
            return None
        
    def show_draft_screen(self, side='blue', has_first=True):
        """Přepne z Lobby do samotného Draftu"""
        for child in self.container.winfo_children():
            child.destroy()

        # Místo ručního vytváření DraftSession použijeme SeriesManager
        # Ten automaticky přibalí fearless_history
        self.current_session = self.series_manager.start_new_game(
            my_side=side, 
            has_first_pick=has_first
        )
        
        # Pro jistotu nastavíme stranu (pokud to DraftSession vyžaduje extra)
        self.current_session.my_side = side 

        # Spuštění UI draftu
        self.draft_ui = DraftScreen(self.container, self.current_session, self)
        
if __name__ == "__main__":
    app = App()
    app.mainloop()