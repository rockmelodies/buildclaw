FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV BUILDCLAW_ADDR=0.0.0.0
ENV BUILDCLAW_PORT=8080

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/pyproject.toml
COPY app /app/app
COPY scripts /app/scripts
COPY config.example.yaml /app/config.example.yaml
COPY .env.example /app/.env.example

RUN python -m pip install --upgrade pip \
    && python -m pip install -e .

RUN mkdir -p /app/workspace

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8080/readyz || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
