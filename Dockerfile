FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Europe/Berlin \
    LANG=C.UTF-8 \
    LANGUAGE=de \
    HOME=/data \
    BI_STORCHCAM_CONFIG=/data/config.json

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        chromium \
        libegl1 \
        libgles2 \
        libgl1-mesa-dri \
        fonts-dejavu-core \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /etc/chromium/policies/managed \
    && echo '{"TranslateEnabled": false}' > /etc/chromium/policies/managed/kiosk.json

# Aus einem temporären Quellordner installieren, damit im Image keine Build-Reste zurückbleiben.
COPY pyproject.toml README.md LICENSE /tmp/src/
COPY bi_storchcam /tmp/src/bi_storchcam
RUN pip install /tmp/src tzdata \
    && rm -rf /tmp/src \
    && mkdir -p /data && chown 1000:1000 /data

WORKDIR /app
COPY --chmod=644 docker-entrypoint.py ./

USER 1000:1000
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=360s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"

ENTRYPOINT ["python", "/app/docker-entrypoint.py"]
