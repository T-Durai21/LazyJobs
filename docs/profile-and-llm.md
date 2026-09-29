# Profile, CV parsing and the LLM

Turns an uploaded CV into an editable profile, and drafts cover letters.

## Where it lives

- `backend/app/cv.py`: PDF (pdfplumber) or DOCX (python-docx) to text; 5 MB cap; anything
  else is a 400.
- `backend/app/storage.py`: keeps the original file under `UPLOAD_DIR/<user_id>/`, so a
  parser fix can be re-run without a new upload.
- `backend/app/llm.py`: `extract_profile(cv_text)` and `draft_cover_letter(profile, job,
  matched_skills)`.
- `backend/app/routers/profile.py`: `GET`/`PATCH /api/profile`, `POST /api/profile/cv`.

## LLM behaviour

- With `ANTHROPIC_API_KEY` set, both functions call Claude (`CLAUDE_MODEL`, default
  `claude-opus-5-5`) through the Anthropic SDK at low effort. Extraction uses a JSON schema
  output format. Requests opt into server-side refusal fallbacks (`fallbacks: "default"`).
  API errors become 502/503 responses with a plain message.
- Without a key, extraction is keyword rules over `SKILL_TERMS` plus the first CV lines, and
  the letter is a short template. Both are starting points the user edits.
- Cover letters are told to write in the posting's language and use only profile facts.
- CV text sent to the model is capped at 60,000 characters and job descriptions at 12,000.

## Profile fields beyond the CV

`preferred_locations`, `remote_only`, `min_salary` (annual USD), `extra_keywords`,
`exclude_keywords` and `prefer_non_coding` drive matching; see [matching.md](matching.md).
