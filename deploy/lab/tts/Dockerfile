# Lab-only derivative of the exact active HTTPS/UI-2.1 image. No dependency install.
FROM corvus-open-webui@sha256:453f9f2c4cee37c5e0d158ed3fcbdfc1e099bc6ef55ab47a7cbcce8b7331df76
COPY kokoro.py /app/backend/open_webui/routers/corvus_tts.py
COPY prepare_audio.py /opt/corvus-tts1/prepare_audio.py
RUN python -B /opt/corvus-tts1/prepare_audio.py /app/backend/open_webui/routers/audio.py /app/build
LABEL org.opencontainers.image.version="0.6.5-arena-ui2.1-https-tts1" \
    io.corvus.scope="lab" \
    io.corvus.tts1.base="sha256:453f9f2c4cee37c5e0d158ed3fcbdfc1e099bc6ef55ab47a7cbcce8b7331df76"
# Inherit authentication, frontend controls, persistent volume and all dependencies.
# Enabling the engine/permission requires the separate, prepared Compose override.
