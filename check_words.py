import json, re
from pathlib import Path

sections = {}
for path in Path("data/text").glob("*/*.json"):
    filing = json.loads(path.read_text(encoding="utf-8"))
    for s in filing["sections"]:
        sections[(filing["ticker"], filing["period_end"], s["item"])] = s["text"]

def whole_word(word, text):
    return re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", text) is not None

bad, too_long, total = [], 0, 0
for line in open("data/chunks.jsonl", encoding="utf-8"):
    c = json.loads(line)
    total += 1
    if len(c["text"]) > 1000:
        too_long += 1
    words = c["text"].split()
    src = sections[(c["ticker"], c["period_end"], c["item"])]
    for w in (words[0], words[-1]):
        if not whole_word(w, src):
            bad.append((c["id"], w))

print(f"{total:,} chunks | over 1000 chars: {too_long} | cut mid-word: {len(bad)}")
for cid, w in bad[:5]:
    print("  e.g.", cid, repr(w))