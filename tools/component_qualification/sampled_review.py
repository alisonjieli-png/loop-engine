"""Sampled independent model review of generated component batches, through the existing review panel.

```text
Sampled review of one qualification run (hybrid: deterministic sampling, one model family's verdicts)
├── 0. decision ledger (decisions.py), opened first: a run that may call a model refuses without it, and
│      a batch whose exact frame it already decided, or that holds a component of a withheld frame, is
│      refused before any component is read
├── 1. batches: the qualified components of each generator (supply line, version and code revision)
├── 2. plan: sample size and acceptance number from the batch size and the generator's observed defect
│      rate as the decision ledger records it (sampling.plan_for), and a recorded random seed; calls are
│      filled within the reviewer's context window, a large data file is shown as a bounded excerpt
│      (excerpts.py), and a run refuses before any model call when a planned call does not fit the window
│      or the call allowance, holds fewer planted controls than asked, or its call ceiling does not cover
│      the calibration and every planned call
├── 3. optional calibration: the frozen native controls, one call each; a reviewer that approves a
│      known-wrong control, or leaves one without a verdict, reviews nothing in this run
├── 4. review: the sampled packages in batch calls to one installation of a family that did not write
│      the generators, each call holding planted known-wrong controls made from unsampled members of the
│      same batch; the unchanged review panel, native written criteria and native reviewer instructions
│      judge them, and the panel's ledger records every dispatch, call, usage and verdict
└── 5. decision per batch (sampling.decide): accepted, or withheld with the generator flagged; an
       admissible run appends each decision on which the reviewer gave a valid verdict to the decision
       ledger, in one synced write, before it writes its own record
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

from . import decisions, sampling
from .components import GeneratedComponent, StoreReader

SAMPLED_REVIEW_RECORD = sampling.REVIEW_RECORD
QUALIFICATION_ENGINE = "component_qualification_record"
CONTROL_ENGINE = "planted_reviewer_control"
MAXIMUM_BATCH = 12
CALL_TOKEN_BUDGET = 150_000
#: Provider-reported input tokens per estimated token (UTF-8 bytes over four). The largest ratio observed is 1.31:
#: on September 30, 2026 Kimi K2.6 read a program-install call estimated at 96,751 tokens as 126,997. A call is
#: planned so that its estimate times this ratio stays within its reviewer's declared context window less the
#: output allocation.
TOKEN_ESTIMATE_RATIO = 1.35
#: The estimated input tokens kept in each call for one planted control while its members are packed. A control is
#: planted only where it fits the call's leftover room; a larger one is not planted, and another unsampled member is
#: tried in its place.
CONTROL_RESERVE_TOKENS = 20_000
#: The batch prompt's own words around its members: the opening line, each member's fence and order line (about 64
#: tokens each), and the closing answer request, generously bounded per member. The exact prompt is built and
#: checked before any call.
BATCH_WORDS_TOKENS = 200
MEMBER_WORDS_TOKENS = 100
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


def review_request(component: GeneratedComponent, criteria, instructions_sha256: str, producer_family: str,
                   data_folders=None):
    """The native package review request for one generated component; its bytes are exactly the package's.

    A large data file is shown to the reviewer as an excerpt (excerpts.py, rule data_file_excerpt/v1); the request
    still carries its complete bytes, so the package binding and every digest are unchanged."""
    from tools.candidate_review.configuration import Producer
    from tools.candidate_review.native import NativePackageReviewRequest, NativeReviewFile
    from .excerpts import excerpt_for
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
    files = tuple(NativeReviewFile(entry, component.payloads[entry.path],
                                   excerpt_for(entry, component.payloads[entry.path], data_folders))
                  for entry in package.files)
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


def _load_qualified(folder: Path, digest=None) -> dict:
    """The qualified records of one run by identity; ``digest`` (a hashlib object) reads the file's exact bytes."""
    qualified = {}
    with open(Path(folder) / "qualification.jsonl", "rb") as stream:
        for line in stream:
            if digest is not None:
                digest.update(line)
            record = json.loads(line)
            if record["outcome"] == "qualified":
                qualified[record["identity"]] = record
    return qualified


def _calibration_calls(root: Path, criteria, instructions) -> int:
    """The calls both calibrations may make: one per frozen native control, then one mixed batch of twelve."""
    from tools.candidate_review.native_calibration import DEFAULT_SET, NativeCalibrationSet
    controls = NativeCalibrationSet.load(DEFAULT_SET, root, criteria)
    return len(tuple(controls.requests(None, None, criteria, instructions.sha256))) + 1


def _call_limits(configuration, installation, instructions) -> tuple:
    """(input tokens a call's sampled members and planted controls may fill, the reviewer's context window, its
    answer allowance).

    The model gateway refuses a call before it reaches the provider when the call's estimated input plus its answer
    allowance exceeds the reviewer's declared context window. A fixed budget above that window (150,000 tokens
    against 131,072 for ollama.kimi-k2.6) let the September 30, 2026 data table calls be planned and then refused
    unanswered. The room is the call allowance (call_allowance: the window less the answer allowance, over the
    observed ratio of provider-reported to estimated tokens, so a call fits the provider's own count as well) less
    the batch instructions and the batch prompt's own words; members leave the room kept for each planted control.
    A reviewer that declares no window keeps the fixed budget; window and allowance are then None."""
    from tools.candidate_review.prompt import batch_system
    from loop_engine.core.context_budget import estimate_tokens
    settings = dict(installation.settings)
    window = settings.get("maximum_context_tokens")
    room = (call_allowance(configuration, installation) - estimate_tokens(batch_system(installation, instructions))
            - BATCH_WORDS_TOKENS - MEMBER_WORDS_TOKENS * MAXIMUM_BATCH)
    if type(window) is not int or window <= 0:
        return room, None, None
    allowance = settings.get("output_allocation_tokens") or configuration.policy.output_allocation_tokens
    return room, window, allowance


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


def call_allowance(configuration, installation) -> int:
    """The estimated input tokens, system part included, that one call to this reviewer may hold.

    Until October 5, 2026 every call was planned against a fixed 150,000 tokens, more than the 131,072 every
    gateway reviewer declares. The gateway refuses a call whose estimate does not fit before it reaches the
    provider, so the members of that call get no verdict, and a sample left incomplete withholds its whole
    batch for good. The allowance is the declared context window less the reviewer's output allocation, divided
    by the observed ratio of reported to estimated tokens. A reviewer that declares no window keeps the fixed
    budget."""
    settings = dict(installation.settings)
    context = settings.get("maximum_context_tokens")
    output = settings.get("output_allocation_tokens") or configuration.policy.output_allocation_tokens
    if type(context) is not int or type(output) is not int or context <= output:
        return CALL_TOKEN_BUDGET
    return min(CALL_TOKEN_BUDGET, int((context - output) / TOKEN_ESTIMATE_RATIO))


def calls_that_do_not_fit(calls_plan: dict, planted: dict, installation, instructions, allowance: int,
                          controls_per_call: int) -> list:
    """Each planned call whose exact batch prompt is over the allowance or holds too few planted controls."""
    from tools.candidate_review.prompt import build_batch_prompt, member_parts
    from loop_engine.core.context_budget import estimate_tokens
    problems = []
    for batch, batch_calls in sorted(calls_plan.items()):
        for number, members in enumerate(batch_calls, 1):
            controls = sum(1 for request in members if request.identity in planted)
            tokens = build_batch_prompt(members, installation, instructions).estimated_input_tokens
            if tokens > allowance or controls < controls_per_call:
                sizes = sorted((estimate_tokens(member_parts(request)), request.identity) for request in members
                               if request.identity not in planted)
                problems.append({"batch": batch, "call": number, "estimated_tokens": tokens,
                                 "allowance": allowance, "planted_controls": controls, "members": len(members),
                                 "largest_member": sizes[-1][1] if sizes else "",
                                 "largest_member_tokens": sizes[-1][0] if sizes else 0})
    return problems


def _listed_model_versions() -> dict:
    """The provider's served models, for the reviewers' availability probe. Read here so the
    sampled review, the daily catalogue review and the tests share one import of the gateway."""
    from tools.candidate_review.reviewers.gateway import listed_model_versions
    return listed_model_versions()


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
    resolver, listing = None, None
    if authorized:
        from tools import operator_credentials
        resolver = operator_credentials.resolve
        # A gateway reviewer declares itself unavailable when the provider's model listing does
        # not name its model. Reading the listing is a listing, not a model call, and the key
        # stays in the environment. Without it every Ollama Cloud reviewer is ineligible for a
        # reason that has nothing to do with the components, and the run reports a calibration
        # that was never attempted.
        read = _listed_model_versions()
        listing = read["models"] if read.get("ok") else None
    context = ReviewerContext(model_listing=listing, repository=root, credential_resolver=resolver)
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
    """One sampled review run. The decision ledger is opened before anything else is read: a run that may call a
    model refuses without a ledger that reads exactly, and holds the ledger's lock until its decisions are
    appended, so two runs never sample one frame at once."""
    ledger = decisions.open_for_review(options.decisions, options.authorize_model_calls)
    try:
        return _review(options, root, ledger)
    finally:
        if ledger is not None:
            ledger.close()


def _review(options, root: Path, ledger) -> dict:
    from tools.candidate_review.panel import PanelRunRequest
    from tools.candidate_review.prompt import build_batch_prompt, member_parts
    from . import excerpts
    from tools.candidate_review.configuration import PRECHECK_KINDS
    from loop_engine.core.context_budget import estimate_tokens
    started = _now()
    qualification_digest = hashlib.sha256()
    qualified = _load_qualified(options.qualification, qualification_digest)
    batches = {}
    for identity, record in qualified.items():
        if not options.batch or record["batch"] in options.batch:
            batches.setdefault(record["batch"], []).append(identity)
    if options.authorize_model_calls and any(
            qualified[identity].get("qualifier", {}).get("uncommitted_changes", True)
            for identities in batches.values() for identity in identities):
        raise ValueError("requalify selected batches with committed code before spending model calls; "
                         "admission cannot use an uncommitted qualifier")
    frames = {batch: [qualified[identity] for identity in identities] for batch, identities in batches.items()}
    if ledger is not None:
        refused = ledger.refusals(frames)
        if refused:
            undecided = sorted(set(batches) - set(refused))
            raise decisions.DecisionLedgerError(
                "batch_already_decided",
                "the decision ledger settled " + "; ".join(f"{batch}: {', '.join(reasons)}"
                                                           for batch, reasons in sorted(refused.items()))
                + ". A decided frame is never sampled again; it proceeds through a full review of every component "
                  "or after its generator changes so the frame differs. "
                + (f"Undecided batches to name with --batch: {', '.join(undecided)}." if undecided
                   else "No selected batch is undecided."))
    history_rows = ledger.history_rows() if ledger is not None else []
    seed = options.seed or secrets_module.token_hex(16)
    rng = random.Random(f"{seed}:controls")
    policy = sampling.SamplingPolicy()
    # Each component is read by its key when it is used; reading every supply candidate first held 7.25 GB.
    reader = StoreReader(options.store_root)
    plans, samples, calls_plan, planted, all_requests = {}, {}, {}, {}, []
    configuration, criteria, instructions, _unused = _panel(root, options.ledger, False, None)
    installation = configuration.installation(options.reviewer)
    allowance = call_allowance(configuration, installation)
    record = {"record_type": SAMPLED_REVIEW_RECORD, "started_at": started, "qualification": str(options.qualification),
              "reviewer": options.reviewer, "producer_family": options.producer_family, "seed": seed,
              "policy": policy.to_dict(), "call_token_budget": CALL_TOKEN_BUDGET, "call_allowance": allowance,
              "token_estimate_ratio": TOKEN_ESTIMATE_RATIO, "batches": {},
              "decision_ledger": None if ledger is None else {
                  "path": str(ledger.path), "sha256_at_start": ledger.sha256, "entries_at_start": len(ledger.entries)}}
    room, window, answer = _call_limits(configuration, installation, instructions)
    data_folders = excerpts.policy_data_folders()
    record["call_limits"] = {"members_input_tokens": room, "context_window_tokens": window,
                             "answer_allowance_tokens": answer, "control_reserve_tokens": CONTROL_RESERVE_TOKENS,
                             "excerpt_rule": excerpts.RULE, "excerpt_threshold_bytes": excerpts.THRESHOLD_BYTES}
    for batch, identities in sorted(batches.items()):
        # The observed rate belongs to the generator (line and version), so a batch written again at a later
        # code revision by an unchanged generator plans from the defects its earlier batches showed.
        history = sampling.GeneratorHistory.from_decisions(sampling.generator_of(batch), history_rows)
        plan = sampling.plan_for(batch, len(identities), history, policy)
        chosen = sampling.draw_sample(identities, plan.sample_size, f"{seed}:{batch}")
        components = {identity: reader.component(reader.row(identity)) for identity in chosen}
        requests = [review_request(components[identity], criteria, instructions.sha256, options.producer_family,
                                   data_folders) for identity in chosen]
        unsampled = sorted(set(identities) - set(chosen)) or sorted(identities)
        estimate = lambda request: estimate_tokens(member_parts(request))  # noqa: E731
        if not 1 <= options.controls_per_call < MAXIMUM_BATCH:
            raise ValueError("each call holds at least one planted control and at least one sampled component")
        # Members fill a call up to the reviewer's allowance less the room its planted controls take.
        calls = _chunks(requests, estimate, max(1, room - CONTROL_RESERVE_TOKENS * options.controls_per_call),
                        MAXIMUM_BATCH - options.controls_per_call)
        batch_calls, kinds = [], [kind for kind in CONTROL_KINDS]
        rng.shuffle(kinds)
        for number, call in enumerate(calls):
            members = list(call)
            left = room - sum(estimate(request) for request in call)
            for extra in range(options.controls_per_call):
                for attempt in range(len(kinds) * 4):
                    kind = kinds[(number * options.controls_per_call + extra + attempt) % len(kinds)]
                    base = reader.component(reader.row(rng.choice(unsampled)))
                    probe = plant(base, kind, base.identity)
                    if probe is None:
                        continue
                    control = plant(base, kind, _neutral_identity(base, rng, probe.package.package_digest))
                    control_request = review_request(control, criteria, instructions.sha256,
                                                     options.producer_family, data_folders)
                    if estimate(control_request) > left:
                        continue  # a control that would push the call over its reviewer's allowance; try another
                    left -= estimate(control_request)
                    planted[control.identity] = {"kind": kind, "criterion": CONTROL_KINDS[kind][0], "batch": batch,
                                                 "base_identity": base.identity,
                                                 "package_digest": control.package.package_digest,
                                                 "expected_decision": "reject"}
                    members.insert(rng.randrange(len(members) + 1), control_request)
                    break
            batch_calls.append(members)
        plans[batch], samples[batch], calls_plan[batch] = plan, chosen, batch_calls
        record["batches"][batch] = {"plan": plan.to_dict(), "sample": chosen,
                                    "frame_sha256": sampling.frame_digest(frames[batch]),
                                    "calls_planned": len(batch_calls),
                                    "members_per_call": [len(members) for members in batch_calls],
                                    # Each planned call's input exactly as the panel will build and the gateway
                                    # will estimate it.
                                    "call_input_tokens": [build_batch_prompt(members, installation,
                                                                             instructions).estimated_input_tokens
                                                          for members in batch_calls]}
    reader.close()
    total_calls = sum(len(value) for value in calls_plan.values())
    record["calls_planned"] = total_calls
    over = []
    if window is not None:
        over = [f"{batch} call {number}: {tokens:,} input tokens" for batch, entry in sorted(record["batches"].items())
                for number, tokens in enumerate(entry["call_input_tokens"], 1) if tokens + answer > window]
        record["calls_over_context_window"] = over
    # A call over its reviewer's window is refused unsent, and one over the allowance may be read past the window by
    # the provider's own count; either leaves its sampled components without a verdict, which withholds the batch. A
    # call without its planted control cannot show a reviewer that approves everything. A run that may call a model
    # therefore refuses before its first call instead.
    unfit = calls_that_do_not_fit(calls_plan, planted, installation, instructions, allowance,
                                  options.controls_per_call)
    record["calls_that_do_not_fit"] = unfit
    if (over or unfit) and options.authorize_model_calls:
        reasons = [f"planned calls that do not fit {options.reviewer}'s context window of {window:,} tokens with its "
                   f"{answer:,}-token answer allowance, which the gateway would refuse unanswered: " + "; ".join(over)
                   ] if over else []
        if unfit:
            reasons.append(
                f"{len(unfit)} planned call(s) do not fit {options.reviewer}'s allowance of {allowance} estimated "
                "tokens with a planted control: " + "; ".join(
                    f"{row['batch']} call {row['call']} ({row['estimated_tokens']} tokens, {row['planted_controls']} "
                    f"control(s), largest member {row['largest_member']} at {row['largest_member_tokens']} tokens)"
                    for row in unfit))
        raise ValueError(". ".join(reasons)
                         + ". Name the other batches with --batch and keep the same --seed, so their samples do not "
                           "change.")
    if options.authorize_model_calls and options.calibrate and not options.measurement_only:
        # Every decision of this run settles its frame in the decision ledger, so a batch the ceiling could not
        # finish would be withheld for want of calls and never sampled again. Refuse before the first call instead.
        needed = _calibration_calls(root, criteria, instructions) + total_calls
        if options.call_ceiling < needed:
            raise ValueError(f"the call ceiling ({options.call_ceiling}) is below the {needed} calls this run plans "
                             f"({needed - total_calls} calibration, then "
                             + ", ".join(f"{batch}: {len(value)}" for batch, value in sorted(calls_plan.items()))
                             + "); raise --call-ceiling or name fewer batches with --batch")
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
    results, order = {}, sorted(calls_plan)
    for position, batch in enumerate(order):
        requests = tuple(request for members in calls_plan[batch] for request in members)
        size = max(len(members) for members in calls_plan[batch])
        # The planned calls of the later batches stay reserved, so retries here never leave a later batch
        # short of the calls its plan needs.
        reserved = sum(len(calls_plan[later]) for later in order[position + 1:])
        ceiling = max(0, min(options.call_ceiling - used - reserved, len(calls_plan[batch]) + 3))
        result = panel.run(PanelRunRequest(
            run_id=f"sampled-review-{batch.replace('/', '-').replace('@', '-')}-"
                   f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            requests=requests, population={}, call_ceiling=ceiling,
            token_ceiling=options.token_ceiling or 20_000_000, model_calls_authorized=options.authorize_model_calls,
            batch_sizes={options.reviewer: size} if size > 1 else {},
            batch_groups={options.reviewer: tuple(tuple(request.identity for request in members)
                                                 for members in calls_plan[batch])} if size > 1 else {},
            excluded_installations=_exclusions(configuration, options.reviewer),
            quota_group_call_ceilings={group: ceiling}, repeated_failure_limit=3,
            collect_below_quorum_reason="Sampled review of generated components: one calibrated family that did "
                                        "not write the generators answers for a random sample of each batch."))
        used += len(result.calls)
        results[batch] = result
    batch_decisions = []
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
                         "controls_without_verdict": sum(1 for row in control_rows if row["decision"] is None),
                         # Each sampled component the reviewer rejected, exactly: the decision ledger keeps them, so
                         # a published one is withdrawn and none is admitted again (October 5, 2026).
                         "rejected_members": sorted([row["identity"], qualified[row["identity"]]["record_version"],
                                                     qualified[row["identity"]]["package_digest"]]
                                                    for row in decided if row["decision"] == "reject")})
        if not record["admissible"]:
            # The rule's arithmetic is kept as a measurement; the decision itself admits nothing.
            decision["measured_outcome"] = decision["outcome"]
            decision["outcome"] = sampling.WITHHELD
            decision["reasons"] = list(decision["reasons"]) + list(record["admissibility_reasons"])
            decision["sample_complete"] = False
        batch_decisions.append(decision)
        record["batches"][batch].update({"verdicts": sample_rows, "controls": control_rows, "decision": decision,
                                         "totals": result.totals()})
    record.update({"finished_at": _now(), "decisions": batch_decisions, "calls_used": used,
                   "ledger": str(options.ledger)})
    if options.authorize_model_calls and record["admissible"]:
        # The ledger first: a run that stopped between the two leaves a decided frame without a review record,
        # which admits nothing, never a review record whose frame the ledger would let a later run sample again.
        try:
            record["decision_ledger"].update(_record_decisions(
                ledger, record, options.output, frames, samples, results, calibration,
                qualification_digest.hexdigest()))
        except (decisions.DecisionLedgerError, OSError) as error:
            record["admissible"] = False
            record["admissibility_reasons"] = list(record["admissibility_reasons"]) + [
                f"decision_ledger_not_appended: {error}"]
            options.output.write_text(json.dumps(record, indent=1, sort_keys=True, default=str) + "\n")
            raise
    options.output.write_text(json.dumps(record, indent=1, sort_keys=True, default=str) + "\n")
    return {"calls_planned": total_calls, "calls_used": used, "decision_ledger": record["decision_ledger"],
            "decisions": {row["batch"]: {key: row[key] for key in ("outcome", "reasons", "sampled", "defective",
                                                                   "controls_planted", "controls_approved")}
                          for row in batch_decisions}}


def _record_decisions(ledger, record: dict, review_path: Path, frames: dict, samples: dict, results: dict,
                      calibration: dict, qualification_sha256: str) -> dict:
    """Append, in one synced write, each decision of an admissible run on which the reviewer gave at least one valid
    verdict on a sampled component (decisions.answered).

    A batch whose sampled components all lack a valid verdict, because its calls were never made, failed or were
    refused by the gateway before they reached the model, has a withheld outcome that says nothing about its
    components: it is reported under ``unanswered`` and stays undecided. Every other decision is complete whatever
    its outcome and whatever withheld it, and settles its frame."""
    real_verdicts = (calibration.get("mixed_batch_of_12") or {}).get("real_verdicts") or {}
    entries, unanswered, recorded_at = [], [], _now()
    for decision in record["decisions"]:
        batch = decision["batch"]
        if not decisions.answered(decision, samples[batch], real_verdicts):
            unanswered.append({"batch": batch, "calls": len(results[batch].calls),
                               "panel_stop_reason": results[batch].stop_reason})
            continue
        entries.append(decisions.entry_for(record, batch, frames[batch], kind=decisions.RUN_SOURCE,
                                           review_path=review_path, review_sha256=None,
                                           qualification_sha256=qualification_sha256, recorded_at=recorded_at))
    appended = ledger.append(entries)
    return {"appended_sequences": appended["sequences"], "sha256_after": appended["sha256"],
            "entries_after": appended["entries"], "unanswered": unanswered}


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
