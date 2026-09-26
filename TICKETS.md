# Tickets

The pipeline runs end to end and is deliberately crude. Each ticket fixes one
thing. Work them in order, one per session.

**Every ticket ends the same way:** run the pipeline stages it touches, check the
"done when" line, write one line in FAILURES.md if anything surprised you, and commit
with a message that names the ticket, e.g. `git commit -m "T03: add chunk overlap"`.

`yours` = core logic, you write it (20-min timebox → hint → help → retype).
`plumbing` = Claude may draft it; you must be able to explain every line.

---

## T00 · Run it and read it · 90 min · orientation

Install the new dependencies (the first one pulls in PyTorch, a few hundred MB):

    uv add sentence-transformers numpy beautifulsoup4 lxml python-dotenv anthropic openai

Then run every stage in order and read each file top to bottom as it runs:

    uv run python extract.py
    uv run python chunk.py
    uv run python embed.py
    uv run python retrieve.py "What are the risks from export controls?"
    uv run python ask.py "What did NVIDIA say about data center demand?"

**Done when** all five run, and you can answer these without looking:
1. Why does `retrieve.py` use `vectors @ q` instead of calling a cosine function?
   (Hint: look at `normalize_embeddings=True`.)
2. What is the `len(body) < 1000` check in `extract.py` trying to throw away?
3. Why does every chunk carry `ticker`, `period_end` and `item`?
4. What happens in `ask.py` if no API key is set?

---

## T01 · Section detection is wrong · 90 min · yours

`extract.py` printed this for NVIDIA:

    NVDA 2026-01-25  items: 16, 1, 1A, 1C, 5, 7, 7A, 9A, 10, 15, 16

Item 16 appears **before** Item 1, and Item 8 (the financial statements) is missing.
Open `data/text/NVDA/2026-01-25.json` and find out why each happens. Then fix
`split_items()`.

**Done when** every one of the 21 filings lists its items in order, starting at
Item 1, with Items 1A, 7 and 8 present. Print the list for all 21 as proof.

## T02 · Page furniture in the text · 45 min · yours

The text still contains repeated junk from every page: "Table of Contents" lines
and bare page numbers. Count how often it appears in one filing, then strip it in
`html_to_text()`.

**Done when** you can show the count before and after for one filing.

## T03 · Chunks have no overlap · 45 min · yours

`chunk_text()` cuts every 1,000 characters exactly, so a sentence that straddles
a boundary is split and neither half makes sense. Add a `CHUNK_OVERLAP` setting
(default 150).

Watch out: the embedding model reads only about 256 tokens (roughly 1,000
characters). Anything longer gets **silently cut off**. Keep that in mind when you
pick sizes.

**Done when** the chunk count changes and you can show one boundary sentence that
is now whole in at least one chunk.

## T04 · Chunks cut mid-word · 60 min · yours

Even with overlap, chunks start and end mid-word. Split on paragraph boundaries
(`\n\n`) and pack paragraphs into chunks up to the size limit, instead of cutting
at raw character positions.

**Done when** no chunk starts or ends mid-word. Write a 3-line check that proves it.

## T05 · Retrieval ignores the company · 60 min · yours

Ask `retrieve.py "AMD revenue"` and look at which companies come back. Add an
optional `ticker` argument to `retrieve()` that only searches that company's chunks.

**Done when** `retrieve("revenue", ticker="AMD")` returns only AMD chunks, and you
can show the result before and after.

## T06 · Work out the company from the question · 60 min · yours

Nobody types `ticker="AMD"`. Detect the company from the question itself: "Nvidia",
"NVIDIA" and "NVDA" should all map to NVDA. Use it in `ask.py`.

**Done when** `ask.py "What did Nvidia say about China?"` retrieves only NVDA chunks.

## T07 · The model answers from memory · 45 min · yours

The prompt in `build_prompt()` never tells the model to stick to the excerpts, so it
will happily answer from what it already knows. Rewrite it: answer **only** from
the excerpts, cite them as [1], [2], and say "Not in the filings" when the answer
isn't there.

**Done when** these three all get a refusal, not an invented answer:
- "What is NVIDIA's stock price target?"
- "What will AMD's revenue be in 2030?"
- "What is AMD's share price today?"

Needs an API key. See `.env.example`.

## T08 · "2025" means different things · 90 min · yours

Your ingest output already showed it: NVIDIA's year ends in January, Micron's in
August, Qualcomm's in September. Add a `fiscal_year` field to every chunk, work out
the rule for each company, and allow filtering by it.

**Done when** you can explain, for three companies, which calendar months their
fiscal 2025 covers, and `retrieve(..., fiscal_year=2025)` respects it.

## T09 · First 10 golden questions · 90 min · yours, and only yours

Create `golden.jsonl`. One line per question:

    {"question": "...", "answer": "...", "ticker": "AMD", "period_end": "2025-12-27", "item": "7", "type": "fact"}

Write 10, mixing the four types from the spec: single fact, cross-period,
cross-company, narrative. Plus 2 the filings can't answer. **Find each answer in
the filing yourself.** That's what makes the evaluation mean something.

**Done when** 10 lines exist and you've checked every answer against the source.

---

*Next batch (after T09): evaluation harness and baseline numbers, pgvector, hybrid
BM25 search, the two experiments, FastAPI, deploy.*
