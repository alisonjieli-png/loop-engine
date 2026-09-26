"""Weekly check of the upstream sources of imported items: a repository gone, a licence changed, an advisory.

Kind: operator tool for the weekly job (roadmap S-6.199). Every imported item
names its upstream in its source reference, `github.com/{owner}/{repository}/{path}@{revision}`.
This command groups the served imported items by repository and asks the
repository host, once for each repository, whether the repository is still
there, which licence it declares now and whether it lists a published
security advisory. It lists what changed and writes a record. It withdraws
nothing: a finding is a reason for a person to withdraw or re-review, and the
record names every item the finding touches.

```text
Findings (current behaviour, bounded first version)
├── repository_gone        the repository answers 404
├── licence_changed        the repository declares another licence than an item carries
├── advisory_published     the repository lists at least one published security advisory
├── repository_archived    the repository is archived (informational)
└── upstream_unknown       the host did not answer, so nothing is concluded
```

Network reads need `--authorize-network-reads`; without it the command writes
the inventory of repositories and items and reads nothing. Reads are bounded
by `--max-repositories` and use the host's public interface without a
credential, so they stay inside the unauthenticated allowance. Nothing here
calls a model or writes to the service store.

    PYTHONPATH=src:tools python tools/check_upstream_sources.py --host /data/host.json --authorize-network-reads
    PYTHONPATH=src:tools python tools/check_upstream_sources.py --items-file items.json --list-only

The record of each run is written under `artifacts/upstream-source-checks/`.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

RECORD_TYPE = "upstream_source_check/v1"
DEFAULT_OUTPUT = ROOT / "artifacts" / "upstream-source-checks"
SOURCE_REF = re.compile(r"^github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repository>[A-Za-z0-9_.-]+)/(?P<path>.+)"
                        r"@(?P<revision>[0-9a-f]{40})$")
API = "https://api.github.com"
USER_AGENT = "baltor-upstream-source-check/1"
DEFAULT_MAX_REPOSITORIES = 30
#: A licence answer that says nothing about the licence: the host could not detect one.
UNKNOWN_LICENCES = frozenset({"", "NOASSERTION", "OTHER"})


def parse_source_ref(value):
    """The upstream of one imported item, or None when the reference is not an imported one."""
    match = SOURCE_REF.match(value) if isinstance(value, str) else None
    if match is None:
        return None
    return {"owner": match["owner"], "repository": match["repository"], "path": match["path"],
            "revision": match["revision"]}


def imported_items(context):
    """Every served imported item version of the active release: identity, source reference, licence and tier."""
    from loop_engine.core.service_runtime.catalogue_bundle import item_version_tier
    from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage
    from loop_engine.core.service_runtime.catalogue_releases import load_release, read_pointer, read_state, withdrawal_keys
    binding = context.binding
    with binding.store() as store:
        read_state(binding, store)
        _row, pointer = read_pointer(binding, store)
        if pointer is None:
            return []
        release = load_release(binding, store, pointer["release_id"])
        withdrawn = withdrawal_keys(binding, store)
    items = []
    for _version, payload in release.versions:
        reference = payload["reference"]
        package = CataloguePackage.from_dict(payload["package"])
        if (reference["identity"], package.served_digest) in withdrawn or parse_source_ref(reference.get("source_ref")) is None:
            continue
        items.append({"identity": reference["identity"], "source_ref": reference["source_ref"],
                      "license": reference.get("license", ""), "library_tier": item_version_tier(payload)})
    return items


def group_by_repository(items):
    """`owner/repository` -> the items imported from it, in identity order; items that are not imports are left out."""
    groups = {}
    for item in items:
        upstream = parse_source_ref(item.get("source_ref"))
        if upstream is None:
            continue
        groups.setdefault(f"{upstream['owner']}/{upstream['repository']}", []).append(dict(item))
    return {name: sorted(rows, key=lambda row: row["identity"]) for name, rows in sorted(groups.items())}


def default_opener(url, timeout=20):
    """(status, body) of one unauthenticated read of the host's public interface."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as answer:
            return answer.status, answer.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def fetch_repository(name, opener):
    """What the host says about one repository now: present or gone, its licence, archived, and its advisories."""
    try:
        status, body = opener(f"{API}/repos/{name}")
    except Exception as error:  # noqa: BLE001 - a failed read is recorded, never guessed
        return {"status": "error", "error": type(error).__name__}
    if status == 404:
        return {"status": "gone", "http_status": 404}
    if status != 200:
        return {"status": "error", "http_status": status}
    try:
        document = json.loads(body)
    except ValueError:
        return {"status": "error", "http_status": status, "error": "unreadable answer"}
    licence = ((document.get("license") or {}).get("spdx_id") or "") if isinstance(document, dict) else ""
    archived = bool(document.get("archived")) if isinstance(document, dict) else False
    advisories = None
    try:
        status, body = opener(f"{API}/repos/{name}/security-advisories?state=published&per_page=100")
        if status == 200:
            listed = json.loads(body)
            advisories = len(listed) if isinstance(listed, list) else None
    except Exception:  # noqa: BLE001 - an advisory list that cannot be read stays unknown
        advisories = None
    return {"status": "present", "http_status": 200, "licence": licence, "archived": archived, "advisories": advisories}


def assess(name, items, answer):
    """The findings for one repository, each naming every served item it touches."""
    identities = [row["identity"] for row in items]
    if answer.get("status") == "gone":
        return [{"code": "repository_gone", "repository": name, "identities": identities,
                 "detail": "the repository answers 404; the served copies stay licensed as imported"}]
    if answer.get("status") != "present":
        return [{"code": "upstream_unknown", "repository": name, "identities": identities,
                 "detail": "the host did not answer, so nothing is concluded"}]
    findings = []
    declared = answer.get("licence") or ""
    if declared not in UNKNOWN_LICENCES:
        changed = [row["identity"] for row in items if row.get("license") and row["license"] != declared]
        if changed:
            findings.append({"code": "licence_changed", "repository": name, "identities": changed,
                             "detail": f"the repository declares {declared} now; the served items carry another licence"})
    if answer.get("advisories"):
        findings.append({"code": "advisory_published", "repository": name, "identities": identities,
                         "detail": f"the repository lists {answer['advisories']} published security advisories"})
    if answer.get("archived"):
        findings.append({"code": "repository_archived", "repository": name, "identities": identities,
                         "detail": "the repository is archived; its files no longer change"})
    return findings


def run(items, *, authorize_network_reads, opener=None, max_repositories=DEFAULT_MAX_REPOSITORIES, clock=time.time):
    started = clock()
    groups = group_by_repository(items)
    checked, answers, findings, skipped = [], {}, [], []
    if authorize_network_reads:
        opener = opener or default_opener
        for name, rows in groups.items():
            if len(checked) >= max_repositories:
                skipped.append(name)
                continue
            answers[name] = fetch_repository(name, opener)
            checked.append(name)
            findings.extend(assess(name, rows, answers[name]))
    return {"record_type": RECORD_TYPE, "run_at": datetime.fromtimestamp(int(started), tz=timezone.utc).isoformat(),
            "network_reads_authorized": bool(authorize_network_reads), "imported_items": sum(len(rows) for rows in groups.values()),
            "repositories": {name: [row["identity"] for row in rows] for name, rows in groups.items()},
            "checked_repositories": checked, "skipped_repositories": skipped, "answers": answers,
            "findings": findings, "max_repositories": max_repositories,
            "elapsed_seconds": round(clock() - started, 3),
            "limitation": "a bounded first version: one public read per repository, no credential, no withdrawal"}


def write_record(folder, record):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = record["run_at"].replace("-", "").replace(":", "").replace("+0000", "Z")
    path = folder / f"upstream-check-{stamp}.json"
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--host", help="the host file, /data/host.json on the Machine")
    source.add_argument("--items-file", help="a JSON list of served items with identity, source_ref and license")
    parser.add_argument("--authorize-network-reads", action="store_true")
    parser.add_argument("--list-only", action="store_true", help="write the inventory and read nothing")
    parser.add_argument("--max-repositories", type=int, default=DEFAULT_MAX_REPOSITORIES)
    parser.add_argument("--output-folder", default=str(DEFAULT_OUTPUT))
    options = parser.parse_args(argv)
    if not options.authorize_network_reads and not options.list_only:
        parser.error("this check reads the repository host over the network; pass --authorize-network-reads, "
                     "or --list-only to write the inventory without reading anything")
    if options.host:
        from loop_engine.core.service_runtime.catalogue_commands import operator_context
        context, _config, _licence_policy, _family_policy = operator_context(options.host)
        items = imported_items(context)
    else:
        items = json.loads(Path(options.items_file).read_text(encoding="utf-8"))
    record = run(items, authorize_network_reads=options.authorize_network_reads and not options.list_only,
                 max_repositories=options.max_repositories)
    path = write_record(options.output_folder, record)
    print(json.dumps({"imported_items": record["imported_items"], "repositories": len(record["repositories"]),
                      "checked_repositories": len(record["checked_repositories"]), "findings": len(record["findings"]),
                      "record": str(path)}, indent=2))
    return 2 if record["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
