"""Model response text: safe final-answer separation for served models.

Some served models — notably reasoning-tuned small models — begin their
generation with a private ``<think>`` block. Raw hidden reasoning is
transient parsing input only: it never becomes stored output, Learned
Intelligence, prompt history, public playback content, or ordinary logs.
This module owns the one split point: it returns the safe final answer and
whether reasoning content was present, so callers can record the fact
without persisting the content.
"""
from __future__ import annotations


def extract_final_answer(text: str) -> tuple[str, bool]:
    """Return (final answer, reasoning-was-present) for one response.

    A leading ``<think>...</think>`` block is stripped. An unterminated
    think block yields no safe final answer at all — guessing where private
    reasoning ends would be fabrication.
    """
    stripped = (text or "").strip()
    if stripped.startswith("<think>"):
        end = stripped.find("</think>")
        if end != -1:
            final = stripped[end + len("</think>"):].strip()
            return final, True
        return "", True
    return stripped, False


def self_test() -> dict:
    """Prove the split is exact, flagged, and fail-closed when unterminated."""
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "note": note})

    final, had_reasoning = extract_final_answer(
        "<think>scratch that never stores</think>the safe answer")
    check("think_block_is_stripped_and_flagged",
          final == "the safe answer" and had_reasoning is True,
          "private reasoning is removed; presence is still recorded")
    plain, plain_reasoning = extract_final_answer("  just the answer  ")
    check("plain_answer_passes_through_unflagged",
          plain == "just the answer" and plain_reasoning is False,
          "responses without reasoning are untouched")
    unterminated, unterminated_flag = extract_final_answer(
        "<think>runaway reasoning without a close")
    check("unterminated_think_block_yields_no_final_answer",
          unterminated == "" and unterminated_flag is True,
          "no safe answer can be guessed from an unterminated block")
    empty, empty_flag = extract_final_answer("")
    check("empty_response_is_safe",
          empty == "" and empty_flag is False)
    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
