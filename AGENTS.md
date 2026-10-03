# AGENTS.md

## Project overview

Kenyan betting jackpot data tool: a FastAPI app that scrapes/ingests football jackpot results from Sportpesa (API) and Mozzart Bet (HTML scraping), plus a user/auth module inherited from the `fastapi-starter-kit` template. Scraped data lands as CSV/JSON files at the repo root and (optionally) in SQLite via SQLAlchemy.

## Commands

Package management is `uv` (see `pyproject.toml` + `uv.lock`; `requirements.txt`/`dev.txt` are legacy, do not edit them for new deps).

```sh
uv sync                                  # install deps
uv add <package>                         # add a dependency
uv run uvicorn app.main:app --reload     # dev server
uv run alembic upgrade head              # run migrations
uv run alembic revision --autogenerate -m "msg"   # new migration
```

There is no test suite, linter, or formatter configured. Verify changes by running the server and hitting endpoints (`/docs` for Swagger).

## Architecture

```
app/
├── main.py              # create_app(); mounts middleware + routers via core/modules.py
├── core/
│   ├── database.py      # SQLite engine (sqlite:///./sqlite.db), SessionLocal, Base
│   ├── dependencies.py  # get_db() session dependency, oauth2_scheme
│   ├── modules.py       # init_routers(), make_middleware() (CORS allow_origins=["*"]), sqladmin Admin
│   └── settings.py      # hardcoded JWT secrets + token expiry (no env loading despite python-dotenv dep)
├── api/
│   ├── routers/         # APIRouters wired into the main router (api.py -> user.py)
│   └── endpoints/       # feature modules: user (auth.py, user.py, functions.py), jackpot
├── models/              # SQLAlchemy models (user, admin, jackpot: Jackpot 1-N Event)
└── schemas/             # Pydantic models; jackpot schemas use PascalCase field names
alembic/                 # migrations; initial revision: fad2f775af95
```

Conventions:
- Endpoint handlers live in `app/api/endpoints/<feature>/` as a `<feature>_module = APIRouter()`; `app/api/routers/` attaches them with prefixes (`/users`, `/jackpot`) and tags. All are included via a single root `router` in `api/routers/api.py`.
- New models must be imported so `Base.metadata` sees them before autogenerating alembic revisions. `app/models/jackpot.py` exports `metadata = Base.metadata`.

## Jackpot data flow (domain-specific)

- `GET /jackpot/fetch-jackpot-details` — walks the Sportpesa history API by following `nextJackpot.jackpotId` recursively, starting at jackpotHumanId 1 (`6ab8a2c7-...`, 2022-12), then writes `jackpot_details.csv` and `jackpot_details.json` at the repo root (~197 jackpots, human IDs 1–201 with 24/102/162/183 absent from the chain). The API is behind Akamai Bot Manager: plain requests get 403, a browser UA alone gets a JS-challenge HTML — `SPORTPESA_HEADERS`/`SPORTPESA_COOKIES` in `jackpot.py` carry a browser UA + `bm_so`/`bm_sv` challenge cookies that must be refreshed from a real browser session when they expire (the endpoint raises 503 with guidance when a challenge page comes back). Scores use colon format (`"0:1"`); postponed/void legs appear as `PD:X`/`PD:1`/`PD:2` while `resultPick` remains `Home`/`Draw`/`Away` and is stored as-is. DB persistence (`save_to_database`) exists but is commented out at the call site.
- `GET /jackpot/scrape-links/?start_page=1&end_page=17&source=mozzart+super+jackpot&filename=...` — paginates `footballplatform.com/archive/?paged=N&tp_s=<source>&tp_pp=100`, collects links from `ul.tp-tips-archive-list`, scrapes each match page, and writes the CSV given by `filename` (default `mozzart-super-jackpot.csv`) at the repo root. `source` selects other jackpot types without code changes.
- Detail pages have multiple templates: newest pages use classed cells (`ha-cell`/`score-cell`/`odds-cell`/`bet-cell`/`pick-cell`), older pages use the legacy `td[style="text-align:left!important"]` + `<b>` team cell (sometimes with a row-number prefix like "3 – Team"), and 2022–2023 pages add extra leading cells before the team cell. `scrape_table_from_link` anchors on the team cell and reads score/odds/bet/pick as the 4 cells after it, so it works on all variants. Score cells may contain en-dashes ("2–1"), "Postp." with trailing dot, or be empty (= abandoned, normalized to "Abn").
- CSV columns for mozzart scrapes: `date, home_team, away_team, league, score, odds, bet_type, pick, result` (league/bet_type/pick are empty on legacy-template pages).
- Result classification (`home`/`draw`/`away`/`postponed`/`abandoned`/`unknown`; score cells may literally contain `Postp` or `Abn`) is duplicated in `scraplinks.py` (`classify_result`) and `functions.py:parse_match_data`; keep them in sync if you touch scoring logic.
- The many root-level CSVs (`sportpesa-*`, `betika-*`, `mozzart-*`) are tracked dataset snapshots, not build artifacts — do not delete or "clean up" them.

## Gotchas

- Dates are stored as strings (Scraped format `dd-mm-yyyy`) in both models and CSVs; the `fix date issues` history shows this area is fragile.
- Scraper is synchronous, unpaged `requests` with per-row try/except that prints errors rather than raising; a failed row/link is silently skipped.
- `app/core/settings.py` contains real-looking hardcoded JWT secrets committed to the repo; don't rotate or move them casually — auth tokens issued with them will break.
- CORS allows all origins with credentials; sqladmin dashboard is mounted at `/admin` with a `UserAdmin` view.
- `sqlite.db` is gitignored; a fresh clone needs `uv run alembic upgrade head` before user/auth or jackpot DB endpoints work.
