ARG BASE_IMAGE
FROM ${BASE_IMAGE} AS verified
USER root
COPY patch /opt/corvus-build/patch
COPY outputs /opt/corvus-build/outputs
COPY install_verified.py /opt/corvus-build/install_verified.py
RUN python -B /opt/corvus-build/install_verified.py

FROM ${BASE_IMAGE}
COPY --from=verified --chown=1000:1000 /app/api/hindsight_api/engine/llm_wrapper.py /app/api/hindsight_api/engine/llm_wrapper.py
COPY --from=verified --chown=1000:1000 /app/api/hindsight_api/engine/retain/fact_extraction.py /app/api/hindsight_api/engine/retain/fact_extraction.py
COPY --from=verified --chown=1000:1000 /app/api/hindsight_api/engine/retain/orchestrator.py /app/api/hindsight_api/engine/retain/orchestrator.py
COPY --from=verified --chown=1000:1000 /app/api/hindsight_api/engine/consolidation/consolidator.py /app/api/hindsight_api/engine/consolidation/consolidator.py
COPY --from=verified --chown=1000:1000 /app/api/hindsight_api/engine/memory_engine.py /app/api/hindsight_api/engine/memory_engine.py
COPY --from=verified --chown=1000:1000 /app/api/hindsight_api/engine/foreground_admission.py /app/api/hindsight_api/engine/foreground_admission.py
COPY --from=verified --chown=1000:1000 /app/api/hindsight_api/engine/providers/openai_compatible_llm.py /app/api/hindsight_api/engine/providers/openai_compatible_llm.py
COPY --from=verified --chown=1000:1000 /app/api/hindsight_api/engine/consolidation_budget.py /app/api/hindsight_api/engine/consolidation_budget.py
COPY patch/manifest.json patch/apply.py verify_runtime.py /opt/corvus-admission/
