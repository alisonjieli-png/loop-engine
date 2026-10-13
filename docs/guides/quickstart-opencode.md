# OpenCode quickstart

Kind: customer quickstart for OpenCode 1.x. It repeats the connection entry that Get set up publishes for OpenCode and adds the first search, the first download and the check that it worked.

One page from an account to a checked download. Every address, field and command on it is read from the service source, and a nightly check runs the same connection, search and download against the live service with a plain protocol client. That check does not run OpenCode itself: the published recipe still says that native end-to-end qualification is pending.

## What you need

- A [Baltor account](https://app.baltor.ai/get-started). Public Good files are free with an account; Pro adds the full library.
- A Baltor key from [your account page](https://app.baltor.ai/account), under Your Baltor keys. The service shows it once.
- OpenCode 1.x installed. Check the version with `opencode --version`. OpenCode 2.x uses a different configuration layout, and this page does not cover it.
- A model connection that already works in OpenCode, using your own provider account, subscription or local endpoint. Baltor library access does not supply model access or pay that provider's charges.
- A terminal where the token is set, because the entry reads it from the environment.
- Python 3.10 or newer, `curl` and `sha256sum`, for the Baltor library skill that places downloaded files.

Before configuring Baltor, start OpenCode in your project and ask it a short
question without using tools. Confirm that your chosen model answers. If that
fails, fix the OpenCode model connection first. A working model connection and
a valid Baltor library token are separate prerequisites; neither verifies the
other.

## Set the token

The prompt below hides the value while you enter it, and the value stays out of the command history:

```bash
read -rsp "Baltor service token: " BALTOR_SERVICE_TOKEN
export BALTOR_SERVICE_TOKEN
```

Start OpenCode from this terminal.

## Paste the configuration

Merge the `baltor` entry into the `mcp` section of your existing `opencode.json`. Do not replace your other settings. The file holds the name of the variable, never the token.

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "baltor": {
      "type": "remote",
      "url": "https://baltor.ai/mcp",
      "enabled": true,
      "oauth": false,
      "headers": {
        "Authorization": "Bearer {env:BALTOR_SERVICE_TOKEN}",
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

```bash
opencode mcp list
```

The list shows `baltor` as connected; it does not list the tools. In a session,
use `intelligence_search`, `provisioning_discover`, `provisioning_list`,
`provisioning_manifest`, `provisioning_read`, `provisioning_report` or
`public_good_files`. This recipe uses a supplied token and therefore sets
`oauth` to false. Baltor also serves OAuth; the separate
[OAuth connection guide](service-serving-and-connections.md#oauth-connections)
describes account linking without passing a key through a conversation.

## Your first search

The first search is `review inputs`. In a session, ask in plain words:

```text
Search Baltor for review inputs with the intelligence_search tool. Show the top three references with their identity, source and body digest.
```

OpenCode calls `intelligence_search` with your words as the `query`. The tool answers a `service_http_result/v1` wrapper whose `result` is the `service_retrieval_result/v1` record: a list of `hits`, each with a `reference` that names the item's `identity`, its `body_digest` and its `size_bytes`, its source and licence, and `body_allowed`. A search never loads a body, so `bodies_loaded` is false, and a search is not measured.

## Install the Baltor library skill

Files reach your project through a command that writes their exact bytes, never through the model retyping them. A model that retypes a file can change it: a customer run on September 27, 2026 found every line break of a downloaded skill written as the two characters `\n`. The command is the client of the Baltor library skill. Install the skill once in this project and check each file against the digests the website publishes:

```bash
# Stage and verify the bootstrap before creating the installed skill.
(
  set -eu
  umask 077
  target="$PWD/.opencode/skills/baltor-library"
  for parent in .opencode .opencode/skills; do
    if [ -L "$parent" ] || { [ -e "$parent" ] && [ ! -d "$parent" ]; }; then
      printf '%s\n' "Refusing non-directory or symbolic-link parent: $parent" >&2
      exit 1
    fi
  done
  if [ -e "$target" ] || [ -L "$target" ]; then
    printf '%s\n' "Existing skill retained: $target. Inspect it before installing another copy." >&2
    exit 1
  fi
  mkdir -p .opencode/skills
  staging=$(mktemp -d "$PWD/.opencode/skills/.baltor-library-stage.XXXXXXXX")
  printf 'Staging directory retained for inspection: %s\n' "$staging"
  cd "$staging"
  for file in SKILL.md LICENSE scripts/baltor.py references/client.md assets/client.example.json verification/test_client.py SHA256SUMS; do
    curl -fsS --proto '=https' --max-time 30 --create-dirs \
      "https://baltor.ai/assets/baltor-library/$file" -o "$file"
  done
  python3 - <<'PY'
import re
from pathlib import Path
expected = {"SKILL.md", "LICENSE", "scripts/baltor.py", "references/client.md",
            "assets/client.example.json", "verification/test_client.py"}
lines = Path("SHA256SUMS").read_text(encoding="utf-8").splitlines()
matches = [re.fullmatch(r"[0-9a-f]{64}  (.+)", line) for line in lines]
if len(lines) != len(expected) or any(match is None for match in matches):
    raise SystemExit("Checksum manifest shape refused")
if {match.group(1) for match in matches} != expected:
    raise SystemExit("Checksum manifest must name exactly the six bootstrap files")
PY
  sha256sum --strict -c SHA256SUMS
  mkdir "$target"
  cp -R -n "$staging/." "$target/"
  cd "$target"
  sha256sum --strict -c SHA256SUMS
  python3 - "$HOME/.config/baltor" <<'PY'
import os
from pathlib import Path
import sys
folder = Path(sys.argv[1])
if any(parent.is_symlink() for parent in (folder.parent, folder)):
    raise SystemExit("Existing symbolic-link configuration directory retained; inspect it manually")
folder.mkdir(parents=True, exist_ok=True, mode=0o700)
try:
    descriptor = os.open(folder / "client.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    print("Existing client.json retained. Check its origin, token variable and declared effects before use.")
else:
    with os.fdopen(descriptor, "wb") as output:
        output.write(Path("assets/client.example.json").read_bytes())
    print("Created client.json without replacing existing configuration.")
PY
)
```

Run the block from the project folder in Bash. It stops on a failed download,
unexpected checksum path or wrong digest before creating the installed skill.
It does not overwrite an existing skill, configuration file or symbolic-link
target. The six files must print `OK` both in staging and after copying. The
staging folder remains available for inspection; no cleanup command deletes it
or other work automatically. A failed copy can leave a partial new skill
folder, which the next attempt refuses. Inspect and move that partial folder
aside yourself before another attempt; do not remove a folder of unknown origin.

The client needs Python 3.10 or newer. A newly created
`~/.config/baltor/client.json` names the token variable and the same four
effects as the `Baltor-Step-Effects` header above; it never holds the token.
If configuration already existed, the block preserves it and asks you to
check its origin, token variable and effects. OpenCode lists the skill from
its next session. This bootstrap places a skill, not arbitrary plugins or
tools, and does not establish that a model has used it successfully.

## Your first download

Choose one reference and ask OpenCode to fetch it and place it with the skill:

```text
Use the baltor-library skill to fetch ITEM-IDENTITY from Baltor and install it for OpenCode in this project.
```

The skill runs its client, which you can also run yourself from the project folder. Replace the two placeholders with the identity and the `body_digest` the search returned:

```bash
BALTOR=.opencode/skills/baltor-library/scripts/baltor.py
mkdir -p ~/.cache/baltor
python3 "$BALTOR" search "review inputs" --limit 3 > ~/.cache/baltor/selection.json
python3 "$BALTOR" fetch --selection ~/.cache/baltor/selection.json --identity ITEM-IDENTITY \
  --digest SELECTED-DIGEST --request-id QUICKSTART-1 --output ~/.cache/baltor/QUICKSTART-1 --authorize-download
python3 "$BALTOR" install --staged ~/.cache/baltor/QUICKSTART-1 --client opencode --authorize-install
```

`fetch` checks every file of the item against its SHA-256 digest and stages it in a new folder. `install` checks the files again and writes their exact bytes into `.opencode/skills/NATIVE-NAME/`, and it never replaces a folder it did not install. It prints its install record, which gives the name it placed the skill under: NATIVE-NAME below. It places skills only; another kind of item stays in its staging folder. The first download of an item version in a calendar month is one measured unit and appears in your usage; downloading the same version again that month, with any `request_id`, adds nothing.

In a session, OpenCode can also read an item through the protocol connection, to decide whether it fits before you place it. `provisioning_read` takes the `identity`, a new `request_id` for each logical download and the `expected_digest` from the search, so a changed body is refused rather than substituted. For a single-file item its `result` is `provisioning_body/v3`, with the `body` inline and its `digest`. For a package of several files it is `provisioning_package_read/v1`: each file's exact content with its `path` and SHA-256 `digest`, one page at a time; ask for the next page with `file_offset` set to `next_file_offset` and the same `request_id`. [Searching and retrieving](service-searching-and-retrieving.md#package-files-through-the-protocol-tool) describes the record. A read is counted like a download. Place files with `install`, not by saving what the model read.

## Check that it worked

Check the placed files first. The command answers `"verified": true`, and names any file that changed since it was placed:

```bash
python3 .opencode/skills/baltor-library/scripts/baltor.py verify --client opencode --name NATIVE-NAME
```

1. Start a new session: OpenCode lists the skill by that name.
2. Open [your account page](https://app.baltor.ai/account): the download is listed in your usage.
3. Confirm the account and its scopes from the terminal with the command below.

```bash
curl -sS -H "Authorization: Bearer $BALTOR_SERVICE_TOKEN" https://baltor.ai/api/v1/session
```

The answer's `result` is `service_session/v1`. Its `principal` names the account and its `scopes`: a search needs `provisioning:metadata` and a download needs `provisioning:read`.

## When it does not work

| Code | Status | What to do |
| --- | --- | --- |
| `unauthorized` | 401 | The token is missing, wrong, expired or revoked. Set `BALTOR_SERVICE_TOKEN` in the terminal that starts OpenCode, then run the session check above. |
| `insufficient_scope` | 403 | The token lacks the scope this operation needs. Create a token with `provisioning:read`. |
| `plan_required` | 403 | Your account has no plan that includes downloads; search still works. Choose Pro on the [pricing page](https://baltor.ai/pricing). The refusal's `details` name that page, and the founding offer while places remain. |
| `step_effects_required` | 403 | The item declares effects your configuration does not declare. Add the `effects_to_declare` that the refusal's `details` name, if your harness may do them, or choose another item. |
| `item_unavailable` | 404 | The identity is not in your library, or it was withdrawn. Search again and use a fresh reference. |
| `request_identity_required` | 400 | A download needs a `request_id`. Give each logical download a new one. |
| `download_required` | 413 | The body is larger than the inline limit. Fetch it through `/api/v1/download`. |
| `failed_attempt_limit_reached` | 429 | Too many refused attempts from your address. Fix the token, then wait a minute. |

Keep `oauth` false for this supplied-token recipe. For an OAuth connection,
follow the separate [connection guide](service-serving-and-connections.md#oauth-connections)
and use the canonical `https://baltor.ai/mcp` endpoint; do not combine a stale
Authorization header with an account-linking attempt. Qualification of this
token recipe does not establish that every OpenCode version's OAuth flow works.
[Troubleshooting](service-troubleshooting.md) explains every code,
[Service status](https://app.baltor.ai/status) shows a current outage, and
[Serving and connections](service-serving-and-connections.md) names the protocol
versions. The nightly record of this page's steps is written under
`artifacts/quickstart-checks/` in the repository by
[the quickstart check](../../tools/check_quickstarts.py).
