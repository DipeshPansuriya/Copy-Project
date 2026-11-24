FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps: libmagic required by python-magic for file type verification.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static

ENV CLIP_DATA_DIR=/data
# Default to local-disk storage so `docker compose up` works without MinIO.
# Switch CLIP_STORAGE=minio + MINIO_ENDPOINT to use the MinIO service below.
ENV CLIP_STORAGE=local

EXPOSE 8000

# Run the app; uvicorn handles graceful shutdown so the purge worker stops cleanly.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
