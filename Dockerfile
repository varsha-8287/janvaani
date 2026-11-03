FROM python:3.11-slim

# Install system audio and ffmpeg dependencies for PyAV / soundfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libavfilter-dev \
    pkg-config \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code and dataset
COPY backend/ /app/backend/
COPY janvaani_government_schemes_dataset/ /app/janvaani_government_schemes_dataset/
COPY scripts/ /app/scripts/

WORKDIR /app/backend

ENV PYTHONPATH=/app/backend:/app
ENV PORT=8000
ENV BHASHINI_USER_ID=7f7a16dbb2564131bee470d969899203
ENV BHASHINI_ULCA_API_KEY=378f6c24b8-ea4e-4c3c-98b7-23bdb2e96e8c
ENV BHASHINI_TIMEOUT_SECONDS=8
ENV JANVAANI_DEV_AUTH=true
ENV JANVAANI_DEV_REVIEWER_AUTH=true

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
