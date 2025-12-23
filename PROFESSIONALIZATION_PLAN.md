# Plan profesjonalizacji projektu `monopolyv3`

Ten dokument opisuje zmiany, które należy wprowadzić, aby projekt wyglądał jak utrzymywany w dojrzałej organizacji (np. Google). Zmiany są pogrupowane tematycznie, z priorytetem **Wysoki/Średni/Niski**.

## 1. Podstawy projektu i konfiguracja

- **[Wysoki] Uporządkować strukturę pakietu `src`**
  - Upewnić się, że repo jest instalowane jako pakiet (np. `pip install -e .`) zamiast polegania na `PYTHONPATH`.
  - W `pyproject.toml` dodać sekcję `tool.setuptools` (lub `tool.uv`/`tool.rye`/`tool.poetry` – zgodnie z wybranym narzędziem), aby `src` było głównym pakietem:
    - Zdefiniować `packages = ["src"]` lub automatyczne wykrywanie pakietów w `src`.
  - Ujednolicić importy w całym projekcie na styl absolutny (`from src.core...`, `from src.data...`) – wszędzie tam, gdzie aktualnie używane są importy względne.

- **[Wysoki] Konsekwentny entrypoint do testów**
  - Dodać prostą instrukcję w `README.md` jak uruchamiać testy: `pytest`.
  - Skonfigurować środowisko tak, aby `pytest` widział pakiet `src` po instalacji:
    - albo przez poprawne pakietowanie (preferowane),
    - albo tymczasowo przez `pytest.ini` z `pythonpath = .` (do czasu pełnego pakietowania).

- **[Średni] Doprecyzować metadane projektu w `pyproject.toml` (pyproject.toml:1)**
  - Uzupełnić:
    - `description` – jednozdaniowy opis,
    - `authors` (imiona, e-maile),
    - `license` (np. MIT/Apache-2.0),
    - `keywords`, `classifiers`,
    - `homepage`, `repository`, `documentation` (jeśli dotyczy).

- **[Średni] Dodać podstawową konfigurację narzędzi jakości**
  - Dodać pliki konfiguracyjne:
    - `ruff.toml` lub `pyproject.toml`/`tool.ruff` – lint + format (lub `flake8`/`black`/`isort` osobno).
    - `mypy.ini` lub `pyproject.toml`/`tool.mypy` – statyczna analiza typów.
    - `pytest.ini` – podstawowa konfiguracja testów (np. `addopts = -q`).
  - Ustalić minimalne reguły (bez przesadnego zaostrzenia na start), np.:
    - zakaz nieużywanych importów, nieużywanych zmiennych,
    - wymóg typu zwracanego przy publicznych funkcjach / metodach.

- **[Niski] Dodać prosty `Makefile` / skrypty w `scripts/`**
  - Komendy typu:
    - `make test` / `./scripts/test.sh`,
    - `make lint`,
    - `make format`,
    - `make docs`.

## 2. Styl kodu i dokumentacja

- **[Średni] Ujednolicić docstringi zgodne z Google style**
  - W repo docstringi są w większości poprawne (np. `src/core/game/board.py:16`, `src/core/game/auction.py:11`, `src/core/game/game.py:33`), ale warto:
    - doprowadzić wszystkie publiczne klasy i metody do spójnego stylu Google (sekcje `Args:`, `Returns:`, `Raises:`),
    - upewnić się, że wszystkie publiczne API (szczególnie w `src/core/__init__.py:10` i `src/data/__init__.py:9`) mają pełny opis użycia.
  - Skonfigurować `mkdocstrings` (już używane w `mkdocs.yml`) tak, aby generowana dokumentacja była kompletna i aktualna.

- **[Średni] Dodanie modułowych README / dokumentacji**
  - W katalogach:
    - `src/core/game`,
    - `src/core/agents`,
    - `src/data`,
    - `server`,
    dodać krótkie `README.md` (lub rozszerzyć istniejące dokumenty w `docs/monopoly` i `docs/server`) z:
      - opisem odpowiedzialności modułu,
      - przeglądem głównych klas/funkcji,
      - typowymi scenariuszami użycia.

- **[Niski] Uporządkować komentarze i komunikaty logowania**
  - Zamienić komentarze typu „# TODO” (gdy się pojawią) na konkretne zadania lub usunąć, jeśli są nieaktualne.
  - Ujednolicić styl komunikatów logów (np. w `server/app.py:29` są emoji i dość „casualne” komunikaty) – w produkcyjnej aplikacji warto:
    - używać strukturalnego logowania,
    - unikać reprezentacji „emoji” w logach serwera HTTP (mogą być w dev-mode, ale nie w prod).

## 3. Architektura domenowa (Monopoly engine)

- **[Średni] Wyraźne rozdzielenie warstw domena / infrastruktura**
  - Obecnie jest dość czyste rozdzielenie:
    - domena: `src/core/game`, `src/core/agents`,
    - infrastruktura: `src/data`, `server`.
  - Warto doprecyzować:
    - aby `src/core` **nie** zależało od `server` ani `src/data`,
    - aby zależności przepływały tylko „w dół”: `server` → `src/services` → `src/core`, `src/data`.
  - Zaimplementować prosty diagram/sekcję w dokumentacji (np. `docs/monopoly/index.md`) z opisem granic modułów.

- **[Średni] Spójna fasada API w `src/core/__init__.py` (src/core/__init__.py:10)**
  - Aktualnie eksponowane są: `Board`, `GameConfig`, `GameState`, `Player`, `PlayerState`, `create_game`, `Agent`, `GreedyAgent`, `LLMAgent`, `RandomAgent`.
  - Warto:
    - upewnić się, że to jest pełne i stabilne API dla użytkowników zewnętrznych,
    - dodać testy kontraktowe dla tego API (np. w `tests/core/test_public_api.py`),
    - ewentualnie ukryć elementy wewnętrzne (poprzez `_` w nazwach lub brak eksportu).

- **[Średni] Walidacja i bezpieczeństwo metod na poziomie domeny**
  - Metody w `GameState` są bogate i dobrze opisane, ale brakuje konsekwentnego sprawdzania warunków brzegowych:
    - np. czy `player_id` istnieje w `self.players` przed użyciem,
    - czy akcje nie mogą być wykonywane po `game_over == True`,
    - spójna obsługa błędów (zwracane wartości `bool` + log + ewentualne wyjątki domenowe).
  - Wprowadzić klasę błędów domenowych (np. `GameError` / `InvalidActionError`) i używać jej zamiast „gołego” `False`.

- **[Niski] Encapsulacja pomocniczych operacji**
  - W `GameState` wiele fragmentów powtarza logikę:
    - obsługa płatności,
    - egzekucja czynszu,
    - wymuszanie bankructwa.
  - Wydzielić prywatne metody pomocnicze, np. `_transfer_cash`, `_handle_bankruptcy`, `_ensure_player_exists`, aby zmniejszyć duplikację i podnieść czytelność.

## 4. System aukcji i trading (src/core/game/auction.py, src/core/game/game.py)

- **[Średni] Wzmocnić kontrakt klasy `Auction` (src/core/game/auction.py:14)**
  - Doprecyzować w docstringach:
    - jakie są możliwe stany (`is_complete`, `active_bidders`),
    - gwarancje dotyczące `current_bid` i `high_bidder` (np. `high_bidder is not None` gdy `is_complete == True`).
  - Rozważyć:
    - rzucanie specyficznych wyjątków przy nieprawidłowych operacjach (np. `ValueError` lub własny `AuctionError`),
    - dodanie prostych metod typu `is_active_for(player_id: int) -> bool`.

- **[Średni] Pełne pokrycie testami scenariuszy aukcji**
  - Testy już istnieją (`tests/test_auction.py`), ale warto:
    - dopisać testy ekstremalne (1 gracz, wszyscy pasują natychmiast, maksymalna liczba bidów na gracza),
    - dodać testy integracyjne w kontekście całego `GameState.start_auction` / `resolve_auction`.

- **[Niski] Ujednolicić integrację aukcji z event logiem**
  - Upewnić się, że wszystkie graniczne przejścia (`AUCTION_START`, `AUCTION_BID`, `AUCTION_PASS`, `AUCTION_END`) są zawsze logowane, a format `details` jest stabilny (do analizy historycznej).
  - Dodać prosty test regresyjny formatu eventów (np. snapshot JSON/EventType).

## 5. Warstwa danych (`src/data`, `server/database`)

- **[Średni] Zlikwidować „shim” w `server/database/models.py` (server/database/models.py:1)**
  - Plik jest oznaczony jako „Deprecated shim. Use `src.data.models` instead.”:
    - upewnić się, że wszystkie importy w repo używają już `src.data.models`,
    - zostawić shim tylko jeśli jest potrzebny dla kompatybilności z zewnętrznymi użytkownikami; w przeciwnym wypadku usunąć.

- **[Średni] Uporządkować API modułu `src.data` (src/data/__init__.py:9)**
  - Aktualnie udostępnia:
    - konfigurację (`get_settings`),
    - modele `Base`, `Game`, `Player`, `GameEvent`, `LLMDecision`,
    - zarządzanie sesją i repozytorium.
  - Warto:
    - jawnie oznaczyć co jest publiczne (`__all__`) – już jest, ale doprecyzować w docstringu gwarantowaną stabilność,
    - dodać dokumentację wzorców użycia (np. „jak poprawnie używać `session_scope` w asynchronicznym kodzie”).

- **[Średni] Konwencje migracji i zarządzania schematem**
  - W `src/data/migrations` ujednolicić sposób generowania i stosowania migracji:
    - dodać do `README.md` sekcję o użyciu `alembic`,
    - zapewnić spójne nazewnictwo plików migracji,
    - wprowadzić test, który weryfikuje, że `Base.metadata` jest zgodne z migracjami (np. komenda `alembic check` w CI).

## 6. Serwer HTTP / WebSocket (`server` i dashboard)

- **[Wysoki] Wyraźny podział na warstwę API, serwisy i domenę**
  - Aktualnie:
    - FastAPI: `server/app.py:17`,
    - logika rejestru gier i runner: `server/registry.py`, `server/runner.py`,
    - serwis domenowy: `src/services/game_service.py`.
  - Wzmocnić podział:
    - `server/app.py` powinien być cienką warstwą (routing + walidacja + mapowanie błędów),
    - cała logika biznesowa powinna być w serwisach (`GameService`, ewentualne inne serwisy),
    - `server/runner.py` powinien odpowiadać tylko za orkiestrację pętli gry i komunikację z agentami/klientami.

- **[Średni] Spójna obsługa błędów i odpowiedzi API**
  - Dodać centralny handler wyjątków (FastAPI `exception_handler`) dla:
    - błędów domenowych gry,
    - błędów repozytorium bazodanowego,
    - walidacji wejścia.
  - Upewnić się, że wszystkie endpointy zwracają JSON o spójnym formacie (`detail`, `code`, `message`).

- **[Średni] Typy Pydantic dla protokołu WebSocket**
  - Obecnie komunikacja WS jest oparta na surowych słownikach (`dict`) – warto:
    - zdefiniować modele Pydantic dla komunikatów wysyłanych/przyjmowanych,
    - używać ich do walidacji i dokumentacji protokołu.

- **[Niski] Parametryzacja i konfiguracja serwera**
  - Przenieść twardo zakodowane parametry (np. limity, timeouty, ścieżki logów) do:
    - pliku konfiguracyjnego,
    - zmiennych środowiskowych mapowanych przez `pydantic-settings`.

## 7. Agenci (`src/core/agents`)

- **[Średni] Wspólny interfejs i kontrakty agentów**
  - Klasa bazowa `Agent` powinna mieć jasno zdefiniowany kontrakt:
    - jakie metody musi zaimplementować podklasa,
    - jakie są oczekiwania dotyczące deterministyczności (np. używania RNG),
    - jakie wyjątki są dopuszczalne.
  - Dodać testy kontraktowe dla wszystkich agentów (`RandomAgent`, `GreedyAgent`, `LLMAgent`), potwierdzające, że:
    - poprawnie reagują na brak akcji,
    - nie zwracają nielegalnych akcji.

- **[Niski] Parametryzacja strategii LLM**
  - Parametr `llm_strategy` w `CreateGameRequest` (server/app.py:63) jest stringiem – warto:
    - zdefiniować enum Pydantic (`LLMStrategy(str, Enum)`),
    - opisać strategie w dokumentacji (`docs/agents/llm.md`).

## 8. Testy i CI

- **[Wysoki] Naprawić uruchamianie testów lokalnie**
  - Obecnie `pytest` kończy się błędami `ModuleNotFoundError: No module named 'src'` oraz brakiem `fastapi`:
    - zapewnić poprawną instalację zależności (`pip install -e .[dev]` lub użycie `uv`/`poetry` z sekcją `dev-dependencies`),
    - dodać krótki opis w `README.md` jak przygotować środowisko deweloperskie.

- **[Średni] Pokrycie testami krytycznych ścieżek**
  - Testy gry są już dość rozbudowane (`tests/test_*.py`, `tests/core/test_rules_basic.py`), ale warto:
    - dopisać testy regresyjne dla kluczowych reguł (czynsze, jail, bankruptcies, trading),
    - dodać testy integracyjne serwera (REST + WebSocket) z użyciem `fastapi.testclient` / `httpx.AsyncClient`.

- **[Średni] Konfiguracja podstawowego CI**
  - Dodać workflow (np. `.github/workflows/ci.yml`) z krokami:
    - `pip install -e .[dev]`,
    - `ruff check .`,
    - `mypy src server`,
    - `pytest`.

## 9. Dokumentacja i dashboard

- **[Średni] Utrzymywać dokumentację w `docs` jako „źródło prawdy”**
  - Konsolidacja:
    - upewnić się, że opis architektury w `docs/monopoly` i `docs/server` odpowiada aktualnemu kodowi,
    - dodać sekcję „Versioning / Changelog” (np. `docs/changelog.md`) z istotnymi zmianami.

- **[Niski] Uspójnić panel dashboardu**
  - W `dashboard/` zadbać o:
    - czytelne nazwy komponentów,
    - spójny styl (bootstrap theme, layout),
    - dokumentację minimalną w `README.md` jak uruchomić dashboard oraz jego funkcje.

## 10. Proces i dobre praktyki

- **[Średni] Konwencja nazewnicza i organizacja modułów**
  - Uzgodnić:
    - konwencje nazewnictwa plików i modułów (np. `snake_case` dla plików, brak skrótów typu `cfg`, `svc` w nazwach),
    - strukturę katalogów (podział na `core`, `data`, `services`, `server` jest dobry – utrzymywać go konsekwentnie).

- **[Średni] Wprowadzić standard PR / code review**
  - W `CONTRIBUTING.md` opisać:
    - wymagania przed PR (lint, testy, mypy),
    - standard opisu zmian,
    - minimalny poziom pokrycia testami dla nowych funkcji.

- **[Niski] Dodać `CODE_OF_CONDUCT.md` / `SECURITY.md` (jeśli projekt publiczny)**
  - Zwiększa to postrzeganie profesjonalizmu projektu i ułatwia zgłaszanie problemów.


---

Ten dokument można traktować jako backlog techniczny. Rekomendowana kolejność wdrażania:

1. Uruchomienie testów (`src` jako pakiet, zależności, minimalny CI).
2. Uporządkowanie API (`src/core`, `src/data`, serwer) i docstringów.
3. Ujednolicenie stylu (lint, typy, logowanie) i rozbudowa dokumentacji.
4. Stopniowe utwardzanie reguł (mypy „strict”, rozszerzenie kontroli błędów, proces PR). 

