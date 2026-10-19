FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_SYSTEM_PYTHON=1

RUN pip install --no-cache-dir uv \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser

COPY api/pyproject.toml api/uv.lock ./
ARG UV_SYNC_ARGS=--no-dev
RUN uv sync --frozen ${UV_SYNC_ARGS}

COPY api/src ./src
COPY api/scripts ./scripts
COPY api/alembic.ini ./

RUN chown -R appuser:appuser /app

USER appuser
EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
