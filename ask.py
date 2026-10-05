"""Ask a question about the filings.

    uv run python ask.py "What did NVIDIA say about export controls?"

Retrieves the top chunks, then asks an LLM to answer from them. Uses Anthropic
if ANTHROPIC_API_KEY is set in .env, otherwise OpenAI if OPENAI_API_KEY is set,
otherwise just prints the retrieved chunks.
"""

import os
import sys

from dotenv import load_dotenv

from retrieve import retrieve
from companies import detect_ticker, detect_fiscal_year

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


def call_llm(prompt: str) -> str | None:
    if os.getenv("ANTHROPIC_API_KEY"):
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5"),
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text
    if os.getenv("OPENAI_API_KEY"):
        from openai import OpenAI
        client = OpenAI()
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content
    return None


def main():
    question = " ".join(sys.argv[1:])
    if not question:
        sys.exit('Usage: uv run python ask.py "your question"')

    ticker = detect_ticker(question)
    fy = detect_fiscal_year(question)
    chunks = retrieve(question, k=5, ticker=ticker, fiscal_year=fy)
    print(f"\nCOMPANY FILTER: {ticker or 'none (searching all companies)'}")
    print(f"FISCAL YEAR FILTER: {fy or 'none (all years)'}")
    answer = call_llm(build_prompt(question, chunks))

    print("\nANSWER\n" + (answer or "(no API key set — showing retrieved chunks only)"))
    print("\nSOURCES")
    for i, c in enumerate(chunks, 1):
        print(f"[{i}] {c['score']:.3f}  {c['ticker']} {c['period_end']} Item {c['item']}")


if __name__ == "__main__":
    main()
