"""Offline checks for the OpenCode step session, housed apart from it.

The checks exercise the whole session path (prompt file handling, budget
and token accounting, parsing, result projection, refusal) against the
adapter's recorded fixture events and a shell stub that stands in for the
harness binary. No process other than that stub, no network and no provider
call. Housed separately so the session module stays under the size cap,
following the convention the other ``*_checks`` modules use.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

from .opencode_step_session import (
    JSON_ONLY_DIRECTIVE, MAX_ARGV_ELEMENT_BYTES, PRIVATE_PROMPT_DIRECTORY_PREFIX,
    PROMPT_FILE_NAME, PROMPT_POINTER_MESSAGE, OpenCodeStepError,
    OpenCodeStepProfile, OpenCodeStepSession, TransportResult,
    _write_prompt_file, subprocess_transport)


def run_checks() -> dict:
    """Prove transport, budget, parsing, projection and refusal offline."""
    from .opencode_harness_adapter import _FIXTURE_EVENTS

    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": str(detail)[:160]})

    # A profile without provider/model is refused before anything can run.
    try:
        OpenCodeStepProfile(model="gemma4")
        check("profile_requires_provider_qualified_model", False, "accepted")
    except OpenCodeStepError as exc:
        check("profile_requires_provider_qualified_model", True, str(exc)[:80])

    profile = OpenCodeStepProfile(model="ollama-cloud/gemma4:31b")
    argv = OpenCodeStepProfile(model="ollama-cloud/gemma4:31b",
                               prompt_via_file=False).command("hello")
    # The message comes immediately after `run`, not last: `--file` is an
    # array flag, so a trailing positional is consumed as another filename
    # and OpenCode exits with "File not found: <the whole message>".
    check("command_is_headless_json_and_pure",
          "--format" in argv and "json" in argv and "--pure" in argv
          and tuple(argv[:3]) == (profile.binary, "run", "hello")
          and "-m" in argv,
          " ".join(argv))
    check("a_file_profile_renders_the_pointer_form_by_default",
          profile.command("hello")[2] == PROMPT_POINTER_MESSAGE
          and "--file" in profile.command("hello"),
          "what a caller reviews is what runs")

    # The environment is built by allowlist: a secret present in this
    # process does not reach the separate process unless the profile admits it.
    os.environ["OPENCODE_SELFTEST_SECRET"] = "must-not-travel"
    try:
        env = profile.environment()
        check("environment_is_allowlisted_not_inherited",
              "OPENCODE_SELFTEST_SECRET" not in env,
              f"{len(env)} names admitted")
        admitting = OpenCodeStepProfile(
            model="ollama-cloud/gemma4:31b",
            additional_environment=("OPENCODE_SELFTEST_SECRET",))
        check("profile_can_admit_one_named_credential",
              admitting.environment().get("OPENCODE_SELFTEST_SECRET")
              == "must-not-travel")
    finally:
        os.environ.pop("OPENCODE_SELFTEST_SECRET", None)

    # --- prompt transport: off argv, and out of `ps` ---
    import tempfile as _tf
    with _tf.TemporaryDirectory() as _tmp:
        workspace = Path(_tmp)
        filed = OpenCodeStepProfile(
            model="ollama-cloud/gemma4:31b", workspace=workspace)
        secret = "PROPRIETARY_SOURCE_LINE " * 5000
        written = _write_prompt_file(filed, secret)
        check("the_prompt_is_written_where_only_this_user_can_read_it",
              written is not None and written.read_text() == secret
              and oct(written.stat().st_mode)[-3:] == "600",
              f"{len(secret):,} bytes, mode "
              f"{oct(written.stat().st_mode)[-3:]}")
        filed_argv = filed.command(secret, written)
        joined = " ".join(filed_argv)
        check("no_prompt_content_reaches_argv",
              "PROPRIETARY_SOURCE_LINE" not in joined
              and PROMPT_POINTER_MESSAGE in joined,
              f"largest argv element {max(len(a) for a in filed_argv)} bytes "
              f"for a {len(secret):,} byte prompt")
        check("the_pointer_message_is_constant_across_steps",
              filed.command("a different prompt entirely", written)
              == filed_argv,
              "`ps` shows the same harmless sentence for every step")

        # With file transport off, an oversized prompt is refused with a
        # message naming the cause, rather than failing the exec with an
        # opaque E2BIG from deep inside subprocess.
        inline = OpenCodeStepProfile(
            model="ollama-cloud/gemma4:31b", workspace=workspace,
            prompt_via_file=False)
        check("argv_transport_still_available_when_asked",
              _write_prompt_file(inline, "x") is None
              and "x" in inline.command("x"))
        try:
            subprocess_transport(inline, "z" * (MAX_ARGV_ELEMENT_BYTES + 10))
            check("an_oversized_argv_prompt_is_refused_by_name", False)
        except OpenCodeStepError as exc:
            check("an_oversized_argv_prompt_is_refused_by_name",
                  "prompt_via_file" in str(exc) and "E2BIG" in str(exc),
                  str(exc)[:110])

    class _Authority:
        max_model_calls = 2

    class _Request:
        prompt = "Orient on the task."

    # The adapter's fixture ends with a prose-wrapped object ("Done." and
    # then the JSON on the next line). The event parser admits only a
    # complete bare or JSON-fenced final object, so the session's own
    # fixture states the object that JSON_ONLY_DIRECTIVE asks for; the
    # prose-wrapped form is exercised below as the case the session must
    # not mistake for an admitted object.
    json_only_events = tuple(
        json.dumps({
            "type": "text", "timestamp": 3, "sessionID": "ses_fixture",
            "part": {"id": "prt_3", "type": "text", "text": json.dumps({
                "status": "ok", "summary": "implemented clamp",
                "files": ["tiny_math.py"]})}})
        if json.loads(line).get("type") == "text" else line
        for line in _FIXTURE_EVENTS)

    def fixture_transport(_profile, _message):
        return json_only_events, ""

    session = OpenCodeStepSession(
        authority=_Authority(), profile=profile, transport=fixture_transport)
    text = session.invoke(_Request(), None)
    check("step_returns_the_final_json_object",
          json.loads(text).get("summary") == "implemented clamp", text[:90])

    def prose_transport(_profile, _message):
        return _FIXTURE_EVENTS, ""

    prose = OpenCodeStepSession(
        authority=_Authority(), profile=profile, transport=prose_transport)
    prose_text = prose.invoke(_Request(), None)
    check("a_prose_wrapped_object_is_returned_as_transcript_not_as_the_object",
          prose.results[-1].ok and not prose_text.startswith("{")
          and "implemented clamp" in prose_text,
          prose_text[:60])
    check("one_step_charges_one_call_and_projects_one_result",
          session.calls_used == 1 and session.semantic_calls_used == 1
          and session.results[-1].ok,
          f"calls={session.calls_used}")
    # 160 and 35, not the fixture's bare 120 and 30: the adapter's parser
    # folds cache reads into input and reasoning into output, which is what
    # the provider actually billed. Asserting the raw fields here would
    # have encoded a token count no invoice would match.
    class _Owner:
        loop_id = "loop:practitioner-42"

    class _IdRequest:
        prompt = "Orient on the task."
        semantic_call_id = "semantic-call:abc123"

    ident = OpenCodeStepSession(
        authority=_Authority(), profile=profile, transport=fixture_transport)
    ident.invoke(_IdRequest(), _Owner())
    res = ident.results[-1]
    check("stage_identity_is_stamped_on_the_result_and_every_attempt",
          res.semantic_call_id == "semantic-call:abc123"
          and res.owner_loop_id == "loop:practitioner-42"
          and all(a.semantic_call_id == "semantic-call:abc123"
                  and a.owner_loop_id == "loop:practitioner-42"
                  for a in res.attempts),
          "the Practitioner's stage recorder compares both against its "
          "occurrence; missing either logs stage_evidence_degraded per step")
    anon = OpenCodeStepSession(
        authority=_Authority(), profile=profile, transport=fixture_transport)
    anon.invoke(_Request(), None)
    import re as _re
    hex64 = _re.compile(r"^[0-9a-f]{64}$")
    check("every_digest_the_stage_recorder_verifies_is_present_and_real",
          res.prompt_digest == hashlib.sha256(
              _IdRequest.prompt.encode("utf-8")).hexdigest()
          and hex64.match(res.request_digest) is not None
          and all(a.prompt_digest == res.prompt_digest
                  and hex64.match(a.provider_request_digest) is not None
                  for a in res.attempts),
          "the recorder rejects a result whose digests do not match the "
          "rendered prompt or are not 64 hex chars; each here digests real "
          "bytes this session saw or sent")
    check("a_request_without_an_id_gets_a_fresh_one_not_an_empty_string",
          anon.results[-1].semantic_call_id.startswith("semantic-call:")
          and anon.results[-1].owner_loop_id == "")

    check("tokens_are_read_from_step_finish_not_guessed",
          session.results[-1].input_tokens == 160
          and session.results[-1].output_tokens == 35,
          f"in={session.results[-1].input_tokens} "
          f"out={session.results[-1].output_tokens}")

    # The budget refuses the third step before a process would start.
    session.invoke(_Request(), None)
    try:
        session.invoke(_Request(), None)
        check("budget_refuses_before_spending_a_process", False, "ran anyway")
    except OpenCodeStepError as exc:
        check("budget_refuses_before_spending_a_process",
              "budget exhausted" in str(exc), str(exc)[:80])

    # A fenced object is recovered rather than read as prose. This is the
    # exact shape the first live run returned.
    fenced_events = (
        '{"type":"text","sessionID":"s","part":{"type":"text","text":'
        + json.dumps("```json\n{\"task_summary\": \"add clamp\"}\n```")
        + '}}',
        '{"type":"step_finish","sessionID":"s","part":{"type":"step-finish",'
        '"reason":"stop","tokens":{"input":10,"output":2}}}')
    fenced_session = OpenCodeStepSession(
        authority=_Authority(), profile=profile,
        transport=lambda _p, _m: (fenced_events, ""))
    fenced_text = fenced_session.invoke(_Request(), None)
    check("fenced_json_is_recovered_not_read_as_prose",
          json.loads(fenced_text).get("task_summary") == "add clamp",
          fenced_text[:80])

    # A run that produces no assistant text fails loudly and still records
    # a result, so a silent empty step cannot be mistaken for progress.
    empty = OpenCodeStepSession(
        authority=_Authority(), profile=profile,
        transport=lambda _p, _m: ((), "provider refused"))
    try:
        empty.invoke(_Request(), None)
        check("empty_event_stream_is_an_error_not_an_empty_success", False)
    except OpenCodeStepError:
        check("empty_event_stream_is_an_error_not_an_empty_success",
              len(empty.results) == 1 and not empty.results[-1].ok
              and empty.results[-1].error_code == "opencode_no_text")

    # --- the prompt file: unlink first, exclusive create, 0600 forced,
    # removed after the process returns, a private directory without a
    # workspace, argv only by explicit choice ---
    with _tf.TemporaryDirectory() as _tmp:
        root = Path(_tmp)
        workspace = root / "ws"
        workspace.mkdir()
        record = root / "argv.txt"
        stub = root / "stub-opencode"
        stub.write_text(
            "#!/bin/sh\n"
            f"printf '%s\\n' \"$@\" > '{record}'\n"
            "printf '%s\\n' '{\"type\":\"text\",\"sessionID\":\"s\",\"part\":"
            "{\"type\":\"text\",\"text\":\"{\\\"ok\\\":true}\"}}'\n"
            "printf '%s\\n' '{\"type\":\"step_finish\",\"sessionID\":\"s\","
            "\"part\":{\"type\":\"step-finish\",\"reason\":\"stop\","
            "\"tokens\":{\"input\":3,\"output\":1}}}'\n")
        stub.chmod(0o755)

        def argv_of():
            return record.read_text().splitlines()

        filed = OpenCodeStepProfile(
            model="ollama-cloud/gemma4:31b", binary=str(stub),
            workspace=workspace)
        prompt_path = workspace / PROMPT_FILE_NAME
        prompt_path.write_text("stale")
        prompt_path.chmod(0o644)
        _write_prompt_file(filed, "REPLACES THE STALE FILE")
        check("a_leftover_world_readable_prompt_file_is_recreated_0600",
              oct(prompt_path.stat().st_mode)[-3:] == "600"
              and prompt_path.read_text() == "REPLACES THE STALE FILE",
              f"mode {oct(prompt_path.stat().st_mode)[-3:]}")
        victim = root / "victim.txt"
        victim.write_text("outside, untouched\n")
        prompt_path.unlink()
        prompt_path.symlink_to(victim)
        _write_prompt_file(filed, "THROUGH A PLANTED LINK")
        check("a_planted_symlink_is_unlinked_not_written_through",
              victim.read_text() == "outside, untouched\n"
              and not prompt_path.is_symlink()
              and prompt_path.read_text() == "THROUGH A PLANTED LINK",
              "O_EXCL|O_NOFOLLOW after unlinking whatever sat at the name")
        subprocess_transport(filed, "PROMPT BODY ONLY THE FILE CARRIES")
        actual_prompt = Path(argv_of()[argv_of().index("--file") + 1])
        check("transport_owns_a_private_prompt_and_preserves_workspace_files",
              not actual_prompt.exists() and not actual_prompt.parent.exists()
              and prompt_path.read_text() == "THROUGH A PLANTED LINK"
              and "--file" in argv_of()
              and not any("PROMPT BODY" in item for item in argv_of()),
              str(argv_of())[:120])
        kept = OpenCodeStepProfile(
            model="ollama-cloud/gemma4:31b", binary=str(stub),
            workspace=workspace, keep_prompt_file=True)
        subprocess_transport(kept, "KEPT ON REQUEST")
        actual_prompt = Path(argv_of()[argv_of().index("--file") + 1])
        check("keep_prompt_file_keeps_it_at_0600_when_a_caller_asks",
              actual_prompt.exists()
              and oct(actual_prompt.stat().st_mode)[-3:] == "600"
              and actual_prompt.read_text().startswith("KEPT ON REQUEST")
              and oct(actual_prompt.parent.stat().st_mode)[-3:] == "700")
        homeless = OpenCodeStepProfile(
            model="ollama-cloud/gemma4:31b", binary=str(stub))
        subprocess_transport(homeless, "NO WORKSPACE PROMPT")
        argv = argv_of()
        private = (Path(argv[argv.index("--file") + 1]).parent
                   if "--file" in argv else None)
        check("without_a_workspace_the_prompt_goes_to_a_private_directory_not_argv",
              private is not None
              and private.name.startswith(PRIVATE_PROMPT_DIRECTORY_PREFIX)
              and not private.exists()
              and "NO WORKSPACE PROMPT" not in argv,
              f"{private.name if private else 'argv'}, removed afterwards")
        inline_stub = OpenCodeStepProfile(
            model="ollama-cloud/gemma4:31b", binary=str(stub),
            prompt_via_file=False)
        subprocess_transport(inline_stub, "ARGV BY EXPLICIT CHOICE")
        check("argv_carries_the_prompt_only_when_prompt_via_file_is_off_explicitly",
              "ARGV BY EXPLICIT CHOICE" in argv_of())
        check("command_renders_the_file_transport_that_will_run",
              filed.command("m") == filed.command("m", prompt_path)
              and "m" not in filed.command("m"),
              "a reviewer and provider_request_digest see the same vector")

    # The size refusal must not depend on a binary being installed: CI has
    # no harness, and the check under test is about the prompt, not PATH.
    absent = OpenCodeStepProfile(
        model="ollama-cloud/gemma4:31b",
        binary="opencode-binary-that-is-not-installed", prompt_via_file=False)
    try:
        subprocess_transport(absent, "z" * (MAX_ARGV_ELEMENT_BYTES + 10))
        check("an_oversized_argv_prompt_is_refused_before_the_binary_is_resolved",
              False, "ran")
    except OpenCodeStepError as exc:
        check("an_oversized_argv_prompt_is_refused_before_the_binary_is_resolved",
              "E2BIG" in str(exc) and "not on PATH" not in str(exc),
              str(exc)[:90])
    try:
        subprocess_transport(absent, "a prompt that fits")
        check("a_missing_binary_is_still_refused_when_the_prompt_fits", False)
    except OpenCodeStepError as exc:
        check("a_missing_binary_is_still_refused_when_the_prompt_fits",
              "not on PATH" in str(exc), str(exc)[:80])

    # --- accounting: tokens summed, uncertainty named, ceilings enforced ---
    class _Wide:
        max_model_calls = 10

    tallied = OpenCodeStepSession(
        authority=_Wide(), profile=profile, transport=fixture_transport)
    tallied.invoke(_Request(), None)
    tallied.invoke(_Request(), None)
    check("tokens_are_summed_into_total_tokens_used",
          tallied.total_tokens_used == 390 and not tallied.accounting_uncertain,
          f"total={tallied.total_tokens_used} after two 195-token steps")
    text_only = tuple(line for line in json_only_events
                      if json.loads(line).get("type") != "step_finish")
    unsure = OpenCodeStepSession(
        authority=_Wide(), profile=profile,
        transport=lambda _p, _m: (text_only, ""))
    unsure.invoke(_Request(), None)
    check("a_run_without_step_finish_marks_accounting_uncertain",
          unsure.accounting_uncertain and unsure.total_tokens_used is None
          and unsure.calls_used == 1,
          "the count is a floor and the token total is unknown; say so")
    finish = next(line for line in json_only_events
                  if json.loads(line).get("type") == "step_finish")
    three_turns = tuple([finish, finish, finish] + [
        line for line in json_only_events
        if json.loads(line).get("type") == "text"])
    over = OpenCodeStepSession(
        authority=_Authority(), profile=profile,
        transport=lambda _p, _m: (three_turns, ""))
    try:
        over.invoke(_Request(), None)
        check("one_run_that_overshoots_the_call_ceiling_is_charged_and_refused",
              False, "returned text")
    except OpenCodeStepError as exc:
        last = over.results[-1]
        check("one_run_that_overshoots_the_call_ceiling_is_charged_and_refused",
              over.calls_used == 3 and not last.ok
              and last.error_code == "budget_overrun"
              and (last.budget_overrun or {}).get("kind") == "model_calls"
              and last.budget_overrun["charged"] == 3
              and over.total_tokens_used == 3 * 195
              and last.to_dict()["budget_overrun"]["ceiling"] == 2,
              str(exc)[:90])
    try:
        over.invoke(_Request(), None)
        check("after_an_overrun_the_next_step_is_refused_before_a_process", False)
    except OpenCodeStepError as exc:
        check("after_an_overrun_the_next_step_is_refused_before_a_process",
              "budget exhausted: 3/2" in str(exc), str(exc)[:80])

    class _TokenBound:
        max_model_calls = 10
        config = SimpleNamespace(max_total_tokens=300)

    bound = OpenCodeStepSession(
        authority=_TokenBound(), profile=profile, transport=fixture_transport)
    bound.invoke(_Request(), None)
    try:
        bound.invoke(_Request(), None)
        check("a_declared_token_ceiling_is_enforced_after_the_run_that_crossed_it",
              False, "ran")
    except OpenCodeStepError:
        check("a_declared_token_ceiling_is_enforced_after_the_run_that_crossed_it",
              (bound.results[-1].budget_overrun or {}).get("kind") == "total_tokens"
              and bound.total_tokens_used == 390,
              f"charged {bound.total_tokens_used} against 300")
    try:
        bound.invoke(_Request(), None)
        check("a_spent_token_ceiling_refuses_before_a_process_starts", False)
    except OpenCodeStepError as exc:
        check("a_spent_token_ceiling_refuses_before_a_process_starts",
              "total-token budget exhausted" in str(exc)
              and len(bound.results) == 2, str(exc)[:80])

    ran = ("/usr/local/bin/opencode", "run", PROMPT_POINTER_MESSAGE,
           "--file", "/w/.step-prompt.md")
    traced = OpenCodeStepSession(
        authority=_Wide(), profile=profile,
        transport=lambda _p, _m: TransportResult(json_only_events, "", ran))
    traced.invoke(_Request(), None)
    sent = f"{_Request.prompt}\n\n{JSON_ONLY_DIRECTIVE}".encode("utf-8")
    expected = hashlib.sha256(
        b"\0".join(part.encode("utf-8") for part in ran) + b"\0\0" + sent
        ).hexdigest()
    check("provider_request_digest_covers_the_argv_that_ran_and_the_prompt_bytes",
          traced.results[-1].attempts[0].provider_request_digest == expected
          and expected != anon.results[-1].attempts[0].provider_request_digest,
          "the transport reports the executed vector; a fixture falls back "
          "to the profile's own rendering")

    # Requested dimensions must bind or refuse before transport. Even the
    # canonical request's default temperature is explicit, not permission
    # for the native harness to choose an unrelated value.
    for field, value in (("system", "PRIVATE_SYSTEM_MARKER"),
                         ("temperature", 0.0), ("temperature", 0.7),
                         ("model", "other-provider/other-model"),
                         ("output_allocation", object()),
                         ("response_admission_policy", object()),
                         ("harness_selection_scope", object()),
                         ("response_evaluation_ref", "evaluator/v1")):
        dispatched = []
        refused_session = OpenCodeStepSession(
            authority=_Wide(), profile=profile,
            transport=lambda p, m: dispatched.append(m))
        try:
            refused_session.invoke(SimpleNamespace(prompt="test", **{field: value}), None)
            check(f"unsupported_{field}_{value if field == 'temperature' else ''}", False)
        except OpenCodeStepError:
            check(f"unsupported_{field}_{value if field == 'temperature' else ''}",
                  not dispatched and not refused_session.results
                  and refused_session.calls_used == 0)

    from .observation_expectations import ObservationExpectation
    digest = hashlib.sha256(json.dumps(
        {"prompt": "test", "system": ""}, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()
    for required, accepted in (("summary", True), ("missing_field", False)):
        req = SimpleNamespace(prompt="test", semantic_call_id="test-call",
                              exact_input_digest=digest)
        req.response_expectation = ObservationExpectation(
            "test-expectation", "test-call", digest, "test/v1",
            json.dumps({"type": "object", "required": [required]}))
        validated = OpenCodeStepSession(
            authority=_Wide(), profile=profile, transport=fixture_transport)
        try:
            validated.invoke(req, None)
        except OpenCodeStepError:
            pass
        check(f"bound_response_schema_{required}",
              validated.results[-1].ok is accepted
              and validated.results[-1].attempts[0].validation_ok is accepted)

    # A later invalid final message cannot be replaced by an earlier object.
    stale_json = (*fenced_events,
                  json.dumps({"type": "text", "part": {"text": "not JSON"}}))
    stale = OpenCodeStepSession(authority=_Wide(), profile=profile,
                               transport=lambda p, m: (stale_json, ""))
    check("earlier_json_does_not_replace_invalid_final_answer",
          not stale.invoke(_Request(), None).startswith("{"))
    multiple = OpenCodeStepSession(
        authority=_Wide(), profile=profile,
        transport=lambda p, m: (json_only_events * 3, ""))
    multiple.invoke(_Request(), None)
    check("every_reported_physical_call_has_an_attempt",
          multiple.results[-1].physical_model_calls == 3
          and len(multiple.results[-1].attempts) == 3)
    partial_usage = SimpleNamespace(model_calls=(
        SimpleNamespace(input_tokens=10), SimpleNamespace(input_tokens=None)))
    check("partial_usage_is_unknown_not_a_complete_subtotal",
          OpenCodeStepSession._sum_tokens(partial_usage, "input_tokens") is None)

    def lost_transport(p, m):
        raise RuntimeError("fixture connection lost after dispatch")

    lost = OpenCodeStepSession(authority=_Wide(), profile=profile,
                               transport=lost_transport)
    for _ in range(2):
        try:
            lost.invoke(_Request(), None)
        except OpenCodeStepError:
            pass
    check("transport_failure_is_preserved_and_finite_budget_cannot_retry_it",
          len(lost.results) == 1 and lost.accounting_uncertain
          and lost.calls_used == 1 and lost.total_tokens_used is None
          and lost.results[-1].to_dict()["physical_model_calls"] is None)
    exited = OpenCodeStepSession(authority=_Wide(), profile=profile,
                                transport=lambda p, m: TransportResult(
                                    json_only_events, "", returncode=1))
    try:
        exited.invoke(_Request(), None)
    except OpenCodeStepError:
        pass
    check("nonzero_process_exit_cannot_succeed_from_partial_text",
          not exited.results[-1].ok and exited.accounting_uncertain)

    return {"module": "core.opencode_step_session", "tests": tests,
            "passed": all(item["passed"] for item in tests)}
