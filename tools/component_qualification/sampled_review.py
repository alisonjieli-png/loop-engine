"""Sampled independent model review of generated component batches, through the existing review panel.

```text
Sampled review of one qualification run (hybrid: deterministic sampling, one model family's verdicts)
├── 1. batches: the qualified components of each generator (supply line, version and code revision)
├── 2. plan: sample size and acceptance number from the batch size and the generator's observed defect
│      rate (sampling.plan_for), and a recorded random seed
├── 3. optional calibration: the frozen native controls, one call each; a reviewer that approves a
│      known-wrong control, or leaves one without a verdict, reviews nothing in this run
├── 4. review: the sampled packages in batch calls to one installation of a family that did not write
│      the generators, each call holding planted known-wrong controls made from unsampled members of the
│      same batch; the unchanged review panel, native written criteria and native reviewer instructions
│      judge them, and the panel's ledger records every dispatch, call, usage and verdict
└── 5. decision per batch (sampling.decide): accepted, or withheld with the generator flagged
```

The planted controls are ordinary defects a reader can see: tests that accept anything, an undeclared
local file write, an import the package does not hold, a licence text that contradicts the declared
licence, and a request method or package that contradicts the package's own description. Their expected
decision stays outside the prompt. The panel's pre-check edge is served by the qualification record: a
sampled component reaches the reviewer only when every deterministic check passed for its exact package
digest, and a planted control is named as such by its own engine identity.

Nothing here writes to the import store, the catalogue or the review panel's resources.
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import secrets as secrets_module

from . import sampling
from .components import GeneratedComponent, StoreReader

SAMPLED_REVIEW_RECORD = "generated_batch_sampled_review/v1"
QUALIFICATION_ENGINE = "component_qualification_record"
CONTROL_ENGINE = "planted_reviewer_control"
MAXIMUM_BATCH = 12
CALL_TOKEN_BUDGET = 150_000
PRODUCER_METHOD = "library_supply_generator"

#: The planted control kinds, each named once, with the native criterion its defect violates.
VERIFICATION_ACCEPTS_ANYTHING = "verification_accepts_anything"
UNDECLARED_FILE_WRITE = "undeclared_file_write"
MISSING_DEPENDENCY = "missing_dependency"
LICENCE_CONTRADICTION = "licence_contradiction"
BEHAVIOR_CONTRADICTS_DESCRIPTION = "behavior_contradicts_description"
CONTROL_KINDS = {
    VERIFICATION_ACCEPTS_ANYTHING: ("contracts_and_checks", "code"),
    UNDECLARED_FILE_WRITE: ("declared_effects", "code"),
    MISSING_DEPENDENCY: ("dependency_closure", "code"),
    LICENCE_CONTRADICTION: ("original_rights", "any"),
    BEHAVIOR_CONTRADICTS_DESCRIPTION: ("whole_package", "any"),
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _public_function(text: str) -> "str | None":
    for node in ast.parse(text).body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            return node.name
    return None


def _main_module(component) -> "str | None":
    modules = [entry.path for entry in component.package.files if entry.path.endswith(".py")
               and "/" not in entry.path and not entry.path.startswith("test_")]
    return sorted(modules)[0] if modules else None


def plant(component: GeneratedComponent, kind: str, identity: str) -> "GeneratedComponent | None":
    """One known-wrong control made from a real component; None when this kind does not apply to it."""
    payloads = dict(component.payloads)
    module = _main_module(component)
    if kind == VERIFICATION_ACCEPTS_ANYTHING:
        tests = [path for path in payloads if path.startswith("test_") and path.endswith(".py")]
        if not tests:
            return None
        payloads[tests[0]] = (b"import unittest\n\n\nclass Tests(unittest.TestCase):\n"
                              b"    def test_call_succeeds(self):\n        self.assertTrue(True)\n\n"
                              b"    def test_error_path(self):\n        self.assertTrue(True)\n\n\n"
                              b"if __name__ == \"__main__\":\n    unittest.main()\n")
    elif kind == UNDECLARED_FILE_WRITE:
        if module is None or "writes_fs" in component.candidate.get("declared_effects", []):
            return None
        text = payloads[module].decode()
        name = _public_function(text)
        if name is None:
            return None
        payloads[module] = (text + f"\n\n_undecorated_{name} = {name}\n\n\ndef {name}(*args, **kwargs):\n"
                            f"    result = _undecorated_{name}(*args, **kwargs)\n"
                            "    import json as _json\n"
                            "    with open(\"last_result.json\", \"w\", encoding=\"utf-8\") as stream:\n"
                            "        stream.write(_json.dumps(result, default=str))\n"
                            "    return result\n").encode()
    elif kind == MISSING_DEPENDENCY:
        if module is None:
            return None
        text = payloads[module].decode()
        lines = text.splitlines(keepends=True)
        position = next((index for index, line in enumerate(lines) if line.startswith(("import ", "from "))), 0)
        lines.insert(position, "import acme_request_helpers\n")
        payloads[module] = "".join(lines).encode()
    elif kind == LICENCE_CONTRADICTION:
        texts = (component.candidate.get("licence") or {}).get("texts") or []
        if not texts or texts[0] not in payloads:
            return None
        payloads[texts[0]] = (b"Copyright (c) 2026 Example Holdings. All rights reserved.\n\n"
                              b"No permission is granted to copy, modify, publish or distribute this software or "
                              b"any part of it.\n")
    elif kind == BEHAVIOR_CONTRADICTS_DESCRIPTION:
        if module is not None:
            text = payloads[module].decode()
            for method, other in (('"GET"', '"DELETE"'), ('"POST"', '"DELETE"'), ('"PATCH"', '"DELETE"')):
                if method in text:
                    payloads[module] = text.replace(method, other).encode()
                    break
            else:
                return None
        else:
            config = ".codex/config.toml"
            if config not in payloads:
                return None
            text = payloads[config].decode()
            changed = text.replace('args = ["', 'args = ["unrelated-helper-server@9.9.9", "', 1)
            if changed == text:
                return None
            payloads[config] = changed.encode()
    else:
        raise ValueError(f"unknown control kind {kind}")
    return component.replaced(identity=identity, payloads=payloads)


def _neutral_identity(component: GeneratedComponent, rng: random.Random, package_digest: str) -> str:
    line = component.line
    return f"library.supply.{line}.{rng.getrandbits(96):024x}.{package_digest[:16]}"


def review_request(component: GeneratedComponent, criteria, instructions_sha256: str, producer_family: str):
    """The native package review request for one generated component; its bytes are exactly the package's."""
    from tools.candidate_review.configuration import Producer
    from tools.candidate_review.native import NativePackageReviewRequest, NativeReviewFile
    package = component.package
    record = component.candidate
    provenance = record.get("provenance") or {}
    generator = provenance.get("generator") or {}
    reference = {"identity": component.identity, "kind": component.kind, "purpose": record.get("description", ""),
                 "digest": package.package_digest, "size_bytes": package.served_size,
                 "license": component.licence_expression, "declared_effects": list(record.get("declared_effects", [])),
                 "source_layer": "harness_local", "family": "harness"}
    item = {"reference": reference,
            "component": {"line": component.line, "form": component.form, "authoring": record.get("authoring"),
                          "credentials_by_variable_name": list(record.get("credentials", [])),
                          "placements": record.get("placements", []),
                          "effect_evidence": record.get("effect_evidence", []),
                          "declared_tests": record.get("tests"),
                          "generator": generator,
                          "fact_sources": [{key: fact.get(key) for key in ("role", "url", "sha256", "licence")}
                                           for fact in provenance.get("facts", []) if isinstance(fact, dict)]}}
    files = tuple(NativeReviewFile(entry, component.payloads[entry.path]) for entry in package.files)
    producer = Producer(f"{PRODUCER_METHOD}:{generator.get('identity', '?')}@{generator.get('version', '?')}",
                        producer_family)
    specification = {"id": component.identity, "authoring": record.get("authoring"), "line": component.line,
                     "generator": generator, "record_version": component.record_version}
    return NativePackageReviewRequest(component.identity, f"bodies/{component.identity}.package.json",
                                      package.document(), json.dumps(item, sort_keys=True), (), producer, criteria,
                                      instructions_sha256, package, files, (), json.dumps(specification,
                                                                                          sort_keys=True))


class QualificationPrecheck:
    """The panel's pre-check edge served by the qualification record of the exact package digest."""

    def __init__(self, kind: str, qualified: dict, planted: set) -> None:
        self.kind, self.qualified, self.planted = kind, qualified, planted
        self.engine_id = QUALIFICATION_ENGINE

    def availability(self):
        return True, "", "1"

    def check(self, request, context):
        from tools.candidate_review.prechecks import PrecheckResult, passed, refused
        if request.identity in self.planted:
            return PrecheckResult(self.kind, CONTROL_ENGINE, "1", "passed", ())
        record = self.qualified.get(request.identity)
        if record is None or record["package_digest"] != request.body_sha256:
            return refused(self.kind, self.engine_id, "1", [("not_qualified", "no qualification record for the "
                                                                               "exact package digest")])
        rows = [row for row in record["checks"] if row["kind"] == self.kind]
        failed = [(finding["code"], finding["detail"]) for row in rows if row["status"] == "refused"
                  for finding in row["findings"]]
        if record["outcome"] != "qualified" or failed:
            return refused(self.kind, self.engine_id, "1", failed or [("not_qualified", record["outcome"])])
        return passed(self.kind, self.engine_id, "1")


def _load_qualified(folder: Path) -> dict:
    qualified = {}
    with open(Path(folder) / "qualification.jsonl", encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            if record["outcome"] == "qualified":
                qualified[record["identity"]] = record
    return qualified


def _history(path: "Path | None") -> list:
    if path is None or not Path(path).is_file():
        return []
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def _chunks(requests, estimate, budget: int, maximum: int = MAXIMUM_BATCH) -> list:
    """Consecutive calls of at most ``maximum`` requests whose estimated input stays within the budget."""
    if not 1 <= maximum <= MAXIMUM_BATCH:
        raise ValueError(f"a call holds from 1 to {MAXIMUM_BATCH} sampled components")
    calls, current, size = [], [], 0
    for request in requests:
        tokens = estimate(request)
        if current and (len(current) == maximum or size + tokens > budget):
            calls.append(current)
            current, size = [], 0
        current.append(request)
        size += tokens
    if current:
        calls.append(current)
    return calls


def _panel(root: Path, ledger: Path, authorized: bool, prechecks: dict):
    from tools.candidate_review import configuration as config
    from tools.candidate_review import engines, native_profile
    from tools.candidate_review.ledger import ReviewLedger
    from tools.candidate_review.panel import ReviewPanel
    from tools.candidate_review.reviewers import ReviewerContext
    base = config.PanelConfiguration.from_dict(json.loads(
        (root / "tools/candidate_review/resources/panel.json").read_text(encoding="utf-8")))
    configuration = native_profile.configuration(base)
    criteria, instructions = native_profile.resources()
    resolver = None
    if authorized:
        from tools import operator_credentials
        resolver = operator_credentials.resolve
    context = ReviewerContext(repository=root, credential_resolver=resolver)
    reviewers = {item.installation_id: engines.build_reviewer(item, configuration.policy, context)
                 for item in configuration.installations}
    panel = ReviewPanel(configuration, criteria, instructions, reviewers,
                        prechecks if prechecks is not None else engines.build_precheck_engines(configuration),
                        ReviewLedger(ledger))
    return configuration, criteria, instructions, panel


def _exclusions(configuration, reviewer: str) -> dict:
    return {item.installation_id: "not_the_reviewer_of_this_sampled_review" for item in configuration.installations
            if item.installation_id != reviewer}


def calibrate(root: Path, ledger: Path, reviewer: str, authorized: bool, calls_left: int) -> dict:
    """The frozen native controls, asked one at a time, exactly as the daily job's single-call pass."""
    from tools.candidate_review import calibration as calibration_module
    from tools.candidate_review.native_calibration import DEFAULT_SET, NativeCalibrationSet
    from tools.candidate_review.panel import PanelRunRequest
    configuration, criteria, instructions, panel = _panel(root, ledger, authorized, None)
    controls = NativeCalibrationSet.load(DEFAULT_SET, root, criteria)
    requests = tuple(request for _item, request in controls.requests(None, None, criteria, instructions.sha256))
    group = configuration.installation(reviewer).quota_group
    result = panel.run(PanelRunRequest(
        run_id=f"sampled-calibration-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}", requests=requests,
        population=controls.population({}), call_ceiling=len(requests), token_ceiling=2_000_000,
        model_calls_authorized=authorized, ask_every_eligible_reviewer=True,
        excluded_installations=_exclusions(configuration, reviewer),
        quota_group_call_ceilings={group: min(calls_left, len(requests))}, repeated_failure_limit=2))
    report = calibration_module.evaluate(controls, result)
    row = report["installations"].get(reviewer, {"status": "not_reached"})
    return {"status": row["status"], "false_approvals": row.get("false_approvals"),
            "label_refusals": row.get("false_refusals"), "decisions": row.get("decisions"),
            "calls": len(result.calls), "totals": result.totals(), "set_sha256": report["set_sha256"]}


class DispatchingPrecheck:
    """Native control packages go to the native engines; generated components to their qualification record."""

    def __init__(self, kind: str, native_engines: list, qualified_engine, native_identities: set) -> None:
        self.kind, self.native_engines, self.qualified_engine = kind, native_engines, qualified_engine
        self.native_identities = native_identities
        self.engine_id = "native_or_qualification_record"

    def availability(self):
        return True, "", "1"

    def check(self, request, context):
        if request.identity in self.native_identities:
            results = [engine.check(request, context) for engine in self.native_engines]
            refused = [result for result in results if result.status == "refused"]
            return refused[0] if refused else results[0]
        return self.qualified_engine.check(request, context)


def calibrate_mixed(root: Path, ledger: Path, reviewer: str, authorized: bool, real_requests: list,
                    qualified: dict) -> dict:
    """The frozen native controls in one batch of twelve with real sampled components between them, the way
    the daily job gates its reviewer (controls at positions 1, 4, 7, 9 and 12)."""
    from tools.candidate_review import calibration as calibration_module
    from tools.candidate_review import engines as engine_factory
    from tools.candidate_review.configuration import PRECHECK_KINDS
    from tools.candidate_review.native_calibration import DEFAULT_SET, NativeCalibrationSet
    from tools.candidate_review.panel import PanelRunRequest
    configuration, criteria, instructions, _panel_unused = _panel(root, ledger, authorized, None)
    controls = NativeCalibrationSet.load(DEFAULT_SET, root, criteria)
    control_requests = [request for _item, request in controls.requests(None, None, criteria, instructions.sha256)]
    real = list(real_requests[:MAXIMUM_BATCH - len(control_requests)])
    if len(real) != MAXIMUM_BATCH - len(control_requests):
        return {"status": "not_run", "reason": "too few sampled components for a mixed batch"}
    native = engine_factory.build_precheck_engines(configuration)
    names = {request.identity for request in control_requests}
    prechecks = {kind: [DispatchingPrecheck(kind, list(native.get(kind, ())), QualificationPrecheck(kind, qualified,
                                                                                                    set()), names)]
                 for kind in PRECHECK_KINDS}
    configuration, criteria, instructions, panel = _panel(root, ledger, authorized, prechecks)
    slots = [round(index * (MAXIMUM_BATCH - 1) / (len(control_requests) - 1)) for index in range(len(control_requests))]
    controls_left, reals_left = iter(control_requests), iter(real)
    order = [next(controls_left) if position in slots else next(reals_left) for position in range(MAXIMUM_BATCH)]
    group = configuration.installation(reviewer).quota_group
    result = panel.run(PanelRunRequest(
        run_id=f"sampled-calibration-mixed-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        requests=tuple(order), population=controls.population({}), call_ceiling=1, token_ceiling=2_000_000,
        model_calls_authorized=authorized, ask_every_eligible_reviewer=True,
        excluded_installations=_exclusions(configuration, reviewer), batch_sizes={reviewer: MAXIMUM_BATCH},
        quota_group_call_ceilings={group: 1}, repeated_failure_limit=2))
    control_items = [item for item in result.items if item.identity in names]
    view = type(result)(**{**result.__dict__, "items": control_items})
    report = calibration_module.evaluate(controls, view)
    row = report["installations"].get(reviewer, {"status": "not_reached"})
    real_verdicts = {item.identity: [verdict["decision"] for verdict in item.verdicts] for item in result.items
                     if item.identity not in names}
    return {"status": row["status"], "false_approvals": row.get("false_approvals"),
            "label_refusals": row.get("false_refusals"), "decisions": row.get("decisions"),
            "real_verdicts": real_verdicts, "calls": len(result.calls), "totals": result.totals()}


def command(options, root: Path) -> dict:
    from tools.candidate_review.panel import PanelRunRequest
    from tools.candidate_review.prompt import member_parts
    from tools.candidate_review.configuration import PRECHECK_KINDS
    from loop_engine.core.context_budget import estimate_tokens
    started = _now()
    qualified = _load_qualified(options.qualification)
    batches = {}
    for identity, record in qualified.items():
        if not options.batch or record["batch"] in options.batch:
            batches.setdefault(record["batch"], []).append(identity)
    history_rows = _history(options.history)
    seed = options.seed or secrets_module.token_hex(16)
    rng = random.Random(f"{seed}:controls")
    policy = sampling.SamplingPolicy()
    reader = StoreReader(options.store_root)
    rows = {row["record_id"]: row for row in reader.rows()}
    plans, samples, calls_plan, planted, all_requests = {}, {}, {}, {}, []
    record = {"record_type": SAMPLED_REVIEW_RECORD, "started_at": started, "qualification": str(options.qualification),
              "reviewer": options.reviewer, "producer_family": options.producer_family, "seed": seed,
              "policy": policy.to_dict(), "call_token_budget": CALL_TOKEN_BUDGET, "batches": {}}
    configuration, criteria, instructions, _unused = _panel(root, options.ledger, False, None)
    for batch, identities in sorted(batches.items()):
        history = sampling.GeneratorHistory.from_decisions(batch, history_rows)
        plan = sampling.plan_for(batch, len(identities), history, policy)
        chosen = sampling.draw_sample(identities, plan.sample_size, f"{seed}:{batch}")
        components = {identity: reader.component(rows[identity]) for identity in chosen}
        requests = [review_request(components[identity], criteria, instructions.sha256, options.producer_family)
                    for identity in chosen]
        unsampled = sorted(set(identities) - set(chosen)) or sorted(identities)
        estimate = lambda request: estimate_tokens(member_parts(request))  # noqa: E731
        if not 1 <= options.controls_per_call < MAXIMUM_BATCH:
            raise ValueError("each call holds at least one planted control and at least one sampled component")
        calls = _chunks(requests, estimate, CALL_TOKEN_BUDGET - 20_000 * options.controls_per_call,
                        MAXIMUM_BATCH - options.controls_per_call)
        batch_calls, kinds = [], [kind for kind in CONTROL_KINDS]
        rng.shuffle(kinds)
        for number, call in enumerate(calls):
            members = list(call)
            for extra in range(options.controls_per_call):
                for attempt in range(len(kinds) * 4):
                    kind = kinds[(number * options.controls_per_call + extra + attempt) % len(kinds)]
                    base = reader.component(rows[rng.choice(unsampled)])
                    probe = plant(base, kind, base.identity)
                    if probe is None:
                        continue
                    control = plant(base, kind, _neutral_identity(base, rng, probe.package.package_digest))
                    planted[control.identity] = {"kind": kind, "criterion": CONTROL_KINDS[kind][0], "batch": batch,
                                                 "base_identity": base.identity,
                                                 "package_digest": control.package.package_digest,
                                                 "expected_decision": "reject"}
                    members.insert(rng.randrange(len(members) + 1),
                                   review_request(control, criteria, instructions.sha256, options.producer_family))
                    break
            batch_calls.append(members)
        plans[batch], samples[batch], calls_plan[batch] = plan, chosen, batch_calls
        record["batches"][batch] = {"plan": plan.to_dict(), "sample": chosen, "calls_planned": len(batch_calls),
                                    "members_per_call": [len(members) for members in batch_calls]}
    reader.close()
    total_calls = sum(len(value) for value in calls_plan.values())
    record["calls_planned"] = total_calls
    calibration, used = {}, 0
    if options.calibrate and options.authorize_model_calls:
        calibration["single"] = calibrate(root, options.ledger, options.reviewer, True, options.call_ceiling)
        used += calibration["single"]["calls"]
        # The smallest sampled packages fill the mixed batch, so twelve packages stay well inside one call.
        reals = sorted((request for batch_calls in calls_plan.values() for members in batch_calls
                        for request in members if request.identity not in planted),
                       key=lambda request: (estimate_tokens(member_parts(request)), request.identity))
        calibration["mixed_batch_of_12"] = calibrate_mixed(root, options.ledger, options.reviewer, True, reals,
                                                           qualified)
        used += calibration["mixed_batch_of_12"].get("calls", 0)
    calibrated = bool(calibration) and all(row.get("status") == "qualified" for row in calibration.values())
    record["calibration"] = calibration
    record["admissible"] = calibrated and not options.measurement_only
    record["admissibility_reasons"] = ([] if calibrated else ["reviewer_not_calibrated_today"]) + (
        ["measurement_only: " + options.measurement_only] if options.measurement_only else [])
    if not calibrated and not options.measurement_only:
        record["stopped"] = "reviewer_not_calibrated"
        options.output.write_text(json.dumps(record, indent=1, sort_keys=True, default=str) + "\n")
        return {"stopped": record["stopped"], "calibration": {mode: row.get("status")
                                                              for mode, row in calibration.items()}}
    prechecks = {kind: [QualificationPrecheck(kind, qualified, set(planted))] for kind in PRECHECK_KINDS}
    configuration, criteria, instructions, panel = _panel(root, options.ledger, options.authorize_model_calls,
                                                          prechecks)
    group = configuration.installation(options.reviewer).quota_group
    results = {}
    for batch in sorted(calls_plan):
        requests = tuple(request for members in calls_plan[batch] for request in members)
        size = max(len(members) for members in calls_plan[batch])
        ceiling = max(0, min(options.call_ceiling - used, len(calls_plan[batch]) + 3))
        result = panel.run(PanelRunRequest(
            run_id=f"sampled-review-{batch.replace('/', '-').replace('@', '-')}-"
                   f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            requests=requests, population={}, call_ceiling=ceiling,
            token_ceiling=options.token_ceiling or 20_000_000, model_calls_authorized=options.authorize_model_calls,
            batch_sizes={options.reviewer: size} if size > 1 else {},
            excluded_installations=_exclusions(configuration, options.reviewer),
            quota_group_call_ceilings={group: ceiling}, repeated_failure_limit=3,
            collect_below_quorum_reason="Sampled review of generated components: one calibrated family that did "
                                        "not write the generators answers for a random sample of each batch."))
        used += len(result.calls)
        results[batch] = result
    decisions = []
    for batch, result in sorted(results.items()):
        verdicts = {}
        for item in result.items:
            chosen = [verdict for verdict in item.verdicts if verdict.get("reviewer_id") == options.reviewer]
            verdicts[item.identity] = chosen[0] if chosen else None
        sample_rows, control_rows = [], []
        for identity in samples[batch]:
            verdict = verdicts.get(identity)
            sample_rows.append({"identity": identity, "decision": verdict["decision"] if verdict else None,
                                "criteria": _criteria(verdict), "reason": _reason(verdict),
                                "call_ref": _call_ref(verdict),
                                "body_sha256": verdict["body_sha256"] if verdict else None})
        for identity, control in planted.items():
            if control["batch"] == batch:
                verdict = verdicts.get(identity)
                control_rows.append({**control, "identity": identity,
                                     "decision": verdict["decision"] if verdict else None,
                                     "criteria": _criteria(verdict), "reason": _reason(verdict),
                                     "call_ref": _call_ref(verdict)})
        decided = [row for row in sample_rows if row["decision"] in ("approve", "reject")]
        defective = sum(1 for row in decided if row["decision"] == "reject")
        decision = sampling.decide(plans[batch], defective=defective, decided=len(decided),
                                   controls_planted=len(control_rows),
                                   controls_approved=sum(1 for row in control_rows if row["decision"] == "approve"))
        decision.update({"decided_at": _now(), "run_id": result.run_id, "stop_reason": result.stop_reason,
                         "controls_rejected": sum(1 for row in control_rows if row["decision"] == "reject"),
                         "controls_without_verdict": sum(1 for row in control_rows if row["decision"] is None)})
        if not record["admissible"]:
            # The rule's arithmetic is kept as a measurement; the decision itself admits nothing.
            decision["measured_outcome"] = decision["outcome"]
            decision["outcome"] = sampling.WITHHELD
            decision["reasons"] = list(decision["reasons"]) + list(record["admissibility_reasons"])
            decision["sample_complete"] = False
        decisions.append(decision)
        record["batches"][batch].update({"verdicts": sample_rows, "controls": control_rows, "decision": decision,
                                         "totals": result.totals()})
    record.update({"finished_at": _now(), "decisions": decisions, "calls_used": used,
                   "ledger": str(options.ledger)})
    options.output.write_text(json.dumps(record, indent=1, sort_keys=True, default=str) + "\n")
    if options.history and options.authorize_model_calls and record["admissible"]:
        with open(options.history, "a", encoding="utf-8") as stream:
            for decision in decisions:
                stream.write(json.dumps(decision, sort_keys=True) + "\n")
    return {"calls_planned": total_calls, "calls_used": used,
            "decisions": {row["batch"]: {key: row[key] for key in ("outcome", "reasons", "sampled", "defective",
                                                                   "controls_planted", "controls_approved")}
                          for row in decisions}}


def _criteria(verdict) -> list:
    if not verdict:
        return []
    return sorted({finding.get("criterion_id") for finding in verdict.get("findings", []) if isinstance(finding, dict)
                   and finding.get("criterion_id")})


def _reason(verdict) -> str:
    if not verdict:
        return ""
    reasons = verdict.get("reasons")
    return (" ".join(str(item) for item in reasons) if isinstance(reasons, list) else str(reasons or ""))[:400]


def _call_ref(verdict) -> str:
    return f"{verdict['run_id']}#{verdict['sequence']}" if verdict else ""


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
