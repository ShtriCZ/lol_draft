class SeriesManager:
    def __init__(self, match_format="BO5"):
        self.match_format = match_format
        self.game_number = 1
        self.series_score = {"team_allied": 0, "team_enemy": 0}
        self.used_champions = set()  # Pro Fearless draft

    def record_game_result(self, winner_is_allied: bool, played_champions: list):
        """Uloží výsledek hry a zablokuje šampiony pro Fearless."""
        if winner_is_allied:
            self.series_score["team_allied"] += 1
        else:
            self.series_score["team_enemy"] += 1
            
        self.game_number += 1
        self.used_champions.update(played_champions)

    def get_unavailable_champions(self):
        return list(self.used_champions)