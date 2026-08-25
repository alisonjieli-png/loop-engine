FROM python@sha256:2407c61b1a18067393fecd8a22cf6fceede893b6aaca817bf9fbfe65e33614a3

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    CUDA_VISIBLE_DEVICES=-1

COPY requirements.lock /tmp/requirements.lock
RUN python -m pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock \
    && rm /tmp/requirements.lock \
    && useradd --uid 65532 --no-create-home --shell /usr/sbin/nologin evaluator

WORKDIR /app
COPY --chown=65532:65532 .cache/upstream/execution.py /app/execution.py
COPY --chown=65532:65532 evaluator_one.py /app/evaluator_one.py

USER 65532:65532
CMD ["python", "/app/evaluator_one.py"]

