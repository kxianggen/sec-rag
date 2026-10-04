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
from companies import detect_ticker

load_dotenv()


def build_prompt(question: str, chunks: list[dict]) -> str:
    context = "\n\n".join(
        f"[{i}] {c['ticker']} 10-K, period ending {c['period_end']}, Item {c['item']}\n{c['text']}"
        for i, c in enumerate(chunks, 1)
    )
    return f"Here are excerpts from SEC filings:\n\n{context}\n\nQuestion: {question}"


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
    chunks = retrieve(question, k=5, ticker=ticker)
    print(f"\nCOMPANY FILTER: {ticker or 'none (searching all companies)'}")
    answer = call_llm(build_prompt(question, chunks))

    print("\nANSWER\n" + (answer or "(no API key set — showing retrieved chunks only)"))
    print("\nSOURCES")
    for i, c in enumerate(chunks, 1):
        print(f"[{i}] {c['score']:.3f}  {c['ticker']} {c['period_end']} Item {c['item']}")


if __name__ == "__main__":
    main()
