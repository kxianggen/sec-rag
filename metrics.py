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

def verdict_score(verdict: str) -> float | None:
    """'correct' -> 1.0, 'partial' -> 0.5, 'incorrect' -> 0.0, anything else -> None."""
    if verdict == 'correct':
        return 1.0
    elif verdict == 'partial':
        return 0.5
    elif verdict == 'incorrect':
        return 0.0
    else:
        return None

def agreement(human: dict[int, str], judged: dict[int, str]) -> float | None:
    """Of the questions BOTH graded, the fraction where the verdicts match. None if none shared."""
    if not human:
        return None
    count = 0
    shared_question = 0
    for n in human:
        if n in judged:
            shared_question += 1
            if human[n] == judged[n]:
                count += 1
    if shared_question == 0:
        return None
    return count/shared_question