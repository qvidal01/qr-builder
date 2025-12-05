FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \    build-essential \    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY qr_builder ./qr_builder

RUN pip install --no-cache-dir build && \    python -m build && \    pip install --no-cache-dir dist/*.whl || pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["qr-builder-api"]
