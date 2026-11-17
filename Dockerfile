FROM ghcr.io/astral-sh/uv@sha256:f459f6f73a8c4ef5d69f4e6fbbdb8af751d6fa40ec34b39a1ab469acd6e289b7 AS uv_tool
FROM python:3.14-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS base
COPY --from=uv_tool /uv /uvx /usr/local/bin/
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
WORKDIR /app

FROM base AS development
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project
COPY README.md ./
COPY src ./src
COPY tests ./tests
COPY data ./data
RUN uv sync --locked
CMD ["uv", "run", "--no-sync", "pytest"]

FROM base AS runtime
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY README.md ./
COPY src ./src
COPY data ./data
RUN uv sync --locked --no-dev && useradd --uid 10001 --create-home app
ENV UV_NO_SYNC=1
USER 10001
ENTRYPOINT ["/app/.venv/bin/snp-allocation"]
