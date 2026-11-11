FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY pyproject.toml app.py ./
COPY src ./src
COPY scripts ./scripts
RUN pip install -e . --no-deps
RUN useradd -m appuser && mkdir -p /data /app/uploads && chown -R appuser /data /app
USER appuser
ENV PROCURAAI_DATA_DIR=/data/procuraai-data PROCURAAI_DB_URL=sqlite:////data/procuraai.db PROCURAAI_UPLOAD_DIR=/data/uploads
EXPOSE 8000 8501
# Generate the synthetic dataset on first start if it is missing, then serve the API.
CMD ["sh", "-c", "[ -d $PROCURAAI_DATA_DIR/structured ] || python scripts/generate_synthetic_data.py --out $PROCURAAI_DATA_DIR; uvicorn procuraai.api.app:app --host 0.0.0.0 --port 8000"]
