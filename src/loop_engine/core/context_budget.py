"""Typed context budget for the model-facing Practitioner state.

Architectural role: one passive versioned policy and one deterministic
bounding transformation. This module owns no runtime, calls no provider, reads
no file, and grants no authority. The adaptive Practitioner applies the policy
to the typed state view at the single point where that view enters an LLM work
packet, so selected source text, command output, fetched pages, generated
files, and attempt history cannot grow a prompt without bound. Every removal is
recorded with the original byte count and SHA-256 digest; the complete text
stays in Run History artifacts, so nothing is lost, only moved out of the model
channel.

Owns:
    - ContextBudgetPolicy: versioned typed limits with one canonical default.
    - bound_state_view(): deterministic deduplication and head/tail trimming
      with a typed record for every change.
    - estimate_tokens(): the same characters-over-four estimate the prompt
      assembly snapshot reports, so budgets and snapshots agree.
    - context_window_allowance(): the input allowance a route leaves after its
      requested output maximum.

Does not own: prompt layout (strings.prompt_fragments), the packet record
(core.adaptive_practitioner_records), route context limits (core.model_routes),
or the gateway preflight that refuses an oversized request (core.model_gateway).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


class ContextBudgetError(ValueError):
    """A context budget policy or bounding request was invalid."""


#: Fields whose text is live input for the current step and therefore keeps
#: the first copy when the same bytes also appear in older history.
PRIORITY_FIELDS = ("available_input_text", "files_already_generated")
#: Lists whose text-bearing items share one byte allowance per list instance.
HEAVY_LISTS = ("available_input_text", "files_already_generated",
               "web_evidence", "selected", "commands")


@dataclass(frozen=True)
class ContextBudgetPolicy:
    """Typed limits for the state view that enters a model work packet.

    Byte limits apply to text as UTF-8. Text fields keep a head and a tail;
    command output keeps its own smaller head and tail. Each heavy list
    (selected source files, available input text, generated files, fetched
    pages, one attempt's commands) shares ``list_total_bytes`` per instance;
    once spent, further text in that list keeps only a digest. Older project
    attempts and older source inspections keep digests only. Any text that
    repeats an earlier copy is replaced by a reference to the first copy. A
    ``None`` ``packet_estimated_tokens_max`` means the route context window,
    minus the requested output maximum, is the only packet ceiling.
    """

    policy_id: str = "adaptive_practitioner.context_budget"
    version: str = "1.1.0"
    text_head_bytes: int = 5_000
    text_tail_bytes: int = 1_000
    command_output_head_bytes: int = 2_000
    command_output_tail_bytes: int = 2_000
    list_total_bytes: int = 24_000
    keep_latest_attempts: int = 3
    keep_latest_inspections: int = 1
    duplicate_min_bytes: int = 512
    packet_estimated_tokens_max: "int | None" = None

    def __post_init__(self) -> None:
        for name in ("text_head_bytes", "text_tail_bytes",
                     "command_output_head_bytes", "command_output_tail_bytes",
                     "list_total_bytes", "keep_latest_attempts",
                     "keep_latest_inspections", "duplicate_min_bytes"):
            value = getattr(self, name)
            if (not isinstance(value, int) or isinstance(value, bool)
                    or value < 0):
                raise ContextBudgetError(
                    f"{name} must be a non-negative integer")
        if (self.packet_estimated_tokens_max is not None
                and (not isinstance(self.packet_estimated_tokens_max, int)
                     or isinstance(self.packet_estimated_tokens_max, bool)
                     or self.packet_estimated_tokens_max < 1)):
            raise ContextBudgetError(
                "packet_estimated_tokens_max must be a positive integer "
                "when provided")
        if not self.policy_id.strip() or not self.version.strip():
            raise ContextBudgetError("policy identity must be non-empty")

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "version": self.version,
            "text_head_bytes": self.text_head_bytes,
            "text_tail_bytes": self.text_tail_bytes,
            "command_output_head_bytes": self.command_output_head_bytes,
            "command_output_tail_bytes": self.command_output_tail_bytes,
            "list_total_bytes": self.list_total_bytes,
            "keep_latest_attempts": self.keep_latest_attempts,
            "keep_latest_inspections": self.keep_latest_inspections,
            "duplicate_min_bytes": self.duplicate_min_bytes,
            "packet_estimated_tokens_max": self.packet_estimated_tokens_max,
        }


@dataclass(frozen=True)
class ContextTrim:
    """One recorded removal of text from the model channel."""

    path: str
    original_bytes: int
    kept_bytes: int
    sha256: str
    method: str

    @property
    def removed_bytes(self) -> int:
        return max(0, self.original_bytes - self.kept_bytes)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "original_bytes": self.original_bytes,
            "kept_bytes": self.kept_bytes,
            "removed_bytes": self.removed_bytes,
            "sha256": self.sha256,
            "method": self.method,
        }


def estimate_tokens(*texts: str) -> int:
    """Characters-over-four estimate shared with the assembly snapshot."""
    total = sum(len(str(text).encode("utf-8")) for text in texts)
    return (total + 3) // 4


def context_window_allowance(
        max_context: int, maximum_output_tokens: int,
        policy: "ContextBudgetPolicy | None" = None) -> "int | None":
    """Return the input-token allowance a route leaves, or None if unknown."""
    if not max_context or max_context <= 0:
        allowance = None
    else:
        allowance = max(0, int(max_context) - int(maximum_output_tokens or 0))
    ceiling = policy.packet_estimated_tokens_max if policy else None
    if ceiling is None:
        return allowance
    if allowance is None:
        return ceiling
    return min(allowance, ceiling)


@dataclass
class _Bounder:
    policy: ContextBudgetPolicy
    trims: list = field(default_factory=list)
    seen: dict = field(default_factory=dict)
    list_budgets: dict = field(default_factory=dict)

    # --- text transformations ---------------------------------------------

    def _marker(self, kind: str, digest: str, count: int, extra: str = "") -> str:
        return (f"[context budget: {kind}; {count} bytes; sha256 {digest[:16]}"
                f"{extra}; full text in Run History artifacts]")

    def digest_only(self, text: str, path: str) -> str:
        raw = text.encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        marker = self._marker("text omitted", digest, len(raw))
        self.trims.append(ContextTrim(
            path, len(raw), len(marker.encode("utf-8")), digest,
            "digest_only"))
        return marker

    def head_tail(self, text: str, path: str, head: int, tail: int) -> str:
        raw = text.encode("utf-8")
        if len(raw) <= head + tail:
            return text
        if head + tail == 0:
            return self.digest_only(text, path)
        digest = hashlib.sha256(raw).hexdigest()
        removed = len(raw) - head - tail
        kept_head = raw[:head].decode("utf-8", errors="ignore")
        kept_tail = (raw[len(raw) - tail:].decode("utf-8", errors="ignore")
                     if tail else "")
        bounded = (kept_head
                   + f"\n[context budget: {removed} bytes trimmed here; "
                     f"sha256 {digest[:16]}; full text in Run History "
                     f"artifacts]\n"
                   + kept_tail)
        self.trims.append(ContextTrim(
            path, len(raw), len(bounded.encode("utf-8")), digest,
            "head_tail"))
        return bounded

    def text(self, text: str, path: str, *, head: int, tail: int,
             list_key: "str | None") -> str:
        raw = text.encode("utf-8")
        size = len(raw)
        if size >= self.policy.duplicate_min_bytes:
            digest = hashlib.sha256(raw).hexdigest()
            first = self.seen.get(digest)
            if first is not None and first != path:
                marker = self._marker(
                    "duplicate", digest, size, f"; same as {first}")
                self.trims.append(ContextTrim(
                    path, size, len(marker.encode("utf-8")), digest,
                    "duplicate"))
                return marker
            self.seen.setdefault(digest, path)
        if list_key is not None:
            remaining = self.list_budgets.get(
                list_key, self.policy.list_total_bytes)
            if remaining <= 0:
                return self.digest_only(text, path)
            head = min(head, remaining)
            tail = min(tail, max(0, remaining - head))
            bounded = self.head_tail(text, path, head, tail)
            self.list_budgets[list_key] = remaining - len(
                bounded.encode("utf-8"))
            return bounded
        return self.head_tail(text, path, head, tail)

    # --- structure walk ----------------------------------------------------

    def walk(self, value, path: str, *, digest_only: bool = False,
             list_key: "str | None" = None, command_output: bool = False):
        if isinstance(value, str):
            if digest_only:
                if len(value.encode("utf-8")) >= self.policy.duplicate_min_bytes:
                    return self.digest_only(value, path)
                return value
            if command_output:
                head, tail = (self.policy.command_output_head_bytes,
                              self.policy.command_output_tail_bytes)
            else:
                head, tail = (self.policy.text_head_bytes,
                              self.policy.text_tail_bytes)
            return self.text(value, path, head=head, tail=tail,
                             list_key=list_key)
        if isinstance(value, dict):
            return {
                key: self.walk(
                    item, f"{path}.{key}" if path else str(key),
                    digest_only=digest_only, list_key=list_key,
                    command_output=(command_output
                                    or key in ("stdout", "stderr")))
                for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            name = path.rsplit(".", 1)[-1]
            heavy = name in HEAVY_LISTS
            items = []
            for index, item in enumerate(value):
                item_path = f"{path}[{index}]"
                item_digest_only = digest_only
                if name == "project_attempts":
                    keep_from = max(
                        0, len(value) - self.policy.keep_latest_attempts)
                    item_digest_only = digest_only or index < keep_from
                elif name == "source_inspections":
                    keep_from = max(
                        0, len(value) - self.policy.keep_latest_inspections)
                    item_digest_only = digest_only or index < keep_from
                items.append(self.walk(
                    item, item_path, digest_only=item_digest_only,
                    list_key=(path if heavy else list_key),
                    command_output=command_output))
            return items if isinstance(value, list) else tuple(items)
        return value


def bound_state_view(view: dict, policy: ContextBudgetPolicy
                     ) -> tuple[dict, tuple[ContextTrim, ...]]:
    """Return a bounded copy of a Practitioner state view plus trim records.

    Structure, digests, exit codes, purposes, paths, and every non-text value
    are preserved exactly. Text fields are deduplicated (live-input fields
    keep the first copy), older attempts and inspections keep digests only,
    heavy lists share one byte allowance each, and any remaining long text
    keeps a head and a tail with an explicit marker.
    """
    if not isinstance(view, dict):
        raise ContextBudgetError("state view must be a mapping")
    if not isinstance(policy, ContextBudgetPolicy):
        raise ContextBudgetError("policy must be a ContextBudgetPolicy")
    bounder = _Bounder(policy)
    transformed: dict = {}
    ordered_keys = [key for key in PRIORITY_FIELDS if key in view] + [
        key for key in view if key not in PRIORITY_FIELDS]
    for key in ordered_keys:
        transformed[key] = bounder.walk(view[key], str(key))
    bounded = {key: transformed[key] for key in view}
    return bounded, tuple(bounder.trims)


def self_test() -> dict:
    """Prove bounding is deterministic, recorded, and structure-preserving."""
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    policy = ContextBudgetPolicy(
        text_head_bytes=30, text_tail_bytes=10,
        command_output_head_bytes=20, command_output_tail_bytes=10,
        list_total_bytes=120, keep_latest_attempts=1,
        keep_latest_inspections=1, duplicate_min_bytes=64)
    big = "A" * 500 + "Z" * 500
    other = "B" * 700
    view = {
        "facts": {"k": "v"},
        "available_input_text": [{"path": "train.csv", "content": big}],
        "source_inspections": [
            {"query": "old", "selected": [{"path": "train.csv",
                                           "content": big, "digest": "d"}]},
            {"query": "new", "selected": [{"path": "train.csv",
                                           "content": big, "digest": "d"},
                                          {"path": "x.csv",
                                           "content": other, "digest": "e"}]},
        ],
        "project_attempts": [
            {"manifest_digest": "d0", "commands": [
                {"purpose": "old", "ok": False, "exit_code": 1,
                 "stdout": other, "stderr": "", "error_code": "x"}]},
            {"manifest_digest": "d1", "commands": [
                {"purpose": "run", "ok": True, "exit_code": 0,
                 "stdout": other + "!", "stderr": "", "error_code": None}]},
        ],
        "web_evidence": [{"final_url": "https://example.test", "text": big}],
        "note": "short text stays",
    }
    bounded, trims = bound_state_view(view, policy)
    bounded_again, trims_again = bound_state_view(view, policy)
    live = bounded["available_input_text"][0]["content"]
    newest = bounded["source_inspections"][1]["selected"]
    oldest = bounded["source_inspections"][0]["selected"][0]["content"]
    latest_cmd = bounded["project_attempts"][1]["commands"][0]
    oldest_cmd = bounded["project_attempts"][0]["commands"][0]
    methods = {t.method for t in trims}
    check("live_input_keeps_the_first_copy_as_head_and_tail",
          live.startswith("A" * 30) and live.endswith("Z" * 10)
          and "trimmed here" in live, f"{len(live)} chars kept of 1000")
    check("repeated_source_text_becomes_a_duplicate_reference",
          "duplicate" in newest[0]["content"]
          and "available_input_text[0].content" in newest[0]["content"]
          and newest[0]["path"] == "train.csv" and newest[0]["digest"] == "d",
          "the newest inspection points at the live copy")
    check("older_inspections_keep_digests_only",
          oldest.startswith("[context budget: text omitted")
          or oldest.startswith("[context budget: duplicate"),
          oldest[:60])
    check("older_attempt_output_is_digest_only_and_newest_is_trimmed",
          oldest_cmd["stdout"].startswith("[context budget:")
          and oldest_cmd["exit_code"] == 1 and oldest_cmd["error_code"] == "x"
          and latest_cmd["stdout"].startswith("B" * 20)
          and "trimmed here" in latest_cmd["stdout"]
          and latest_cmd["exit_code"] == 0,
          "exit codes and purposes survive; text is bounded")
    check("structure_and_short_values_are_preserved",
          bounded["facts"] == {"k": "v"} and bounded["note"] == "short text stays"
          and list(bounded) == list(view)
          and bounded["web_evidence"][0]["final_url"] == "https://example.test",
          "key order and non-text values unchanged")
    check("every_removal_is_recorded_with_digest_and_method",
          len(trims) >= 5 and all(len(t.sha256) == 64 for t in trims)
          and {"head_tail", "duplicate"} <= methods
          and sum(t.removed_bytes for t in trims) > 2000,
          f"{len(trims)} trims, methods {sorted(methods)}")
    check("bounding_is_deterministic_and_does_not_mutate_input",
          bounded == bounded_again and trims == trims_again
          and view["available_input_text"][0]["content"] == big,
          "same in, same out; caller mapping untouched")
    small_view, small_trims = bound_state_view(
        {"project_attempts": [{"commands": [{"stdout": "ok", "stderr": ""}]}],
         "available_input_text": [{"content": "tiny"}]},
        ContextBudgetPolicy())
    check("small_state_passes_through_untouched",
          small_trims == () and small_view["available_input_text"][0][
              "content"] == "tiny")
    exhausted_policy = ContextBudgetPolicy(
        text_head_bytes=50, text_tail_bytes=0, list_total_bytes=60,
        duplicate_min_bytes=10_000)
    many, many_trims = bound_state_view(
        {"available_input_text": [{"content": "C" * 400},
                                  {"content": "D" * 400},
                                  {"content": "E" * 400}]}, exhausted_policy)
    check("a_heavy_list_shares_one_byte_allowance",
          "trimmed here" in many["available_input_text"][0]["content"]
          and many["available_input_text"][2]["content"].startswith(
              "[context budget: text omitted"),
          "later items keep digests once the list allowance is spent")
    check("allowance_uses_route_window_minus_output_and_operator_ceiling",
          context_window_allowance(131072, 65536) == 65536
          and context_window_allowance(0, 65536) is None
          and context_window_allowance(
              131072, 65536, ContextBudgetPolicy(
                  packet_estimated_tokens_max=20000)) == 20000
          and context_window_allowance(
              0, 0, ContextBudgetPolicy(packet_estimated_tokens_max=9)) == 9)
    check("token_estimate_matches_snapshot_rule",
          estimate_tokens("abcd" * 10) == 10 and estimate_tokens("", "a") == 1)
    invalid = False
    try:
        ContextBudgetPolicy(text_head_bytes=-1)
    except ContextBudgetError:
        invalid = True
    check("invalid_policy_fails_closed", invalid)
    passed = sum(1 for test in tests if test["passed"])
    return {"record_type": "context_budget_self_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
