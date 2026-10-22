# Exact installed CPU image; no new model, dependency, or upstream source.
FROM ghcr.io/hsiang-han/kokoro-fastapi-zh-cpu@sha256:a675c4d280ff08002778468a2687d35c27d0a9709c6a8259afbfa573a72e7e2b
COPY guard.py launch.py verify.py source-lock.json /opt/corvus-kokoro/
RUN /app/.venv/bin/python -B /opt/corvus-kokoro/verify.py
ENTRYPOINT ["/app/.venv/bin/python", "-B", "/opt/corvus-kokoro/launch.py"]
LABEL io.corvus.kokoro.base="sha256:a675c4d280ff08002778468a2687d35c27d0a9709c6a8259afbfa573a72e7e2b" \
      io.corvus.kokoro.privacy="metadata-only-process-logging-v1"
