# sec-rag web app: FastAPI + hybrid search + XBRL facts, CPU only.
#   docker build -t sec-rag .
#   docker run --rm -p 8000:7860 --env-file .env sec-rag      -> http://localhost:8000
# Secrets (OPENAI_API_KEY, DATABASE_URL) are passed in when the container STARTS (--env-file or the host's
# secret settings). They are never copied into the image: .dockerignore excludes .env.

# 1. Start from a small official Linux image that already has Python 3.11 (same version as .python-version)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/.cache/huggingface \
    PORT=7860

WORKDIR /app

# 2. PyTorch, CPU-only build. The default build bundles ~3 GB of NVIDIA GPU libraries this app never uses.
RUN pip install --no-cache-dir torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu

# 3. Everything else the web app imports at runtime (pinned to the versions in uv.lock)
COPY requirements-deploy.txt .
RUN pip install --no-cache-dir -r requirements-deploy.txt

# 4. Download the embedding model now, so the container never needs the internet to start
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
ENV HF_HUB_OFFLINE=1

# 5. The app code and the data it searches (8,883 chunks + vectors, 21,821 XBRL facts)
COPY app.py ask.py retrieve.py companies.py facts.py metrics.py ./
COPY static/ static/
COPY data/chunks_final.jsonl data/embeddings_final.npy data/facts.jsonl data/

# 6. Run as an ordinary user, not root (safer; Hugging Face Spaces also expects user id 1000)
RUN useradd -m -u 1000 user && chown -R user /app
USER user

# 7. Start the web server. ${PORT} lets a host choose the port (Hugging Face uses 7860).
EXPOSE 7860
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT}
