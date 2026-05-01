import customtkinter as ctk
from PIL import Image
import os
from draft_manager import DRAFT_ORDER
import pandas as pd

class DraftScreen(ctk.CTkFrame):
    def __init__(self, parent, session_manager, app_instance):
        super().__init__(parent)
        self.session = session_manager  # Instance DraftSession
        self.app = app_instance        # Přístup k funkcím hlavní aplikace (např. get_champion_image)
        
        self.pack(fill="both", expand=True)
        
        # Konfigurace layoutu (3 sloupce: Allied, Center, Enemy)
        self.grid_columnconfigure(0, weight=1) # Allied
        self.grid_columnconfigure(1, weight=3) # Center (Champions)
        self.grid_columnconfigure(2, weight=1) # Enemy
        self.grid_rowconfigure(1, weight=1)    # Hlavní obsah

        self.setup_ui()

    def setup_ui(self):
       # 1. NEJDŘÍVE DEFINUJEME RÁMY (Kontejnery)
        # Horní lišta pro bany
        self.ban_frame = ctk.CTkFrame(self, height=80)
        self.ban_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
        
        # Postranní panely pro picky
        self.left_panel = ctk.CTkFrame(self, width=80, fg_color="#1a2b3c")
        self.left_panel.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        self.right_panel = ctk.CTkFrame(self, width=80, fg_color="#3c1a1a")
        self.right_panel.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)

        # Středový panel pro výběr
        self.center_frame = ctk.CTkFrame(self)
        self.center_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
            
        self.status_label = ctk.CTkLabel(
            self.center_frame, 
            text="ZAČÍNÁME DRAFT", 
            font=("Roboto", 16, "bold"),
            text_color="yellow"
        )
        self.status_label.pack(pady=10)
        
        # 2. TEĎ TEPRVE VYTVÁŘÍME SLOTY (Už mají kam patřit)
        self.allied_ban_slots = []
        self.enemy_ban_slots = []
        self.left_pick_slots = []
        self.right_pick_slots = []
        for i in range(5):
            # Teď už self.ban_frame existuje, takže to nehodí chybu
            lbl = ctk.CTkLabel(self.ban_frame, text="", width=45, height=45, fg_color="#333", corner_radius=5)
            lbl.pack(side="left", padx=5, pady=10)
            self.allied_ban_slots.append(lbl)
            
        for i in range(5):
            lbl = ctk.CTkLabel(self.ban_frame, text="", width=45, height=45, fg_color="#333", corner_radius=5)
            lbl.pack(side="right", padx=5, pady=10)
            self.enemy_ban_slots.append(lbl)
            
        ctk.CTkLabel(self.left_panel, text=self.app.blue_team, 
                     font=("Roboto", 18, "bold"), text_color="cyan").grid(row=0, column=0, pady=0, sticky="ew")
        ctk.CTkLabel(self.right_panel, text=self.app.red_team, 
                     font=("Roboto", 18, "bold"), text_color="red").grid(row=0, column=0, pady=0, sticky="ew")
        
        self.left_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)
        
        # SLOTY PRO PICKY SE JMÉNY HRÁČŮ
        for i in range(5):
            # Získáme jméno hráče z uložené soupisky
            try:
                p_blue = self.app.blue_roster.iloc[i]['playername']
            except (IndexError, AttributeError):
                p_blue = f"Player {i+1}"
            try:
                p_red = self.app.red_roster.iloc[i]['playername']
            except (IndexError, AttributeError):
                p_red = f"Player {i+1}"

            # --- LEVÁ STRANA (BLUE) ---
            # Kontejner pro jeden slot (ikona + jméno)
            blue_slot_container = ctk.CTkFrame(self.left_panel, fg_color="transparent")
            blue_slot_container.grid(row=i+1, column=0, pady=0, sticky="ew")
            blue_slot_container.grid_columnconfigure(0, weight=1)

            # 1. Samotná dlaždice pro ikonu šampiona
            blue_icon_tile = ctk.CTkFrame(blue_slot_container, width=80, height=80, fg_color="#222", corner_radius=4)
            blue_icon_tile.pack_propagate(False)
            blue_icon_tile.pack(pady=(0, 2)) # Malý odstup od textu dole
            self.left_pick_slots.append(blue_icon_tile) # Do seznamu ukládáme jen tu dlaždici

            # 2. Label pro jméno hráče pod ikonou
            p_blue = self.app.blue_roster.iloc[i]['playername'] if i < len(self.app.blue_roster) else f"Player {i+1}"
            blue_name_label = ctk.CTkLabel(blue_slot_container, text=p_blue, font=("Roboto", 11, "bold"), text_color="white")
            blue_name_label.pack()
            # Uložíme si odkaz na label, abychom ho mohli později měnit (např. přidat název šampiona)
            # self.left_name_labels.append(blue_name_label) # Pokud si vytvoříš tento seznam v __init__


            # --- PRAVÁ STRANA (RED) ---
            red_slot_container = ctk.CTkFrame(self.right_panel, fg_color="transparent")
            red_slot_container.grid(row=i+1, column=0, pady=0, sticky="ew")
            red_slot_container.grid_columnconfigure(0, weight=1)

            red_icon_tile = ctk.CTkFrame(red_slot_container, width=80, height=80, fg_color="#222", corner_radius=4)
            red_icon_tile.pack_propagate(False)
            red_icon_tile.pack(pady=(0, 2))
            self.right_pick_slots.append(red_icon_tile)

            p_red = self.app.red_roster.iloc[i]['playername'] if i < len(self.app.red_roster) else f"Player {i+1}"
            red_name_label = ctk.CTkLabel(red_slot_container, text=p_red, font=("Roboto", 11, "bold"), text_color="white")
            red_name_label.pack()
            
        # --- STŘED (VÝBĚR ŠAMPIONŮ) ---
        self.center_frame = ctk.CTkFrame(self)
        self.center_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        
        # Vyhledávání
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.filter_champions)
        self.search_entry = ctk.CTkEntry(self.center_frame, placeholder_text="Hledej šampiona...", textvariable=self.search_var)
        self.search_entry.pack(fill="x", padx=5, pady=5)

        # Scrollable mřížka
        self.scroll_canvas = ctk.CTkScrollableFrame(self.center_frame)
        self.scroll_canvas.bind("<Configure>", self.on_resize)
        self.scroll_canvas.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.champion_buttons = {}
        self.render_champion_grid()

        # --- SPODNÍ LIŠTA (AI RADY) ---
        self.ai_frame = ctk.CTkFrame(self, height=150, fg_color="#222")
        self.ai_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
        
        self.rec_cards = []
        for i in range(5):
            card = ctk.CTkFrame(self.ai_frame, width=250, height=120, fg_color="#333")
            card.pack(side="left", expand=True, padx=5, pady=5)
            self.rec_cards.append(card)
            
        self.update_recommendations()
        
        self.fearless_frame = ctk.CTkFrame(self.center_frame, height=40)
        self.fearless_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(self.fearless_frame, text="Fearless Bans:", font=("Roboto", 10)).pack(side="left", padx=5)

        # V refresh_draft_visuals pak tyhle šampiony vykresli jako malé šedé ikonky
        for champ in self.session.fearless_history:
            img = self.app.get_champion_image(champ, size=(25, 25))
            ctk.CTkLabel(self.fearless_frame, image=img, text="").pack(side="left", padx=2)
            
        # V gui_draft.py -> setup_ui
        self.next_game_btn = ctk.CTkButton(
        self.center_frame, 
        text="DALŠÍ HRA V SÉRII", 
        command=self.go_to_next_game,
        fg_color="green"
        )
    
    # V gui_draft.py (uvnitř třídy DraftScreen)
    def go_to_next_game(self):
        # 1. Uložíme výsledky aktuální hry do historie série
        self.app.series_manager.finish_game(
            allied_picks=self.session.allied_picks,
            enemy_picks=self.session.enemy_picks
        )
    
        # 2. Exportujeme log pro diplomku (volitelné, ale doporučené)
        self.session.export_log()

        # 3. Vrátíme se do Lobby, aby si uživatel mohl vybrat stranu pro další hru
        # (V profi scéně si strany vybírá poražený tým)
        self.app.show_lobby()

    def update_ui_after_pick(self, side, champ_name):
        """Aktualizuje správný prvek v UI (Pick slot nebo Ban slot)"""
        # 1. Zjistíme, co to bylo za akci (musíme se podívat na krok ZPĚT, 
        # protože add_action už posunul current_step dopředu)
        last_step_index = self.session.current_step - 1
        if last_step_index < 0: return
        
        last_step = self.session.steps[last_step_index]
        action_type = last_step['type']

        if action_type == 'pick':
            # Zjistíme kolikátý pick dané strany to je (0-4)
            # Pokud side=='blue', spočítáme kolik má blue_picks a odečteme 1 (protože už je tam uložen)
            pick_index = (len(self.session.allied_picks) if side == self.session.my_side 
                          else len(self.session.enemy_picks)) - 1
            
            # Voláme tu tvou metodu pro vykreslení ikony do dlaždice
            self.update_slot_with_champion(pick_index, side, champ_name)
            
        elif action_type == 'ban':
            # Tady by měla být logika pro vykreslení banů (ty malé ikonky)
            # Pokud bany zatím jen loguješ a nevykresluješ, nech to prázdné
            print(f"BAN: {side} zakázal {champ_name}")
            # self.render_bans() # <-- tuhle si můžeš dodělat později
            
    def update_slot_with_champion(self, slot_index, side, champ_name):
        """Aktualizuje dlaždici šampiona: vloží ikonu přes celou plochu a smaže provizorní text."""
        # 1. Výběr správného seznamu slotů (dlaždic)
        slots = self.left_pick_slots if side == 'blue' else self.right_pick_slots
        
        # Bezpečnostní kontrola indexu
        if slot_index < 0 or slot_index >= len(slots):
            return

        tile = slots[slot_index]

        # 2. Vyčištění vnitřku dlaždice (smaže text "Player X")
        for child in tile.winfo_children():
            child.destroy()

        # 3. Načtení obrázku ve velikosti dlaždice (předpokládám 80x80 dle setup_ui)
        img = self.app.get_champion_image(champ_name, size=(80, 80))

        if img:
            # 4. Vytvoření labelu jen pro obrázek a roztažení přes celou plochu
            img_label = ctk.CTkLabel(tile, image=img, text="")
            img_label.place(relx=0, rely=0, relwidth=1, relheight=1)
            
            # Nastavíme průhledné pozadí framu, aby vynikla ikona
            tile.configure(fg_color="transparent")
        else:
            # Fallback pokud obrázek neexistuje (vypíše jméno šampiona textem)
            fallback_lbl = ctk.CTkLabel(tile, text=champ_name, font=("Roboto", 10))
            fallback_lbl.place(relx=0.5, rely=0.5, anchor="center")
            
    def update_status_indicator(self):
        # Ochrana proti IndexError: pokud už není další krok, draft skončil
        # V gui_draft.py -> update_status_indicator
        if self.session.current_step >= len(self.session.steps):
            self.status_label.configure(text="DRAFT DOKONČEN", text_color="gold")

            # Kontrola, jestli série pokračuje
            if not self.app.series_manager.is_series_over():
                self.update_recommendations()
                # Ještě zbývají hry (zobrazíme zelené tlačítko)
                self.next_game_btn.configure(text=f"DALŠÍ HRA")
                self.next_game_btn.pack(pady=20)
            else:
                self.update_recommendations()
                # Série skončila (zobrazíme tlačítko pro návrat do menu)
                self.finish_series_btn = ctk.CTkButton(
                    self.center_frame,
                    text="UKONČIT SÉRII",
                    fg_color="red",
                    command=self.finish_entire_series
                )
                self.finish_series_btn.pack(pady=20)
            return

        # Teď je bezpečné přistoupit k indexu
        current_step_data = self.session.steps[self.session.current_step]
        active_side = current_step_data['side']
        action_type = current_step_data['type']

        team_name = self.app.blue_team if active_side == 'blue' else self.app.red_team
        color = "cyan" if active_side == 'blue' else "red"

        self.status_label.configure(
            text=f"NA ŘADĚ: {team_name} ({action_type.upper()})",
            text_color=color
        )

    def finish_entire_series(self):
        # 1. Poslední export logu
        self.session.export_log()

        # 2. Resetování SeriesManageru v hlavní aplikaci
        self.app.series_manager = None
        self.app.series_fearless_history = []

        # 3. Návrat do úplně prvního menu
        self.app.show_main_menu()

    def on_resize(self, event):
        # Ignoruj malé změny
        if hasattr(self, '_last_width') and abs(self._last_width - event.width) < 20:
            return
        self._last_width = event.width

        # Zruš předchozí plán, pokud uživatel stále táhne za roh okna
        if hasattr(self, '_resize_timer'):
            self.after_cancel(self._resize_timer)
        
        # Spusť to až 200ms poté, co uživatel přestane hýbat s oknem
        self._resize_timer = self.after(200, self.delayed_resize)

    def delayed_resize(self):
        """Tato funkce se spustí až po zastavení tahání za okno"""
        self.render_champion_grid(self.search_var.get())
        
    def render_champion_grid(self, filter_text=""):
        # Získání šířky - pokud je okno čerstvé, zkusíme update_idletasks
        self.scroll_canvas.update_idletasks()
        self.scroll_canvas._parent_canvas.configure(scrollregion=self.scroll_canvas._parent_canvas.bbox("all"))
        
        container_width = self.scroll_canvas.winfo_width()

        # Pokud je šířka příliš malá (při startu), použijeme odhad nebo vyskočíme
        if container_width < 50:
            return
        
        fearless = getattr(self.session, 'fearless_history', [])
                    
        # Vyčištění mřížky
        for btn in self.champion_buttons.values():
            btn.destroy()
        self.champion_buttons = {}
            
        button_width = 70  # Šířka tlačítka (60) + padding (5+5)
        max_cols = max(1, (container_width-50) // button_width)
        
        row, col = 0, 0
        unavailable = self.session.all_unavailable
        
        # Seřadíme šampiony abecedně
        for champ in sorted(self.session.all_champs):
            if filter_text.lower() in champ.lower():
                img = self.app.get_champion_image(champ, size=(50, 50))
                
                btn = ctk.CTkButton(self.scroll_canvas, text=champ if not img else "", 
                                   image=img, width=60, height=60, 
                                   fg_color="transparent", hover_color="#444",
                                   command=lambda c=champ: self.handle_click(c))
                btn.grid(row=row, column=col, padx=5, pady=5)
                self.champion_buttons[champ] = btn
                
                if champ in self.session.all_bans or champ in self.session.allied_picks or champ in self.session.enemy_picks or champ in unavailable:
                    btn.configure(state="disabled", fg_color="#222")

                btn.grid(row=row, column=col, padx=5, pady=5)
                self.champion_buttons[champ] = btn
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
                    
        self.scroll_canvas._parent_canvas.yview_moveto(0) # Volitelné: vrátí scroll nahoru při novém hledání

    def complete_game_and_save_history(self):
        """Uloží hru a vrátí nás do Lobby pro další hru v sérii"""
        # 1. Uložení dat do SeriesManageru
        allied = self.session.allied_picks
        enemy = self.session.enemy_picks
        self.app.series_manager.finish_game(allied, enemy)
        
        # Aktualizace historie pro start_new_game
        self.app.series_manager.games_history = list(self.app.series_manager.fearless_unavailable)
        
        # 2. Místo vyskakovacího okna zavoláme přímo Lobby v hlavním okně
        # To umožní znovu vybrat strany pro hru č. 2, 3...
        self.app.show_lobby()
        
    def filter_champions(self, *args):
        self.render_champion_grid(self.search_var.get())

    def handle_click(self, champ_name):
        """Bod A: Propojení kliknutí s logikou a vizuálem"""
        
        current_step_data = self.session.get_current_step() # Vytvoř si tuhle pomocnou funkci
        
        if current_step_data is None:
            print("Draft už skončil, nelze vybírat další šampiony.")
            return
    
        side = current_step_data['side']
        
        success = self.session.add_action(champ_name)
        
        if success:
            # UI update - ikona se vykreslí na správnou stranu (Blue/Red)
            # nezávisle na tom, kdo začínal
            self.update_ui_after_pick(side, champ_name)
            self.update_status_indicator()
            
        # Kontrola, jestli už draft neskončil
        if self.session.current_step >= len(DRAFT_ORDER):
            print("Draft již skončil.")
            return

        # 1. Zjistíme, co je to za akci, Z TOHO SPRÁVNÉHO SEZNAMU
        action_type, side = DRAFT_ORDER[self.session.current_step]
        
        # 2. Provedeme akci v logice (tato metoda v manageru už ví, co má dělat)
        self.session.add_action(champ_name)
        
        # 3. Aktualizujeme vizuály
        self.refresh_draft_visuals()
        self.update_recommendations()
        
        # 4. Zablokujeme tlačítko
        if champ_name in self.champion_buttons:
            self.champion_buttons[champ_name].configure(state="disabled", fg_color="#222")


    def refresh_draft_visuals(self):
        # Resetování lokálních indexů pro vykreslování
        b_ban_i, r_ban_i = 0, 0
        b_pick_i, r_pick_i = 0, 0

        # Kontrola, zda historie vůbec existuje
        if not hasattr(self.session, 'draft_history') or not self.session.draft_history:
            return

        # Procházíme historii krok po kroku
        for i in range(len(self.session.draft_history)):
            if i >= len(DRAFT_ORDER): 
                break
            
            action_type, side = DRAFT_ORDER[i]
            champ_name = self.session.draft_history[i]
            img = self.app.get_champion_image(champ_name, size=(45, 45))
            pick_img = self.app.get_champion_image(champ_name, size=(80, 80))

            if action_type == "ban":
                if side == "blue":
                    # OCHRANA: Máme jen 5 slotů (index 0-4)
                    if b_ban_i < len(self.allied_ban_slots):
                        self.allied_ban_slots[b_ban_i].configure(image=img, text="")
                        b_ban_i += 1
                else:
                    if r_ban_i < len(self.enemy_ban_slots):
                        self.enemy_ban_slots[r_ban_i].configure(image=img, text="")
                        r_ban_i += 1
                        
            elif action_type == "pick":
                # Zjistíme, jestli tento pick v historii patří Blue nebo Red straně
                # V LoL draftu jde Blue vždy vlevo a Red vždy vpravo (standardní zobrazení)
                if side == "blue":
                    if b_pick_i < len(self.left_pick_slots):
                        self.update_slot_with_champion(i, 'blue', champ_name)
                        b_pick_i += 1
                else:
                    if r_pick_i < len(self.right_pick_slots):
                        self.update_slot_with_champion(i, 'red', champ_name)
                        r_pick_i += 1

        # Aktualizace placeholderu pro další tah
        next_info = self.session.get_next_action_info()
        self.search_entry.configure(placeholder_text=f"NA ŘADĚ: {next_info}")
        
        if self.session.current_step >= len(DRAFT_ORDER):
            self.show_next_game_button()
            self.update_recommendations()
        
    def update_recommendations(self):
        if self.session.current_step >= len(DRAFT_ORDER):
            print("KONEC")
            # Vyčistíme všechny 3 karty, aby byly prázdné
            for card in self.rec_cards:
                for child in card.winfo_children():
                    child.destroy()            

            # Pokud máš karty v nějakém hlavním rámu (např. self.rec_frame), můžeš ho schovat celý:
            # self.rec_frame.pack_forget() 
            return
        try:
            # Získání dat
            recs = self.session.get_recommendations()
            my_occupied = self.session.get_occupied_roles("allied")
            enemy_occupied = self.session.get_occupied_roles("enemy")
            
            # 1. Výpis obsazených pozic (vizuální kontrola pro tebe)
            # Předpokládám, že máš v GUI nějaký status label, nebo ho vytvoř:
            status_text = f"Naše pozice: {', '.join(my_occupied) if my_occupied else 'Žádné'}"
            if hasattr(self, 'status_label'):
                self.status_label.configure(text=status_text)
            else:
                print(status_text) # Aspoň do konzole
    
            for i in range(5):
                card = self.rec_cards[i]
                for child in card.winfo_children(): child.destroy()
    
                if i < len(recs):
                    row = recs.iloc[i]
                    champ = row['champion']
                    roles = row['roles']
                    
                    # Zobrazení karty
                    img = self.app.get_champion_image(champ, size=(80, 80))
                    ctk.CTkLabel(card, image=img, text="").pack(pady=2)
                    ctk.CTkLabel(card, text=champ, font=("Roboto", 11, "bold")).pack()
                        
                    handler = lambda e, c=champ: self.handle_click(c)
                    card.bind("<Button-1>", handler)
                    # Důležité: hromadný bind na děti pro plynulost
                    for child in card.winfo_children(): child.bind("<Button-1>", handler)
                else:
                    ctk.CTkLabel(card, text="---").pack(expand=True)
                    
        except Exception as e:
            print(f"Chyba v UI: {e}")
                
    def show_draft_screen(self, side='blue', has_first=True):
        for child in self.container.winfo_children():
            child.destroy()

        # Vytvoření session skrze manažera se správnými parametry
        self.current_session = self.series_manager.start_new_game(
            my_side=side,        # 'blue' nebo 'red'
            has_first_pick=has_first
        )
        
        # Důležité: Synchronizace strany v session objektu
        self.current_session.my_side = side 

        # Spuštění UI
        self.draft_ui = DraftScreen(self.container, self.current_session, self)
        
    def show_next_game_button(self):
        # Vyčistíme spodní AI panel a dáme tam tlačítko
        for child in self.ai_frame.winfo_children():
            child.destroy()
            
        next_btn = ctk.CTkButton(
            self.ai_frame, 
            text="UKONČIT HRU A PŘEJÍT NA DALŠÍ DRAFT",
            fg_color="green",
            hover_color="#218838",
            height=50,
            font=("Roboto", 16, "bold"),
            command=self.complete_game_and_save_history # Volání naší funkce
        )
        next_btn.pack(expand=True, pady=20)
        
    def setup_next_game_config(self):
        # Uložíme aktuální picky do fearless banů v SeriesManageru
        all_picks = self.session.allied_picks + self.session.enemy_picks
        self.app.series_fearless_history.extend(all_picks)
        
        # Vytvoříme malé okno/overlay pro výběr stran
        config_win = ctk.CTkToplevel(self)
        config_win.title("Nastavení další hry")
        config_win.geometry("300x250")
        config_win.attributes("-topmost", True) # Aby bylo vidět nahoře

        ctk.CTkLabel(config_win, text="Vyber stranu pro váš tým:").pack(pady=10)
        side_var = ctk.StringVar(value="blue")
        ctk.CTkRadioButton(config_win, text="Blue Side", variable=side_var, value="blue").pack()
        ctk.CTkRadioButton(config_win, text="Red Side", variable=side_var, value="red").pack()

        def confirm():
            my_side = side_var.get()
            # Pokud je side blue, obvykle má first pick (nebo podle pravidla ligy)
            has_first = True if my_side == "blue" else False 
            
            config_win.destroy()
            # Spustíme nový draft skrze hlavní aplikaci
            self.app.start_new_series_game(my_side, has_first)

        ctk.CTkButton(config_win, text="START DRAFT", command=confirm).pack(pady=20)