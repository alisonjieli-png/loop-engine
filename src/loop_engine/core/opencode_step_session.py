"""Run each Practitioner cognitive step through an OpenCode instance.

Every adaptive step reaches the model through exactly one seam --
``AdaptiveRunServices.model_session.invoke(ModelInvocationRequest, owner)``.
This module supplies an alternative object for that seam, so a run can put
each loop node's cognitive step inside an OpenCode session that already
carries its own tools, skills, context and agent definitions, instead of the
engine assembling those itself. Nothing here replaces the default path: the
session is constructed only when a caller asks for it, and a run that does
not ask is byte-for-byte the run it was before.

WHY THIS IS A SEPARATE SESSION RATHER THAN A HARNESS ADAPTER
``OpenCodeProcessAdapter`` in ``opencode_harness_adapter`` deliberately
refuses to execute: it reports ``available=False`` because a working
directory is not a sandbox and ambient configuration is not isolated. That
judgement is about *unattended host execution of arbitrary generated code*
and it stands -- this module does not lift it, and the adapter still
refuses. What runs here is narrower and is stated plainly so nobody has to
infer it:

  * the process is started only when a caller passes an explicit profile,
  * the environment is an allowlist built from nothing, never ``os.environ``
    inherited wholesale, so ambient credentials do not travel by default,
  * ``--pure`` disables external plugins, so the run's tool surface is the
    one OpenCode ships plus whatever the profile's config directory admits,
  * ``--dir`` confines the working directory to the supplied workspace.

That is a *host process with a scrubbed environment*, which is a weaker
boundary than the engine's Docker profile (``--read-only --cap-drop ALL
--network none``). It is appropriate for driving a cognitive step, whose
product is text this engine then validates, and it is NOT a substitute for
the sandbox that executes generated code. ``requires_trusted_workspace`` is
True to keep that distinction legible to callers rather than buried here.

OFFLINE BY CONSTRUCTION
``transport`` is injectable, so ``self_test`` exercises the whole path --
budget, parsing, result projection, refusal -- against the adapter's own
recorded fixture events with no process, no network and no provider call.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

from .model_gateway import GatewayAttempt, ModelGatewayResult
from .opencode_harness_adapter import parse_opencode_events

#: Environment names an OpenCode step may inherit. Everything absent from
#: this tuple is dropped, so a credential the profile did not name cannot
#: reach the separate process by having been present in this one.
INHERITABLE_ENVIRONMENT = ("PATH", "HOME", "LANG", "LC_ALL", "TERM", "TMPDIR")

#: What travels in argv when the prompt goes through a file. Constant, so
#: `ps` shows the same harmless sentence for every step of every run.
PROMPT_POINTER_MESSAGE = (
    "Follow the instructions in the attached file exactly.")

#: Where a step's prompt is written when file transport is used. Inside the
#: composed instance directory, which is already per-step and disposable.
PROMPT_FILE_NAME = ".step-prompt.md"

#: The engine states the response contract in the prompt and validates the
#: parsed object itself. OpenCode is asked for one JSON object and nothing
#: else; the parser already takes the last JSON-parsing text part.
JSON_ONLY_DIRECTIVE = (
    "Return exactly one JSON object matching the stated contract as your "
    "final message. Emit no prose before or after it.")

#: Only a backstop for a caller that supplied no budget. Real runs pass a
#: grant from core.night_budget, which divides the night rather than
#: guessing at a step. A fixed number here decides in advance that a step
#: needing longer fails, which is how an 880-second wrapper killed a run
#: that had eleven hours of night left.
#: MAX_ARG_STRLEN on Linux: 32 pages of 4096 bytes. Measured on this
#: machine by bisection at 130,945 bytes. Exceeding it fails the exec with
#: E2BIG, which surfaces as an opaque OSError rather than anything a
#: reader would connect to prompt size.
MAX_ARGV_ELEMENT_BYTES = 131_072

DEFAULT_TIMEOUT_SECONDS = 3600.0


class OpenCodeStepError(RuntimeError):
    """An OpenCode-backed cognitive step could not be run or read."""


@dataclass(frozen=True)
class OpenCodeStepProfile:
    """Everything a caller must state to run steps through OpenCode.

    There is no default model and no default binary discovery: a profile
    that does not name them is refused, so an OpenCode run is never the
    accidental consequence of a binary happening to be on PATH.
    """

    model: str
    binary: str = "opencode"
    agent: str = ""
    variant: str = ""
    workspace: Path | None = None
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    pure: bool = True
    config_directory: Path | None = None
    #: Extra environment names this profile admits beyond the inheritable
    #: set -- how a caller passes one provider credential without passing
    #: the whole environment.
    additional_environment: tuple[str, ...] = ()
    requires_trusted_workspace: bool = True
    #: Carry the prompt in a mode-600 file and put only a constant pointer
    #: in argv. Two measured reasons, both of which argv fails:
    #:
    #:   * a single argv element caps at 130,945 bytes (MAX_ARG_STRLEN) and
    #:     a real orient prompt measured ~70 KB -- 55% of the wall;
    #:   * /proc/<pid>/cmdline is mode 444, verified, so every step's full
    #:     prompt is readable by any local user through `ps`. On a shared
    #:     build host that exposes source, customer data, and anything a
    #:     failing command happened to print.
    #:
    #: Default on. `False` restores argv for a caller that needs it.
    prompt_via_file: bool = True

    def __post_init__(self) -> None:
        if not str(self.model).strip():
            raise OpenCodeStepError(
                "an OpenCode profile must name a model as provider/model, "
                "for example 'ollama-cloud/gemma4:31b'")
        if "/" not in self.model:
            raise OpenCodeStepError(
                f"model {self.model!r} must be provider/model, for example "
                "'ollama-cloud/gemma4:31b'")
        if not str(self.binary).strip():
            raise OpenCodeStepError("an OpenCode profile must name a binary")
        if not isinstance(self.timeout_seconds, (int, float)) or (
                self.timeout_seconds <= 0):
            raise OpenCodeStepError("timeout_seconds must be a positive number")

    def environment(self) -> dict:
        """Build the separate process environment from nothing, by allowlist."""
        names = tuple(INHERITABLE_ENVIRONMENT) + tuple(
            self.additional_environment)
        env = {name: os.environ[name] for name in names if name in os.environ}
        if self.config_directory is not None:
            env["OPENCODE_CONFIG_DIR"] = str(self.config_directory)
        return env

    def command(self, message: str, prompt_file: "Path | None" = None
                ) -> tuple:
        """The exact argument vector, so a caller can log or review it.

        With ``prompt_file`` the message is a constant pointer and the real
        text rides in the file, so argv is both unbounded and uninteresting
        to anyone reading `ps`.
        """
        argv = [self.binary, "run"]
        argv.append(PROMPT_POINTER_MESSAGE if prompt_file is not None
                    else message)
        argv += ["--format", "json"]
        if self.pure:
            argv.append("--pure")
        argv += ["-m", self.model]
        if self.agent:
            argv += ["--agent", self.agent]
        if self.variant:
            argv += ["--variant", self.variant]
        if self.workspace is not None:
            argv += ["--dir", str(self.workspace)]
        if prompt_file is not None:
            argv += ["--file", str(prompt_file)]
        return tuple(argv)


def _write_prompt_file(profile: OpenCodeStepProfile, message: str) -> "Path | None":
    """Write the prompt where only this user can read it."""
    if not profile.prompt_via_file or profile.workspace is None:
        return None
    target = Path(profile.workspace) / PROMPT_FILE_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    # Created 0600 before any content is written, so the prompt is never
    # briefly world-readable between creation and chmod.
    handle = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        stream.write(message)
    return target


def subprocess_transport(profile: OpenCodeStepProfile, message: str) -> tuple:
    """Run one headless OpenCode turn; return (stdout lines, stderr tail)."""
    binary = shutil.which(profile.binary)
    if binary is None:
        raise OpenCodeStepError(
            f"OpenCode binary {profile.binary!r} is not on PATH; install it "
            "or name an absolute path in the profile")
    prompt_file = _write_prompt_file(profile, message)
    if prompt_file is None and len(message) > MAX_ARGV_ELEMENT_BYTES:
        raise OpenCodeStepError(
            f"the prompt is {len(message):,} bytes and argv caps a single "
            f"element at {MAX_ARGV_ELEMENT_BYTES:,}; enable prompt_via_file "
            "rather than letting the exec fail with E2BIG")
    argv = list(profile.command(message, prompt_file))
    argv[0] = binary
    try:
        completed = subprocess.run(
            argv, capture_output=True, text=True, check=False,
            timeout=profile.timeout_seconds, env=profile.environment(),
            cwd=str(profile.workspace) if profile.workspace else None)
    except subprocess.TimeoutExpired as exc:
        raise OpenCodeStepError(
            f"OpenCode step exceeded {profile.timeout_seconds}s") from exc
    except OSError as exc:
        raise OpenCodeStepError(f"OpenCode step could not start: {exc}") from exc
    if completed.returncode != 0 and not completed.stdout.strip():
        tail = (completed.stderr or "").strip()[-400:]
        raise OpenCodeStepError(
            f"OpenCode exited {completed.returncode} with no events: {tail}")
    return tuple(completed.stdout.splitlines()), (completed.stderr or "")[-400:]


def _unfenced_json(texts) -> "dict | None":
    """Recover a JSON object a model wrapped in a Markdown code fence.

    Observed on the first live run of this module: gemma4:31b returned a
    correct, complete orientation object inside ```json ... ```. The event
    parser only accepts a text part that parses as JSON on its own, so a
    perfectly good answer was read as prose and the step was scored as
    having produced no object.

    Fencing is not a model defect to be prompted away -- it is the single
    most common way models emit JSON, and it survives an explicit
    instruction not to do it. Recovering it here costs one string operation;
    refusing it costs a whole step, and the repair attempt that follows is
    just as likely to come back fenced.
    """
    for text in reversed(list(texts)):
        stripped = str(text).strip()
        if not stripped.startswith("```"):
            continue
        body = stripped.split("\n", 1)[-1] if "\n" in stripped else ""
        if body.rstrip().endswith("```"):
            body = body.rstrip()[:-3]
        try:
            value = json.loads(body.strip())
        except ValueError:
            continue
        if isinstance(value, dict):
            return value
    return None


@dataclass
class OpenCodeStepSession:
    """A model_session whose every step is one OpenCode run.

    Duck-compatible with ``ModelExecutionSession``: the practitioner reads
    ``calls_used``, ``semantic_calls_used``, ``results``, ``authority`` and
    calls ``invoke``. Budget enforcement mirrors the in-process session --
    ``authority.max_model_calls`` is the ceiling, refused before a process
    starts rather than after it has spent one.
    """

    authority: object
    profile: OpenCodeStepProfile
    results: list = field(default_factory=list)
    #: Injected so the whole path is testable with no process. Signature is
    #: (profile, message) -> (stdout_lines, stderr_tail).
    transport: object = field(default=subprocess_transport, repr=False)
    _calls_charged: int = field(default=0, init=False, repr=False)
    _tokens_charged: int = field(default=0, init=False, repr=False)
    _accounting_uncertain: bool = field(default=False, init=False, repr=False)
    _lock: object = field(default_factory=Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.results:
            raise OpenCodeStepError(
                "session requires an empty result projection")
        if not isinstance(self.profile, OpenCodeStepProfile):
            raise OpenCodeStepError("session requires an OpenCodeStepProfile")

    @property
    def calls_used(self) -> int:
        return self._calls_charged

    @property
    def semantic_calls_used(self) -> int:
        return len(self.results)

    @property
    def accounting_uncertain(self) -> bool:
        return self._accounting_uncertain

    @property
    def total_tokens_used(self):
        if self._accounting_uncertain:
            return None
        return self._tokens_charged

    def _max_calls(self):
        return getattr(self.authority, "max_model_calls", None)

    def invoke(self, request, parent_loop) -> str:
        """Run one cognitive step inside an OpenCode session."""
        if not self._lock.acquire(blocking=False):
            raise OpenCodeStepError(
                "an OpenCode session already has a step in flight")
        try:
            return self._invoke_serial(request, parent_loop)
        finally:
            self._lock.release()

    def _invoke_serial(self, request, parent_loop=None) -> str:
        prompt = getattr(request, "prompt", None)
        if not isinstance(prompt, str) or not prompt.strip():
            raise OpenCodeStepError("invoke requires a request carrying a prompt")
        maximum = self._max_calls()
        if maximum is not None and self.calls_used >= maximum:
            raise OpenCodeStepError(
                "whole-Solution model-call budget exhausted: "
                f"{self.calls_used}/{maximum}")
        message = f"{prompt}\n\n{JSON_ONLY_DIRECTIVE}"
        provider, _, model_id = self.profile.model.partition("/")
        # The two identities the Practitioner's stage recorder compares
        # against its stage occurrence, on the result AND on every attempt.
        # The first version set neither, so the recorder saw "" against a
        # real id on every step and logged stage_evidence_degraded 48 times
        # in a 24-step run -- the instrumentation was degraded, not the run,
        # but a reviewer cannot tell those apart from the log. Same derivation
        # as the gateway: the request's id, else a fresh one; the owner Loop's
        # id, else empty.
        import uuid as _uuid
        semantic_call_id = str(
            getattr(request, "semantic_call_id", "") or "").strip() or (
            f"semantic-call:{_uuid.uuid4().hex}")
        owner_loop_id = str(getattr(parent_loop, "loop_id", "") or "")
        # The digests the stage recorder verifies. Each is a real digest of
        # what this session actually saw or sent -- never a filler string
        # that happens to be 64 characters. prompt_digest is sha256 of the
        # prompt exactly as the gateway computes it, so it equals the
        # recorder's snapshot digest of the same rendered prompt.
        # provider_request_digest covers the exact argv that reached
        # OpenCode, which is this session's provider request.
        prompt_digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        system_digest = hashlib.sha256(
            str(getattr(request, "system", "") or "").encode("utf-8")).hexdigest()
        request_digest = hashlib.sha256(json.dumps({
            "prompt_digest": prompt_digest, "system_digest": system_digest,
            "temperature": getattr(request, "temperature", None),
            "semantic_call_id": semantic_call_id,
            "provider": provider, "model": model_id,
            "pure": self.profile.pure, "agent": self.profile.agent,
        }, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        provider_request_digest = hashlib.sha256(
            "\0".join(self.profile.command(message)).encode("utf-8")).hexdigest()
        lines, stderr_tail = self.transport(self.profile, message)
        parsed = parse_opencode_events(
            lines, provider_id=provider, model_id=model_id)
        self._calls_charged += max(1, len(parsed.model_calls))
        text = self._text_of(parsed)
        ok = bool(text.strip())
        result = ModelGatewayResult(
            ok=ok, text=text, provider=provider, model=model_id,
            route=f"opencode.{provider}",
            input_tokens=self._sum_tokens(parsed, "input_tokens"),
            output_tokens=self._sum_tokens(parsed, "output_tokens"),
            attempts=[GatewayAttempt(
                provider, model_id, f"opencode.{provider}",
                parsed.session_id or "opencode", ok,
                self._sum_tokens(parsed, "input_tokens") or 0,
                self._sum_tokens(parsed, "output_tokens") or 0,
                True, provider_ok=ok,
                semantic_call_id=semantic_call_id,
                owner_loop_id=owner_loop_id,
                prompt_digest=prompt_digest, system_digest=system_digest,
                provider_request_digest=provider_request_digest)],
            error_code="" if ok else "opencode_no_text",
            error="" if ok else f"no assistant text in events; {stderr_tail}",
            prompt_digest=prompt_digest, system_digest=system_digest,
            request_digest=request_digest,
            transport_succeeded=True,
            semantic_call_id=semantic_call_id,
            owner_loop_id=owner_loop_id,
            gateway_loop_id=parsed.session_id or "opencode")
        self.results.append(result)
        if not ok:
            raise OpenCodeStepError(
                "OpenCode returned no assistant text for this step; "
                f"{parsed.event_count} events, stderr: {stderr_tail}")
        return text

    @staticmethod
    def _text_of(parsed) -> str:
        """Prefer the parser's final JSON object; fall back to raw text.

        The engine's step contract is a JSON object. Returning the parsed
        object re-serialized, rather than the whole visible transcript,
        keeps an OpenCode step's return shape identical to the gateway's
        and spares the caller re-finding the object in prose.
        """
        if isinstance(parsed.final_json, dict):
            return json.dumps(parsed.final_json, separators=(",", ":"))
        fenced = _unfenced_json(parsed.texts)
        if fenced is not None:
            return json.dumps(fenced, separators=(",", ":"))
        return "\n".join(parsed.texts).strip()

    @staticmethod
    def _sum_tokens(parsed, attribute: str):
        total = 0
        seen = False
        for call in parsed.model_calls:
            value = getattr(call, attribute, None)
            if isinstance(value, int) and not isinstance(value, bool):
                total += value
                seen = True
        return total if seen else None


def self_test() -> dict:
    """Exercise budget, parsing, projection and refusal with no process."""
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
    argv = profile.command("hello")
    # The message comes immediately after `run`, not last: `--file` is an
    # array flag, so a trailing positional is consumed as another filename
    # and OpenCode exits with "File not found: <the whole message>".
    check("command_is_headless_json_and_pure",
          "--format" in argv and "json" in argv and "--pure" in argv
          and tuple(argv[:3]) == (profile.binary, "run", "hello")
          and "-m" in argv,
          " ".join(argv))

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

    def fixture_transport(_profile, _message):
        return _FIXTURE_EVENTS, ""

    session = OpenCodeStepSession(
        authority=_Authority(), profile=profile, transport=fixture_transport)
    text = session.invoke(_Request(), None)
    check("step_returns_the_final_json_object",
          json.loads(text).get("summary") == "implemented clamp", text[:90])
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

    return {"module": "core.opencode_step_session", "tests": tests,
            "passed": all(item["passed"] for item in tests)}
