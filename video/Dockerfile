FROM node:22.23.3-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    npm_config_update_notifier=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       python3 make ca-certificates ffmpeg fonts-dejavu-core \
       libnss3 libatk-bridge2.0-0 libx11-xcb1 libxcomposite1 \
       libxdamage1 libxrandr2 libgbm1 libasound2 libcups2 \
       libpango-1.0-0 libcairo2 \
    && apt-get clean

WORKDIR /app/video
COPY video/package.json video/package-lock.json ./
RUN npm ci && npm run browser

# Use the repository root as the Docker build context. Package fixtures are
# read by DepDiff, never installed or executed.
COPY . /app
RUN npm run prepare-demo && npm test && make -C /app test

CMD ["npm", "run", "render"]
