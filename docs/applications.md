# Applications and the frontend

The review queue: a match becomes an application the user tracks, drafts a letter for, and
marks submitted only after applying on the employer's own site.

## Where it lives

- `backend/app/routers/applications.py`: `GET`/`POST /api/applications`,
  `PATCH /api/applications/{id}`, `POST /api/applications/{id}/draft`.
- `backend/app/static/index.html`: the whole UI, served at `/` by FastAPI. Three screens:
  Matches, Tracker, Profile.

## Contracts

- Lifecycle, enforced by `TRANSITIONS`: matched to drafted or discarded; drafted to drafted
  (redraft), submitted or discarded; submitted to interview or rejected; interview to
  rejected. Anything else is a 409; an unknown status is a 400.
- `submitted_at` is stamped the first time an application enters `submitted` and never again.
- One application per `(user, job)`; a second create is a 409.
- Nothing is ever submitted to an employer by this app. "I applied" asks for confirmation
  and only records what the user already did.
- "Open next 10 apply pages" opens the next ten untracked matches in new tabs and tracks
  them as `matched`. Browsers block all but the first tab until pop-ups are allowed for the
  site.
- Discarded jobs are hidden from Matches.

## Sign-in

`POST /api/auth/local/login` signs in as `LOCAL_LOGIN_EMAIL` with no password. It exists
only for running on one's own machine and returns 404 when that variable is empty. The
Google flow in [auth.md](auth.md) is unchanged and shows up on the sign-in screen when
configured.
