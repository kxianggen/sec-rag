"""Ask a question about the filings.

    uv run python ask.py "What did NVIDIA say about export controls?"

Retrieves the top chunks, then asks an LLM to answer from them. Uses Anthropic
if ANTHROPIC_API_KEY is set in .env, otherwise OpenAI if OPENAI_API_KEY is set,
otherwise just prints the retrieved chunks.
"""

import os
import sys

from dotenv import load_dotenv

from retrieve import retrieve_multi
from companies import detect_fiscal_years, detect_latest, detect_tickers

load_dotenv()


def build_prompt(question: str, chunks: list[dict]) -> str:
    context = "\n\n".join(
                f"[{i}] {c['ticker']} 10-K, fiscal {c['fiscal_year']} (period ending {c['period_end']}), Item {c['item']}\n{c['text']}"
        for i, c in enumerate(chunks, 1)
    )
    return f"""You answer questions about companies' SEC 10-K filings. Follow these rules:
1. Use only the numbered excerpts below. Do not use outside knowledge, even if you know the answer.
2. After every claim, cite the excerpt it came from, like [1] or [2][3].
3. When you state a fact, say which company and which fiscal period it comes from.
4. If the excerpts do not contain the answer, reply exactly: Not in the filings.

Excerpts:
{context}

Question: {question}"""


def call_llm(prompt: str, temperature: float | None = None) -> str | None:
    """temperature=None uses the provider default; the judge passes 0 so its grades repeat."""
    extra = {} if temperature is None else {"temperature": temperature}
    if os.getenv("ANTHROPIC_API_KEY"):
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5"),
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
            **extra,
        )
        return resp.content[0].text
    if os.getenv("OPENAI_API_KEY"):
        from openai import OpenAI
        client = OpenAI()
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            **extra,
        )
        return resp.choices[0].message.content
    return None


def main():
    question = " ".join(sys.argv[1:])
    if not question:
        sys.exit('Usage: uv run python ask.py "your question"')

    tickers = detect_tickers(question)
    years = detect_fiscal_years(question)
    latest = detect_latest(question)
    chunks = retrieve_multi(question, k=10, tickers=tickers, fiscal_years=years, latest=latest)
    print(f"\nCOMPANY FILTER: {tickers or 'none (searching all companies)'}")
    print(f"FISCAL YEAR FILTER: {years or ('latest filing per company' if latest else 'none (all years)')}")
    answer = call_llm(build_prompt(question, chunks))

    print("\nANSWER\n" + (answer or "(no API key set — showing retrieved chunks only)"))
    print("\nSOURCES")
    for i, c in enumerate(chunks, 1):
        print(f"[{i}] {c['score']:.3f}  {c['ticker']} {c['period_end']} Item {c['item']}")


if __name__ == "__main__":
    main()
