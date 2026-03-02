FROM python:3.14 AS builder

RUN apt-get update --no-install-recommends && \
    apt-get install -y build-essential curl unzip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY loom /app/loom/
COPY scripts/cythonizer.py /app/scripts/cythonizer.py
COPY pyproject.toml /app/
COPY README.md /app/
COPY Makefile /app/

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

RUN . $HOME/.local/bin/env && \
    uv sync --no-dev && \
    uv pip install cython wheel && \
    make compile && \
    uv pip install --no-cache-dir dist/*.whl && \
    rm -rf Makefile scripts pyproject.toml README.md dist loom uv.lock

FROM python:3.14-slim AS runtime

WORKDIR /app

COPY --from=builder /app /app
COPY scripts/serve.py /app/serve.py

ENTRYPOINT [ ".venv/bin/python", "serve.py" ]
