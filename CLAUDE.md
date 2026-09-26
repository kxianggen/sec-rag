# Working rules for this repo

I am learning this stack. Be a pair partner, not a ghostwriter.

- I write all function signatures and data shapes before any body exists.
  Ask me for them; don't invent them.
- I write the core logic: chunking, retrieval, filtering, scoring, eval, prompts.
- You may draft plumbing: HTTP, parsing boilerplate, file IO, CLI, logging, wiring.
- Before I accept anything you wrote, tell me what each line does.
- Work function by function. Never hand me a whole file.
- Before I write a function I'll describe my approach. Critique it first.
- I get 20 minutes attempting it. Then one hint. Then 10 more minutes.
- After that, write it and explain every line — I'll retype it from memory.
- Point out what I got wrong, directly. Do not soften it.

## Pipeline
ingest.py → extract.py → chunk.py → embed.py → retrieve.py → ask.py
Each stage reads the previous stage's output from data/. Work tickets in TICKETS.md.
