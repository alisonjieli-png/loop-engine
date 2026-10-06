# Claude Code quickstart

Kind: customer quickstart for Claude Code. It repeats the connection entry that Get set up publishes for Claude Code and adds the first search, the first download and the check that it worked.

One page from an account to a checked download. Every address, field and command on it is read from the service source, and a nightly check runs the same connection, search and download against the live service with a plain protocol client. That check does not run Claude Code itself: the published recipe still says that native end-to-end qualification is pending.

## What you need

- A [Baltor account](https://app.baltor.ai/get-started). Public Good files are free with an account; Baltor Pro adds the full library.
- A client token from [your account page](https://app.baltor.ai/account), under Your client tokens. The service shows it once.
- Claude Code installed, and a project folder that it opens. Check the version with `claude --version`.
- A terminal where the token is set, because Claude Code reads it from the environment.
- Python 3.10 or newer, `curl` and `sha256sum`, for the Baltor library skill that places downloaded files.

## Set the token

The prompt below hides the value while you enter it, and the value stays out of the command history:

```bash
read -rsp "Baltor service token: " BALTOR_SERVICE_TOKEN
export BALTOR_SERVICE_TOKEN
```

Start Claude Code from this terminal. A variable set in one terminal does not reach a desktop application started elsewhere.

## Paste the configuration

Create `.mcp.json` in your project folder, or merge the `baltor` entry into the `mcpServers` section of an existing one. Do not replace your other settings. The file holds the name of the variable, never the token, so it is safe to keep in version control.

```json
{
  "mcpServers": {
    "baltor": {
      "type": "http",
      "url": "https://baltor.ai/mcp",
      "headers": {
        "Authorization": "Bearer ${BALTOR_SERVICE_TOKEN}",
        "Baltor-Step-Effects": "reads_fs, writes_fs, spawns_process, network"
      }
    }
  }
}
```

## Declare what your harness may do

The `Baltor-Step-Effects` header tells Baltor what your harness's steps may do with an item: `reads_fs` reads files in your project, `writes_fs` writes them, `spawns_process` runs commands and `network` uses the network. `reads_secret` is left out unless your steps read secrets. Remove any effect your harness does not allow.

Search always shows every item your account may use, with its `declared_effects` and its `effects_to_declare`: the effects your header does not declare. Such an item's download is refused with `step_effects_required`, and the refusal's `details` name the effects to add. Without the header, your steps hold `reads_fs` only.

## Check the connection

Run this in the project folder, in the terminal where the token is set:

```bash
claude mcp list
```

The list shows a status next to `baltor`. If the status is Pending approval, start `claude` in this folder once and approve the server. If the list warns about a missing environment variable, set the token before you start Claude Code. In a session, enter `/mcp` and confirm that Baltor's tools are listed, among them `intelligence_search` and `provisioning_read`, which this page uses. The list also holds tools for Public Good files, ratings, problem reports and material requests, and tools for Baltor staff that refuse a customer's token.

## Your first search

The first search is `review inputs`. In a session, ask in plain words:

```text
Search Baltor for review inputs with the intelligence_search tool. Show the top three references with their identity, source and body digest.
```

Claude Code calls `intelligence_search` with your words as the `query`. The tool answers a `service_http_result/v1` wrapper whose `result` is the `service_retrieval_result/v1` record: a list of `hits`, each with a `reference` that names the item's `identity`, its `body_digest` and its `size_bytes`, its source and licence, and `body_allowed`. A search never loads a body, so `bodies_loaded` is false, and a search is not measured.

## Install the Baltor library skill

Files reach your project through a command that writes their exact bytes, never through the model retyping them. A model that retypes a file can change it: a customer run on September 27, 2026 found every line break of a downloaded skill written as the two characters `\n`. The command is the client of the Baltor library skill. Install the skill once in this project and check each file against the digests the website publishes:

```bash
mkdir -p .claude/skills/baltor-library && cd .claude/skills/baltor-library
for file in SKILL.md LICENSE scripts/baltor.py references/client.md assets/client.example.json verification/test_client.py; do
  curl -fsSL --create-dirs "https://baltor.ai/assets/baltor-library/$file" -o "$file"
done
curl -fsSL https://baltor.ai/assets/baltor-library/SHA256SUMS | sha256sum -c -
cd -
mkdir -p ~/.config/baltor
cp -n .claude/skills/baltor-library/assets/client.example.json ~/.config/baltor/client.json
```

`sha256sum -c` prints `OK` for each of the six files. The client needs Python 3.10 or newer. Its configuration, `~/.config/baltor/client.json`, names the token variable and the same four effects as the `Baltor-Step-Effects` header above; it never holds the token. Claude Code lists the skill from its next session.

## Your first download

Choose one reference and ask Claude Code to fetch it and place it with the skill:

```text
Use the baltor-library skill to fetch ITEM-IDENTITY from Baltor and install it for Claude Code in this project.
```

The skill runs its client, which you can also run yourself from the project folder. Replace the two placeholders with the identity and the `body_digest` the search returned:

```bash
BALTOR=.claude/skills/baltor-library/scripts/baltor.py
mkdir -p ~/.cache/baltor
python3 "$BALTOR" search "review inputs" --limit 3 > ~/.cache/baltor/selection.json
python3 "$BALTOR" fetch --selection ~/.cache/baltor/selection.json --identity ITEM-IDENTITY \
  --digest SELECTED-DIGEST --request-id QUICKSTART-1 --output ~/.cache/baltor/QUICKSTART-1 --authorize-download
python3 "$BALTOR" install --staged ~/.cache/baltor/QUICKSTART-1 --client claude-code --authorize-install
```

`fetch` checks every file of the item against its SHA-256 digest and stages it in a new folder. `install` checks the files again and writes their exact bytes into `.claude/skills/NATIVE-NAME/`, and it never replaces a folder it did not install. It prints its install record, which gives the name it placed the skill under: NATIVE-NAME below. It places skills only; another kind of item stays in its staging folder. The first download of an item version in a calendar month is one measured unit and appears in your usage; downloading the same version again that month, with any `request_id`, adds nothing.

In a session, Claude Code can also read an item through the protocol connection, to decide whether it fits before you place it. `provisioning_read` takes the `identity`, a new `request_id` for each logical download and the `expected_digest` from the search, so a changed body is refused rather than substituted. For a single-file item its `result` is `provisioning_body/v3`, with the `body` inline and its `digest`. For a package of several files it is `provisioning_package_read/v1`: each file's exact content with its `path` and SHA-256 `digest`, one page at a time; ask for the next page with `file_offset` set to `next_file_offset` and the same `request_id`. [Searching and retrieving](service-searching-and-retrieving.md#package-files-through-the-protocol-tool) describes the record. A read is counted like a download. Place files with `install`, not by saving what the model read.

## Check that it worked

Check the placed files first. The command answers `"verified": true`, and names any file that changed since it was placed:

```bash
python3 .claude/skills/baltor-library/scripts/baltor.py verify --client claude-code --name NATIVE-NAME
```

1. Start a new session: Claude Code lists the skill by that name.
2. Open [your account page](https://app.baltor.ai/account): the download is listed in your usage.
3. Confirm the account and its scopes from the terminal with the command below.

```bash
curl -sS -H "Authorization: Bearer $BALTOR_SERVICE_TOKEN" https://baltor.ai/api/v1/session
```

The answer's `result` is `service_session/v1`. Its `principal` names the account and its `scopes`: a search needs `provisioning:metadata` and a download needs `provisioning:read`.

## When it does not work

| Code | Status | What to do |
| --- | --- | --- |
| `unauthorized` | 401 | The token is missing, wrong, expired or revoked. Set `BALTOR_SERVICE_TOKEN` in the terminal that starts Claude Code, then run the session check above. |
| `insufficient_scope` | 403 | The token lacks the scope this operation needs. Create a token with `provisioning:read`. |
| `plan_required` | 403 | Your account has no plan that includes downloads; search still works. Choose Baltor Pro on the [pricing page](https://baltor.ai/pricing). The refusal's `details` name that page, and the founding offer while places remain. |
| `step_effects_required` | 403 | The item declares effects your configuration does not declare. Add the `effects_to_declare` that the refusal's `details` name, if your harness may do them, or choose another item. |
| `item_unavailable` | 404 | The identity is not in your library, or it was withdrawn. Search again and use a fresh reference. |
| `request_identity_required` | 400 | A download needs a `request_id`. Give each logical download a new one. |
| `download_required` | 413 | The body is larger than the inline limit. Fetch it through `/api/v1/download`. |
| `failed_attempt_limit_reached` | 429 | Too many refused attempts from your address. Fix the token, then wait a minute. |

A configured entry is not a completed handshake, and a listed tool is not a loaded file. [Troubleshooting](service-troubleshooting.md) explains every code, [Service status](https://app.baltor.ai/status) shows a current outage, and [Serving and connections](service-serving-and-connections.md) names the protocol versions. The nightly record of this page's steps is written under `artifacts/quickstart-checks/` in the repository by [the quickstart check](../../tools/check_quickstarts.py).
