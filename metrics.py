REFUSAL = "Not in the filings."

def is_refusal(answer: str) -> bool:
    """True if the answer is a refusal. Ignore spaces/newlines around it."""
    clean_answer = answer.strip()
    if clean_answer and clean_answer == REFUSAL:
        return True
    else:
        return False

def source_found(source: dict, chunks: list[dict]) -> bool:
    """True if ANY chunk has the same ticker, period_end AND item as source."""
    for i in chunks:
        if i["ticker"] == source["ticker"] and i["period_end"] == source["period_end"] and i["item"] == source["item"]:
            return True
        else:
            continue
    return False

def source_recall(sources: list[dict], chunks: list[dict]) -> float | None:
    """Fraction of golden sources found in chunks. None if sources is empty."""
    if not sources:
        return None
    count = 0
    for i in sources:
        if source_found(i, chunks):
            count += 1
    return count/len(sources)


def refusal_correct(answer: str, expected: str) -> bool:
    """True when the system refused exactly when it should have."""
    refused = is_refusal(answer)
    should_refuse = is_refusal(expected)
    if refused == should_refuse:
        return True
    else:
        return False