# Baltor Harness quickstart

Kind: customer quickstart for the Baltor Harness. It repeats the installation and the connection values that Get set up publishes for the Baltor Harness and adds the first search, the first download and the check that it worked.

The Baltor Harness is Baltor's own engine: the free, open source `loop-engine` command, published on [GitHub](https://github.com/alisonjieli-png/loop-engine). It works through a task in small steps on the model you bring and keeps a record of every step. Today it does not search or download from Baltor by itself: you search and download with your token, check the digest, add the material to your task file, then run the task. Every address, field and command on this page is read from the service source, and a nightly check runs the same connection, search and download against the live service. The whole path was checked on September 23, 2026 with loop-engine 0.1.0 from GitHub main: install, doctor, the Ollama Cloud route, search, download with a digest check, and a task that used the downloaded item.

## What you need

- A Baltor account with an active plan. Create it on [Get started](https://app.baltor.ai/get-started).
- A client token from [your account page](https://app.baltor.ai/account), under Your client tokens. The service shows it once.
- Python 3.10 or newer, `curl` and `sha256sum`.
- A model you bring. The example below runs on Ollama Cloud with `OLLAMA_API_KEY` in your environment; a local model server works through the engine's own provider settings.

## Install the engine

```bash
python3 -m venv ~/.baltor-harness
~/.baltor-harness/bin/pip install 'git+https://github.com/alisonjieli-png/loop-engine'
export PATH="$HOME/.baltor-harness/bin:$PATH"
loop-engine doctor
```

The first line of the answer ends with `CONFIGURATION VALID`. This checks the installation only: it makes no model call and does not contact Baltor. Check the installed version with `pip show loop-engine`.

## Set the token

The prompt below hides the value while you enter it, and the value stays out of the command history:

```bash
read -rsp "Baltor service token: " BALTOR_SERVICE_TOKEN
export BALTOR_SERVICE_TOKEN
```

## The connection values

There is no configuration file yet. The steps below use these values with `curl`. The same address and variable work with the protocol client that ships with the engine (`McpServerSpec`, installed with `loop-engine[integrations]`). Keep the token in your environment, never in a file.

```json
{
  "mcp_servers": {
    "baltor": {
      "transport": "streamable_http",
      "url": "https://baltor.ai/mcp",
      "credential_env": "BALTOR_SERVICE_TOKEN",
      "headers": {
        "Baltor-Step-Effects": "reads_fs, writes_fs, spawns_process, network"
      }
    }
  }
}
```

The `Baltor-Step-Effects` header says what your task's steps may do with a Baltor item: `reads_fs` reads files, `writes_fs` writes them, `spawns_process` runs commands and `network` uses the network. Remove any effect your steps do not have. Search shows every item your account may use, each with its `effects_to_declare`: the effects the header leaves out. A download of such an item is refused with `step_effects_required`, and the refusal's `details` name the effects to add.

## Check the connection

```bash
curl -sS -H "Authorization: Bearer $BALTOR_SERVICE_TOKEN" https://baltor.ai/api/v1/session
```

The answer's `result` is `service_session/v1`. Its `principal` names the account and its `scopes`: a search needs `provisioning:metadata` and a download needs `provisioning:read`.

## Your first search

The first search is `review inputs`:

```bash
curl -sS -X POST https://baltor.ai/api/v1/retrieval -H "Authorization: Bearer $BALTOR_SERVICE_TOKEN" -H "Baltor-Step-Effects: reads_fs, writes_fs, spawns_process, network" -H "Content-Type: application/json" -d '{"record_type":"service_retrieval_request/v2","query":"review inputs","mode":"lexical","top_n":3}'
```

The answer is a `service_http_result/v1` wrapper whose `result` is the `service_retrieval_result/v1` record: a list of `hits`, each with a `reference` that names the item's `identity`, its `body_digest` and its `size_bytes`, its source and licence, and `body_allowed`. A search never loads a body, so `bodies_loaded` is false, and a search is not measured. Keep the `identity` and the `body_digest` of the one you choose.

## Your first download

Replace the two placeholders with the values you kept, and give the download a new `request_id`:

```bash
curl -sS -X POST https://baltor.ai/api/v1/download -H "Authorization: Bearer $BALTOR_SERVICE_TOKEN" -H "Baltor-Step-Effects: reads_fs, writes_fs, spawns_process, network" -H "Content-Type: application/json" -d '{"record_type":"service_provisioning_request/v2","operation":"read","identity":"ITEM-IDENTITY","expected_digest":"SELECTED-DIGEST","request_id":"QUICKSTART-1"}' -D headers.txt -o item.md
sha256sum item.md
grep -i x-content-sha256 headers.txt
```

The download answers the bytes themselves, with the `X-Content-SHA256` header that repeats their digest. The `expected_digest` binds the read to the body you chose, so a changed body is refused rather than substituted. This download is one measured unit and appears in your usage. Keep the same `request_id` if you retry an uncertain outcome; the service records one unit for one request identity.

## Run a task with it

Put the downloaded material where your task reads it and name it in the task file. Then run the task, for example on Ollama Cloud:

```bash
loop-engine solve --file task.md --ollama-api-key --model-route cloud.default --unattended --max-model-calls 60 --workspace baltor-run
```

`--workspace` must be an empty folder or one that does not exist yet. When the run ends it prints its output files; compare them with what you asked for. The engine's own verification is strict and can refuse a correct result, so check the output yourself.

## Check that it worked

1. The two digests are equal: `sha256sum` of the downloaded file, and the `body_digest` the search returned. The header `X-Content-SHA256` repeats it.
2. Open [your account page](https://app.baltor.ai/account): the download is listed in your usage.
3. The task run names the downloaded file among its inputs and prints its output files.

## When it does not work

| Code | Status | What to do |
| --- | --- | --- |
| `unauthorized` | 401 | The token is missing, wrong, expired or revoked. Set `BALTOR_SERVICE_TOKEN` in this terminal, then run the session check again. |
| `insufficient_scope` | 403 | The token lacks the scope this operation needs. Create a token with `provisioning:read`. |
| `item_unavailable` | 404 | The identity is not in your library, or it was withdrawn. Search again and use a fresh reference. |
| `request_identity_required` | 400 | A download needs a `request_id`. Give each logical download a new one. |
| `download_requires_read` | 400 | Only the `read` operation is answered at `/api/v1/download`. A manifest goes to `/api/v1/provisioning`. |
| `meter_commit_unknown` | 503 | The service could not confirm the usage record. Retry with the same `request_id`. |
| `failed_attempt_limit_reached` | 429 | Too many refused attempts from your address. Fix the token, then wait a minute. |

A `loop-engine doctor` answer that is not valid names the setting to fix and does not involve Baltor. [Troubleshooting](service-troubleshooting.md) explains every code, [Service status](https://app.baltor.ai/status) shows a current outage, and [Serving and connections](service-serving-and-connections.md) names the protocol versions. To run on a model on your own machine, follow the engine's [installation guide](../../README.md#install). The nightly record of this page's steps is written under `artifacts/quickstart-checks/` in the repository by [the quickstart check](../../tools/check_quickstarts.py).
