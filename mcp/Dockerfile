FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock* ./
# No uv.lock yet — install straight from pyproject.toml (RUN uses /bin/sh, so no bash <(...)).
RUN pip install --no-cache-dir uv && \
    uv pip install --system -r pyproject.toml

COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 9000

CMD ["python", "-m", "server.main"]
