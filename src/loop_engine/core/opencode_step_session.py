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

PROMPT FILE AND BUDGET, STATED ONCE
The prompt travels in a file created exclusively (no existing path is
followed, a leftover is unlinked first) at mode 0600, and the file is
removed once the process returns unless the profile asks to keep it. A
profile with no workspace writes into a private temporary directory;
argv carries the prompt only when ``prompt_via_file`` is switched off by
name. One ``opencode run`` decides its own number of model turns, so a
ceiling can only be checked after it returns: what ran is charged in
full, and a run that crossed ``max_model_calls`` (or the gateway config's
``max_total_tokens``) is recorded with ``budget_overrun`` and refused.

OFFLINE BY CONSTRUCTION
``transport`` is injectable, so ``self_test`` exercises the whole path --
budget, parsing, result projection, refusal -- against the adapter's own
recorded fixture events with no process, no network and no provider call.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import signal
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

from .model_gateway import GatewayAttempt, ModelGatewayResult
from .opencode_harness_adapter import parse_opencode_events
from .observation_expectations import (
    ObservationBinding, ObservationExpectation, assess_observation)

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

#: Prefix of the private 0700 directory a step with no workspace writes its
#: prompt into. Made per step by mkdtemp and removed together with the file.
PRIVATE_PROMPT_DIRECTORY_PREFIX = "opencode-step-prompt-"

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
    #: Default on. `False` restores argv for a caller that needs it, and is
    #: the only way the prompt reaches argv: a profile with no workspace
    #: writes the file into a private temporary directory rather than
    #: falling back to argv on its own.
    prompt_via_file: bool = True
    #: The prompt file is removed once the process returns. A caller who
    #: wants to read it afterwards says so here; nothing keeps it by accident.
    keep_prompt_file: bool = False

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
        if (type(self.timeout_seconds) not in (int, float)
                or not math.isfinite(self.timeout_seconds)
                or self.timeout_seconds <= 0):
            raise OpenCodeStepError("timeout_seconds must be a positive number")
        for name in ("pure", "requires_trusted_workspace", "prompt_via_file",
                     "keep_prompt_file"):
            if type(getattr(self, name)) is not bool:
                raise OpenCodeStepError(f"{name} must be a Boolean")

    def environment(self) -> dict:
        """Build the separate process environment from nothing, by allowlist."""
        names = tuple(INHERITABLE_ENVIRONMENT) + tuple(
            self.additional_environment)
        env = {name: os.environ[name] for name in names if name in os.environ}
        if self.config_directory is not None:
            env["OPENCODE_CONFIG_DIR"] = str(self.config_directory)
        return env

    def prompt_file_path(self, directory=None) -> "Path | None":
        """Where this profile's prompt file goes, or None for argv transport.

        Without a workspace the directory is chosen when the step runs (a
        private temporary directory), so only the file's name is known here.
        """
        if not self.prompt_via_file:
            return None
        base = directory if directory is not None else self.workspace
        if base is None:
            return Path(PROMPT_FILE_NAME)
        return Path(base) / PROMPT_FILE_NAME

    def command(self, message: str, prompt_file: "Path | None" = None
                ) -> tuple:
        """The exact argument vector, so a caller can log or review it.

        With ``prompt_file`` the message is a constant pointer and the real
        text rides in the file, so argv is both unbounded and uninteresting
        to anyone reading `ps`. With no ``prompt_file`` the profile's own
        transport decides, so what a caller reviews is what runs: only
        ``prompt_via_file=False`` puts the message itself in argv.
        """
        if prompt_file is None:
            prompt_file = self.prompt_file_path()
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


def _write_prompt_file(profile: OpenCodeStepProfile, message: str,
                       directory=None) -> "Path | None":
    """Write the prompt where only this user can read it.

    Whatever already sits at the name is unlinked first: a stale file, or a
    symlink someone planted, and unlinking removes a link rather than its
    target. The file is then created O_EXCL|O_NOFOLLOW at 0600 and fchmod'd
    to 0600, so neither a leftover mode nor the umask can widen it. A
    profile with no workspace gets a private 0700 temporary directory (the
    caller owns it); argv is used only when ``prompt_via_file`` is off.
    """
    if not profile.prompt_via_file:
        return None
    if directory is None and profile.workspace is None:
        directory = tempfile.mkdtemp(prefix=PRIVATE_PROMPT_DIRECTORY_PREFIX)
    target = profile.prompt_file_path(directory)
    target.parent.mkdir(parents=True, exist_ok=True)
    if os.path.lexists(target):
        if os.path.isdir(target) and not os.path.islink(target):
            raise OpenCodeStepError(
                f"{target} is a directory; refusing to write the prompt over it")
        os.unlink(target)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        handle = os.open(str(target), flags, 0o600)
    except FileExistsError as exc:
        raise OpenCodeStepError(
            f"{target} reappeared between unlink and create; refusing to "
            "write the prompt through whatever put it there") from exc
    if hasattr(os, "fchmod"):
        os.fchmod(handle, 0o600)
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        stream.write(message)
    return target


def _discard_prompt_file(profile: OpenCodeStepProfile, prompt_file,
                         private_directory=None) -> bool:
    """Remove the prompt file once the process has returned.

    ``keep_prompt_file`` leaves it in place for a caller who wants to read
    it afterwards. A private directory made for a workspace-less step goes
    with its file; a workspace is never touched beyond that one name.
    """
    if prompt_file is None or profile.keep_prompt_file:
        return False
    try:
        os.unlink(prompt_file)
    except OSError:
        pass
    if private_directory is not None:
        shutil.rmtree(private_directory, ignore_errors=True)
    return True


class TransportResult(tuple):
    """``(stdout lines, stderr tail)`` plus the argv that actually ran.

    A two-tuple, so every caller that unpacks two names keeps working; the
    executed vector rides as an attribute for the session's request digest.
    """

    def __new__(cls, lines, stderr_tail, argv=(), returncode=0):
        made = super().__new__(cls, (tuple(lines), str(stderr_tail)))
        made.argv = tuple(str(part) for part in argv)
        made.returncode = returncode
        return made


def subprocess_transport(profile: OpenCodeStepProfile, message: str) -> tuple:
    """Run one headless OpenCode turn; return (stdout lines, stderr tail)."""
    size = len(message.encode("utf-8"))
    if not profile.prompt_via_file and size > MAX_ARGV_ELEMENT_BYTES:
        # Decided before anything is resolved or launched: the refusal is
        # about the prompt, so a machine with no harness installed (CI)
        # reaches it too, rather than a missing-binary error first.
        raise OpenCodeStepError(
            f"the prompt is {size:,} bytes and argv caps a single "
            f"element at {MAX_ARGV_ELEMENT_BYTES:,}; enable prompt_via_file "
            "rather than letting the exec fail with E2BIG")
    binary = shutil.which(profile.binary)
    if binary is None:
        raise OpenCodeStepError(
            f"OpenCode binary {profile.binary!r} is not on PATH; install it "
            "or name an absolute path in the profile")
    private_directory = None
    if profile.prompt_via_file:
        # Each invocation owns a private directory, including when sessions
        # share one workspace. Never unlink a user's workspace prompt file
        # or let concurrent sessions replace each other's instructions.
        private_directory = tempfile.mkdtemp(
            prefix=PRIVATE_PROMPT_DIRECTORY_PREFIX,
            dir=str(profile.workspace) if profile.workspace else None)
    prompt_file = _write_prompt_file(profile, message, private_directory)
    try:
        argv = list(profile.command(message, prompt_file))
        argv[0] = binary
        try:
            process = subprocess.Popen(
                argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                env=profile.environment(), start_new_session=True,
                cwd=str(profile.workspace) if profile.workspace else None)
            try:
                stdout, stderr = process.communicate(timeout=profile.timeout_seconds)
                completed = subprocess.CompletedProcess(
                    argv, process.returncode, stdout, stderr)
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.communicate()
        except subprocess.TimeoutExpired as exc:
            raise OpenCodeStepError(
                f"OpenCode step exceeded {profile.timeout_seconds}s") from exc
        except OSError as exc:
            raise OpenCodeStepError(
                f"OpenCode step could not start: {exc}") from exc
        if completed.returncode != 0 and not completed.stdout.strip():
            tail = (completed.stderr or "").strip()[-400:]
            raise OpenCodeStepError(
                f"OpenCode exited {completed.returncode} with no events: {tail}")
        return TransportResult(completed.stdout.splitlines(),
                               (completed.stderr or "")[-400:], argv,
                               completed.returncode)
    finally:
        _discard_prompt_file(profile, prompt_file, private_directory)


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
    # An earlier valid object must never replace an invalid final answer.
    for text in list(texts)[-1:]:
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
class OpenCodeStepResult(ModelGatewayResult):
    """A gateway result plus the ceiling one OpenCode run crossed, if any.

    ``budget_overrun`` is None on a step within authority. Otherwise it
    names the ceiling (model_calls or total_tokens), what was charged before
    and after the run, and the refusal, so the run record shows where
    authority was exceeded instead of a bare failed step.
    """

    budget_overrun: "dict | None" = None
    model_call_accounting_complete: bool = True

    @property
    def physical_model_calls(self):
        if not self.model_call_accounting_complete:
            return None
        return super().physical_model_calls

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["budget_overrun"] = self.budget_overrun
        data["model_call_accounting_complete"] = self.model_call_accounting_complete
        return data


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

    def _max_tokens(self):
        """The gateway config's total-token ceiling, when the authority has one."""
        ceiling = getattr(getattr(self.authority, "config", None),
                          "max_total_tokens", None)
        if isinstance(ceiling, int) and not isinstance(ceiling, bool) and ceiling > 0:
            return ceiling
        return None

    def _budget_overrun(self, calls_before: int, tokens_before: int,
                        calls_in_step: int) -> "dict | None":
        """Name the ceiling one OpenCode run crossed, or None.

        How many model turns a run makes is decided inside OpenCode, so a
        ceiling can only be checked after the process returns. What ran is
        charged in full and the step is refused: the honest reading of an
        authority that was exceeded, neither a refund nor a quiet overshoot.
        """
        maximum = self._max_calls()
        if maximum is not None and self._calls_charged > maximum:
            return {"kind": "model_calls", "ceiling": maximum,
                    "charged_before_step": calls_before,
                    "calls_in_step": calls_in_step,
                    "charged": self._calls_charged,
                    "message": (
                        f"one OpenCode run made {calls_in_step} model calls "
                        "and pushed the whole-Solution count to "
                        f"{self._calls_charged}/{maximum}; the calls are "
                        "charged and the step is refused")}
        ceiling = self._max_tokens()
        if (ceiling is not None and not self._accounting_uncertain
                and self._tokens_charged > ceiling):
            return {"kind": "total_tokens", "ceiling": ceiling,
                    "charged_before_step": tokens_before,
                    "calls_in_step": calls_in_step,
                    "charged": self._tokens_charged,
                    "message": (
                        "one OpenCode run pushed the whole-Solution token "
                        f"total to {self._tokens_charged}/{ceiling}; the "
                        "tokens are charged and the step is refused")}
        return None

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
        expected = self._validate_request(request)
        maximum = self._max_calls()
        if maximum is not None and self._accounting_uncertain:
            raise OpenCodeStepError(
                "model-call accounting is incomplete; a finite ceiling "
                "cannot authorize another native run")
        if maximum is not None and self.calls_used >= maximum:
            raise OpenCodeStepError(
                "whole-Solution model-call budget exhausted: "
                f"{self.calls_used}/{maximum}")
        token_ceiling = self._max_tokens()
        if token_ceiling is not None:
            if self._accounting_uncertain:
                raise OpenCodeStepError(
                    "token accounting is incomplete after a run that reported "
                    "no step_finish; the declared total-token ceiling cannot "
                    "be enforced, so no further step starts")
            if self._tokens_charged >= token_ceiling:
                raise OpenCodeStepError(
                    "whole-Solution total-token budget exhausted: "
                    f"{self._tokens_charged}/{token_ceiling}")
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
        # provider_request_digest is computed after the transport returns,
        # over the argv that actually ran plus the prompt bytes it pointed
        # at, which is this session's provider request.
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
        try:
            outcome = self.transport(self.profile, message)
        except Exception as exc:
            # A transport exception may occur after spending or a native
            # effect. Preserve an unknown outcome, never a free retry.
            self._accounting_uncertain = True
            self._calls_charged += 1
            self.results.append(OpenCodeStepResult(
                ok=False, provider=provider, model=model_id,
                error_code="opencode_transport_unknown",
                error="native transport failed; outcome and usage unknown",
                semantic_call_id=semantic_call_id, owner_loop_id=owner_loop_id,
                prompt_digest=prompt_digest, system_digest=system_digest,
                request_digest=request_digest, transport_succeeded=None,
                model_call_accounting_complete=False))
            raise OpenCodeStepError(
                "native transport failed; outcome and usage unknown") from exc
        lines, stderr_tail = outcome[0], outcome[1]
        # A fixture transport reports no argv; then the profile's own
        # rendering stands in, which is the vector the real transport builds.
        ran = (tuple(getattr(outcome, "argv", ()) or ())
               or self.profile.command(message))
        provider_request_digest = hashlib.sha256(
            b"\0".join(str(part).encode("utf-8") for part in ran)
            + b"\0\0" + message.encode("utf-8")).hexdigest()
        parsed = parse_opencode_events(
            lines, provider_id=provider, model_id=model_id)
        calls_before, tokens_before = self._calls_charged, self._tokens_charged
        calls_in_step = len(parsed.model_calls)
        # No step_finish means the call count is a floor and the token total
        # is unknown; say so rather than report a smaller number as the truth.
        if calls_in_step == 0:
            self._accounting_uncertain = True
        self._calls_charged += max(1, calls_in_step)
        input_tokens = self._sum_tokens(parsed, "input_tokens")
        output_tokens = self._sum_tokens(parsed, "output_tokens")
        if input_tokens is None or output_tokens is None:
            self._accounting_uncertain = True
        else:
            self._tokens_charged += input_tokens + output_tokens
        overrun = self._budget_overrun(calls_before, tokens_before, calls_in_step)
        text = self._text_of(parsed)
        responded = bool(text.strip())
        compatible = None
        assessments = ()
        if expected is not None:
            try:
                assessment = assess_observation(expected, ObservationBinding(
                    semantic_call_id, request.exact_input_digest, text))
                compatible = assessment.handoff_ready
                assessments = (assessment,)
            except (ValueError, TypeError):
                compatible = False
        validator = getattr(self.authority, "validator", None)
        if validator is not None:
            try:
                valid = validator(text) is True
            except Exception:
                valid = False
            compatible = valid and compatible is not False
        process_ok = (getattr(outcome, "returncode", 0) == 0
                      and "error" not in parsed.unmapped_types)
        if not process_ok:
            self._accounting_uncertain = True
        ok = responded and process_ok and compatible is not False and overrun is None
        error_code = ("budget_overrun" if overrun is not None else
                      "opencode_process_failed" if not process_ok else
                      "response_contract_mismatch" if compatible is False else
                      "" if ok else "opencode_no_text")
        attempts = [GatewayAttempt(
            provider, model_id, f"opencode.{provider}",
            parsed.session_id or "opencode", ok,
            getattr(call, "input_tokens", None),
            getattr(call, "output_tokens", None), compatible,
            provider_ok=responded, response_received=responded,
            semantic_call_id=semantic_call_id, owner_loop_id=owner_loop_id,
            prompt_digest=prompt_digest, system_digest=system_digest,
            provider_request_digest=provider_request_digest,
            transport_succeeded=process_ok, error_code=error_code)
            for call in parsed.model_calls]
        result = OpenCodeStepResult(
            ok=ok, text=text, provider=provider, model=model_id,
            route=f"opencode.{provider}",
            input_tokens=input_tokens, output_tokens=output_tokens,
            attempts=attempts, error_code=error_code,
            error=("" if ok else overrun["message"] if overrun is not None
                   else error_code),
            prompt_digest=prompt_digest, system_digest=system_digest,
            request_digest=request_digest,
            transport_succeeded=process_ok,
            semantic_call_id=semantic_call_id,
            owner_loop_id=owner_loop_id,
            gateway_loop_id=parsed.session_id or "opencode",
            budget_overrun=overrun, response_admissions=assessments,
            model_call_accounting_complete=calls_in_step > 0 and process_ok)
        self.results.append(result)
        if overrun is not None:
            raise OpenCodeStepError(overrun["message"])
        if not ok:
            raise OpenCodeStepError(f"OpenCode step refused: {error_code}")
        return text

    def _validate_request(self, request):
        """Apply supported contract fields and refuse every unsupported one.

        This native command path is not the complete gateway. In particular,
        it has no reviewed per-request system-role or generation-setting
        binding. Even a default-valued explicit setting must not disappear.
        """
        unsupported = [name for name in (
            "system", "output_allocation", "response_admission_policy",
            "harness_selection_scope", "response_evaluation_ref")
            if getattr(request, name, None)]
        if getattr(request, "temperature", None) is not None:
            unsupported.append("temperature")
        requested_model = getattr(request, "model", "")
        if requested_model and requested_model not in (
                self.profile.model, self.profile.model.partition("/")[2]):
            unsupported.append("model override")
        if unsupported:
            raise OpenCodeStepError(
                "OpenCode native session cannot bind these request fields: "
                + ", ".join(unsupported) + "; use the canonical gateway")
        expected = getattr(request, "response_expectation", None)
        if expected is not None and (
                not isinstance(expected, ObservationExpectation)
                or expected.operation_id != getattr(request, "semantic_call_id", "")
                or expected.input_digest != hashlib.sha256(json.dumps(
                    {"prompt": request.prompt, "system": ""}, sort_keys=True,
                    separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
                or expected.input_digest != getattr(request, "exact_input_digest", "")
                or expected.semantic_questions):
            raise OpenCodeStepError("response expectation must bind the exact request")
        return expected

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
        if not parsed.model_calls:
            return None
        for call in parsed.model_calls:
            value = getattr(call, attribute, None)
            if type(value) is not int or value < 0:
                return None
            total += value
        return total


def self_test() -> dict:
    """Run the separately housed offline session checks."""
    from .opencode_step_session_checks import run_checks

    return run_checks()
