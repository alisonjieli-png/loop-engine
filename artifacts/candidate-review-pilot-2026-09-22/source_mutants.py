"""Source mutants for the independent review panel: remove one guard, and a named check must fail.

The checks in ``tools/test_candidate_review_*.py`` hold their own mutant
controls, which replace a guard while the check runs. This script goes one
step further and edits the source itself. For each mutant it copies the
repository's ``tools`` folder into a scratch folder, replaces one exact piece of
source text, runs the review panel checks there, and records whether they
failed and which checks failed. A mutant that leaves every check passing is a
guard no check holds, and the script reports it as a survivor.

The repository is never edited. ``src``, ``examples`` and every other
top-level folder that a catalogue item cites are linked into the scratch folder
by hard links, and nothing writes to them. When the unmutated copy does not
pass every check, no mutant is run, because a mutant is only measured against
a passing baseline. No model is called and no network is reached:

    PYTHONPATH=src:tools python \\
        artifacts/candidate-review-pilot-2026-09-22/source_mutants.py \\
        --scratch SCRATCH_FOLDER \\
        --write artifacts/candidate-review-pilot-2026-09-22/source-mutants-1.json
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
RECORD_TYPE = "candidate_review_source_mutants/v1"
PACKAGE = "tools/candidate_review"
CHECKS = ("test_candidate_review_configuration", "test_candidate_review_prechecks", "test_candidate_review_engines",
          "test_candidate_review_panel", "test_candidate_review_calibration", "test_candidate_review_record")
RUN_SECONDS = 900
SPECIFICATIONS = "examples/29_intelligence_service/starter-catalogue/specifications-[0-9][0-9][0-9].json"
#: Each mutant: an identity, the file under the package, the exact text replaced, its replacement, and the guard.
MUTANTS = (
    ("any_rejection_ignored", "panel.py",
     "    if rejections:\n        return REJECTED, REJECTION_RULE",
     "    if False:\n        return REJECTED, REJECTION_RULE",
     "one written rejection keeps the item a candidate"),
    ("families_counted_as_reviewers", "panel.py",
     "    return len({family_of[member] for member in members})",
     "    return len(list(members))",
     "approval needs distinct model families, not only distinct reviewers"),
    ("producer_family_asked", "panel.py",
     "    return installation.family == producer.family",
     "    return False",
     "the producer's family is never asked"),
    ("producer_family_counted", "panel.py",
     "    return family != producer_family",
     "    return True",
     "an approval from the producer's family never counts"),
    ("prompt_left_out_of_the_review_key", "panel.py",
     ',\n                   "prompt_sha256": prompt.sha256})',
     "})",
     "a verdict is reused only for the exact prompt it answered"),
    ("ceiling_ignored", "panel.py",
     "            if self.calls + 1 > self.call_ceiling:",
     "            if False:",
     "the declared call ceiling stops the run before the next call"),
    ("pause_unbounded", "panel.py",
     "            pause = min(float(wanted), rate.maximum_seconds, rate.maximum_total_seconds - state.pause_total)",
     "            pause = float(wanted)",
     "a rate limit pause stays inside the declared bounds"),
    ("lasting_failure_repeated", "panel.py",
     "            if attempt.outcome in LASTING_FAILURES:",
     "            if False:",
     "a refused login is not asked again in the same run"),
    ("secret_written_to_the_ledger", "panel.py",
     "            for pattern in self.patterns:\n                value = pattern.sub(REDACTED, value)",
     "            pass",
     "no secret-shaped value is written to the ledger"),
    ("answer_about_other_bytes_counted", "verdicts.py",
     "BIND_TO_BODY_DIGEST = True",
     "BIND_TO_BODY_DIGEST = False",
     "a verdict is bound to the digest of the exact bytes"),
    ("unknown_criterion_counted", "verdicts.py",
     '        if row["criterion_id"] not in criteria_ids:',
     "        if False:",
     "a finding cites only the criteria the request lists"),
    ("stored_verdict_ignored", "ledger.py",
     "        return self._verdicts.get(review_key)",
     "        return None",
     "a stopped run never reviews the same bytes twice"),
    ("interrupted_call_repeated", "ledger.py",
     '        return any((row["run_id"], row["sequence"]) not in self._completed',
     '        return False and any((row["run_id"], row["sequence"]) not in self._completed',
     "a dispatched call that never completed is not repeated"),
    ("every_criterion_for_every_kind", "configuration.py",
     "    return not criterion.applies_to_groundings or grounding in criterion.applies_to_groundings",
     "    return True",
     "each kind of body receives only its own grounding criterion"),
    ("quorum_floor_lowered", "configuration.py",
     "QUORUM_FLOOR = 3",
     "QUORUM_FLOOR = 1",
     "a policy below three approvals from three families is refused"),
    ("unquoted_criterion_accepted", "configuration.py",
     "    if canonical_whitespace(quote) not in sheet:",
     "    if False:",
     "every criterion is a quote of the review sheet"),
    ("kind_without_engine_skipped", "prechecks/__init__.py",
     "KIND_REQUIRES_A_COMPLETED_ENGINE = True",
     "KIND_REQUIRES_A_COMPLETED_ENGINE = False",
     "a pre-check kind is never skipped"),
    ("licence_list_ignored", "prechecks/licence.py",
     "        if licence not in self.accepted:",
     "        if False:",
     "a licence outside the accepted list is refused"),
    ("secrets_only_in_the_body", "prechecks/secrets.py",
     '        places += [(f"cited source {source.path}", source.text) for source in request.cited_sources]',
     "        places = places[:2]",
     "nothing sent to a reviewer holds a secret-shaped value"),
    ("vocabulary_unchecked", "prechecks/format_rules.py",
     "        findings += self._vocabulary(request, text)",
     "        findings += []",
     "internal vocabulary is refused"),
    ("safety_rules_emptied", "prechecks/safety_rules.py",
     "            for code, pattern in RULES:",
     "            for code, pattern in ():",
     "instruction overrides, shell pipes and credential reads are refused"),
    ("near_duplicates_accepted", "prechecks/duplicates.py",
     "            if similarity >= self.threshold:",
     "            if similarity > 2:",
     "a near duplicate is refused"),
    ("false_approval_trusted", "calibration.py",
     "        status = FAILED_CALIBRATION if false_approvals else",
     "        status = FAILED_CALIBRATION if False else",
     "a reviewer that approves a known-wrong item is not trusted"),
    ("calibration_criterion_unchecked", "calibration.py",
     "            if item.criterion_id not in request.applicable_criteria_ids:",
     "            if False:",
     "a calibration item names a criterion of its own kind"),
    ("record_quorum_unchecked", "review_record.py",
     "        if not approval_rule_holds(approvers, family_of, policy):",
     "        if False:",
     "the record reader refuses an approval below the quorum"),
    ("record_producer_family_unchecked", "review_record.py",
     '        if family_of[decision["reviewer_id"]] == producer_family:',
     "        if False:",
     "the record reader refuses a decision by the producer's family"),
    ("record_criteria_unchecked", "review_record.py",
     '        if any(type(finding) is not dict or finding.get("criterion_id") not in applied',
     '        if False and any(type(finding) is not dict or finding.get("criterion_id") not in applied',
     "the record reader refuses a finding under a criterion of the other kind"),
    ("record_interruption_unchecked", "review_record.py",
     "        if f\"{row['run_id']}#{row['sequence']}\" in calls:",
     "        if False:",
     "an interruption with a completed call is refused"),
    ("record_bytes_unbound", "review_record.py",
     '        if decision["body_sha256"] != row["body_sha256"]:',
     "        if False:",
     "every decision in the record names the row's exact bytes"),
    ("credential_presence_unchecked", "reviewers/gateway.py",
     '        if missing:\n            return Availability(False, missing, "", {}, AUTHENTICATION_UNAVAILABLE)',
     "        if False:\n            return None",
     "a gateway reviewer is unavailable without its credential variable in the environment"),
    ("listing_reads_the_key_elsewhere", "reviewers/gateway.py",
     '    if missing:\n        record["error"] = missing\n        return record\n'
     "    key = os.environ[credential_variable(spec)].strip()",
     "    key = ollama_client.load_api_key()",
     "the model listing reads the key only from the environment"),
    ("record_paths_unchecked", "review_record.py",
     '        if pure is None or not path or pure.is_absolute() or ".." in pure.parts or "\\\\" in path:',
     "        if False:",
     "the record reader refuses a path that is absolute or leaves the repository"),
    ("record_versions_unchecked", "review_record.py",
     "        if _version(call) != _version(reviewer):",
     "        if False:",
     "the record reader refuses a reviewer version its calls do not name"),
    ("reviewer_versions_merged", "review_record.py",
     "        if len({_version(call) for call in calls}) != 1:",
     "        if False:",
     "a reviewer whose calls name two versions is not written as one reviewer"),
    ("review_time_counts_rewrites", "review_record.py",
     '                        and run["run_id"] in reviewing), 3)',
     "), 3)",
     "throughput counts only the runs that made calls"),
    ("retired_words_unescaped", "review_record.py",
     "    for term in retired_terms():",
     "    for term in ():",
     "the committed record holds no retired word"),
)
#: Mutants added by the adversarial verification of the panel. The first group removes guards that the
#: list above did not cover; run on revision 7564c71 before their checks existed, 14 of them left every
#: check passing (source-mutants-4.json). The second group removes the guards the verification's repairs
#: added. Not listed: returning ``remaining[0] if remaining else None`` in ``ReviewPanel._next`` is an
#: equivalent mutant, because the reachability test above that line already returns nobody when no
#: remaining reviewer can add a family, so no check can tell the two apart.
VERIFICATION_MUTANTS = (
    ("ledger_truncation_unchecked", "ledger.py",
     '            if data and not data.endswith(b"\\n"):', "            if False:",
     "a ledger whose last line was not completed is refused"),
    ("record_fixture_run_unchecked", "review_record.py",
     '    if record["fixture_run"] is not False and not allow_fixture:', "    if False:",
     "a record of a fixture run is refused"),
    ("record_fixture_reviewer_unchecked", "review_record.py",
     '        if reviewer["engine_kind"] == FIXTURE_ENGINE_KIND and not allow_fixture:', "        if False:",
     "a fixture reviewer is refused in a real record"),
    ("fixture_outside_fixture_run_asked", "panel.py",
     "        if installation.engine_kind == FIXTURE_ENGINE_KIND and not run_request.fixture_run:",
     "        if False:",
     "a fixture reviewer is never asked outside a fixture run"),
    ("token_ceiling_ignored", "panel.py",
     "            if self.charged + self.reserved + tokens > self.token_ceiling:", "            if False:",
     "the declared token ceiling stops the run before the next call"),
    ("spent_allowance_ignored", "panel.py",
     "                    state.spent.add(installation.quota_group)", "                    pass",
     "a spent allowance stops every installation that shares it"),
    ("new_family_not_first", "panel.py",
     "            if distinct_families(heard + [item.installation_id], self.family_of) > current:",
     "            if True:",
     "a reviewer of a new family is asked first"),
    ("rejection_without_reason_counted", "verdicts.py",
     "    if decision == REJECT and not reasons.strip():", "    if False:",
     "a rejection without a written reason is not counted"),
    ("rows_population_unchecked", "review_record.py",
     '    if identities != list(population["selected"]):', "    if False:",
     "the rows name exactly the selected items"),
    ("record_totals_unchecked", "review_record.py",
     '    if record["totals"] != _totals(record["rows"], ordered, runs, interrupted):', "    if False:",
     "the totals agree with the rows and the calls"),
    ("record_prefix_unchecked", "review_record.py",
     '    if prefix != record["record_path"] + "#":', "    if False:",
     "the approval reference prefix names this record"),
    ("source_digest_unchecked", "catalogue.py",
     "            if self.source_digests.get(path) != measured:", "            if False:",
     "a cited source is the pinned bytes"),
    ("source_revision_unchecked", "catalogue.py",
     "        if not separator or revision != self.source_revision:", "        if False:",
     "a cited source is at the anchor revision"),
    ("path_traversal_unchecked", "catalogue.py",
     '    if pure.is_absolute() or ".." in pure.parts or any(part.startswith(".") for part in pure.parts):',
     "    if False:",
     "a path stays inside its folder and passes through no hidden part"),
    ("licence_state_unchecked", "prechecks/licence.py",
     '        if item.get("license_state") not in self.states:', "        if False:",
     "a licence state that is not settled is refused"),
    ("licence_sentence_unchecked", "prechecks/licence.py",
     "        if expected not in text:", "        if False:",
     "the text states its declared licence"),
    ("licence_disagreement_unchecked", "prechecks/licence.py",
     "        if others:", "        if False:",
     "the text states no other licence"),
    ("shell_block_effect_unchecked", "prechecks/effects.py",
     "        if SHELL_FENCE.search(request.body_text_lenient) and PROCESS not in effects:", "        if False:",
     "a shell block declares the process effect"),
    ("word_count_unchecked", "prechecks/format_rules.py",
     "        if not self.minimum <= count <= self.maximum:", "        if False:",
     "the word count is inside the declared range"),
    ("required_parts_unchecked", "prechecks/format_rules.py",
     "        if missing:", "        if False:",
     "every required part is present"),
    ("practice_sentence_unchecked", "prechecks/format_rules.py",
     "        if (self.practice_sentence in text) != (grounding == self.practice_grounding):", "        if False:",
     "the practice sentence appears exactly on a body of general practice"),
    ("description_truncation_unchecked", "prechecks/format_rules.py",
     "        if truncated:", "        if False:",
     "a purpose too long for the skill description is refused"),
    ("skillspector_threshold_raised", "prechecks/skillspector.py",
     'SEVERITY_ORDER.get(str(issue.get("severity")), limit) >= limit]',
     'SEVERITY_ORDER.get(str(issue.get("severity")), limit) > limit]',
     "an issue at the declared severity refuses"),
    ("secrets_item_record_unchecked", "prechecks/secrets.py",
     '                  ("item record", json.dumps(item, sort_keys=True, ensure_ascii=False))]', "                  ]",
     "the item record is scanned for secret shapes"),
    ("producer_evidence_unchecked", "configuration.py",
     "        if canonical_whitespace(quote) not in canonical_whitespace(evidence_text):", "        if False:",
     "a producer declaration quotes its evidence"),
    ("exclude_producer_policy_unchecked", "configuration.py",
     '        if part["exclude_producer_family"] is not True:', "        if False:",
     "a policy that admits the producer family is refused"),
    ("rejection_policy_unchecked", "configuration.py",
     '        if part["any_rejection_withholds_approval"] is not True:', "        if False:",
     "a policy that ignores a rejection is refused"),
    ("reviewers_below_quorum_unchecked", "configuration.py",
     "        if asked < approvals:", "        if False:",
     "each item is put to at least as many reviewers as approve it"),
    ("disabled_without_reason_unchecked", "configuration.py",
     "        if not enabled and not reason.strip():", "        if False:",
     "a disabled reviewer says why"),
    ("calibration_incomplete_trusted", "calibration.py",
     '(CALIBRATION_INCOMPLETE if unanswered else "qualified")', '("qualified")',
     "a reviewer with no verdict on a known-wrong item is not trusted"),
    ("calibration_never_reached_trusted", "calibration.py",
     "    asked = {identity: set() for identity, probe in result.availability.items()",
     "    asked = {identity: set() for identity, probe in () ",
     "a reviewer the calibration never reached is not trusted"),
    ("model_calls_unauthorized", "panel.py",
     "        if not run_request.model_calls_authorized:", "        if False:",
     "no model call without explicit authority"),
    ("decision_without_call_unchecked", "review_record.py",
     '        if (call is None or call["outcome"] != VERDICT_OUTCOME',
     '        if False and (call is None or call["outcome"] != VERDICT_OUTCOME',
     "every decision names its call"),
    ("record_version_accepted", "records.py",
     "    if found != record_type:", "    if False:",
     "another record version is refused"),
    ("unknown_field_accepted", "records.py",
     '    if unknown:\n        refuse("unknown_record_fields"', '    if False:\n        refuse("unknown_record_fields"',
     "an unknown field is refused"),
    ("missing_field_accepted", "records.py",
     '    if missing:\n        refuse("missing_record_fields"', '    if False:\n        refuse("missing_record_fields"',
     "a missing field is refused"),
    ("answer_unknown_keys_accepted", "verdicts.py",
     "    if set(value) - ANSWER_FIELDS:", "    if False:",
     "an answer with unknown keys is not counted"),
    ("rejection_row_unchecked", "review_record.py",
     '        if not rejections or row["rule_applied"] != REJECTION_RULE:', "        if False:",
     "a rejected row records its rejection under the rejection rule"),
    ("row_without_verdict_ref_unchecked", "review_record.py",
     '    if row["approval_ref"] != "" or row["approval_state"] != NO_STATE:', "    if False:",
     "a row without an approval carries no approval reference"),
    ("hidden_character_unchecked", "prechecks/safety_rules.py",
     "            if hidden:", "            if False:",
     "an invisible character is refused"),
    ("control_character_unchecked", "prechecks/safety_rules.py",
     "            if controls:", "            if False:",
     "a control character is refused"),
    ("exact_duplicate_unchecked", "prechecks/duplicates.py",
     "            if other_digest == digest or other_tokens == tokens:", "            if False:",
     "a copy is named an exact duplicate"),
    # The guards the verification's repairs added.
    ("run_identity_unchecked", "ledger.py",
     '        if row["record_type"] == RUN_RECORD and row["run_id"] in self._run_ids:', "        if False:",
     "a run identity the ledger already holds is refused"),
    ("record_reviewer_identity_unchecked", "review_record.py",
     "        if _identity(call) != _identity(reviewer):", "        if False:",
     "a reviewer's family and installation are those of its calls"),
    ("record_call_without_reviewer_unchecked", "review_record.py",
     '        if reviewer is None:\n            refuse("call_without_reviewer"',
     '        if False:\n            refuse("call_without_reviewer"',
     "every call names a reviewer of the record"),
    ("builder_installation_change_unchecked", "review_record.py",
     "        if {_identity(call) for call in calls} != {declared}:", "        if False:",
     "the builder refuses calls made under another installation"),
    ("record_reviewer_decided_twice_unchecked", "review_record.py",
     '        if decision["reviewer_id"] in decided or decision["call_ref"] in answered:', "        if False:",
     "one reviewer and one call decide a row once"),
    ("criterion_type_unchecked", "verdicts.py",
     '        if type(row) is not dict or set(row) != FINDING_FIELDS or type(row["criterion_id"]) is not str:',
     "        if type(row) is not dict or set(row) != FINDING_FIELDS:",
     "a criterion that is not text is an invalid finding, never an error"),
    ("recursion_error_raised", "verdicts.py",
     "UNREADABLE = (ValueError, RecursionError)", "UNREADABLE = (ValueError,)",
     "text nested past the reader's limit is not one answer, never an error"),
    ("record_prechecks_unread", "review_record.py",
     '        _read_prechecks(row["prechecks"], row["identity"], row["outcome"])', "        pass",
     "each row's pre-check results are read"),
    ("record_refused_flag_unchecked", "review_record.py",
     '    if part["refused"] is not refused:', "    if False:",
     "the refused flag agrees with the pre-check results"),
    ("record_refused_row_unchecked", "review_record.py",
     "        if not refused:\n            refuse(\"precheck_inconsistent\"",
     "        if False:\n            refuse(\"precheck_inconsistent\"",
     "a row refused before review names a refusing pre-check"),
    ("record_precheck_kinds_unchecked", "review_record.py",
     "    if refused or undecided:", "    if False:",
     "a row put to reviewers passed every pre-check kind"),
    ("record_approval_licence_unchecked", "review_record.py",
     '        if row["outcome"] == APPROVED and row["declared_license"] not in policy.accepted_licences:',
     "        if False:",
     "an approved row declares a licence the policy accepts"),
)
MUTANTS = MUTANTS + VERIFICATION_MUTANTS
FAILED_CHECK = re.compile(r"^(?:FAIL|ERROR): (\S+) \(([^)]+)\)", re.MULTILINE)


def _linked_folders() -> list:
    """src, examples and every top-level folder a catalogue item cites, so every cited source is present."""
    names = {"src", "examples"}
    for path in sorted(ROOT.glob(SPECIFICATIONS)):
        for row in json.loads(path.read_text(encoding="utf-8"))["specifications"]:
            names.update(source.split("/")[0] for source in row["sources"])
    return sorted(names)


def _scratch(folder: Path) -> Path:
    """A scratch copy: tools copied, the cited folders hard linked, so an edit touches only the copy."""
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    for name in _linked_folders():
        subprocess.run(["cp", "-al", str(ROOT / name), str(folder / name)], check=True)
    shutil.copytree(ROOT / "tools", folder / "tools", symlinks=True,
                    ignore=shutil.ignore_patterns("node_modules", "__pycache__"))
    return folder


def _run(folder: Path) -> dict:
    environment = dict(os.environ, PYTHONPATH=f"{folder / 'src'}{os.pathsep}{folder / 'tools'}",
                       PYTHONDONTWRITEBYTECODE="1")
    started = time.monotonic()
    finished = subprocess.run([sys.executable, "-m", "unittest", *(f"tools.{name}" for name in CHECKS)],
                              cwd=folder, env=environment, capture_output=True, text=True, timeout=RUN_SECONDS)
    output = finished.stdout + finished.stderr
    summary = next((line for line in reversed(output.splitlines()) if line.startswith(("OK", "FAILED"))), "")
    return {"exit_code": finished.returncode, "summary": summary, "seconds": round(time.monotonic() - started, 1),
            "failed_checks": sorted({f"{match.group(2)}.{match.group(1)}" for match in FAILED_CHECK.finditer(output)})}


def run(scratch: Path) -> dict:
    folder = _scratch(scratch)
    baseline = _run(folder)
    rows = []
    for identity, relative, old, new, guard in MUTANTS if baseline["exit_code"] == 0 else ():
        path = folder / PACKAGE / relative
        pristine = path.read_text(encoding="utf-8")
        occurrences = pristine.count(old)
        if occurrences != 1:
            rows.append({"mutant": identity, "file": f"{PACKAGE}/{relative}", "guard": guard,
                         "applied": False, "reason": f"the replaced text occurs {occurrences} times"})
            continue
        path.write_text(pristine.replace(old, new), encoding="utf-8")
        try:
            outcome = _run(folder)
        finally:
            path.write_text(pristine, encoding="utf-8")
        rows.append({"mutant": identity, "file": f"{PACKAGE}/{relative}", "guard": guard, "applied": True,
                     "killed": outcome["exit_code"] != 0, **outcome})
    survivors = [row["mutant"] for row in rows if row.get("applied") and not row["killed"]]
    return {"record_type": RECORD_TYPE, "checks": list(CHECKS), "linked_folders": _linked_folders(),
            "baseline": baseline, "baseline_passed": baseline["exit_code"] == 0, "mutants": rows,
            "applied": sum(1 for row in rows if row.get("applied")),
            "killed": sum(1 for row in rows if row.get("killed")), "survivors": survivors,
            "not_applied": [row["mutant"] for row in rows if not row.get("applied")]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scratch", type=Path, required=True, help="An empty scratch folder outside the repository.")
    parser.add_argument("--write", type=Path, help="Write the report here instead of printing it.")
    options = parser.parse_args(argv)
    scratch = options.scratch.resolve()
    if scratch == ROOT or ROOT in scratch.parents:
        parser.error("the scratch folder must be outside the repository")
    report = run(scratch)
    payload = json.dumps(report, indent=2, ensure_ascii=True) + "\n"
    if options.write:
        options.write.write_text(payload, encoding="ascii")
    else:
        sys.stdout.write(payload)
    return 0 if report["baseline"]["exit_code"] == 0 and not report["survivors"] and not report["not_applied"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
