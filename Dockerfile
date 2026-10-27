FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONUTF8=1 PORT=7860
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
RUN python -m src.kb build && python -m src.rag warmup && mkdir -p /app/data/chroma_db && chown -R 1000:1000 /app
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
USER 1000:1000
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','7860')+'/health',timeout=4)"
CMD ["sh", "-c", "uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-7860}"]
