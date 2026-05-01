import pandas as pd
from features.global_stats import global_pick_rate_weighted, global_ban_rate_weighted
from features.team_stats import team_preference_score
from features.player_stats import player_preference_score
from features.synergy_stats import get_synergy_score
from features.counter_stats import get_counter_score
from model.role_resolver import RoleResolver
from model.draft_engine import get_available_champions

def recommend_bans_v2_5(context, phase=1, top_n=5, weights=None):
    """
    phase 1: bany na začátku (3 na tým)
    phase 2: bany po prvním picku (2 na tým)
    """
    if weights is None:
        # Použijeme výsledky z tvé optimalizace
        if phase == 1:
            weights = [1.0, 0.0]  # Meta 100%
        else:
            weights = [0.8, 0.0, 0.2] # Meta 80%, Strat 20%
        
    available_to_ban = [c for c in context.all_champions 
                       if c not in context.fearless_unavailable 
                       and c not in context.banned_champions]
    
    df_global_bans = global_ban_rate_weighted(context.region, n_patches=2)
    ban_map = dict(zip(df_global_bans['champion'], df_global_bans['score']))

    results = []
    for champion in available_to_ban:
        # F1_F2: Meta hrozba
        f_meta = ban_map.get(champion, 0)
        
        # F3_F4: Preference soupeře (Tým + Hráč)
        f_pref_team = team_preference_score(champion, context)
        f_pref_player = player_preference_score(champion, context)
        
        # --- NOVINKA: RESPECT FACTOR ---
        # Pokud má soupeř na šampionovi extrémně vysoké WR nebo pick rate, 
        # i když šampion NENÍ v globální metě, musí se posunout nahoru.
        respect_factor = 1.0
        if f_pref_player > 0.8: # Signature pick hráče
            respect_factor = 2.0
        elif f_pref_team > 0.7: # Týmová strategie
            respect_factor = 1.5
        
        # F6_F7: Strategická hrozba (Synergie/Countery)
        f_strat = 0
        if phase == 2:
            # Ve druhé fázi nás zajímá, co soupeř může vzít k tomu, co už má
            # nebo co může vzít proti nám.
            f_strat = get_synergy_score(champion, context.enemy_picks, context.region) + \
                      get_counter_score(champion, context.allied_picks, context.region)

        # Dynamické váhy podle fáze
        if phase == 1:
            # Snížíme váhu globální mety ve prospěch "Respect banů"
            # Tím se bany začnou lišit podle toho, proti komu hraješ
            score = (f_meta * 0.9 + (f_pref_team + f_pref_player) * 0.1) * respect_factor
        else:
            # 2. fáze zůstává strategická
            f_strat = get_synergy_score(champion, context.enemy_picks, context.region)
            score = (f_meta * 0.5 + f_pref_team * 0.4 + f_strat * 0.1)

        results.append({"champion": champion, "score": score})

    return pd.DataFrame(results).sort_values(by="score", ascending=False).head(top_n)

def normalize_weights(weights):
    """Pomocná funkce pro zajištění součtu 1.0"""
    if isinstance(weights, dict):
        s = sum(weights.values())
        return {k: v / s for k, v in weights.items()}
    else:
        s = sum(weights)
        return [v / s for v in weights]
    
def recommend_champions_v2_5(context, weights=None, top_n=10):
    resolver = RoleResolver()
    if weights:
        weights = normalize_weights(weights)
     
    if weights is None:
        # Rozlišení mezi Power Picks a Counter Picks podle fáze draftu
        # (předpokládejme, že context má informaci o tom, kolikátý je to pick)
        if context.current_step < 4: # B1, B2, B3
            weights = {'meta': 0.7, 'pref': 0.3, 'strategic': 0.0}
        else: # R4, R5
            weights = {'meta': 0.5, 'pref': 0.1, 'strategic': 0.4}
               
    # 1. Zjistíme, které pozice už jsou v týmu obsazené
    occupied_positions = resolver.get_occupied_positions(context.allied_picks)
    
    # 2. Dynamické nastavení vah podle fáze draftu
    current_phase_count = len(context.allied_picks) + len(context.enemy_picks)
    if weights is None:
        if current_phase_count < 4: # Raná fáze (B1-B3)
            weights = {"meta": 0.3, "pref": 0.6, "strategic": 0.1}
        else: # Pozdní fáze (Countery a Synergie mají váhu)
            weights = {"meta": 0.2, "pref": 0.6, "strategic": 0.2}

    # 3. Získání dostupných šampionů (včetně Fearless filtru)
    available_champs = get_available_champions(
        all_champions=context.all_champions,
        banned=context.banned_champions,
        picked=context.allied_picks + context.enemy_picks,
        fearless_unavailable=context.fearless_unavailable
    )

    # --- MOŽNOST A: Hromadné načtení globálních dat ---
    # Načteme DataFramy pro všechny šampiony najednou
    df_global_picks = global_pick_rate_weighted(context.region, n_patches=2)
    df_global_bans = global_ban_rate_weighted(context.region, n_patches=2)

    # Převedeme je na slovníky {jméno: skóre} pro bleskové vyhledávání
    pick_map = dict(zip(df_global_picks['champion'], df_global_picks['score']))
    ban_map = dict(zip(df_global_bans['champion'], df_global_bans['score']))
    # --------------------------------------------------

    top_league_bans = df_global_bans.sort_values(by='score', ascending=False).head(3)['champion'].tolist()
    
    results = []

    for champion in available_champs:
        opportunity_bonus = 1.0
        if ban_map.get(champion, 0) > 0.7:
            # Čím víc je šampion "perma-ban", tím větší bonus dostane, když projde
            opportunity_bonus = 1.0 + (ban_map.get(champion, 0) * 0.5)
        
        if champion in top_league_bans and champion not in context.banned_champions:
            opportunity_bonus = 2.0  # Masivní bonus, aby se dostal na 1. místo doporučení
        
        # ROLE FILTER
        champ_roles = resolver.get_champion_positions(champion)
        is_flex = len(champ_roles) > 1
        
        # Pokud šampion hraje jen role, které jsou už obsazené, penalizujeme ho
        if all(role in occupied_positions for role in champ_roles):
            role_penalty = 0.1 if is_flex else 0.0
        else:
            role_penalty = 1.0

        if role_penalty == 0: 
            continue

        # F1 & F2: Globální data (bereme ze slovníků, co jsme načetli nahoře)
        f1 = pick_map.get(champion, 0)
        f2 = ban_map.get(champion, 0)
        f1_f2 = f1 + f2

        # F3 & F4: Preference (tým a hráč)
        f3 = team_preference_score(champion, context)
        f4 = player_preference_score(champion, context)
        f3_f4 = f3 + f4

        # F6 & F7: Strategické (Synergie a Countery)
        f6_f7 = 0
        if context.allied_picks or context.enemy_picks:
            f6_f7 = get_synergy_score(champion, context.allied_picks, context.region) + \
                    get_counter_score(champion, context.enemy_picks, context.region)
        else:
            # Na začátku draftu (B1) dáváme váhu 0, aby to neházelo abecední seznam
            f6_f7 = 0

        # Celkové skóre S(C) dle tvé diplomky
        score = (
            weights["meta"] * f1_f2 * opportunity_bonus +
            weights["pref"] * f3_f4 +
            weights["strategic"] * f6_f7
        ) * role_penalty

        results.append({
            "champion": champion,
            "score": round(score, 4),
            "is_flex": is_flex,
            "f1_f2": f1_f2,  # Ukládáme pro pozdější rozdělení
            "f3_f4": f3_f4,
            "f6_f7": f6_f7,
            "roles": champ_roles
        })

    df = pd.DataFrame(results)

    #print(get_categorized_recommendations(df))
    
    if not results:
        return pd.DataFrame(columns=["champion", "score", "is_flex", "roles"])

    return pd.DataFrame(results).sort_values(by="score", ascending=False).head(top_n)

def get_categorized_recommendations(df_results):
    """Pomocná funkce pro rozdělení výsledků do kategorií (pro UI/Analýzu)"""
    categories = {
        "Meta": df_results.sort_values(by="f1_f2", ascending=False).head(3)['champion'].tolist(),
        "Comfort": df_results.sort_values(by="f3_f4", ascending=False).head(3)['champion'].tolist(),
        "Strategic": df_results.sort_values(by="f6_f7", ascending=False).head(3)['champion'].tolist()
    }
    return categories