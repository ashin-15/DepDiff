FROM python:3.11.2-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/showcase
COPY showcase/ /srv/showcase/
# Keep deployment-only files out of the served directory. No packages are installed.
RUN rm -f /srv/showcase/Dockerfile /srv/showcase/.dockerignore

USER 10001:10001
EXPOSE 4173

CMD ["python3", "-m", "http.server", "4173", "--bind", "0.0.0.0", "--directory", "/srv/showcase"]
