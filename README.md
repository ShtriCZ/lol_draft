# README – DraftAnalyzer pro League of Legends

Tato aplikace slouží k pokročilé analýze a predikci draftů (fází výběru a zákazů šampionů) v profesionálních turnajích hry League of Legends. Systém využívá historická data z let 2026 k výpočtu synergií, counter-picků a celkové síly týmové kompozice.

## 1. Požadavky (Prerekvizity)

- **Python 3.12** (testováno na této verzi)
- Knihovny uvedené v souboru `requirements.txt`

## 2. Instalace a spuštění

1.  **Instalace potřebných knihoven:**
    Otevřete terminál (příkazový řádek) v kořenovém adresáři projektu a spusťte:

    ```bash
    pip install -r requirements.txt
    ```

2.  **Spuštění aplikace (GUI):**
    Hlavní grafické uživatelské rozhraní spustíte příkazem:
    ```bash
    python gui_main.py
    ```

## 3. Struktura projektu

Projekt je strukturován do modulů pro zajištění přehlednosti a oddělení logiky od dat:

- **`data/`** – Obsahuje SQLite databáze (`lol_draft.db`) a surová data z Oracle's Elixir (CSV).
- **`features/`** – Výpočetní moduly pro statistiky (Win Rate týmů, hráčů, synergie a counter-stats).
- **`model/`** – Jádro aplikace zajišťující logiku draftu, engine pro doporučování a přiřazování rolí.
- **`scoring/`** – Implementace matematických modelů (v1 až v2.5) pro evaluaci kvality draftu.
- **`scripts/`** – Nástroje pro backtesting modelu a optimalizaci vah metrik.
- **`utils/`** – Pomocné skripty, např. pro správu herních patchů.
- **`gui_main.py` & `gui_draft.py`** – Hlavní spouštěcí soubory uživatelského rozhraní.

## 4. Klíčové funkcionality pro testování

Pro ověření funkčnosti doporučuji zaměřit pozornost na:

1.  **Interaktivní analýza:** Spuštěním `gui_main.py` získáte přístup k simulátoru draftu, který v reálném čase reaguje na volby šampionů.
2.  **Ověření modelu (Backtesting):** Skript `scripts/comprehensive_backtest.py` demonstruje predikční schopnosti modelu na historických datech.
3.  **Zpracování dat:** Moduly `import_to_sqlite.py` a `filter_dataset.py` v kořenovém adresáři dokumentují proces transformace dat.

## 5. Technická poznámka

Pro účely akademické kontroly a transparentnosti doporučuji spouštět aplikaci přímo ze zdrojových kódů Python (viz sekce 2) nebo vytvořit .exe soubor. Veškerá data jsou uložena lokálně v přiložené SQLite databázi, není vyžadováno externí API připojení.
