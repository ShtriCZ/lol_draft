import numpy as np
from scripts.comprehensive_backtest import run_comprehensive_backtest

def optimize():
    # Definujeme mřížku parametrů
    meta_steps = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    strat_steps = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
    
    best_results = {
        "bans_ph1": {"acc": 0, "cfg": None},
        "bans_ph2": {"acc": 0, "cfg": None},
        "power_picks": {"acc": 0, "cfg": None},
        "counter_picks": {"acc": 0, "cfg": None}
    }

    print("🚀 Startování hloubkové optimalizace fází...")

    for m_w in meta_steps:
        for s_w in strat_steps:
            # Zbytek do 1.0 jsou preference
            p_w = round(1.0 - m_w - s_w, 2)
            
            if p_w < 0: continue  # Neplatná kombinace (součet > 1)

            current_cfg = {
                "w_ban1": [round(m_w + s_w, 2), p_w], 
                "w_ban2": [m_w, p_w, s_w],
                "w_pick_early": {"meta": m_w, "pref": p_w, "strategic": s_w},
                "w_pick_late": {"meta": m_w, "pref": p_w, "strategic": s_w}
            }

            # --- DŮLEŽITÉ: Backtest musí být UVNITŘ obou cyklů ---
            stats = run_comprehensive_backtest(limit=50, cfg=current_cfg)
            
            # Vyhodnocení každé kategorie
            for cat in best_results.keys():
                hits = stats[cat]["hits"]
                total = stats[cat]["total"]
                acc = (hits / total * 100) if total > 0 else 0
                
                # Pokud najdeme stejnou nebo lepší přesnost, uložíme si ji
                if acc >= best_results[cat]["acc"]:
                    best_results[cat]["acc"] = acc
                    # Uložíme si konkrétní váhy pro danou kategorii
                    if cat == "bans_ph1":
                        best_results[cat]["cfg"] = current_cfg["w_ban1"]
                    elif cat == "bans_ph2":
                        best_results[cat]["cfg"] = current_cfg["w_ban2"]
                    else:
                        best_results[cat]["cfg"] = current_cfg["w_pick_early" if cat == "power_picks" else "w_pick_late"]

            # Volitelný průběžný výpis (můžeš zakomentovat, pokud je toho moc)
            # print(f"🔍 Test: Meta {m_w} | Strat {s_w} | Pref {p_w} -> Ph1 Ban: {acc:.1f}%")

    print("\n" + "🏆" * 20)
    print(" NALEZENÉ OPTIMÁLNÍ KONFIGURACE")
    print("🏆" * 20)
    for cat, data in best_results.items():
        print(f"📌 {cat.upper()}:")
        print(f"   Max Accuracy: {data['acc']:.1f}%")
        print(f"   Váhy (Meta/Pref/Strat): {data['cfg']}")
    print("=" * 40)

if __name__ == "__main__":
    optimize()