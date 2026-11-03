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

WORKDIR /app/backend

ENV PYTHONPATH=/app/backend
ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && python scripts/seed_pilot_schemes.py || true && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
