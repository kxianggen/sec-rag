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
   Open.

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
    Open.

13. **Citations bunched at the end (T07).** Rule 2 says cite after every claim, but the
    China answer put one [4][5] block at the end of the paragraph. Readers can't tell
    which sentence came from which excerpt. Prompt rules are followed loosely; needs
    checking in the eval harness (citation coverage), not just trusting the prompt.
    Open.

14. **Newest filing ignored (T07).** For "What did Nvidia say about China?", source [1]
    (FY2026, highest score 0.575) was not used; the answer cites only FY2025 and FY2024
    and presents older restrictions as the whole story. → T08, plus a golden question
    that checks the latest year is used.
    Open.