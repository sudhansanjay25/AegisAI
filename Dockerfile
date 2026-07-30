FROM python:3.11.9-slim

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app

ENV PATH="/app/.venv/bin:$PATH"
ENV PORT=8000
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
