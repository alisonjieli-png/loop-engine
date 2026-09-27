---
name: check-service-status
description: Reads the public status page of a developer service at the moment of the call and reports the overall indicator, the components that are not operational and the open incidents with their links. The providers on the allow list are anthropic, cloudflare, digitalocean, flyio, github, netlify, npm, render, supabase and vercel. Use it when a build, a deploy, a package install or an API call fails and you need to know whether the provider reports a problem right now. Use it instead of a remembered or stored status, because a status changes within minutes.
license: MIT
metadata:
  asset_id: "check_service_status"
  asset_version: "1.0.0"
  kind: "tool"
  source_host: "www.githubstatus.com, www.cloudflarestatus.com, status.flyio.net, www.vercel-status.com, status.render.com, www.netlifystatus.com, status.supabase.com, status.digitalocean.com, status.claude.com, status.npmjs.org"
  source_format: "Statuspage v2 summary.json"
  observed_on: "2026-09-27"
---

# Check service status

## What it returns

The tool reads the Statuspage v2 summary of one provider when you call it,
for example `https://www.githubstatus.com/api/v2/summary.json`. It returns:

- the overall indicator and its description, as the page gives them;
- the time that the page gives as its last update;
- every component that is not operational, with its status;
- every open incident, with its status, impact, start time and link;
- the address it read and the time it read it.

It never returns a stored status. When the page leaves a value out, the
value is null. The tool does not guess it.

## How to call it

Give one JSON object as the only argument. Run the command from the package
folder.

```text
python3 scripts/check_service_status.py '{"provider": "github"}'
```

To read the JSON object from standard input instead, give `-` as the only
argument.

| provider | status host that the tool reads |
|---|---|
| anthropic | status.claude.com |
| cloudflare | www.cloudflarestatus.com |
| digitalocean | status.digitalocean.com |
| flyio | status.flyio.net |
| github | www.githubstatus.com |
| netlify | www.netlifystatus.com |
| npm | status.npmjs.org |
| render | status.render.com |
| supabase | status.supabase.com |
| vercel | www.vercel-status.com |

The request contract is [contracts/input.schema.json](contracts/input.schema.json).

Exit codes:

- 0: success. The tool prints the result.
- 2: the request is invalid, for example a provider that is not on the list.
  The tool sends nothing.
- 3: the status page could not be read, or it answered in an unexpected shape.

On exit code 2 or 3 the tool prints only an error record, never a partial
result:

```json
{"record_type": "knowledge_radar_tool_error/v1", "code": "unknown_provider", "message": "provider must be one of: anthropic, cloudflare, digitalocean, flyio, github, netlify, npm, render, supabase, vercel"}
```

Error codes: invalid_request, unknown_provider, source_unreachable,
source_http_error, source_too_large, redirect_refused,
unexpected_source_shape and internal_error.

## Output fields

The result contract is [contracts/output.schema.json](contracts/output.schema.json).

| Field | Meaning |
|---|---|
| record_type | Always knowledge_radar_check_service_status_result/v1. |
| provider | The provider that you asked for. |
| indicator | status.indicator from the page, for example none, minor, major, critical or maintenance. |
| description | status.description from the page, for example All Systems Operational. |
| updated_at | page.updated_at from the page. |
| non_operational_components | Each component whose status is not operational, as name and status, in page order. Component groups are included. |
| open_incidents | Each incident whose status is not resolved or postmortem, as name, status, impact, started_at and shortlink, in page order. |
| source | The https address that the tool read. |
| observed_at | The UTC time of the read. |

Example, from the recorded Supabase answer in the test fixtures:

```json
{"record_type": "knowledge_radar_check_service_status_result/v1", "provider": "supabase", "indicator": "minor", "description": "Partially Degraded Service", "updated_at": "2026-09-27T14:59:19.729Z", "non_operational_components": [{"name": "API Gateway", "status": "degraded_performance"}], "open_incidents": [{"name": "401 errors due to JWT rejections", "status": "identified", "impact": "minor", "started_at": "2026-08-14T02:23:18.361Z", "shortlink": "https://stspg.io/18v97b9scdh2"}], "source": "https://status.supabase.com/api/v2/summary.json", "observed_at": "2026-09-27T15:05:45Z"}
```

## Effects

- Network: one HTTPS GET to the status host of the chosen provider, and to
  no other host. The tool follows a redirect only when it stays on the same
  host and on https. It sends no credentials and no cookies.
- Files: Python reads the script. The test reads the fixtures in the
  verification folder. The tool reads no other file.
- Process: each call starts one Python process.
- Writes: nothing. The tool writes no file, no cache and no log.

## Source, terms and attribution

- Source format: the Statuspage v2 summary endpoint `/api/v2/summary.json`,
  which each status page on the list serves to anyone without a key. Two
  examples are https://www.githubstatus.com/api/v2/summary.json and
  https://status.supabase.com/api/v2/summary.json.
- Each status page, with its component names and incident names, belongs to
  its provider. The tool passes on the indicator, the description, the
  component names and the incident names as the page gives them. It does not
  copy the text of incident updates.
- How the allow list was checked: on 2026-09-27, between 15:05 and 15:11 UTC,
  the tool author sent one GET of `/api/v2/summary.json` to each candidate
  host, with no redirect followed. A host is on the list only when it answered
  with HTTP status 200 and a JSON object that holds page, status, components,
  incidents and scheduled_maintenances in the Statuspage v2 shape.
- Verified that day, with the Statuspage version header in the answer:
  www.githubstatus.com, status.flyio.net, www.vercel-status.com,
  status.render.com, www.netlifystatus.com, status.supabase.com,
  status.digitalocean.com, status.npmjs.org and status.claude.com.
- Verified that day by shape only: www.cloudflarestatus.com answered with the
  complete Statuspage v2 shape, but without the Statuspage version header. Its
  page.updated_at was 2026-08-27T00:00:00.000Z while it listed open incidents
  that started on 2026-09-22 and 2026-09-23. For cloudflare, read updated_at
  as the value that the page reports, not as the time of its last change.
- Changed that day: status.anthropic.com answered with a permanent redirect
  (HTTP status 301) to status.claude.com, which is another host. The list
  therefore names status.claude.com for anthropic, and that host passed its own
  check.
- Left out that day: status.openai.com answered with page, status and
  components only. It had no incidents list, so it is not the Statuspage v2
  shape. status.pypi.org had no address in the domain name system.
- Live check of the finished tool: on 2026-09-27 at 15:33:39 UTC,
  `python3 scripts/check_service_status.py '{"provider": "anthropic"}'`
  exited with 0 and reported the indicator none, the description All Systems
  Operational, no component that was not operational and no open incident.
  The same day, the tool also read the full recorded answer of every host on
  the list without a network: all ten parsed, and cloudflare gave 60
  components that were not operational and 3 open incidents.

## Limits

- Only the ten providers in the table. The tool cannot read another host.
- A status page shows what the provider has published. A problem that the
  provider has not posted yet does not appear.
- The tool reads the summary only. It does not return incident update text,
  component descriptions or maintenance that has not started. A component
  under maintenance still appears, with the status under_maintenance.
- A large page gives a long list. On 2026-09-27 cloudflare listed 480
  components, and 60 of them were not operational.
- An answer larger than 2 MB is refused. The tool waits at most 20 seconds.
- The tool keeps no cache and sends one request for each call. Call it again
  only when you need a newer answer, and not in a tight loop.
- A provider can move or change its status page. When that happens the tool
  ends with exit code 3 and the code unexpected_source_shape,
  source_http_error or redirect_refused. It does not fall back to another
  source.

## How to check it

From the package folder, run:

```text
python3 scripts/test_check_service_status.py
```

The test needs no network. It serves the recorded and hand-made answers that
[verification/cases.json](verification/cases.json) names to the tool, in
place of the network. It prints one line such as
`{"passed": 21, "failed": 0, "known_wrong_rejected": 2}` and exits 0 only when
every case passes. The cases include deliberately wrong expectations that the
test must reject, malformed answers and a network timeout that must end
with exit code 3, and invalid requests that must be refused before any
request is sent.
