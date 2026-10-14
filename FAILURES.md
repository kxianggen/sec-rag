# Failures log

Every problem found in the pipeline, with where it was found and what fixed it.
Open items are still to do; ✓ marks fixed ones.

## extract.py

1. **Intel (all years) – only Item 16 extracted (T00).** Intel's body uses plain titles
   ("Risk Factors") with no "Item" numbers; the only "Item X" labels are in a lookup
   table at the end. Each table line is a short piece (<1,000 chars) so it gets
   dropped, and everything before the first bookmark (~99% of the report) is never
   stored. Item 16 survives only because it's the last bookmark, so it runs to the end
   and picks up the signatures page (>1,000 chars). → T01
   Open: T01 changed the symptom but not the cause (see #9).
   **Descoped (14 Oct):** Intel's 10-K is structured differently from the other six
   (plain titles, no "Item" headings in the body), so section detection can't work on it
   without a separate approach. The project covers 6 companies; Intel is left out on purpose.

2. **Fake Item 16 listed first (T00; NVDA, MU, AVGO, QCOM, MRVL).** The TOC's last line
   is "Item 16". Its next bookmark is the real Item 1, so it swallows the intro pages
   in between (NVDA: social media list + forward-looking statements, 4,117 chars).
   That's over 1,000, so the intro gets saved and wrongly labelled Item 16. → T01
   ✓ Fixed in T01 (body starts at the last "Item 1").

3. **Items 8 and 9 missing (T00; NVDA, QCOM).** The real sections are just one sentence
   each (Item 8 = "see the financial statements", Item 9 = "None"), under 1,000
   chars, so they're dropped like TOC lines. Root cause of 2 and 3: length is the
   wrong clue for "is this a TOC line". No threshold works (NVDA's fake 16 at 4,117
   is longer than the real Item 1C at 3,974). → T01
   ✓ Fixed in T01 (length filter removed; NVDA Item 8 now kept at 206 chars).

4. **Duplicate chunk ids (T00).** Fake 16 and real 16 both produce ids like
   NVDA-2026-01-25-16-0. Ids should be unique.
   ✓ Fixed in T01 (fake 16 gone, so no duplicate ids).

9. **Intel still broken, now silently (T01).** The last "Item 1" is in the end-of-doc
   lookup table, so all 23 sections are one-line index entries. The item list looks
   perfect; the text is empty. Needs a different approach (plain-title headings or
   the lookup table). → T01b
   Descoped with #1.

10. **Page-number rule only catches "number + Table of Contents" pairs (T02).** QCOM
    (0 found), AMD 2025 (1) and MRVL 2024 (6) likely still have bare page numbers.
    Needs a per-company check.
    Open.

## retrieval

5. **Intel queries return AMD's text about Intel (T00).** Scores 0.56–0.62, a
   consequence of #1. No signal that Intel's own filing is missing.
   Open (depends on #1 / #9). T05 confirmed: Intel-only results score just 0.29–0.34.

6. **Near-duplicate results (T00).** The top 3 for "export controls" are the same NVDA
   paragraph from 3 fiscal years. Wastes top-k slots.
   Open.

8. **AMD chunk returned for an NVIDIA-only question (T00).** Rank 2, score 0.574.
   Retrieval ignored the company named in the question. → T05/T06
   ✓ Fixed in T05 + T06 (ticker filter; company detected from the question).

## answers (ask.py)

7. **ask.py refused the Intel question correctly (T00),** but only because the excerpt
   headers said "AMD". No prompt instruction enforced it. The correct answer exists in
   data/raw/INTC but was dropped at extract (→ #1).
   ✓ Addressed in T07 (prompt now says: excerpts only, exact refusal phrase).

11. **No citations in answers (T06 run).** For "What did Nvidia say about China?" the
    answer never said which of the five sources each claim came from, so a reader
    couldn't check claims like "the NAC process has not resulted in approvals".
    → T07 (grounded prompt: cite [1]–[5], refuse if the answer isn't in the excerpts).
    ✓ Partly fixed in T07 (citations now present; see #13).

12. **Three fiscal years blended into one story (T06 run).** The sources span FY2024,
    FY2025 and FY2026, but the answer reads as if everything is current. The A100/H100
    restrictions most likely come from the FY2024 filing (source [2] or [5]).
    → T08 (fiscal-year awareness).
    Partly addressed in T08: every excerpt header now states its fiscal year.

13. **Citations bunched at the end (T07).** Rule 2 says cite after every claim, but the
    China answer put one [4][5] block at the end of the paragraph. Readers can't tell
    which sentence came from which excerpt. Prompt rules are followed loosely; needs
    checking in the eval harness (citation coverage), not just trusting the prompt.
    Open.

14. **Newest filing ignored (T07).** For "What did Nvidia say about China?", source [1]
    (FY2026, highest score 0.575) was not used; the answer cites only FY2025 and FY2024
    and presents older restrictions as the whole story. → T08, plus a golden question
    that checks the latest year is used.
    ✓ Addressed in T14 for questions that say "latest" (see #17).
## Found by the eval harness (T10–T14 and Experiment 1)

Question numbers refer to `golden.jsonl`.

### retrieval

15. **Only the first fiscal year in a question was used (T10 baseline; Q4, Q5).**
    "From fiscal 2024 to fiscal 2026" was filtered to 2024 only, so the 2026 figure was
    never retrieved and the model refused. → T11: detect every year, filter on a list.
    ✓ Fixed: cross-period recall 0.50 → 1.00, refusal 0/2 → 2/2.

16. **One company crowded out the other (T09/T10; Q6, Q7).** With no company filter, top-5
    is winner-takes-all: the Broadcom vs Qualcomm question got 5/5 Qualcomm chunks.
    → T12: retrieve separately per company, keeping the total at k (k // n each) so the
    comparison with the baseline stays fair.
    ✓ Fixed: both companies now retrieved; cross-company recall 0.25 → 0.50.

17. **"Latest fiscal year" was not understood (T12; Q7).** With no year filter, each
    company's chunks could come from any of its three filings, and Q7 was answered with
    fiscal 2023 data. → T14: when a question says "latest" / "most recent" and names no
    year, keep only each company's newest filing.
    ✓ Years fixed. Open: with only 2 chunks per company the exact passage is still missed,
    so Q6 and Q7 now refuse ("Not in the filings") instead of answering wrongly. Better
    failure, still a failure → Experiment 2 (more chunks per company).

18. **Regression in T12: a missing argument dropped the year filter (Q1, Q10).** In
    `retrieve_multi`, the one-company branch didn't pass `fiscal_years` to `retrieve()`,
    so it searched all three years and took whatever top 5 came back, which included the
    wrong years. Q1 and Q10 fell from 1.00 to 0.00. Q4, Q5 and Q9 went through the same
    branch but still scored 1.00 by luck, so a passing test doesn't prove the code right.
    ✓ Fixed the same day; caught only because the eval was re-run.

19. **Financial-statement notes labelled Item 15 / 16 (NVDA, QCOM).** These filings put
    the notes after the Item 15/16 headings, so their chunks carry that label instead of
    Item 8. Golden sources were labelled to match.
    Open.

20. **Fixed-size chunks hurt retrieval and answers (Experiment 1).** Cutting every 1,000
    characters splits sentences and table rows: recall@5 0.40 vs 0.65 for paragraph
    chunks, answer score 0.38 vs 0.62. ✓ Paragraph chunking kept (see README).

### answers

21. **Invented a number (T12; Q6, AMD vs NVIDIA net income).** The answer gave AMD's net
    income as "$2.0 billion ... not directly stated in the excerpts but can be inferred";
    the filing says $4,335 million. Rule 1 of the prompt ("use only the excerpts") already
    existed since T07, but the retrieved chunks didn't contain AMD's figure and the model
    filled the gap instead of refusing. Prompt rules are not guarantees, which is why
    answers are now graded by a judge.
    Open. Since T14 the model refuses on Q6 instead of inventing; the fix is retrieving the
    passage that has the figure (Experiment 2).

22. **Q3 answered with the wrong debt figure.** Even after rewording to "debt principal",
    retrieval returns only Item 8 tables and the answer quotes fair value ($64,609M) instead
    of principal ($67,120M).
    Open.

### evaluation

23. **The judge gave different grades on different runs (T13).** `call_llm` didn't set a
    temperature, so the same answer could be graded differently each run (Q5 flipped from
    correct to partial with nothing changed). That moves both the answer score and the
    judge-vs-human agreement. ✓ Fixed: the judge runs at temperature 0.

24. **Incomplete answer key (Q8).** The golden key points for NVIDIA's export-control
    answer left out the filing's headline statement ("effectively foreclosed from
    competing in China's data center market"), so a correct system answer was graded
    incorrect. ✓ Fixed by adding it as key point (0), backed by a quote from the filing.
    Caution: editing an answer key after seeing answers can bend the test; only done here
    because the filing quote proves the key was missing it.

25. **Ambiguous question (Q3).** "Total debt" can mean principal ($67,120M) or the
    balance-sheet amount ($65,136M); both are defensible, so it couldn't be graded
    cleanly. ✓ Reworded to "total debt principal".

26. **Judge agreement compared two different sets of answers (eval.py bug, T14).** A full
    run graded new answers but compared them with labels made on old answers.
    ✓ Fixed: agreement is only reported with `--rejudge` on the labelled run.

27. **Golden set never tests a question with no company in it.** So the "search all
    companies" branch of `retrieve_multi` is untested; a bug there would go unnoticed.
    Open: add such questions when the golden set grows to 30.

28. **Partially answerable questions aren't tested.** A planned unanswerable question ("How
    many H200 chips did NVIDIA ship to China?") was dropped because the filing half-answers
    it (a licence was granted, no H200 revenue yet), so "Not in the filings" vs "none so far"
    couldn't be graded cleanly. The underlying behaviour — answer what the filings support,
    say clearly what they don't — is real and matters (see Q6 at k = 10). Open: add
    questions with an explicit partial answer key.

29. **"Latest" depends on when the corpus was downloaded.** The corpus is a fixed snapshot
    (filings downloaded September 2026). Companies keep filing — Micron's fiscal 2026 10-K
    came out after the snapshot — so "latest fiscal year" in the golden set means the newest
    filing *in the corpus*. Keeping the snapshot fixed keeps every result reproducible; a
    live product would need to refresh the corpus and re-check these answers.
