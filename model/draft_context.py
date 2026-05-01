from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DraftContext:
    region: str
    team: str
    player: Optional[str]

    allied_picks: List[str]
    enemy_picks: List[str]
    banned_champions: List[str]
    fearless_unavailable: List[str]

    game_number: int  # pro BO5 (1–5)
    all_champions: List[str]
    has_first_pick: int