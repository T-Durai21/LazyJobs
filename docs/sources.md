# Job sources

Collects postings into the shared `jobs` table so matching can rank them.

## Where it lives

`backend/app/sources/`. Each source module exposes `NAME` and a plain
`fetch(profile, limit) -> list[Posting]`; `registry.py` maps names to those functions,
runs them from `POST /api/jobs/refresh`, and upserts on `(source, external_id)`.
`base.py` holds `Posting`, the HTTP client, HTML-to-text and salary normalisation.

| Source | What | Notes |
| --- | --- | --- |
| `tracker_csv` | The user's own spreadsheet at `TRACKER_CSV_PATH` | Covers Indeed/Naukri/LinkedIn finds, which have no public API. Rows whose Status starts with `Skip` are ignored. |
| `remotive` | `remotive.com/api/remote-jobs` | Public feed is small (about 16 postings) and 24 hours delayed. |
| `himalayas` | `himalayas.app/jobs/api`, cursor-paged, 10 pages of 20 | Carries salary, currency and `locationRestrictions`; an empty list means open worldwide. |
| `ats` | Greenhouse, Lever and Ashby boards listed in `companies.py` | 51 large employers, about 11,500 postings. Ashby is asked for compensation. |

## Contracts and constraints

- **Refresh floor.** Every network source is skipped if it ran within
  `SOURCE_MIN_REFRESH_HOURS` (default 6). Remotive's terms ask for at most four fetches a day
  and threaten to cut access otherwise, so there is deliberately no way to force a refresh.
  The CSV is exempt because it is a local file.
- **Remotive attribution.** Its terms require linking to the Remotive URL and naming Remotive
  as the source. `url` and `apply_url` are the Remotive links, and the UI shows "via Remotive".
- **Politeness.** One request per `SOURCE_REQUEST_DELAY` seconds with an identifying
  User-Agent. A failing ATS board is logged and skipped rather than failing the refresh.
- **Locations mean eligibility for remote roles.** For a remote posting, `locations` lists
  where applicants may live, not where the office is. Matching relies on this.
- **Salary.** `salary_max_usd` is annual USD using the rough rates in `USD_PER_UNIT`
  (strong Gulf currencies included). Good for ranking, not for quoting pay. Zero means unknown.
- **Adding a company.** Append `(provider, slug)` to `WATCHLIST` after checking the board
  URL in `ats.BOARD_URLS` returns postings.
