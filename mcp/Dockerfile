FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock* ./
RUN pip install --no-cache-dir uv && \
    uv pip install --system -r <(uv pip compile pyproject.toml)

COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 9000

CMD ["python", "-m", "server.main"]
