# The Loop Engine worker image.
#
# Builds the engine from this repository and runs the loop-engine command.
# The base image is pinned by digest (python:3.12-slim as resolved on
# 2026-09-18); update the digest deliberately and record the new one in the
# deployment manifest. No provider key, no model, and no customer data is
# baked into the image.
FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY examples ./examples

RUN python -m pip install --upgrade pip \
    && python -m pip install . \
    && useradd --uid 65534 --no-create-home --shell /usr/sbin/nologin loopengine 2>/dev/null || true

USER 65534
WORKDIR /work
VOLUME ["/work"]

ENTRYPOINT ["loop-engine"]
CMD ["doctor", "--format", "json"]
