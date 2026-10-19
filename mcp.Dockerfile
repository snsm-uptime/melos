FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_SYSTEM_PYTHON=1

RUN pip install --no-cache-dir uv \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser

COPY mcp/pyproject.toml mcp/uv.lock ./
ARG UV_SYNC_ARGS=--no-dev
RUN uv sync --frozen ${UV_SYNC_ARGS}

COPY mcp/server ./server
COPY mcp/tools ./tools

RUN chown -R appuser:appuser /app

USER appuser
EXPOSE 9000

CMD ["uv", "run", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "9000"]
