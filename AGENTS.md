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

- `GET /jackpot/fetch-jackpot-details` — walks the Sportpesa history API by following `nextJackpot.jackpotId` recursively from a hardcoded starting jackpot UUID (`jackpot.py:26`), then writes `jackpot_details.csv` and `jackpot_details.json` at the repo root. DB persistence (`save_to_database`) exists but is commented out at the call site.
- `GET /jackpot/scrape-links/?start_page=1&end_page=17&source=mozzart+super+jackpot&filename=...` — paginates `footballplatform.com/archive/?paged=N&tp_s=<source>&tp_pp=100`, collects links from `ul.tp-tips-archive-list`, scrapes each match page, and writes the CSV given by `filename` (default `mozzart-super-jackpot.csv`) at the repo root. `source` selects other jackpot types without code changes.
- Detail pages have TWO templates across the archive: newer pages use classed cells (`ha-cell`/`score-cell`/`odds-cell`/`bet-cell`/`pick-cell`), older pages (e.g. May 2025) use the legacy `td[style="text-align:left!important"]` + `<b>` team cell. `scrape_table_from_link` handles both; column positions (odds/bet/pick at td index 3/4/5) are the same in both.
- CSV columns for mozzart scrapes: `date, home_team, away_team, league, score, odds, bet_type, pick, result` (league/bet_type/pick are empty on legacy-template pages).
- Result classification (`home`/`draw`/`away`/`postponed`/`abandoned`/`unknown`; score cells may literally contain `Postp` or `Abn`) is duplicated in `scraplinks.py` (`classify_result`) and `functions.py:parse_match_data`; keep them in sync if you touch scoring logic.
- The many root-level CSVs (`sportpesa-*`, `betika-*`, `mozzart-*`) are tracked dataset snapshots, not build artifacts — do not delete or "clean up" them.

## Gotchas

- Dates are stored as strings (Scraped format `dd-mm-yyyy`) in both models and CSVs; the `fix date issues` history shows this area is fragile.
- Scraper is synchronous, unpaged `requests` with per-row try/except that prints errors rather than raising; a failed row/link is silently skipped.
- `app/core/settings.py` contains real-looking hardcoded JWT secrets committed to the repo; don't rotate or move them casually — auth tokens issued with them will break.
- CORS allows all origins with credentials; sqladmin dashboard is mounted at `/admin` with a `UserAdmin` view.
- `sqlite.db` is gitignored; a fresh clone needs `uv run alembic upgrade head` before user/auth or jackpot DB endpoints work.
