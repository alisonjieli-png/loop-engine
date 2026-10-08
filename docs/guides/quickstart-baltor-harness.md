# Baltor Harness quickstart

Kind: customer quickstart for the Baltor Harness. It repeats the installation and the connection values that Get set up publishes for the Baltor Harness and adds the first search, the first download and the check that it worked.

Use the free, open-source Baltor Harness to run a task in small steps with your
chosen model and a record of each step. Install the `loop-engine` command from
[GitHub](https://github.com/alisonjieli-png/loop-engine), select library material,
verify its files and include them in your task. This guide takes you through
setup, search, download and an Ollama-backed run. The recorded September 23
journey used loop-engine 0.1.0 and checked each of those steps.

## What you need

- A [Baltor account](https://app.baltor.ai/get-started). Public Good files are free with an account; Agent Feeds + Harness Files adds the full library.
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

The first line of the answer ends with `CONFIGURATION VALID`. This confirms
the local installation. Check the installed version with `pip show loop-engine`.

## Set the token

The prompt below hides the value while you enter it, and the value stays out of the command history:

```bash
read -rsp "Baltor service token: " BALTOR_SERVICE_TOKEN
export BALTOR_SERVICE_TOKEN
```

## The connection values

The commands below use these connection values with `curl`. The same address
and credential variable work with the engine's protocol client (`McpServerSpec`,
installed with `loop-engine[integrations]`). Keep the token in your environment.

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

The download answers the bytes themselves, with the `X-Content-SHA256` header that repeats their digest, and `curl` writes them unchanged. When the search result's `package` lists several files, this download answers the package document that lists them; download each file by adding its `path` to the same request, or use the Baltor library skill's `fetch` and `install`, as the [OpenCode quickstart](quickstart-opencode.md#install-the-baltor-library-skill) shows. The `expected_digest` binds the read to the body you chose, so a changed body is refused rather than substituted. The first download of an item version in a calendar month is one measured unit and appears in your usage; downloading the same version again that month, with any `request_id`, adds nothing. A retry of an uncertain outcome is therefore safe; keep the same `request_id` so your records name one download.

## Run a task with it

For a complete package staged by the first-party library client's `fetch`
command, pass the staging folder directly. Follow the
[library client setup](quickstart-opencode.md#install-the-baltor-library-skill)
and fetch the selected package into `selected-material`, then run:

```bash
loop-engine solve --file task.md --material-package selected-material --allow-source-to-model --ollama-api-key --model-route cloud.default --unattended --max-model-calls 60 --workspace baltor-run
```

The harness verifies the package's exact files and lets the task select the
parts it needs. The [native package-input guide](baltor-native-package-inputs.md)
describes its supported inputs and checks. Install the current source version
above to use this option. For a small single-file reference, you can also
include its text in `task.md` and run the same command without the two package
input options.

Use an empty output folder for `--workspace`. Compare the result with an
independent acceptance check and retain the selected-file evidence. Package
input, automatic project discovery and active skill registration have separate
qualification records.

## Check that it worked

1. The two digests are equal: `sha256sum` of the downloaded file, and the `body_digest` the search returned. The header `X-Content-SHA256` repeats it.
2. Open [your account page](https://app.baltor.ai/account): the download is listed in your usage.
3. The task run names the downloaded file among its inputs and prints its output files.

## When it does not work

| Code | Status | What to do |
| --- | --- | --- |
| `unauthorized` | 401 | The token is missing, wrong, expired or revoked. Set `BALTOR_SERVICE_TOKEN` in this terminal, then run the session check again. |
| `insufficient_scope` | 403 | The token lacks the scope this operation needs. Create a token with `provisioning:read`. |
| `plan_required` | 403 | Your account has no plan that includes downloads; search still works. Choose Agent Feeds + Harness Files on the [pricing page](https://baltor.ai/pricing). The refusal's `details` name that page, and the founding offer while places remain. |
| `step_effects_required` | 403 | The item declares effects your configuration does not declare. Add the `effects_to_declare` that the refusal's `details` name, if your harness may do them, or choose another item. |
| `item_unavailable` | 404 | The identity is not in your library, or it was withdrawn. Search again and use a fresh reference. |
| `request_identity_required` | 400 | A download needs a `request_id`. Give each logical download a new one. |
| `download_requires_read` | 400 | Only the `read` operation is answered at `/api/v1/download`. A manifest goes to `/api/v1/provisioning`. |
| `meter_commit_unknown` | 503 | The service could not confirm the usage record. Retry with the same `request_id`; it cannot count twice. |
| `usage_store_busy` | 503 | Other downloads held the usage store. Nothing was counted. Wait for `Retry-After`, then retry. |
| `failed_attempt_limit_reached` | 429 | Too many refused attempts from your address. Fix the token, then wait a minute. |

A `loop-engine doctor` answer that is not valid names the setting to fix and does not involve Baltor. [Troubleshooting](service-troubleshooting.md) explains every code, [Service status](https://app.baltor.ai/status) shows a current outage, and [Serving and connections](service-serving-and-connections.md) names the protocol versions. To run on a model on your own machine, follow the engine's [installation guide](../../README.md#install). The nightly record of this page's steps is written under `artifacts/quickstart-checks/` in the repository by [the quickstart check](../../tools/check_quickstarts.py).
