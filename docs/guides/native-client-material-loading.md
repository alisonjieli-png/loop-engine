# Loading selected material into a native client

Kind: operating guide. It describes what one tool does today, what a passing
run proves and what it does not prove. Planned behavior has its own section
at the end.

The hosted intelligence service can offer an item and deliver its bytes. That
is not the same as a client having loaded the item. The
[install tool](../../tools/install_selected_material.py) closes the first part
of that gap. It takes selected material from the service, places it where a
supported client discovers material, and then asks the client itself what it
reports. It never starts a model turn.

The tool was checked on September 20 and September 21, 2026 against the local
fixture service, a scripted loopback service written inside the checks, and
the OpenCode binary installed on the development workstation. It has not been
run against the hosted service. A run against the hosted service makes one
metered body read for each new item and needs the owner's authority. Use
`--preview` first to see the exact list without any metered read.

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
    ├── Role: Practitioner, Intelligence, or Solution
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

A client such as OpenCode is a harness: an adapter that a Loop uses. A
separately initialized harness process can perform the assignment of a
discrete cognitive or act step Loop node. Read the
[complete behavioral explanation](../../ASTRA.md#complete-behavioral-explanation)
before describing one. A skill folder, an install record and this tool are
not runtime types and are not graph vertices. Placing a file grants no
permission and does not promote the item. On the service side, three of the
four requests that this tool makes are already owned by a classified Loop in
the [HTTP adapter](../../src/loop_engine/core/service_runtime/http.py): the
search, the manifest and the download. The fourth, the read of
`/api/v1/capabilities`, returns a static record from the adapter itself and
is not wrapped in a Loop.

## Four separate facts

The report keeps four facts apart for every selected item. A later fact never
replaces an earlier one, and an unknown fact is written as `null`, not as
`false`.

```text
One selected item
├── Offered
│   └── The service named the item for this key, in a search hit or a manifest
├── Fetched
│   └── The body arrived and matched the response header and the manifest
├── Installed
│   └── The file is in the client's native location, written now or already identical
└── Reported by the client
    └── The client's own listing names that exact file and returns the same content
```

"Reported by the client" is true only when all three observations hold: the
listing names that exact file, the name is the expected one and the content
has the digest of the served body. The three observations stay separate in
`client_report`. The summary counts a path match on its own as
`listed_at_installed_path`, which can be higher than `reported_by_client`.

Three further facts are outside this tool: loaded into a model turn, used by
the model, and verified as helpful. They need a model turn, and the tool
starts none.

## What the tool does today

The tool runs on a system that can open a path without following a symbolic
link and can open a file relative to an open folder. That is POSIX behavior.
On a system without it, for example Windows, the tool refuses with
`confined_file_operations_unavailable` before any effect.

1. It validates the command line without any effect. It refuses a missing
   approval flag, an origin that is not an exact HTTPS origin, an unknown
   client kind, an unusable identity and a report path that already exists.
   Exactly one approval flag is allowed: `--authorize-install` or
   `--preview`.
2. It reads the service key from the environment variable that you name. The
   key is never accepted on the command line. A key that appears in any
   argument is refused, and a wrong command line is refused without repeating
   its values.
3. It creates the report file exclusively before the first request, so a run
   never replaces an earlier report. The file says `"complete": false` until
   the run ends. The origin, the request prefix and the selection are written
   there before the first request leaves the tool, and the request identity of
   a body read is written there before that read is sent. A run that is
   stopped can therefore be repeated with `--request-prefix` without paying
   for the same read twice.
4. It reads `/api/v1/capabilities` and refuses an unknown service contract
   before any authenticated request. The record version, the interface
   version, the download route, the declared body format and the download
   allowance must all be the ones this tool supports.
5. It selects items. With `--query` it searches through `/api/v1/retrieval`
   and selects every hit. With `--identity` it takes the identities you name.
   A search answer that does not state that it loaded no body is refused.
6. For each item it reads the manifest through `/api/v1/provisioning`. It
   refuses a manifest of another record version, a manifest that answers for
   another identity, a digest that differs from the one the search named, and
   manifest text that UTF-8 cannot carry. It refuses, before any body read, a
   kind without a native location, a body that this key may not read, a
   declared size over the allowance, a symbolic link in the path, a different
   existing file, and a target folder that could not take the file. When the
   identical file is already in place it makes no body read at all.
7. It downloads the body through `/api/v1/download` with the manifest digest
   as the expected digest. The response must carry the download record type.
   The tool computes the SHA-256 digest of the bytes and compares it with the
   `X-Content-SHA256` response header and with the manifest. It also compares
   the size with the manifest and requires text in UTF-8. Any difference is
   refused and nothing is written.
8. It writes the file below the target folder. Every folder on the way is
   opened without following a symbolic link. The bytes go to a new partial
   name in the same folder, and the final name appears only as a hard link to
   the finished file, so a stopped run leaves no cut file under the name that
   the client discovers. A hard link never replaces an existing name, so an
   existing file is never replaced.
9. It runs the client's version command and listing command in the target
   folder. The service key is removed from the environment of that process.
   For each installed item it records whether the listing names the exact
   file, whether the name matches and whether the content has the same digest
   as the served body. It also records every path that the client process
   itself added below the client's own folder.
10. It reads every installed file again through the same confined reader and
    compares it with the install record. The client process is not this tool's
    code, so a file that changed while that process ran is refused with
    `file_changed_after_install`.
11. It writes the report and prints a short summary.

Every response is bounded twice: by a size, so an endless body stops at the
declared size plus one byte, and by a deadline on the monotonic clock for the
whole response, so a service that sends one byte at a time cannot hold a run
open. `request_timeout_seconds` bounds one socket operation;
`response_deadline_seconds` bounds one whole response.

### A preview before the approval

`--preview` runs the capabilities read, the search and the manifests, and
writes a report of what would be selected. It makes no body read, writes no
file below the target and starts no client process. Use it to see the exact
list before approving `--authorize-install`, especially with `--query`, where
the set of items is not known when the approval is given. A preview exits 0
when every selected item could be installed.

### Command

```bash
PYTHONPATH=src .venv/bin/python tools/install_selected_material.py \
  --origin https://app.baltor.ai \
  --key-variable BALTOR_SERVICE_TOKEN \
  --client opencode \
  --target /path/to/your/project \
  --query "review inputs" \
  --report /path/to/new-report.json \
  --authorize-install
```

Set the variable from your secret store before you run the command. The name
`BALTOR_SERVICE_TOKEN` is the one that the
[client recipes](../../src/loop_engine/core/service_runtime/web_assets/client-recipes.json)
use. Any other variable name works.

| Input | Meaning |
|---|---|
| `--origin` | Exact service origin without a path. Plain HTTP is accepted only for a loopback address together with `--allow-loopback-http`. |
| `--key-variable` | Name of the environment variable that holds the key. |
| `--query` or `--identity` | Exactly one of them. `--identity` can be repeated. `--top-n` limits the search hits. |
| `--client` | Client kind from the client recipes registry. Only `opencode` has a layout profile today. |
| `--target` | Existing project folder. It may not be a symbolic link. |
| `--report` | New report path. It may not exist. |
| `--client-executable` | Client binary to ask. Without it the tool looks for `opencode` on the search path. |
| `--request-prefix` | Prefix of an earlier report. The same prefix repeats the same read requests. |
| `--authorize-install` | Approves metered body reads, file writes below the target and one listing process. |
| `--preview` | Shows what would be selected. No body read, no file write, no client process. It cannot be given together with `--authorize-install`. |

The exit code is 0 only when every selected item is installed, the client
reports it with the matching name and content, and the file on disk still
holds the installed bytes when the run ends. It is 1 when any item was
refused, not reported or not checkable. It is 2 when the command line was
refused before any effect.

### Where the file goes

For OpenCode the tool places a served item of kind `skill` at
`.opencode/skills/<name>/SKILL.md`. The name is the service identity in lower
case with dots and underscores replaced by hyphens, for example
`skill.review_inputs` becomes `skill-review-inputs`. An identity that cannot
follow the documented name rule of 1 to 64 lower-case letters, digits and
single hyphens is refused.

The file starts with a generated header that holds the name and the purpose
from the manifest as the description. Both are written as quoted strings,
because both observed client versions drop a skill whose bare name reads as a
number or a boolean. The served body follows byte for byte.
The service does not declare the format of a body in a typed field today, so
the tool does not guess whether a body already carries its own header. The
install record keeps both digests: `body_sha256` is the served body, and
`file_sha256` is the file on disk. The bytes after `body_offset_bytes` are the
served body.

The install record is part of the report. The tool writes no second record
into the project and keeps no store of its own.

The other served kinds are refused before any body read:

| Served kind | Why it has no native location today |
|---|---|
| `instruction_file` | OpenCode reads instructions from `AGENTS.md` and from entries in the project's own configuration. Both belong to the project, and the tool does not edit existing files. |
| `reusable_code` and `tool` | Code needs independent admission before local use. A download is not an admission. |

## Where OpenCode discovers project material

Sources: the public documentation for
[skills](https://opencode.ai/docs/skills/),
[rules](https://opencode.ai/docs/rules/),
[agents](https://opencode.ai/docs/agents/) and
[commands](https://opencode.ai/docs/commands/), the client's own help output,
and listing commands run on September 20, 2026. No command started a model
turn.

| Material | Project location | Command that lists it without a model turn |
|---|---|---|
| Skills | `.opencode/skills/<name>/SKILL.md`. Documented and observed. Also observed: `.opencode/skill/`, `.claude/skills/` and `.agents/skills/`. | `opencode debug skill` prints entries with `name`, `description`, `location` and `content`. |
| Agents | `.opencode/agents/<name>.md`. Documented and observed. The client's built-in help text also names `.opencode/agent/`. | `opencode agent list` prints names and permission rules. `opencode debug agent <name>` prints one agent with its prompt. |
| Commands | `.opencode/commands/<name>.md`. Documented and observed. The built-in help text also names `.opencode/command/`. | None of its own. `opencode debug config` names it under `command`. |
| Instructions | `AGENTS.md`, found by walking up from the working folder, else `CLAUDE.md`. Also the `instructions` entries of `opencode.json`. Documented only. | None. No command reports which instruction files were loaded. `opencode debug config` shows only the configured entries. |

`opencode debug config` prints the resolved configuration, which can hold
header values. The tool never runs it.

### What was observed with the installed client

The workstation holds two installations. The binary first on the search path,
`~/.opencode/bin/opencode`, reports version 1.18.31. The package installation
at `~/.local/bin/opencode` reports version 1.17.9, the version that the
earlier connection reports recorded. The skill observations below were made
with both versions and were the same for both. The log lines and the agent
and command observations were made with 1.18.31 only.

- The `content` field of `opencode debug skill` equals the bytes after the
  header exactly. This held for a body with its own inner header, without a
  final line break, with Windows line endings, with a leading rule line, with
  text outside ASCII, for an empty body and for leading tabs.
- Captured through a pipe that a Python `subprocess` call created and read,
  the listing stopped at exactly 65,536 bytes and the exit code was still 0.
  The same command in a shell, with its output piped to a fast reader,
  delivered the whole listing: 208,318 bytes with version 1.18.31 and 208,236
  bytes with version 1.17.9. Written to a regular file, the listing was
  complete as well. The cut therefore depends on the reader, not on the client
  alone. The tool captures the listing in a regular file, and it treats a
  listing that does not parse as unknown, never as "not reported".
- Project skills were discovered in a folder that is not a git repository.
- The listing accepted a folder name that breaks the documented name rule,
  and it showed the name from the header, not the folder name. The tool still
  follows the documented rule.
- When two skills share a name, the client logs a duplicate name and lists
  one of them. The report then says that the same name was reported from
  another location.
- At information log level the listing named no protocol server, session or
  model service.
- The listing process created `.opencode/.gitignore` in the project. The
  report lists every path that the client process added below the client's
  own folder.
- For an agent, the reported prompt had its final line break removed, so
  agent content is not byte exact. Agents are not a served kind today.

## What a passing run proves and what it does not prove

A passing run proves, for every selected item:

- the service offered the item to this key;
- the downloaded bytes have the SHA-256 digest that the response header and
  the manifest both state, and the size that the manifest states;
- the file below the target folder holds the generated header followed by
  exactly those bytes, and no existing file was replaced;
- the file still holds exactly those bytes after the client process ran. The
  tool reads it again and compares it with the install record;
- the client's own listing names that exact file, shows the expected name and
  returns content with the digest of the served body;
- the tool started no model turn. It runs only the version command and the
  listing command from its typed client profile, and a profile that names the
  `run` subcommand is refused when it is built.

A passing run does not prove:

- that a model read the skill. OpenCode documents that a skill is loaded on
  demand through its skill tool, when the agent decides to load it;
- that the skill was used, or that it helped the task;
- that one agent's permission rules do not hide the skill. The listing is not
  evaluated for one agent;
- anything about another client version. The report names the version it saw
  and says whether the layout was observed with that version;
- anything about the hosted service. Every run so far used the local fixture
  service;
- anything about the licence. The record keeps the licence name that the
  manifest states and whether one was stated. The tool does not judge it;
- independent qualification of the item. Placement is not promotion.

## Refusals

Each refusal has a stable code and a stage. The text beside a code never holds
the key or a response body.

| Stage | Codes |
|---|---|
| Before any effect | `install_not_authorized`, `preview_excludes_authorize_install`, `invalid_arguments`, `invalid_origin`, `invalid_key_variable_name`, `key_variable_not_set`, `key_value_not_usable`, `key_on_command_line`, `exactly_one_of_query_or_identities_required`, `invalid_query`, `invalid_search_limit`, `duplicate_identity`, `identity_has_no_native_name`, `invalid_request_prefix`, `invalid_limits`, `client_registry_unreadable`, `unsupported_client_registry_version`, `unknown_client_kind`, `client_has_no_layout_profile`, `target_not_a_real_directory`, `confined_file_operations_unavailable`, `report_path_not_new`, `report_path_not_usable` |
| Service contract | `unsupported_service_capabilities`, `unsupported_service_record`, `service_unreachable`, `redirect_refused`, `response_too_large`, `response_deadline_passed` |
| Selection and offer | `identity_has_no_native_name`, `service_refused`, `kind_has_no_native_location`, `body_not_permitted`, `body_exceeds_download_allowance`, `offer_changed_between_search_and_manifest`, `purpose_has_no_printable_text` |
| Fetch and verification | `service_refused`, `digest_header_missing_or_malformed`, `body_differs_from_header_digest`, `body_differs_from_manifest_digest`, `body_size_differs_from_manifest`, `download_exceeds_declared_size`, `body_is_not_utf8_text` |
| Placement | `path_traversal_refused`, `symbolic_link_refused`, `path_component_not_a_directory`, `existing_path_not_a_regular_file`, `different_file_exists`, `target_folder_not_writable`, `path_not_usable`, `write_failed`, `file_changed_after_install` |
| Client profile | `invalid_layout_profile`, `model_turn_command_refused` |
| After the report was reserved | `unexpected_error` |

`unexpected_error` means that something outside the typed refusals was raised
after the report existed. The report then keeps every item that was already
recorded, names the type of the error under `interrupted_by` and says
`"complete": false`. The run never ends without a report.

The listing has its own states. They are not refusals, and an unknown listing
is never read as "not reported":

| Listing state | What it means |
|---|---|
| `observed` | The listing ran and could be read. |
| `nothing_installed` | No item reached the client's folder, so no listing was run. |
| `preview_only_no_client_process` | The run was a preview. No client process was started. |
| `client_offers_no_listing_command` | The client profile has no listing command. |
| `client_executable_not_found` | No binary was named and none was found on the search path. |
| `client_executable_not_usable` | The named binary could not be run. |
| `listing_timed_out` | The listing command did not finish inside its bound. |
| `listing_command_failed` | The listing command ended with a status other than 0. |
| `listing_too_large` | The output was larger than the bound for a listing. |
| `listing_unreadable` | The output was cut, was not text in UTF-8, was nested too deeply or was not a list. |

The service key goes to the named origin only. The tool ignores proxy
settings in the environment and refuses every redirect.

A `service_refused` detail keeps the status and the service's own code, for
example `404:item_unavailable` or `403:body_forbidden`.

One body read adds one usage record at the service. The tool makes no
automatic retry. When no response arrives, the fetch outcome is
`unknown_no_response_received`, because the service may already have recorded
the read. Run again with `--request-prefix` set to the prefix in that report.
The service then treats the read as the same request. This was observed with
the local service: two runs with one prefix left one usage record.

## Checks

```bash
PYTHONPATH=src:tools .venv/bin/python -m unittest tools/test_install_selected_material.py
```

The [checks](../../tools/test_install_selected_material.py) start the real
local service from the HTTP test fixtures and use a small fixture program as
the client. They cover a digest that differs from the header, a body that
differs from the manifest, a longer body, traversal and absolute paths, a
symbolic link at every level of the path, a different existing file, an
existing file under another header of the same length, an identical existing
file, a target folder that cannot take the file, a body that the key may not
read, a kind without a native location, an item that the client omits,
changed content and a changed name in the listing, a cut listing, a listing
over its bound, a listing nested too deeply, a listed location that the
platform cannot resolve, a listed name that UTF-8 cannot carry, a client that
rewrites the installed file while it lists it, and a preview.

A second group of checks serves scripted answers from a loopback address,
because the real local service answers correctly and cannot show what the
tool does with a faulty or hostile peer. Those checks cover a download under
another record type, a manifest for another identity, a manifest of another
record version, a manifest that declares more than the allowance, an offer
that changed between the search and the manifest, manifest text that UTF-8
cannot carry, a service record nested too deeply, capabilities that name
another body format, a search that claims to have loaded bodies, a response
over the bound for a record, a body that keeps arriving after the declared
size, a response that arrives too slowly, a dropped connection, and the
report content at the moment of the first request and of the metered read.
No provider, model or external host is used.

The removed-guard controls are listed in the `MUTANTS` table of the checks.
Each control removes one guard in memory, runs the named check of that guard
and requires that the check fails. Source files are never changed by a
control. There are 46 controls. They cover both digest comparisons, the
download status and the download record type separately, the body permission,
the download allowance, the manifest identity and record version, the offer
comparison, the capabilities body format, the search that returns references
only, the bounds on a record, on a body and on a listing, the whole response
deadline, the name rule, traversal, symbolic links, the real target folder, a
different existing file before the read and at the write, the header of an
existing file, a placement that is possible before the read, the listing as
the only source of "reported", the name and the content behind the headline
fact, the second read of the installed file, a location the platform cannot
resolve, every character of the report written as an escape, nesting depth as
a parse failure, the record written before the first request and before the
metered read, the client registry version, the preview, the key kept from the
client process, from the command line and from proxies and redirects, the new
report path, the service contract, the declared text format and the refusal
of a model turn command.

One control needs a folder that really refuses a new file. A process that may
write anywhere, for example the machine administrator, cannot show that
refusal, so that check and its control are skipped there instead of passing
for the wrong reason.

One optional check asks the real OpenCode binary for its listing only. It is
skipped when the binary is absent.

## Not implemented yet

- A run against the hosted service under the owner's authority.
- Proof that a model loaded a skill during a task. This needs model-call
  authority and a comparison with a withheld or changed resource, as the
  [harness instance layout guide](harness-instance-context-layout.md)
  describes.
- Placement of instruction files. It needs a decision about how a project
  accepts an entry in its own configuration.
- Layout profiles for other clients. Codex has a client recipe but no layout
  profile, because no layout evidence was gathered for it.
- Writing a complete skill file unchanged. This waits for a typed field in
  which the service declares the format of a body.
- Updating or removing installed material. The tool never replaces and never
  deletes a file.
- A licence refusal. The serving path owns that decision; see the open
  findings in the [takeover checkpoint](../context/TAKEOVER-CHECKPOINT-2026-09-20.md).

The [onboarding guide](harness-service-onboarding.md) describes the wider
customer journey that this tool is one step of.
