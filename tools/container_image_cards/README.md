# Container image contract cards

Kind: tool component. One small card per repository and tag family of a
container image: what the image runs, the environment variables, ports,
volumes and arguments it takes, what it gives back, its platforms with the
exact manifest and config digest of each, and a typed helper that writes the
`docker run` command for given inputs and refuses inputs the contract rules
out. The owner, October 9, 2026: "we could even index full docker images, with
clear inputs and outputs to accomplish certain tasks, because an LLM doesn't
need to recreate the code and it doesn't need to reread the entire code if it
knows the inputs and outputs and functions and basic docstrings of a docker
image or service, etc, and its compatibilities".

The supply line is [`container_image_cards`](../supply_lines/container_image_cards.py)
(command `container-image-cards` of
[`tools/build_library_supply.py`](../build_library_supply.py)). It starts with
the Docker Official Images. Each card is a review candidate; qualification and
the ongoing independent review decide what is served.

## Runtime classification

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

A card run is a Starting Practitioner task of the code execution profile that
an operator starts; it runs deterministically and calls no model. The library
reader, the registry engines, the OCI reader, the card writer, the registry
check and the smoke run are adapters the run uses: none is a graph vertex, a
role, a mode or a runtime type, and none grants authority. Network reads need
`--authorize-network-reads`; a smoke run pulls and starts containers only for
the families `--smoke` names.

## One card

```text
container_image_contract/v1 (contract.json) and container_image_card/v1 (component.json): the fixed edge
├── README.md          the card a harness reads first; every line image_contract.card_lines() writes is in it, in order
├── contract.json      the image (registry, repository, tags, the index digest it pins), the family (its identity,
│                      declared architectures, library entry and build context), the common runtime, inputs
│                      (environment, ports, volumes), outputs, every platform (manifest and config digests, layers,
│                      compressed bytes, base image, what differs from the common runtime), documentation facts
│                      and compatibility notes
├── schema.json        the JSON Schema of contract.json, the same bytes in every card (card_files/schema.json)
├── image_contract.py  the shared helper (card_files/image_contract.py), standard library only: problems(),
│                      notices(), render_run() for docker or podman, card_lines(), disagreements(), card_digest()
├── schema_check.py    the small JSON Schema validator every schema package carries (supply_lines/schema_check.py)
├── test_image_contract.py  the shared test: the contract against its schema, the README against the contract, the
│                      component card against the files, the evidence against the card digest; known-wrong controls
├── component.json     the small contract card a harness reads first, written after the registry check
├── verification/registry.json  the registry check of this card (container_image_registry_check/v1)
├── verification/smoke.json     a smoke run on a local engine, for the few families a run names
├── LICENSE            Baltor's MIT, for every generated file
├── UPSTREAM-LICENSE   docker-library/docs' MIT, for the one-line summary the README quotes
└── ATTRIBUTION.md     the generator, every fact with its address, time, digest and licence, every file's digest
```

The card's checked lines are written by the shipped `image_contract.py`
itself (loaded from `card_files`), so the writer and the checker cannot
disagree about a format; the package test fails when the README loses, adds or
reorders a row, and the qualification mutation check makes sure that test can
fail.

### Inputs and outputs

- Environment: every variable the config sets (its value, or "varies by
  platform" with each platform's value under its differences), and every name
  the image's documentation gives in a heading or after `-e`/`--env` in an
  example command. A documented name is a name only: no sentence and no
  example value is copied (the postgres example's value is a sample password).
  Whether a documented variable is required is not stated.
- A credential is never written: an image's value under a name that marks a
  credential (`PASSWORD`, `SECRET`, `TOKEN`, `CREDENTIAL`, `PRIVATE_KEY`,
  `API_KEY`, `ACCESS_KEY`, `AUTH_KEY`, `SALT`) or shaped like one by
  qualification's own secret patterns is withheld, its name kept. A
  credential-shaped value anywhere else in a config refuses the family
  (`credential_shaped_value_in_image`). The helper refuses a credential given
  as a value: `--env NAME` alone makes the engine copy it from the caller's
  environment, so it never appears on a command line or in a model's context.
- Ports, volumes, entrypoint, default command, working directory, user, stop
  signal, healthcheck, shell, ONBUILD triggers and labels are the config's.
- Outputs are what every container gives: its logs (standard output and
  standard error), the main process's exit status, the exposed ports while it
  runs, files under the declared volumes, and the healthcheck's status when one
  is declared. What the program itself writes is not described.

The history (the build's commands) is never copied: it is the image's own
build code, not a fact about running it.

## The Docker Official Images

```text
docker-library/official-images (Apache-2.0) and docker-library/docs (MIT), each at its head commit
├── library/<name>: one paragraph per tag family (Tags, SharedTags, Architectures, GitRepo, GitFetch,
│   GitCommit, Directory, File, Builder, Constraints, <architecture>-<field> overrides), read as facts by
│   library.py; 141 files and 2,129 families at commit e45c28e3 (October 9, 2026)
├── <name>/ of the docs: README-short.txt (quoted), metadata.json (categories), content.md (variable names),
│   license.md (the software licence addresses) and github-repo, read by docs.py
└── the registry: the family's first own tag (the most specific, in docker-library's order) resolved by HEAD;
    the index, every platform manifest and every config read by digest and checked against it (registry.py,
    oci.py); attestation manifests are not platforms
```

A family's SharedTags (hello-world's `latest`, python's `3.14`) name an index
that joins several families, so a card pins its own first tag's index and
lists the shared tags beside it.

### The family identity, which is the job key

A family is one library entry. Its identity is the entry's own build context
without a commit: its fetch reference, directory, Dockerfile name, constraints
and per-architecture directories (`context:directory=mainline/debian` for
nginx's mainline Debian family, `context:fetch=refs/heads/v3.24;...` for
alpine 3.24). When two entries of one repository share a build context it is
the shortest of the entry's own tags other than latest (`tag:6.4` for crate,
`tag:22.04` for ubuntu, `tag:2023` for amazonlinux). Of the 2,129 entries of
October 9, 2026, 2,117 are named by their build context and 12 by a tag. The
job key is `component.json` job.registry, job.repository and job.family:
never a digest, a tag that moves or a commit, so the same family rebuilt or
moved to its next patch release is one job, and a complete run supersedes its
card.

## Licence findings

Read on October 9, 2026:

- docker-library/official-images is Apache-2.0: GitHub's licence interface
  and the `LICENSE` text agree once the shared matcher sets aside the notice
  the licence's own appendix prescribes, which this file carries right after
  "END OF TERMS AND CONDITIONS" with no appendix heading (blob `27448585`, the
  same as docker-library/repo-info's). The matcher had counted the notice's
  words as added text; it now sets aside exactly those words in that order
  (`src/loop_engine/core/library_ingestion/licences.py`, with a known-wrong
  control: a notice that adds a condition is still refused). A card copies no
  text of this repository: tags, architectures and build contexts are facts.
- docker-library/docs is MIT, Copyright (c) 2014 Docker, Inc., for every file.
  No image folder holds a licence file of its own or states another licence
  for its documentation (all 142 folders and their `content.md` read). Each
  folder's `license.md` names the licence of the software inside the image
  (the PostgreSQL licence, GPL-2.0, LGPL-2.1, AGPL-3.0, Oracle's and
  Perforce's end-user licence agreements, ...). That licence governs the
  image, never the card: a card links to it and says it grants no licence to
  the image. The one-line `README-short.txt` is the only documentation text a
  card quotes, marked as a quotation under the docs' MIT, whose text travels
  as `UPSTREAM-LICENSE`.
- An image's index, manifests and config are registry facts read by digest
  (role `registry_entry`, `NOASSERTION`): no byte of them is a package file.

## The registry engines

```text
read_tag, read_document, head_document: the fixed edge (registry.py)
├── docker_hub (default): registry-1.docker.io; anonymous bearer tokens from auth.docker.io, held in memory only
│   and sent as an unredirected header, so the content delivery host a blob redirects to never receives one
│   ├── a tag by HEAD; every index, manifest and config by digest through the blob endpoint, which serves an
│   │   index and a manifest too (they are content-addressed blobs there)
│   └── a manifest the blob endpoint lacks is read from the manifest endpoint, which counts a pull, only while the
│       allowance stays above a reserve (20)
└── ecr_public: public.ecr.aws, the mirror docker/library/<name> of the Docker Official Images, the same digests
```

Measured on October 9, 2026 from this workstation (`ratelimit-limit` and
`ratelimit-remaining` headers):

- The anonymous pull allowance is `100;w=3600`: 100 counted manifest reads an
  hour per address. Docker's documentation says 100 per 6 hours; the registry
  states and enforces the hourly window.
- A HEAD of a manifest and a GET of a blob leave the allowance unchanged (100
  before and after a config read; 100 after the 2,076 requests of a six
  repository trial run, 76 families).
- One `docker pull` of a multi-platform image by its index digest costs 2: the
  index and the platform manifest (100 to 98).
- A blob answer redirects to `production.cloudfront.docker.com`; requests took
  257 to 380 ms on average. Four workers behind one 0.1 s pause read and
  checked 76 families (437 platform images) in 350 s, about 6 requests a
  second, well under Docker's stated abuse limit of thousands a minute.
- ECR Public served alpine's index byte for byte with the same digest; AWS
  documents 1 anonymous pull a second per region and 500 GB a month.

### The registry check

`verify.py` runs after every card is written and before any is packaged: a
HEAD of the resolved tag must still name the index digest, a HEAD of the
index, of every platform manifest and of every config blob must answer with the
card's digest and size, and each config, parsed again by `verify.py`'s own
reader (no shared code with `oci.py`), must state the runtime
`image_contract.platform_runtime()` gives for that platform. The record binds
the card digest and carries no time stamp. A card whose record is missing,
stale (for other bytes) or failed is refused by name.

### The smoke run

`smoke.py` runs a few small images a run names with `--smoke name:tag` on the
local engine (docker 29.5.2 here, containerd image store): it pulls the platform
image by its index digest, compares `docker image inspect --platform`'s Config
with the card's runtime. A failed pull or config comparison ends before
execution. It runs the argument list `render_run()` writes for the selected
Docker or Podman engine with `--network none`, 256 MiB memory, one CPU,
128 processes and no privilege escalation. An image that exposes no port must exit 0; one that
exposes a port is started detached, must still be running after five seconds
and is stopped with its stop signal. A private engine-written container ID
binds cleanup, including after a timeout; a missing identity or failed cleanup
fails the run. Pulled images remain cached because the daemon may have other
users. A failed smoke run refuses the card (`smoke_check_failed`).

## Existing work: adopted, adapted and rejected

| Project | Decision and reason |
|---|---|
| OCI image specification (index, manifest, config, annotations) and distribution specification (token flow, HEAD, blobs by digest) | Adopted as the definitions every reader here follows: media types, descriptors, platform fields, the pre-defined annotation keys (`org.opencontainers.image.base.name` and the rest) and content addressing. |
| docker-library/official-images library files and bashbrew's manifest format | Adopted as the source of tag families: one entry is one family, its Tags one index, SharedTags several. bashbrew itself (Go) is not run: the format is small and a standard-library reader (library.py) parses all 141 files. |
| docker-library/docs | Adopted for the summary (quoted, MIT), categories, variable names, licence addresses and source repository; content.md prose is read for names only. |
| Docker Hub's registry API | Adopted as the engine: HEAD for tags, the blob endpoint for every document by digest, which counts no pull. |
| Docker Hub's web API (hub.docker.com/v2) | Not used for official images: it lists tags with per-platform manifest digests and sizes but no config, so it cannot give a card's runtime, and its descriptions are prose under Docker's terms. It is the discovery source for the next collections (see Scaling). |
| docker-library/repo-info (Apache-2.0) | Rejected as a source: its `remote/<tag>.md` pages render the registry's facts (entrypoint, default command, sizes, the history) as Markdown on a schedule; the registry's own bytes, checked by digest, are the facts a card pins. |
| docker-library/meta (Apache-2.0) | Not used: build metadata of the docker-library pipeline, not needed when the registry answers by digest. |
| skopeo, crane (go-containerregistry), regctl (regclient), oras | Rejected as engines: none is installed, each is a Go binary to install and pin, `inspect` reshapes the config into its own JSON, and their manifest reads count against the anonymous allowance. The token flow and Accept headers they use are the ones registry.py sends. An adapter for one of them can stand beside the native engine behind the same edge. |
| Syft and Docker's SBOM attestations | Not used: Syft reads layers, which a card never pulls. The official images already publish SPDX attestations (the `attestation-manifest` descriptors the index lists); reading those blobs is the way to add package lists without a layer (see Scaling). |
| ECR Public `docker/library` mirror | Adapted as a second engine (`--registry ecr_public`): the same digests, a separate allowance. |
| supply_lines/schema_check.py | Adopted unchanged as the validator every card carries, as the JSON Schema line does. |
| engine_api_cards' card pattern (shared checker and test, native evidence bound to a card digest) | Adopted: the card files, the evidence binding and the refusals by name follow it. |

## Scaling beyond the official images

The card format, the helper, the check and the registry engines take any
repository whose config is readable by digest; what changes per collection is
the source of facts and the licence of any text a card quotes.

1. Docker Verified Publisher and Sponsored OSS images: list them through Docker
   Hub's web API (`/v2/repositories/<namespace>/` and the search filters for
   the badges), read each repository's tags there (per-platform manifest
   digests and sizes, no pull counted), then the configs through the blob
   endpoint as here. They have no docker-library/docs folder, so a card quotes
   no prose: no summary, and documented variables only where the publisher's
   own repository states a licence on the allowlist for its documentation.
2. Popular community images: the same, ordered by pull count, with a family
   per tag pattern the publisher keeps; a repository whose description or
   source licence is unknown still gets a card of registry facts only.
3. Other registries behind the same edge: GHCR, Quay, the Microsoft Container
   Registry and ECR Public answer the same distribution API; each is a
   `RegistryProfile` with its hosts and its allowance headers.
4. Package lists without layers: read each platform's SPDX attestation blob
   (BuildKit's in-toto statement) and add its package names and versions to
   the card as compatibility facts.

The allowance is not the limit: blob reads and HEADs count no pull. The limit
is request time, about 6 requests a second through one address with four
workers, so 2,129 families and about 7,800 platform images take about 37,000
requests (an hour and a half). A rerun reads only new digests: documents are
kept by digest (`--document-cache`), so an unchanged family costs two HEADs
and its check.

## Commands

```bash
PYTHONPATH=src:tools python tools/build_library_supply.py container-image-cards \
  --run-folder /run/media/username/baltor-offload/docker-cards-20261009/run-1 \
  --authorize-network-reads --authorize-store-writes --store-root STORE \
  --registry-workers 4 --registry-pause-seconds 0.1 --document-cache CACHE \
  [--repository NAME] [--maximum-families N] [--smoke name:tag] [--registry ecr_public]
```

## Checks

```bash
PYTHONPATH=src:tools python -m unittest tools.test_container_image_cards
PYTHONPATH=src:tools:. python -m unittest tools.test_container_image_cards_line
```

## Limits

- A card describes the digests it names. A tag moves when docker-library
  rebuilds it; the registry check fails a card whose tag moved between the
  read and the check, and the next run writes a new card.
- Documented variable names come from headings and example commands; one the
  entrypoint reads that the documentation mentions only in prose is missed, and
  none is marked required.
- No layer is read: the files and packages inside an image, its uncompressed
  size and what its programs do are not in a card.
- Windows images are carded with their `os.version`; nothing here runs one.
- Only the images a run names are smoke-run, on one platform (linux/amd64).
- Nothing here was loaded by a harness.
