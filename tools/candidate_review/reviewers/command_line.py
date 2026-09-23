"""Reviewer engine ``command_line``: a coding harness's own command line, run once with no tools.

Two output protocols are read exactly:

- ``codex_exec_jsonl``: ``codex exec --json`` prints one JSON event per line.
  The answer is the last completed agent message, and the usage is the
  completed turn's usage as the command line reported it. With its tools
  switched off by the installation's arguments, one turn is one model response;
  retries inside the command line are not visible, which the call record says.
  This qualified event subset does not report the answering model, so a
  completed response cannot count as a reviewer verdict. Requested identity
  is never substituted for missing reported identity.
- ``claude_print_json``: ``claude -p --output-format json`` prints one JSON
  result with the answer, the usage and the models used. A result that used no
  model (for example a refused login) records zero physical calls.

The prompt travels on standard input and never on the command line, where other
processes could read it. The command runs in an empty temporary folder that is
removed afterwards, with a timeout. The command line adds its own instructions
to every request, so an installation declares ``reserved_overhead_tokens`` and
the panel reserves them against the token ceiling before the call. Arguments
are a declared list with two named placeholders, ``{model}`` and ``{workdir}``,
substituted only as whole tokens. The command reads its own credentials from
its own configuration; this engine never reads, passes or records them.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from ..configuration import thawed
from ..records import positive_number, read_part, refuse, text_field
from ..verdicts import JSON_ONLY
from . import (
    ANSWERED, AUTHENTICATION_UNAVAILABLE, COMMAND_LINE_REPORTED, CONTEXT_WINDOW_EXCEEDED, ENGINE_UNAVAILABLE,
    MODEL_IDENTITY_MISMATCH, MODEL_NOT_FOUND, PROVIDER_FAILED, PROVIDER_UNAVAILABLE, RATE_LIMITED, TIMEOUT,
    UNKNOWN_USAGE, USAGE_LIMIT_REACHED, Availability, ReviewerAttempt, Usage, failed,
)

SETTINGS_FIELDS = ("program", "arguments", "version_arguments", "output_protocol", "timeout_seconds",
                   "reserved_overhead_tokens")
MODEL_PLACEHOLDER, WORKDIR_PLACEHOLDER = "{model}", "{workdir}"
PLACEHOLDERS = (MODEL_PLACEHOLDER, WORKDIR_PLACEHOLDER)
CODEX_PROTOCOL, CLAUDE_PROTOCOL = "codex_exec_jsonl", "claude_print_json"
VERSION_TIMEOUT_SECONDS = 30.0
ONE_TURN = "one completed turn reported by the command line; retries inside it are not visible"
NO_MODEL_USED = "the command line reports that no model was used"
CODEX_MODEL_UNREPORTED = "the codex_exec_jsonl protocol does not report the answering model"
#: Words in a command line's error text, checked in this order, and the outcome each one names.
ERROR_WORDS = (
    (USAGE_LIMIT_REACHED, ("usage limit", "quota", "insufficient_quota", "out of credits", "credit balance")),
    (RATE_LIMITED, ("429", "rate limit", "rate_limit", "too many requests")),
    (AUTHENTICATION_UNAVAILABLE, ("401", "403", "unauthorized", "not logged in", "log in", "login",
                                  "authentication", "invalid api key", "invalid_api_key")),
    (CONTEXT_WINDOW_EXCEEDED, ("context window", "context length", "context_length", "prompt is too long")),
    (PROVIDER_UNAVAILABLE, ("overloaded", "502", "503", "service unavailable", "temporarily unavailable")),
)


def classify(text: str) -> str:
    low = text.casefold()
    if "model" in low and any(words in low for words in ("not found", "does not exist", "not supported")):
        return MODEL_NOT_FOUND
    for outcome, words in ERROR_WORDS:
        if any(word in low for word in words):
            return outcome
    return PROVIDER_FAILED


def _count(value) -> "int | None":
    return value if type(value) is int and value >= 0 else None


def read_codex(stdout: str, stderr: str, returncode: int, installation, command: str,
               elapsed: float) -> ReviewerAttempt:
    events = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if type(event) is dict:
            events.append(event)
    answers = [event["item"].get("text") for event in events if event.get("type") == "item.completed"
               and type(event.get("item")) is dict and event["item"].get("type") == "agent_message"]
    usages = [event["usage"] for event in events if event.get("type") == "turn.completed"
              and type(event.get("usage")) is dict]
    errors = [str(event.get("message") or "") for event in events if event.get("type") == "error"]
    errors += [str((event.get("error") or {}).get("message") or "") for event in events
               if event.get("type") == "turn.failed" and type(event.get("error")) is dict]
    usage = UNKNOWN_USAGE
    if usages:
        reported = usages[-1]
        usage = Usage(_count(reported.get("input_tokens")), _count(reported.get("output_tokens")),
                      _count(reported.get("reasoning_output_tokens")), _count(reported.get("cached_input_tokens")),
                      COMMAND_LINE_REPORTED)
    text = answers[-1] if answers and type(answers[-1]) is str else ""
    if returncode == 0 and text.strip() and usages and not errors:
        return ReviewerAttempt(MODEL_IDENTITY_MISMATCH, "", usage, 1, elapsed, None, "", command,
                               CODEX_MODEL_UNREPORTED, ONE_TURN)
    detail = " ".join(errors + [stderr]).strip() or f"the command exited with {returncode} and no answer"
    return failed(classify(detail), command, detail[:300], physical_model_calls=1 if usages else None,
                  elapsed_seconds=elapsed, usage=usage)


def read_claude(stdout: str, stderr: str, returncode: int, installation, command: str,
                elapsed: float) -> ReviewerAttempt:
    try:
        value = json.loads(stdout.strip().splitlines()[-1]) if stdout.strip() else None
    except ValueError:
        value = None
    if type(value) is not dict:
        detail = stderr.strip() or f"the command exited with {returncode} and printed no result"
        return failed(classify(detail), command, detail[:300], physical_model_calls=None, elapsed_seconds=elapsed)
    models = value.get("modelUsage") if type(value.get("modelUsage")) is dict else {}
    no_model = not models and value.get("duration_api_ms") == 0
    reported = value.get("usage") if type(value.get("usage")) is dict else {}
    parts = [_count(reported.get(name)) for name in ("input_tokens", "cache_read_input_tokens",
                                                     "cache_creation_input_tokens")]
    details = reported.get("output_tokens_details") if type(reported.get("output_tokens_details")) is dict else {}
    usage = Usage(sum(parts) if None not in parts else None, _count(reported.get("output_tokens")),
                  _count(details.get("thinking_tokens")), parts[1], COMMAND_LINE_REPORTED) if reported \
        else UNKNOWN_USAGE
    physical = 0 if no_model else (1 if models else None)
    basis = NO_MODEL_USED if no_model else ONE_TURN
    if returncode != 0 or value.get("is_error") is not False:
        detail = str(value.get("result") or "") + " " + stderr
        return failed(classify(detail), command, detail.strip()[:300], physical_model_calls=physical,
                      elapsed_seconds=elapsed, usage=usage)
    answer = value.get("result")
    if set(models) != {installation.model}:
        return failed(MODEL_IDENTITY_MISMATCH, command, f"the command line reports the models {sorted(models)}",
                      physical_model_calls=physical, elapsed_seconds=elapsed, usage=usage,
                      reported_model=",".join(sorted(models)))
    if type(answer) is not str or not answer.strip():
        return failed(PROVIDER_FAILED, command, "the result carries no answer", physical_model_calls=physical,
                      elapsed_seconds=elapsed, usage=usage, reported_model=",".join(sorted(models)))
    return ReviewerAttempt(ANSWERED, answer, usage, physical, elapsed, None, ",".join(sorted(models)), command,
                           "", basis)


PROTOCOLS = {CODEX_PROTOCOL: read_codex, CLAUDE_PROTOCOL: read_claude}


class CommandLineReviewer:
    """One installation of a coding harness's command line, asked once per review with no tools."""

    def __init__(self, installation, policy, context) -> None:
        settings = read_part(thawed(installation.settings), installation.installation_id, SETTINGS_FIELDS)
        self.installation, self.policy = installation, policy
        self.program = text_field(settings["program"], "program", limit=1000)
        self.arguments = self._arguments(settings["arguments"], PLACEHOLDERS)
        self.version_arguments = self._arguments(settings["version_arguments"], ())
        if settings["output_protocol"] not in PROTOCOLS:
            refuse("installation_output_protocol_unknown", f"output protocols are {sorted(PROTOCOLS)}")
        self.reader = PROTOCOLS[settings["output_protocol"]]
        self.timeout_seconds = positive_number(settings["timeout_seconds"], "timeout_seconds")
        overhead = settings["reserved_overhead_tokens"]
        if type(overhead) is not int or overhead < 0:
            refuse("installation_setting_invalid", "reserved_overhead_tokens is a whole number of zero or more")
        self._availability = None
        self.answer_format, self.output_allocation_tokens = JSON_ONLY, None

    @staticmethod
    def _arguments(value, placeholders) -> tuple:
        if type(value) is not list or any(type(item) is not str for item in value):
            refuse("installation_setting_invalid", "arguments are a list of text values")
        for item in value:
            if ("{" in item or "}" in item) and item not in placeholders:
                refuse("installation_argument_unknown", f"{item!r} is not one of the placeholders {list(placeholders)}")
        return tuple(value)

    @property
    def route_or_command(self) -> str:
        return Path(self.program).name

    def _resolved(self) -> "str | None":
        if os.sep in self.program:
            path = Path(self.program)
            return str(path) if path.is_file() and os.access(path, os.X_OK) else None
        return shutil.which(self.program)

    def availability(self) -> Availability:
        if self._availability is None:
            self._availability = self._probe()
        return self._availability

    def _probe(self) -> Availability:
        executable = self._resolved()
        if executable is None:
            return Availability(False, f"the program {self.route_or_command!r} is not installed", "", {},
                                ENGINE_UNAVAILABLE)
        try:
            finished = subprocess.run([executable, *self.version_arguments], capture_output=True, text=True,
                                      timeout=VERSION_TIMEOUT_SECONDS, check=False, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError) as error:
            return Availability(False, f"the version could not be read: {type(error).__name__}", "", {},
                                ENGINE_UNAVAILABLE)
        lines = (finished.stdout or finished.stderr).strip().splitlines()
        if finished.returncode != 0 or not lines:
            return Availability(False, "the version could not be read", "", {}, ENGINE_UNAVAILABLE)
        if self.reader is read_codex:
            return Availability(False, CODEX_MODEL_UNREPORTED, lines[0][:200], {}, MODEL_IDENTITY_MISMATCH)
        return Availability(True, "", lines[0][:200], {})

    def review(self, prompt, allowance) -> ReviewerAttempt:
        executable = self._resolved()
        if executable is None:
            return failed(ENGINE_UNAVAILABLE, self.route_or_command, "the program is not installed")
        timeout = min(allowance.timeout_seconds, self.timeout_seconds)
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="review-call-") as workdir:
            substitutions = {MODEL_PLACEHOLDER: self.installation.model, WORKDIR_PLACEHOLDER: workdir}
            argv = [executable] + [substitutions.get(argument, argument) for argument in self.arguments]
            try:
                finished = subprocess.run(argv, input=prompt.system + "\n\n" + prompt.user, capture_output=True,
                                          text=True, encoding="utf-8", errors="replace", timeout=timeout,
                                          cwd=workdir, check=False)
            except subprocess.TimeoutExpired:
                return failed(TIMEOUT, self.route_or_command, f"no answer within {timeout:g} seconds",
                              physical_model_calls=None, elapsed_seconds=round(time.monotonic() - started, 3))
            except OSError as error:
                return failed(ENGINE_UNAVAILABLE, self.route_or_command, type(error).__name__)
        elapsed = round(time.monotonic() - started, 3)
        return self.reader(finished.stdout or "", finished.stderr or "", finished.returncode, self.installation,
                           self.route_or_command, elapsed)
