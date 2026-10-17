# Lab-only backend manifest correction; reuse the exact active UI-2.1 frontend.
FROM corvus-open-webui@sha256:8dea93c991ce80e1d1496783ee7badca025ec38be3fee666a682a679705980be
COPY prepare_manifest.py manifest.json /opt/corvus-https/
RUN python -B /opt/corvus-https/prepare_manifest.py /app/backend/open_webui/main.py
LABEL org.opencontainers.image.version="0.6.5-arena-ui2.1-https-r03b" \
    io.corvus.scope="lab" \
    io.corvus.https.base="sha256:8dea93c991ce80e1d1496783ee7badca025ec38be3fee666a682a679705980be"
# Inherit entrypoint, dependencies, frontend, Pipe handling and authentication.
