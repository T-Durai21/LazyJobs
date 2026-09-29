# Matching

Ranks stored postings against one user's profile, with a readable reason per match. No LLM
call per posting, so ranking thousands of jobs is free.

## Where it lives

`backend/app/matching.py` (pure functions, tested in `backend/tests/test_matching.py`) and
`GET /api/matches` in `backend/app/routers/jobs.py`.

## How a posting is judged

1. **Hard filters** (`rejection`): an `exclude_keywords` word in the title or employment
   type; not remote when `remote_only`; stated pay under `min_salary` (annual USD; unknown
   pay passes); location not in `preferred_locations`, unless the remote role is open to
   anyone or marked worldwide.
2. **Score 0 to 100** (`score`): skills found in the title and the first 8,000 characters of
   the description (40), target title (30 for a full title, 12 per distinctive shared word),
   recency (10), stated pay (10), remote (5), strong-currency country (10), and with
   `prefer_non_coding` +10 for non-coding titles and -15 for coding ones.
3. **Relevance gate**: a posting must hit a target title or at least five skills. Without
   it, well-paid but unrelated roles (a radiologist, say) float to the top.
4. **Ordering** (`rank`), before score: place tier (strong-currency country, then open or
   worldwide, then India-only), then large employers from the ATS watchlist, then
   non-coding before coding when preferred.

## Constraints

- Term lookups are substring checks on space-joined normalised words, with term
  normalisation cached. The earlier regex-per-term approach took about 25 seconds for
  11,000 postings.
- `GET /api/matches` caches the ranked list per user until the profile's `updated_at`, the
  job count or the latest `fetched_at` changes; the first call after a refresh takes several
  seconds.
- `GENERIC_TITLE_WORDS` keeps words like "engineer", "senior" and "data" from counting as
  a title match on their own.
