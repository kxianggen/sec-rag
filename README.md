# sec-rag — question answering over SEC 10-K filings

Ask questions about six US semiconductor companies' annual reports (NVIDIA, AMD, Micron,
Broadcom, Qualcomm, Marvell; fiscal years 2023–2026) and get answers that quote only the
filings, cite their sources, and say "Not in the filings." when the answer isn't there.

The corpus is a fixed snapshot of 18 10-K filings downloaded in September 2026 (Intel was
dropped: its 10-K structure defeats the section parser — see FAILURES #1). "Latest fiscal
year" means the newest filing in this snapshot.

*Full README (architecture, setup, demo) in progress. Results so far:*

## Results

Measured on 12 hand-written golden questions (10 answerable + 2 unanswerable) with
`eval.py`. Answers graded by an LLM judge (see below). The golden set later grew to 30
questions — current results are in [Results on 30 questions](#results-on-30-questions).

| Stage | Change | Recall@5 | Refusal ok | Answer score |
|---|---|---|---|---|
| Baseline (T10) | dense retrieval, company + year filters | 0.50 | 8/12 | — |
| T11 | detect every fiscal year in the question | 0.60 | 10/12 | — |
| T12 | retrieve per company for cross-company questions | 0.65 | 12/12 | — |
| T14 | "latest fiscal year" → each company's newest filing | 0.65 | 10/12 | 0.62 |
| Exp 2 (current) | 10 chunks instead of 5 | 0.80 @10 | 12/12 | 0.67 |

- **Recall@k:** share of the golden source passages (company + filing + section) found in
  the top k chunks (k = 5 until Experiment 2, then 10), averaged over answerable questions.
- **Refusal ok:** answered when it should, refused when it should.
- **Answer score:** correct = 1, partial = 0.5, incorrect = 0, graded against the golden
  answer.

T14 lowered refusal ok for a good reason: two cross-company questions that were
previously answered *wrongly* (fiscal 2023 data; an invented figure) are now refused. The
system went from confidently wrong to honestly saying it doesn't have the answer.

### Experiment 1 — does where you cut the text matter?

| Chunking | Recall@5 | Answer score | Refusal ok |
|---|---|---|---|
| Fixed (cut every 1,000 characters) | 0.40 | 0.38 | 8/12 |
| **Paragraph (whole lines packed up to 1,000 characters)** | **0.65** | **0.62** | **10/12** |

I compared fixed-size chunks with paragraph chunks, keeping everything else the same: the
12 golden questions, chunk size, embedding model, k = 5, LLM and judge. Paragraph chunking
won clearly. Fixed cuts hurt in two ways: sometimes they split the sentence holding the
answer, so it was no longer retrieved (Q1, NVIDIA's fiscal 2026 revenue); sometimes the
right section was retrieved but the chunk no longer contained the full figure, so the model
refused (Q4, recall 1.00 but "Not in the filings."). Number questions suffered most (fact
recall 0.33 → 0.00). Caveats: 12 questions is a small set, where one question moves the
score by about 0.1, and paragraph chunks are also shorter on average (8,504 vs 6,953
chunks), so chunk length changed slightly too.

### Experiment 2 — does the model need more context?

| Chunks per question | Answer score | Refusal ok | Prompt size |
|---|---|---|---|
| 5 | 0.62 | 10/12 | 1× |
| **10** | **0.67** | **12/12** | ~2× |

With 5 chunks, the two cross-company questions get only 2 chunks per company and refuse.
With 10, every answerable question gets an answer. (Recall rises to 0.80, but recall@10 vs
recall@5 isn't a fair comparison: more slots, more chances.) The answer-score gain comes
from one question: Micron's gross margin is now quoted exactly ("40%") instead of
recomputed ("≈39.8%"). The cross-company questions still miss: for AMD vs NVIDIA net income
the model now gives NVIDIA's correct figure and says AMD's isn't in the excerpts, which is
better than inventing it (an earlier run did) or refusing, but still graded incorrect.
The missing piece is one specific table row, which suggests keyword search (BM25) next.
Decision: **k = 10**. At this scale the extra cost is negligible (well under a tenth of a
US cent per question with gpt-4o-mini) and answers are more complete and more honest; at
production volume the 2× prompt size would need weighing against that small gain.

## Results on 30 questions

The 12-question set was too small (one question moves the score by ~0.08) and I had tuned the
system on it. I grew it to 30: 7 fact, 6 cross-period, 6 cross-company, 7 narrative and
4 unanswerable, each answer checked against a quote from the filing.

| Run (k = 10, answers at temperature 0) | Recall@10 | Refusal ok | Answer score |
|---|---|---|---|
| Baseline: dense retrieval | 0.68 | 26/30 | 0.55 |
| **Hybrid: dense + BM25 keyword search (current)** | **0.76** | **27/30** | **0.65** |

The score *dropped* when the set grew (0.67 on 12 → 0.58 on 30, before temperature 0): the
original 12 scored ~0.71 against ~0.50 on the 18 new ones. Scores on the questions you tuned
on are optimistic — that's why the set grew before any more tuning.

Answers now run at temperature 0. Before that, re-running the same 30 questions flipped
8 grades (4 up, 4 down) while the total barely moved, so a single run couldn't tell a real
improvement from luck.

### Experiment 3 — fixing what retrieval misses

**The problem.** In the baseline, financial-statement notes (Items 8 and 15 — dense tables
full of numbers) crowded out the prose sections that hold many answers. For "How many
employees did NVIDIA have at the end of fiscal 2026?", 8 of the 10 retrieved chunks were
Item 15 notes and the employee count in Item 1 never made it in, so the system said
"Not in the filings."

**What I tried**, one change at a time, against the same baseline:

| Run | Recall@10 | Refusal ok | Answer score |
|---|---|---|---|
| Baseline (dense) | 0.68 | 26/30 | 0.55 |
| A. Section cap: at most 3 chunks from one section | 0.87* | 26/30 | 0.55 |
| **B. Hybrid: dense + BM25 keyword search** | **0.76** | **27/30** | **0.65** |
| C. Hybrid + section cap | 0.88* | 27/30 | 0.57 |
| D. Hybrid + prompt rule "use the company total, not a segment" | 0.76 | 27/30 | 0.63 |

\* inflated — see below.

**A. Section cap.** Keep at most 3 chunks from the same section (company + filing + Item);
when a 4th comes up, skip it and take the next-ranked chunk from another section. Recall
jumped to 0.87 but the answer score didn't move. Two reasons. First, recall only checks that
*a* chunk from the right section was retrieved, not *the* chunk with the answer, and forcing
more sections into the top 10 raises that almost automatically: the NVIDIA employees
question went from recall 0 to 1.00 and still refused, because the two Item 1 chunks that
got in weren't the employees paragraph. Second, the cap is blind: it drops the 4th chunk of
a section even when that chunk holds the answer. It fixed three questions (e.g. NVIDIA's $40.4B of share
buybacks, which sits in Items 5 and 7) and broke one where the answer *was* in the busy
section (Micron's revenue, from Item 8).

**B. Hybrid search — adopted.** Dense retrieval ranks chunks by meaning; BM25 ranks them by
exact word matches, giving more weight to words that are rare across the filings. I merge
the two rankings with reciprocal rank fusion (each chunk scores 1/(60 + its rank) in each
list, so the two scoring scales never need matching). A word like "employees" is fairly rare,
so the paragraph that contains it moved up and NVIDIA's ~42,000 employees was answered
correctly. Answer score 0.55 → 0.65, the biggest single gain on the 30 questions. One
caveat: refusal ok rose to 27/30 partly because one question (Broadcom's R&D) went from an
honest refusal to a wrong number.

**C. Both together.** Worse than hybrid alone (0.57). The cap cut Qualcomm Item 7 chunks
that hybrid had found, so two questions lost their figures; one then quoted Qualcomm's chip
segment ($37.7B) instead of its total revenue ($44.3B).

**D. Prompt rule.** I added "use the company-wide total, not a segment's figure, unless the
question names the segment". It fixed nothing (none of the remaining wrong answers were
segment mix-ups) and made one worse: for AMD vs NVIDIA net income, the model swapped
"AMD's figure isn't in the excerpts" for a wrong number. Not adopted. (A prompt change
can't affect retrieval — recall was identical — only how the answer is written.)

**Decision:** hybrid search is the default; the section cap and the prompt rule stay
available as options but are off. **What's left:** two employee questions that span two
years or two companies (only 5 chunk slots each, and Item 1 doesn't make it), and answers
that pick the wrong number from a table even when the right section is retrieved — next
step is to save the retrieved chunk text with each result so those numbers can be traced.

### Can the judge be trusted?

Answers are graded by an LLM judge (`judge.py`) against written rules (correct / partial /
incorrect; invented numbers are always incorrect). Before trusting it, I graded 8 answers
by hand and compared: the judge agrees on **7 of 8 (0.88)**, after fixing two problems the
comparison exposed (the judge was run without temperature 0, and one answer key was
incomplete). The remaining disagreement is on a question I later reworded as ambiguous.

See [FAILURES.md](FAILURES.md) for everything that went wrong and what fixed it.
