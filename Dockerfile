FROM python:3.11.2-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY . /app

# The project has no runtime dependencies. The local PEP 517 backend keeps
# installation reproducible without contacting an index or running package code.
RUN pip install --no-cache-dir --no-index --no-deps . \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin depdiff \
    && chown -R depdiff:depdiff /app

USER depdiff

ENTRYPOINT ["depdiff"]
CMD ["--help"]
