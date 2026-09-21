# Run the intelligence service locally

Kind: executable local setup example. No provider account or model key is needed.

This starts the actual website, authorized metadata search, body retrieval,
usage records and Model Context Protocol transport. The example material is
first-party text with an explicit host attestation. It is not an independently
qualified starter catalogue, a paid subscription or a live cloud deployment.

## Prepare and start

Install from this repository with Python 3.12. Select a new absolute directory
beneath an existing directory you control. The preparation command refuses
existing paths and writes no credential.

```bash
python -m pip install '.[serving]'
python examples/29_intelligence_service/prepare.py --directory /absolute/path/loop-service-demo --allow-write --operator-access-seconds 3600
loop-engine service configure --config /absolute/path/loop-service-demo/host.json
loop-engine service issue-key --config /absolute/path/loop-service-demo/host.json --tenant demo
loop-engine service serve --config /absolute/path/loop-service-demo/host.json --host 127.0.0.1 --port 8000
```

The explicit operator option grants one hour of example-body access, not
payment status. Omit it for metadata-only access. Save the one-time key output
privately. Do not capture it in logs or paste it into chat.

Visit `http://127.0.0.1:8000/app`, connect with that service key and search for
`review`. Inspect the source and digest, then fetch the selected file. The
browser verifies the downloaded bytes. The endpoint for a compatible client
is `http://127.0.0.1:8000/mcp`, with protocol `2025-11-25`.

Stop the process with your terminal's interrupt control. Serving again reopens
the existing state. Do not run `configure` as a restart command: it is an
explicit setup operation, not part of normal serving.

## Review candidate intelligence separately

`candidate-specifications.json` contains twelve authored review inputs across
the four existing intelligence layers and ten content families. They include
methods, checks, source references to reusable code, actual diagnostic history
and previously recorded owner guidance. These are candidates, not active
commercial material. Code references are not packaged executable capabilities.

The development tool `tools/stage_intelligence_candidates.py` validates the
population, binds repository source digests and writes an isolated catalogue
through `CatalogWriteBatch`. It requires a new database, an explicit namespace
and `--authorize-isolated-staging`. It exports only acknowledged records.
It cannot update the hosted service, create tenant grants or promote records.

Normal intelligence search excludes these candidates. An explicit review
search uses the existing `query_intelligence` boundary and returns typed
references. The title-derived retrieval probes are smoke checks, not evidence
of semantic relevance or downstream task benefit. Independently review each
source, license, contract and intended use before any separate publication.

## The reviewed starter catalogue in the release

`starter-catalogue/` holds 49 candidate items. Three independent reviewers
judged all of them on 21 September 2026. Their decisions and reasons are in
`starter-catalogue/reviews.json`, and `starter-catalogue/REVIEW.md` explains
how to read the folder. An item is approved only when every reviewer approves
it. Forty-three items were approved. Six were rejected with written reasons
and stay candidates.

`tools/build_host_catalogue_manifest.py` turns the approved rows into
`starter-catalogue/host-release/`, which holds the host manifest and the
approved bodies and nothing else. It refuses to write a rejected item, refuses
a licence the host policy does not accept, and measures the digest and size of
every body from the file itself. The release image copies that folder to
`/opt/baltor/catalogue`, read only and owned by the unprivileged service user,
so the catalogue travels in the image rather than on a storage volume.

## Verify

```bash
PYTHONPATH=src python examples/29_intelligence_service/run.py
loop-engine service smoke
PYTHONPATH=src:tools python -m unittest tools.test_build_host_catalogue_manifest
```

The first command checks real preparation, domain retrieval, exact bytes,
restart after revocation and overwrite refusal. Smoke also exercises real
loopback HTTP and the official protocol client without external providers.

Use the [owner setup runbook](../../docs/guides/launch-setup-runbook.md) for
accounts and deployment, and the [Jev tool guide](../../docs/guides/jev-and-harness-decision-tools.md)
for optional decision calls. Do not expose this example's HTTP port to the
public internet. Cloud storage and hosted authorization need their own configured
adapters and qualification.
