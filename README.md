# sec-rag — question answering over SEC 10-K filings

Ask questions about six US semiconductor companies' annual reports (NVIDIA, AMD, Micron,
Broadcom, Qualcomm, Marvell; fiscal years 2023–2026) and get answers that quote only the
filings, cite their sources, and say "Not in the filings." when the answer isn't there.

*Full README (architecture, setup, demo) in progress. Results so far:*

## Results

Measured on 12 hand-written golden questions (10 answerable + 2 unanswerable) with
`eval.py`. Retrieval: top 5 chunks. Answers graded by an LLM judge (see below).

| Stage | Change | Recall@5 | Refusal ok | Answer score |
|---|---|---|---|---|
| Baseline (T10) | dense retrieval, company + year filters | 0.50 | 8/12 | — |
| T11 | detect every fiscal year in the question | 0.60 | 10/12 | — |
| T12 | retrieve per company for cross-company questions | 0.65 | 12/12 | — |
| T14 | "latest fiscal year" → each company's newest filing | 0.65 | 10/12 | 0.62 |

- **Recall@5:** share of the golden source passages (company + filing + section) found in
  the top 5 chunks, averaged over answerable questions.
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

### Can the judge be trusted?

Answers are graded by an LLM judge (`judge.py`) against written rules (correct / partial /
incorrect; invented numbers are always incorrect). Before trusting it, I graded 8 answers
by hand and compared: the judge agrees on **7 of 8 (0.88)**, after fixing two problems the
comparison exposed (the judge was run without temperature 0, and one answer key was
incomplete). The remaining disagreement is on a question I later reworded as ambiguous.

See [FAILURES.md](FAILURES.md) for everything that went wrong and what fixed it.
