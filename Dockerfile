FROM python:3.12-slim

# Prevent bytecode creation and enforce unbuffered stdout/stderr logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app/src:/app"

# 1. Create a dedicated non-root user with explicit UID/GID 1000 for volume compatibility
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -d /app -s /bin/bash appuser

WORKDIR /app

# 2. Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# 3. Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy project files and ensure storage target directories exist
COPY . .
RUN mkdir -p /app/storage /app/data && \
    chown -R appuser:appgroup /app

# 5. Switch to non-root user
USER appuser

EXPOSE 8010

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8010"]