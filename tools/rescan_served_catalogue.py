"""Rescan every served item of the active catalogue release with the current deterministic pre-checks.

Kind: operator tool for the nightly job (roadmap S-6.199). The library is
published after one screening review, so a rule that is tightened later, or a
pattern added to the scanners, must be run again over what is already served.
This command reads the active release and the body store of one host file,
runs the deterministic rules that apply to every served item whatever profile
reviewed it, lists what fails a rule now, and with `--withdraw` records the
durable withdrawal of each failing item version through the same edge an
operator's withdrawal uses. A withdrawal keeps the item's record and its note,
and a new review of new bytes serves the item again.

```text
Rules run over every served item version (current behaviour)
├── licence   the declared licence is on the panel's accepted list
├── safety    the static safety rules of the review panel, over every text file
├── effects   the declared effects are valid, and a shell block declares the process effect
└── secrets   the panel's secret patterns, over every file and the item record
```

The format and duplicate kinds are bound to the review profile of the candidate
(original package or licensed import) and to material the store does not hold,
such as the licence texts a licensed import cites, so they are not run here;
they remain the review's own checks. That is planned work, not a promise of
this version. The duplicate rule is a merge decision, never a withdrawal.

It reads the host file, the service store and the body store, and with
`--withdraw` writes withdrawal records and the catalogue state marker. It calls
no model, opens no network connection and needs no credential. Run it on the
Machine, where the host file and the volume are:

    PYTHONPATH=src:tools python tools/rescan_served_catalogue.py --host /data/host.json
    PYTHONPATH=src:tools python tools/rescan_served_catalogue.py --host /data/host.json --withdraw

The record of each run is written under `artifacts/served-catalogue-rescans/`.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

RECORD_TYPE = "served_catalogue_rescan/v1"
PANEL = ROOT / "tools" / "candidate_review" / "resources" / "panel.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "served-catalogue-rescans"
#: The kinds this rescan decides. A finding of any of them fails the item.
KINDS = ("licence", "safety", "effects", "secrets")
#: The kinds the review runs that this rescan does not, with the reason.
NOT_RESCANNED = {"format": "bound to the review profile of the candidate and to material the store does not hold",
                 "duplicates": "a merge decision between served items, never a withdrawal"}
WITHDRAWAL_NOTE = "Withdrawn by the nightly rescan: fails the current {kinds} rule(s)"


@dataclass(frozen=True)
class Material:
    """What one pre-check engine reads: the bytes, the item record and the identity, as the review shows them."""

    body: bytes
    item: dict
    identity: str
    cited_sources: tuple = ()

    @property
    def body_text_lenient(self):
        return self.body.decode("utf-8", "replace")


@dataclass(frozen=True)
class ServedItem:
    identity: str
    item_version: str
    library_tier: str
    reference: dict
    package: object
    files: tuple = field(repr=False)


@dataclass(frozen=True)
class _Policy:
    accepted_licences: tuple


def panel_settings(path=PANEL):
    """The accepted licences and the secret pattern settings of the review panel, read from its own record."""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    return {"accepted_licences": tuple(value["policy"]["accepted_licences"]),
            "secret_settings": dict(value["precheck_engines"]["builtin_secret_patterns"])}


def build_engines(accepted_licences, secret_settings):
    from candidate_review.prechecks.effects import EffectRules
    from candidate_review.prechecks.safety_rules import StaticSafetyRules
    from candidate_review.prechecks.secrets import SecretPatterns
    policy = _Policy(tuple(accepted_licences))
    return {"safety": StaticSafetyRules({}, policy), "effects": EffectRules({}, policy),
            "secrets": SecretPatterns(secret_settings, policy), "policy": policy}


def served_items(context, *, limit=None):
    """Every item version the active release serves and no withdrawal withholds, with its verified file bytes."""
    from loop_engine.core.service_runtime.catalogue_bundle import item_version_tier
    from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage
    from loop_engine.core.service_runtime.catalogue_releases import (load_release, read_pointer, read_state,
                                                                     withdrawal_keys)
    binding = context.binding
    with binding.store() as store:
        read_state(binding, store)
        _row, pointer = read_pointer(binding, store)
        if pointer is None:
            return "", []
        release = load_release(binding, store, pointer["release_id"])
        withdrawn = withdrawal_keys(binding, store)
    body_store = context.body_store()
    items = []
    for version, payload in release.versions:
        package = CataloguePackage.from_dict(payload["package"])
        identity = payload["reference"]["identity"]
        if (identity, package.served_digest) in withdrawn:
            continue
        files = tuple((entry, body_store.read(entry.digest, entry.size_bytes)) for entry in package.files)
        items.append(ServedItem(identity, version, item_version_tier(payload), dict(payload["reference"]), package, files))
        if limit is not None and len(items) >= limit:
            break
    return release.release_id, items


def rescan_item(item, engines):
    """The findings of the current rules for one served item; empty when it passes every rule this rescan runs."""
    findings = []
    licence = item.reference.get("license")
    if licence not in engines["policy"].accepted_licences:
        findings.append({"kind": "licence", "code": "licence_not_accepted",
                         "detail": f"the declared licence {licence!r} is not on the accepted list"})
    record = {"reference": item.reference}
    joined = b"\n".join(entry.path.encode() + b"\n" + payload for entry, payload in item.files)
    for entry, payload in item.files:
        material = Material(payload, record, item.identity)
        for kind in ("safety", "secrets"):
            result = engines[kind].check(material, None)
            findings.extend({"kind": kind, "code": finding.code, "detail": f"{entry.path}: {finding.detail}"}
                            for finding in result.findings)
    result = engines["effects"].check(Material(joined, record, item.identity), None)
    findings.extend({"kind": "effects", "code": finding.code, "detail": finding.detail} for finding in result.findings)
    return findings


def rescan(items, engines):
    results = []
    for item in items:
        findings = rescan_item(item, engines)
        results.append({"identity": item.identity, "item_version": item.item_version, "library_tier": item.library_tier,
                        "files": len(item.files), "findings": findings, "refused": bool(findings)})
    return results


def withdraw_failures(context, results, *, clock=time.time):
    """Withdraw each item version whose rescan holds a finding. An item without a finding is never touched."""
    from loop_engine.core.service_runtime.catalogue_releases import withdraw
    withdrawn = []
    for row in results:
        if not row["refused"]:
            continue
        if not row["findings"]:
            raise ValueError(f"{row['identity']} is marked refused without a finding; nothing was withdrawn")
        kinds = ", ".join(sorted({finding["kind"] for finding in row["findings"]}))
        outcome = withdraw(context, identity=row["identity"], note_text=WITHDRAWAL_NOTE.format(kinds=kinds)[:400],
                           item_version=row["item_version"], clock=clock)
        withdrawn.append({"identity": row["identity"], "item_version": row["item_version"], "state": outcome["state"],
                          "withdrawn_versions": outcome["withdrawn_versions"]})
    return withdrawn


def run(context, *, panel=PANEL, withdraw_failing=False, limit=None, clock=time.time):
    settings = panel_settings(panel)
    engines = build_engines(settings["accepted_licences"], settings["secret_settings"])
    started = clock()
    release_id, items = served_items(context, limit=limit)
    results = rescan(items, engines)
    withdrawn = withdraw_failures(context, results, clock=clock) if withdraw_failing else []
    failing = [row for row in results if row["refused"]]
    return {"record_type": RECORD_TYPE, "run_at": datetime.fromtimestamp(int(started), tz=timezone.utc).isoformat(),
            "release_id": release_id, "served_items": len(results), "kinds": list(KINDS), "not_rescanned": NOT_RESCANNED,
            "accepted_licences": list(settings["accepted_licences"]), "failing": len(failing),
            "failing_items": failing, "withdraw_requested": bool(withdraw_failing), "withdrawn": withdrawn,
            "elapsed_seconds": round(clock() - started, 3),
            "limitation": "the format and duplicate kinds of the review are not rescanned; see not_rescanned"}


def write_record(folder, record):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = record["run_at"].replace("-", "").replace(":", "").replace("+0000", "Z")
    path = folder / f"rescan-{stamp}.json"
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--host", required=True, help="the host file, /data/host.json on the Machine")
    parser.add_argument("--withdraw", action="store_true", help="withdraw every item version that fails a rule now")
    parser.add_argument("--panel", default=str(PANEL), help="the review panel record that names the accepted licences")
    parser.add_argument("--output-folder", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--limit", type=int, default=None, help="rescan the first N served items only")
    options = parser.parse_args(argv)
    from loop_engine.core.service_runtime.catalogue_commands import operator_context
    context, _config, _licence_policy, _family_policy = operator_context(options.host, needs_bodies=True)
    record = run(context, panel=options.panel, withdraw_failing=options.withdraw, limit=options.limit)
    path = write_record(options.output_folder, record)
    summary = {key: record[key] for key in ("release_id", "served_items", "failing", "withdraw_requested")}
    summary["withdrawn"] = len(record["withdrawn"])
    summary["record"] = str(path)
    print(json.dumps(summary, indent=2))
    return 2 if record["failing"] and not options.withdraw else 0


if __name__ == "__main__":
    raise SystemExit(main())
