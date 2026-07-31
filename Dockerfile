FROM python:3.11.9-slim

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app
COPY tests ./tests

ENV PATH="/app/.venv/bin:$PATH"

# Pre-download the embedding model so it's baked into the Docker image
# This eliminates cold-start latency and avoids HF Hub rate limits at runtime
RUN python -c "from app.ingestion.embed import get_model; get_model()"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
