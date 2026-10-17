"""Stage 8: serve sec-rag over HTTP.

    uv run uvicorn app:app --reload          # then open http://localhost:8000/docs

GET  /        the web page (static/index.html)
POST /ask     {"question": "..."}  ->  answer + sources + the filters that were used
GET  /health  is the server up? (also touches the database, which keeps Supabase awake)

Same pipeline as ask.py and eval.py: detect companies / years -> hybrid retrieval (k = 10)
-> grounded prompt -> LLM at temperature 0. Pick the store with SEC_RAG_STORE in .env
("numpy" = local files, "pgvector" = Supabase).

Public URL = anyone can spend your API credit, so two limits (both settable in .env):
  RATE_PER_IP_PER_HOUR   questions one visitor may ask per hour        (default 20)
  DAILY_LIMIT            questions everyone together may ask per day   (default 200)
"""

import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

load_dotenv()

import retrieve  # noqa: E402  (after load_dotenv, so SEC_RAG_STORE is read)
from ask import build_prompt, call_llm  # noqa: E402
from companies import detect_fiscal_years, detect_latest, detect_tickers  # noqa: E402
from facts import lookup as lookup_facts  # noqa: E402  (Phase 2: exact XBRL figures)
from metrics import REFUSAL, is_refusal  # noqa: E402

K = 10
RATE_PER_IP_PER_HOUR = int(os.getenv("RATE_PER_IP_PER_HOUR", "20"))
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "200"))


# ---------- request / response shapes (FastAPI checks these and shows them in /docs) ----------

class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=300,
                          examples=["How many employees did NVIDIA have at the end of fiscal 2026?"])


class Source(BaseModel):
    n: int                 # the [n] the answer cites
    ticker: str
    fiscal_year: int
    period_end: str
    item: str
    text: str


class Filters(BaseModel):
    tickers: list[str]
    fiscal_years: list[int]
    latest: bool


class AskResponse(BaseModel):
    question: str
    answer: str
    refused: bool
    filters: Filters
    sources: list[Source]
    seconds: float


# ---------- cost protection ----------

_recent = defaultdict(deque)       # visitor IP -> times of their recent questions
_today = {"date": date.today(), "count": 0}


def _check_limits(ip: str) -> None:
    now = time.time()
    if _today["date"] != date.today():
        _today["date"], _today["count"] = date.today(), 0
    if _today["count"] >= DAILY_LIMIT:
        raise HTTPException(429, "Daily question limit reached for this demo. Please try again tomorrow.")
    times = _recent[ip]
    while times and now - times[0] > 3600:
        times.popleft()
    if len(times) >= RATE_PER_IP_PER_HOUR:
        raise HTTPException(429, f"Limit of {RATE_PER_IP_PER_HOUR} questions per hour reached. Please wait a while.")
    times.append(now)
    _today["count"] += 1


def _client_ip(request: Request) -> str:
    # Behind a hosting proxy the real visitor is the first address in X-Forwarded-For.
    forwarded = request.headers.get("x-forwarded-for")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "?")


# ---------- app ----------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the model, chunks and BM25 index once at start-up, so the first visitor isn't
    # the one who waits ~10 s for it.
    retrieve.retrieve_multi("warm up", k=1, mode="hybrid")
    yield


app = FastAPI(title="sec-rag", description="Questions about six US chip makers' 10-K filings, "
              "answered only from the filings, with sources.", lifespan=lifespan)


@app.get("/", include_in_schema=False)
def home():
    # The page calls /ask on this same server, so the browser never sees the API key
    # and no cross-site (CORS) settings are needed.
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health")
def health():
    if retrieve.STORE == "pgvector":
        retrieve._connect().execute("select 1")
    return {"status": "ok", "store": retrieve.STORE, "chunks": len(retrieve._chunks)}


@app.post("/ask", response_model=AskResponse)
def ask(body: AskRequest, request: Request):
    # A plain `def` (not `async def`): retrieval and the LLM call block while they wait, so
    # FastAPI runs this in a worker thread and other visitors aren't stuck behind it.
    _check_limits(_client_ip(request))
    start = time.time()
    question = body.question.strip()

    tickers = detect_tickers(question)
    years = detect_fiscal_years(question)
    latest = detect_latest(question)
    chunks = retrieve.retrieve_multi(question, k=K, tickers=tickers, fiscal_years=years,
                                     latest=latest, mode="hybrid")
    # exact figures from the filings' XBRL data, numbered after the passages (0.67 -> 0.77 in eval)
    chunks = chunks + lookup_facts(question, tickers, years, latest) if chunks else chunks
    if not chunks:
        # e.g. "fiscal 2028": the filters matched no filing, so skip the paid LLM call
        return AskResponse(question=question, answer=REFUSAL, refused=True,
                           filters=Filters(tickers=tickers, fiscal_years=years, latest=latest and not years),
                           sources=[], seconds=round(time.time() - start, 2))
    try:
        answer = call_llm(build_prompt(question, chunks), temperature=0)
    except Exception as e:                      # provider down, bad key, network...
        raise HTTPException(502, f"The language model call failed: {type(e).__name__}")
    if answer is None:
        raise HTTPException(503, "No LLM API key is configured on the server.")

    return AskResponse(
        question=question,
        answer=answer,
        refused=is_refusal(answer),
        filters=Filters(tickers=tickers, fiscal_years=years, latest=latest and not years),
        sources=[Source(n=i, ticker=c["ticker"], fiscal_year=c["fiscal_year"], period_end=c["period_end"],
                        item=c["item"], text=c["text"]) for i, c in enumerate(chunks, 1)],
        seconds=round(time.time() - start, 2),
    )
