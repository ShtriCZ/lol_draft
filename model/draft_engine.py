def get_available_champions(
    all_champions: list[str],
    banned: list[str],
    picked: list[str],
    fearless_unavailable: list[str]
) -> list[str]:
    """
    Vrátí seznam dostupných šampionů
    po odečtení banů, picků a fearless omezení.
    """

    unavailable = set(banned) | set(picked) | set(fearless_unavailable)

    return [c for c in all_champions if c not in unavailable]