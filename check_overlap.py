import json

with open("data/chunks.jsonl", encoding="utf-8") as f:
    lines = f.readlines()

a = json.loads(lines[0])
b = json.loads(lines[1])

print("CHUNK 0 ENDS WITH:\n", a["text"][-150:])
print("\nCHUNK 1 STARTS WITH:\n", b["text"][:150])
print("\nSame?", a["text"][-150:] == b["text"][:150])