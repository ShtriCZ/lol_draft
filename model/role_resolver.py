from utils.patch_utils import get_connection
import pandas as pd

class RoleResolver:
    def __init__(self):
        self.conn = get_connection()
        # Načteme si mapu rolí do paměti pro rychlost
        self.role_map = pd.read_sql_query("SELECT * FROM champion_roles", self.conn)
        self.conn.close()

    def get_champion_positions(self, champion: str, threshold=0.1):
        """Vrátí seznam pozic, které šampion reálně hraje (nad x %)."""
        roles = self.role_map[self.role_map['champion'] == champion]
        valid_roles = roles[roles['percentage'] >= threshold]
        return valid_roles['position'].tolist()

    def get_occupied_positions(self, picks: list):
        """
        Pokusí se logicky přiřadit šampiony k rolím a vrátí ty, 
        které jsou už s vysokou pravděpodobností obsazené.
        """
        if not picks:
            return set()

        # 1. Zjistíme možné pozice pro každého šampiona
        possible_assignments = {p: self.get_champion_positions(p) for p in picks}
        
        # 2. Jednoduchá logika pro identifikaci obsazených rolí:
        # Pokud má šampion jen jednu možnou roli, ta je obsazená.
        occupied = set()
        for p, roles in possible_assignments.items():
            if len(roles) == 1:
                occupied.add(roles[0])
        
        # 3. TODO: Pokročilejší algoritmus pro Flex picky (např. backtracking),
        # pokud by jednoduchá logika nestačila.
        
        return occupied