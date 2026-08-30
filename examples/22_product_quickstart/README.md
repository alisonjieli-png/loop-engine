# Product quickstart acceptance

This example exercises the public solver capability envelope with four changed
tasks. Task text and fixture implementations live here, not in the generic
runtime.

The offline model adapter validates typed model and gateway contracts. It does
not prove live-provider quality. File writes, Docker commands, artifact checks,
and Run History are real.

```bash
PYTHONPATH=src python3 examples/22_product_quickstart/run_acceptance.py \
  --output-root /tmp/loop-engine-product-acceptance
```

The script produces one JSON result per task and a combined acceptance report.
Run an authorized live provider solve separately before claiming provider
support.
