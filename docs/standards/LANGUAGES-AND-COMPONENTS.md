# Languages and components

Kind: engineering standard. It records which language and which library each
component uses today, why it uses them, and what a new language or a new
dependency has to satisfy. It proposes no change to the current choices.

```text
Language by component
├── Python: the engine, the hosted service, the development commands
├── JavaScript in the browser: the website pages, plain and same origin
├── Node.js: browser checks and generated reports only, never at run time
└── Container images: Python base images pinned by digest
```

## Python

Python is the product. The distribution is `loop-engine`, the import is
`loop_engine`, and the command is `loop-engine`
([pyproject.toml](../../pyproject.toml)).

- The declared minimum is `requires-python = ">=3.10"`. Continuous integration
  runs the suite on Python 3.10, 3.11 and 3.12
  ([ci.yml](../../.github/workflows/ci.yml)).
- The same minimum is machine readable as `min_python` in
  [forbidden_paths.json](../../src/loop_engine/forbidden_paths.json). The
  conformance gate `syntax_newer_than_the_declared_minimum_python` fails when a
  module uses newer syntax. Write code that the oldest supported version parses.
- Two more limits from the same file apply to every module: a module is at most
  800 lines (`module_size_hard_cap`) and a public interface takes at most nine
  parameters (`public_parameter_hard_cap`). Both have a named exception list.
  Add a small typed record instead of a tenth parameter.

### The default install stays small

The default dependencies are `PyYAML`, `jsonschema>=4.20`, and `tomli` on
Python before 3.11. The comment above them in `pyproject.toml` states the
reason: a first install must not pull a large data or model stack that the
solving path does not use. Everything heavier is an optional extra.

| Extra | What it adds | Why it is separate |
|---|---|---|
| `optimization` | `optuna`, `cmaes` | Only a search or optimization run needs them. |
| `data` | `numpy`, `pandas`, `scikit-learn`, `lightgbm`, `xgboost`, `kaggle`, `duckdb`, `model2vec`, `lancedb` | Large scientific packages used by data tasks and benchmarks. |
| `integrations` | `mcp`, the OpenTelemetry interfaces | Protocol and telemetry adapters. |
| `serving` | `mcp`, `starlette`, `uvicorn`, `httpx`, `PyJWT[crypto]`, `anyio`, each pinned to one version | Only the hosted service serves requests. |
| `all` | Every extra above | Continuous integration installs this one. |

The service image installs `loop-engine[serving]` and nothing else
([Dockerfile.service](../../Dockerfile.service)).

### The service domain keeps to the standard library

The hosted service is written in `src/loop_engine/core/service_runtime/`. Its
domain modules use the Python standard library only. They hold no web
framework import and no database driver import.

- The named check
  `service_domain_uses_catalog_authority_without_transport_or_database_inversion`
  in [runtime_checks.py](../../src/loop_engine/core/service_runtime/runtime_checks.py)
  parses `records.py`, `runtime.py`, `storage.py`, `provisioning.py`,
  `billing.py`, `billing_records.py` and `stripe_provider.py`. It treats the
  two import forms differently, and it also requires a `README.md` beside
  them.

  | Import form | Refused today |
  |---|---|
  | `import NAME` | Only `sqlite3`, `duckdb`, `httpx` and `fastapi`, compared on the first part of the name. |
  | `from NAME import ...` | Any module name that starts with `http` or with `loop_engine_devtools`. |

  So `from http.client import HTTPConnection` in `runtime.py` fails the check,
  while a plain `import http.client` in the same file passes it today. Do not
  read the check as a complete guard against the standard library transport
  modules. The conformance gate `direct_model_or_network_calls_outside_gateway`
  is the wider net.
- The web framework is imported where it is used and nowhere else.
  `ServiceHttpApplication.create_app` imports Starlette inside the function
  ([http.py](../../src/loop_engine/core/service_runtime/http.py)), and
  `http_entrypoint.py` imports uvicorn inside the run function. The domain can
  be checked without either package installed.
- Storage reaches the database through the catalog contract.
  `service_runtime/storage.py` uses `SQLiteRecordStore` from
  [sqlite_store.py](../../src/loop_engine/catalog/stores/sqlite_store.py), which
  is the one place that imports `sqlite3` for this path. Its docstring states
  the position exactly: one supported backend, not the ontology.
- A module that opens a network connection must be registered in
  `network_allowed_modules` in `forbidden_paths.json`. The conformance gate
  `direct_model_or_network_calls_outside_gateway` refuses any other module,
  including a checks module. See
  [Checks and evidence](CHECKS-AND-EVIDENCE.md#continuous-integration-traps).

## JavaScript in the browser

The website is plain JavaScript served from the same origin as the service.
There is no framework, no bundler and no build step for the pages themselves.

- The served files are a fixed map, `WEB_ASSETS` in `web_pages.py`. Every page path
  returns `index.html`, and `/assets/` returns the named stylesheet, script or
  data file. The adapter never serves the repository, the source inventory,
  configuration or an internal report
  ([web assets README](../../src/loop_engine/core/service_runtime/web_assets/README.md)).
- `index.html` loads two stylesheets and five scripts with the `defer`
  attribute, all from `/assets/`. Four are written by hand:
  `architecture-story.js`, `catalogue-browser.js`, `client-access.js` and
  `service.js`, 1,052 lines together on September 22, 2026. The fifth,
  `supabase-client.js`, is a generated bundle of 223,189 bytes. Its line
  count means nothing, because it is minified.
- The response header `Content-Security-Policy` is
  `default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'`
  plus the configured identity origin, with `base-uri`, `frame-ancestors` and
  `form-action` set to `'none'` (`http.py`). A page cannot load a script from
  another site, so a content delivery network is not an option here.
- A service token stays in page memory and is cleared on disconnect. Model
  provider keys are not collected.

One asset is generated rather than hand written. `supabase-client.js` is built
from `@supabase/supabase-js` version 2.116.0 by esbuild. The exact build
command is the `build` script in
[tools/browser_identity_sdk/package.json](../../tools/browser_identity_sdk/package.json),
the dependency graph is pinned in the lock file beside it, and the licence
travels with the asset as
[THIRD-PARTY-NOTICES.md](../../src/loop_engine/core/service_runtime/web_assets/THIRD-PARTY-NOTICES.md),
served at `/assets/third-party-notices.txt`. The generated file is committed.
The service never builds anything while it runs. Rebuild it only by running
that script, and commit the new file with the updated notice.

## Node.js

Node.js is a development tool. No part of the running service needs it.

| Use | Where | Pinned to |
|---|---|---|
| Browser checks against a local service | [check_service_workspace.mjs](../../tools/check_service_workspace.mjs) | `playwright-core` 1.62.1, loaded from `showcase/node_modules` |
| Browser checks against the live hostnames | [check_hosted_website.mjs](../../tools/check_hosted_website.mjs) | the same browser driver |
| Layout for the offline architecture report | [tools/architecture_report/package.json](../../tools/architecture_report/package.json) | `elkjs` 0.12.0 |
| The showcase player and its exporters | [showcase/package.json](../../showcase/package.json) | Node.js 20 or newer |
| Documentation checks | `ci.yml` | Node.js 22, `markdownlint-cli2` 0.23.2, Mermaid 11.16.0 |

Each of these is installed with a lock file (`npm ci`) or by exact version on
the command line. Do not add a package that the checks can do without.

## Container images

| Image | File | Purpose |
|---|---|---|
| Service | [Dockerfile.service](../../Dockerfile.service) | Builds wheels, installs `loop-engine[serving]`, runs as user 65534, entry point `loop-engine`, command `service serve`. Deployed as the pilot ([fly.toml](../../fly.toml)). |
| Worker | [Dockerfile](../../Dockerfile) | Installs the default engine and runs the `loop-engine` command in a mounted work folder. |
| Benchmark sandbox | `benchmarks/ds1000/Dockerfile` | Installs a hash checked requirement lock for a bounded benchmark. |

Rules that all three follow: the base image is pinned by a `sha256` digest,
the container runs as a user that is not root, and no provider key, model or
customer data is written into the image. The service image and the worker
image share the same base, `python:3.12-slim` at digest `sha256:78387bc3...`.
The benchmark sandbox pins a different digest of the unqualified `python`
repository and names no tag, so read its first line before you assume the
base. Change a digest deliberately and record the new value in the deployment
manifest, as the comment at the top of `Dockerfile` says. Deploy by digest,
never by a tag.

## Development commands

`tools/` holds the development commands. Python modules such as
`tools/check_rollback_key_version.py` and `tools/build_records_index.py` carry
the logic, and the four `.mjs` files drive a browser. `devtools/` is a second
Python distribution, `loop-engine-devtools`, imported as `loop_engine_devtools`
([devtools/pyproject.toml](../../devtools/pyproject.toml)). It owns the
hardcoding audit and the experimental embodiment work. The product does not
install it.

## Adding a language or a dependency

Answer these before you add one. Record the answers in the change.

1. Can the standard library do it? The service domain, the records and the
   checks are written this way today.
2. Which component owns it? A library used by one component belongs to that
   component's optional extra, not to the default install.
3. Does it cross a boundary the checks defend? A transport or a database
   driver may not enter the service domain. A network call needs a registered
   module. Run the owning check before you commit.
4. Is it pinned? Pin an exact version for anything that serves, signs, meters
   or renders evidence. Continuous integration already failed once because a
   parser arrived only as a dependency of another package, so
   `markdown-it-py` is now installed by exact version in `ci.yml`.
5. What is the licence, and where does the notice live? A browser asset carries
   its notice beside it and serves it.
6. Can a clean machine install it? The default install proof in `ci.yml` builds
   a wheel, installs it in an empty environment and runs the packaged checks.
7. A new language needs more than a preference. State the component it serves,
   the check that proves it works, how it is built and pinned, and who updates
   it. Until those exist, use Python.
