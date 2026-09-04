FROM python:3.12-slim

# Set at build time to the upstream patchright release this image tracks.
ARG PATCHRIGHT_VERSION

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
      xvfb xauth ca-certificates tini \
      fonts-liberation fonts-noto-core fonts-noto-color-emoji \
      wget gnupg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
      "patchright==${PATCHRIGHT_VERSION}" \
      fastapi \
      uvicorn

# Real Google Chrome rather than the bundled chromium test build: that build
# ships without proprietary codecs and reports a SwiftShader WebGL renderer.
# Chrome stable is published for linux/amd64 only, hence the single platform.
RUN patchright install --with-deps chrome \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app.py /app/app.py
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV PORT=3000 \
    USER_DATA_DIR=/data/profile
EXPOSE 3000

ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]
