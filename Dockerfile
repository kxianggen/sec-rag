# sec-rag web app: FastAPI + hybrid search + XBRL facts. Slim build for a 512 MB host (no PyTorch).
#   docker build -t sec-rag .
#   docker run --rm -p 8000:7860 --env-file .env sec-rag      -> http://localhost:8000
#   docker run --rm -p 8000:7860 --env-file .env --memory 512m --cpus 0.1 sec-rag   # rehearse Render's free tier
# Secrets (OPENAI_API_KEY ...) are passed in when the container STARTS (--env-file, or the host's
# environment settings). They are never copied into the image: .dockerignore excludes .env.

# 1. Start from a small official Linux image that already has Python 3.11 (same version as .python-version)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SEC_RAG_EMBEDDER=onnx \
    FASTEMBED_CACHE_PATH=/app/.cache/fastembed \
    PORT=7860

WORKDIR /app

# 2. What the web app imports at runtime (pinned). Questions are embedded with ONNX Runtime (fastembed):
#    same all-MiniLM-L6-v2 model, but no PyTorch -- the image and its memory use are about half the size.
COPY requirements-deploy.txt .
RUN pip install --no-cache-dir -r requirements-deploy.txt

# 3. Download the ONNX model now, so the container never needs the internet to start
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/all-MiniLM-L6-v2')"
ENV HF_HUB_OFFLINE=1

# 4. The app code and the data it searches (8,883 chunks + vectors, 21,821 XBRL facts)
COPY app.py ask.py retrieve.py companies.py facts.py metrics.py ./
COPY static/ static/
COPY data/chunks_final.jsonl data/embeddings_final.npy data/facts.jsonl data/

# 5. Run as an ordinary user, not root (safer)
RUN useradd -m -u 1000 user && chown -R user /app
USER user

# 6. Start the web server. ${PORT} lets the host choose the port (Render sets PORT=10000; default here 7860).
#    "exec" makes uvicorn the main process, so stop signals (Ctrl+C, a redeploy) reach it directly.
EXPOSE 7860
CMD ["sh", "-c", "exec uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
