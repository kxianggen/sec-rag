## extract.py

1. **Intel (all years) – only Item 16 extracted.** Intel's body uses plain titles
   ("Risk Factors") with no "Item" numbers; the only "Item X" labels are in a lookup
   table at the end. Each table line is a short piece (<1,000 chars) so it gets
   dropped, and everything before the first bookmark (~99% of the report) is never
   stored. Item 16 survives only because it's the last bookmark, so it runs to the end
   and picks up the signatures page (>1,000 chars). → T01

2. **Fake Item 16 listed first (NVDA, MU, AVGO, QCOM, MRVL).** The TOC's last line
   is "Item 16". Its next bookmark is the real Item 1, so it swallows the intro pages
   in between (NVDA: social media list + forward-looking statements, 4,117 chars).
   That's over 1,000, so the intro gets saved and wrongly labelled Item 16. → T01

3. **Items 8 and 9 missing (NVDA, QCOM).** The real sections are just one sentence
   each (Item 8 = "see the financial statements", Item 9 = "None"), under 1,000
   chars, so they're dropped like TOC lines. Root cause of 2 and 3: length is the
   wrong clue for "is this a TOC line". No threshold works (NVDA's fake 16 at 4,117
   is longer than the real Item 1C at 3,974). → T01

4. **Duplicate chunk ids.** Fake 16 and real 16 both produce ids like NVDA-2026-01-25-16-0.
   Ids should be unique. Goes away when T01 removes the fake 16; worth a uniqueness check after.

5. **Intel queries return AMD's text about Intel** (0.56–0.62), consequence of #1.
   No signal that Intel's own filing is missing.
   
6. **Near-duplicate results.** Top 3 for "export controls" are the same NVDA
   paragraph from 3 fiscal years. Wastes top-k slots.

7. **ask.py refused the Intel question correctly** because excerpt headers show "AMD".
   No prompt instruction enforces this; untested on harder cases (→ T07).
   Correct answer exists in data/raw/INTC but was dropped at extract (→ #1).

8. **AMD chunk returned for an NVIDIA-only question** (rank 2, 0.574).
   Retrieval ignores the company named in the question. (→ T05/T06)

9. **T01b – Intel still broken, now silently.** Last "Item 1" is in the end-of-doc lookup
   table, so all 23 sections are one-line index entries. Item list looks perfect; text is
   empty. Needs a different approach (plain-title headings or the lookup table).

10. **T02 rule only catches "number + Table of Contents" pairs.** QCOM (0 found), AMD 2025 (1),
    MRVL 2024 (6) likely still have bare page numbers. Needs a per-company check.