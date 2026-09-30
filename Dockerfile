# The Loop Engine worker image.
#
# Builds the engine and its pinned OpenCode adapter. The engine's own harness
# remains the default; OpenCode is an explicitly selected per-step adapter.
# The base image is pinned by digest (python:3.12-slim as resolved on
# 2026-09-18); update the digest deliberately and record the new one in the
# deployment manifest. No provider key, no model, and no customer data is
# baked into the image.
FROM node:24-bookworm-slim@sha256:0e0ff40c39bc087845bfb27465a0df4ea419520094bc35842ff83dd8cbe6f9b6 AS harnesses
WORKDIR /harnesses
COPY containers/worker/package.json containers/worker/package-lock.json ./
ARG TARGETARCH
# The lockfile pins the platform binary. Select it directly without running an
# installer that could fetch a fallback outside that lockfile. x64 uses the
# baseline build so an older CPU does not need AVX2.
RUN npm ci --omit=dev --ignore-scripts --no-audit --no-fund \
    && node -e 'const fs=require("fs"),p={amd64:"opencode-linux-x64-baseline",arm64:"opencode-linux-arm64"}[process.env.TARGETARCH];if(!p)throw Error("unsupported worker architecture");const root="/usr/local/lib/node_modules/opencode-ai";fs.mkdirSync(root+"/bin",{recursive:true});fs.copyFileSync(require.resolve(p+"/bin/opencode"),root+"/bin/opencode.exe");for(const f of ["LICENSE","package.json"])fs.copyFileSync("node_modules/opencode-ai/"+f,root+"/"+f);fs.chmodSync(root+"/bin/opencode.exe",0o755)' \
    && ln -s /usr/local/lib/node_modules/opencode-ai/bin/opencode.exe /usr/local/bin/opencode \
    && opencode --version

FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/tmp/baltor-home

RUN apt-get update \
    && apt-get install --yes --no-install-recommends bubblewrap git ca-certificates libstdc++6 libatomic1 \
    && rm -r /var/lib/apt/lists \
    && ln -s /usr/local/bin/python3 /usr/bin/python3
COPY --from=harnesses /usr/local/ /usr/local/

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY examples ./examples
COPY containers/worker/opencode-harness.json /opt/baltor/opencode-harness.json
COPY containers/worker/baltor-harness.json /opt/baltor/baltor-harness.json
COPY src/loop_engine/core/harness_baltor_recipe.py /opt/baltor/baltor_harness.py
COPY tools/check_harness_fresh_instances.py /opt/baltor/check_harness_fresh_instances.py
COPY containers/worker/run-task.py /usr/local/bin/baltor-worker

RUN python -m pip install --upgrade pip \
    && python -m pip install . \
    && mkdir -p /work \
    && chown 65534:65534 /work \
    && chmod 0555 /usr/local/bin/baltor-worker

USER 65534
WORKDIR /work
VOLUME ["/work"]

ENTRYPOINT ["loop-engine"]
CMD ["doctor", "--format", "json"]
