FROM python:3.12-slim AS builder

ARG TORCH_VARIANT=cpu

COPY --from=ghcr.io/astral-sh/uv:0.7.13 /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --extra ${TORCH_VARIANT}

COPY . .
RUN uv sync --frozen --no-dev --extra ${TORCH_VARIANT}

FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-jpn \
        tesseract-ocr-chi-sim \
        tesseract-ocr-kor \
        tesseract-ocr-spa \
        tesseract-ocr-fra \
        tesseract-ocr-deu \
        tesseract-ocr-por \
        tesseract-ocr-ita \
        ccache \
        libgl1 \
        libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app /app

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /app/uploads && chown -R appuser:appuser /app/uploads

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/pipeline/runs?limit=1')" || exit 1

CMD ["uvicorn", "ocr_manga_title.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
