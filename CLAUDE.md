# FilingLens (sec-rag) — notes for Claude Code

RAG over 18 SEC 10-K filings (NVIDIA, AMD, Micron, Broadcom, Qualcomm, Marvell; FY2023–2026).
Live: https://filinglens-wtl8.onrender.com · Docker Hub image `jaysonkong/sec-rag:vN` on Render free.
The system is FROZEN at dev 0.77 / held-out 0.82: do not change retrieval, prompts, facts or eval
unless I explicitly ask.

## How we work
- You may write the code. I own the decisions, so ask before any choice that changes behaviour.
- Before I accept a change, explain in plain language what changed and why, file by file.
- Prefer small, reviewable changes. Show me the diff; I read it before anything is committed.
- Never commit or push without my OK.

## Secrets — hard rules
- Never read, print or copy `.env` (OpenAI key, DATABASE_URL). `.env` must never appear in `git status`.
- Never put secrets in code, the Docker image, commits, logs or screenshots.
- `.dockerignore` must keep excluding `.env`, `.venv/`, `.git/`, `results/`, and `data/*` except
  `chunks_final.jsonl`, `embeddings_final.npy`, `facts.jsonl`.

## Commands (Windows, uv)
- Run the app: `uv run uvicorn app:app` → http://localhost:8000 (page = `static/index.html`)
- Checks before saying "done": `uv run python -m py_compile app.py ask.py retrieve.py facts.py`,
  then `uv run python test_metrics.py`, `uv run python test_scoring.py`, `uv run python test_companies.py`
- Each question asked through the app costs a little OpenAI money; keep test questions few.
- Do NOT run `eval.py` (costs ~30 US cents with the gpt-4o judge) unless I ask.

## Web page rules (static/index.html)
- Plain HTML/CSS/JS in one file. No framework, no build step, no new Python dependencies.
- Insert server/model text with `textContent` only, never `innerHTML` (XSS).
- The page calls `/ask` on its own server (same origin). No API keys or other hosts in the page.
- Keep visible: the answer with clickable citations, the sources (text passages and XBRL figures,
  labelled differently), the filters used, honest refusals ("Not in the filings."), the note that
  the first answer after idle can take ~1 minute, and the GitHub link.
- API: `POST /ask {"question": "..."}` (3–300 chars) → `answer, refused, filters, sources, seconds`;
  `GET /health`. Rate limits: 20/visitor/hour, 200/day.
- Must work at phone width (360 px), in light and dark mode, with visible keyboard focus.

## Release (new image)
build `jaysonkong/sec-rag:vN` → rehearse `docker run --rm --memory 512m --cpus 0.1 -p 8000:7860
--env-file .env <image>` → /health shows 8883 chunks → R&D question (NVIDIA vs AMD, latest year)
gives $18,497M vs $8,091M → `docker push` → I switch the tag in Render → smoke-test the live URL.
