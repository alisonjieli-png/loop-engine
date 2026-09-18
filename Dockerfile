# The Loop Engine worker image.
#
# Builds the engine from this repository and runs the loop-engine command.
# The base image is pinned by tag; pin it by digest before production use
# and record the digest in the deployment manifest. No provider key, no
# model, and no customer data is baked into the image.
FROM python:3.12-slim

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
