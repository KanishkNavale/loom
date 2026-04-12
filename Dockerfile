FROM python:3.14 AS build

RUN apt-get update --no-install-recommends && \
    apt-get install -y --no-install-recommends build-essential curl unzip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /loom

COPY ./loom /loom/loom/
COPY ./pyproject.toml /loom/
COPY ./scripts/serve.py /loom/
COPY ./scripts/cythonizer.py /loom/
COPY Makefile /loom/Makefile
COPY README.md /loom/README.md
COPY LICENSE /loom/LICENSE

RUN uv sync --no-dev && \
    uv pip install cython wheel && \
    make compile && \
    uv pip install --no-cache-dir dist/*.whl && \
    rm -rf Makefile tag_interface.py pyproject.toml cythonizer.py README.md dist loom uv.lock


FROM python:3.14-slim AS final

LABEL author="Kanishk Navale"

WORKDIR /loom

COPY --from=build /loom/.venv /loom/.venv/
COPY --from=build /loom/serve.py /loom/

ENV HOME=/loom
ENV PATH="/loom/.venv/bin:$PATH"

ENTRYPOINT ["/loom/.venv/bin/python3", "/loom/serve.py"]
