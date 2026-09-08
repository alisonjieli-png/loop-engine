"""Turn the catalogue into a recommendation for one situation.

Thirty folders is a menu, not an answer. This asks about the situation and
names one embodiment per axis, with the reason and the measurement the reason
rests on, plus what it would have chosen instead and what would change the
answer.

Every rule cites evidence from a manifest rather than a preference, and every
identifier a rule can return is checked against what is on disk, so a rule
cannot outlive the folder it recommends. Run `--explain` to see the whole rule
table rather than one path through it.

    python3 choose.py --units 5000 --workers 8 --untrusted-steps --stakes high
    python3 choose.py --units 40 --repeats --explain
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import registry

#: Each rule: (predicate over the situation, embodiment id, why, evidence).
#: The order matters; the first matching rule wins, so put the sharpest
#: conditions first and the fallback last.
RULES = {
 "context-transport": [
  (lambda s: s["units"] * 120 < s["window"] * 0.5,
   "context-transport/01-monolith",
   "the whole input fits the window with room to spare, so steps buy nothing",
   "grows about 117 bytes per unit; the wall sat between 128 and 256 units at "
   "a 16,000-byte window"),
  (lambda s: s["rare_deep_lookups"],
   "context-transport/08-hybrid-push-pull",
   "most steps need the same small state and a few need something rare",
   "cheapest arm at every horizon measured, 951 bytes at 256 units, and the "
   "fetch path is only paid when used"),
  (lambda s: s["needs_raw_recent"],
   "context-transport/07-summarised-history",
   "the task needs recent detail verbatim and a state schema would lose it",
   "flat at 1,474 bytes to 256 units, with the tail budget rather than the "
   "horizon setting the peak"),
  (lambda s: True,
   "context-transport/06-bounded-state",
   "no field grows with the horizon, so there is no wall to reach",
   "949 bytes at 4 units and 986 at 1,024; one tenth the total bytes of the "
   "state arm for identical answers"),
 ],
 "control-flow": [
  (lambda s: s["order_depends_on_content"],
   "control-flow/02-model-chosen-next",
   "the order genuinely depends on what a unit contained",
   "costs a list proportional to the horizon: 10,085 bytes at 1,024 units "
   "against 967 for a cursor, so this is a real price for real flexibility"),
  (lambda s: s["fixed_prompt_size_required"],
   "control-flow/03-fixed-batch",
   "an auditable, fixed prompt size per call is required",
   "32 units cost 32 calls at K=1 and 2 calls at K=16; you own the tuning"),
  (lambda s: True,
   "control-flow/04-adaptive-batch",
   "it finds the batch size without being told the window",
   "1,024 units in 22 calls and 138,096 bytes, against 1,025 calls and "
   "981,450 bytes one at a time; a refusal is recoverable, not fatal"),
 ],
 "execution-placement": [
  (lambda s: s["untrusted_steps"],
   "execution-placement/03-container-per-step",
   "the step body is generated or untrusted and must fail closed",
   "about 1,400 ms per step against 0.1 ms in process, so spend it on the "
   "steps that need it rather than on all of them"),
  (lambda s: s["needs_real_boundary"],
   "execution-placement/02-subprocess-per-step",
   "you want a real boundary without paying for containment",
   "about 194 ms per step; a memory boundary only, same filesystem and "
   "network and user"),
  (lambda s: True,
   "execution-placement/01-in-process",
   "the step body is your own trusted code",
   "0.1 ms per step, and nothing to contain"),
 ],
 "verification": [
  (lambda s: s["stakes"] == "high",
   "verification/03-independent-recompute",
   "something acts on the answer without a person reading it",
   "caught 5 of 5 injected faults including the one consistent with itself; "
   "cost 96 reads to check 5 runs"),
  (lambda s: s["stakes"] == "low",
   "verification/02-engine-gate",
   "a free check that is strictly better than none",
   "caught 4 of 5 for no extra reads; missed only the fault that agreed with "
   "itself at every level"),
  (lambda s: True,
   "verification/02-engine-gate",
   "the default worth having when recomputation is too expensive",
   "caught 4 of 5 for no extra reads"),
 ],
 "memory": [
  (lambda s: s["repeats"] and s["multi_writer"],
   "memory/04-governed-journal",
   "runs repeat and more than one thing can write",
   "reached 0 calls on a repeat and refused an outsider's staged answer, "
   "where the plain cache served it and answered wrongly"),
  (lambda s: s["repeats"],
   "memory/03-cross-run-cache",
   "runs repeat and the store is trusted end to end",
   "0 calls on a repeat, but it bought only one call over a checkpoint store "
   "and paid with total exposure; prefer the journal if that is available"),
  (lambda s: s["long_runs"],
   "memory/02-checkpoint-resume",
   "runs are long and interruption is normal",
   "1 call on a repeat against a 17-call cold run, and nothing to poison "
   "because conclusions are never stored"),
  (lambda s: True,
   "memory/01-none",
   "nothing repeats, and reproducibility from inputs alone is worth more",
   "the only design with nothing to poison"),
 ],
 "failure-handling": [
  (lambda s: s["partial_results_useful"],
   "failure-handling/04-skip-and-continue",
   "a partial answer has value and the caller can read what was lost",
   "the only policy that finished a run containing an unfixable failure, and "
   "the answer was wrong; pair it with independent recompute"),
  (lambda s: s["failures_are_transient_only"],
   "failure-handling/02-retry-same",
   "every failure you see clears on its own",
   "recovered 3 of 4 shapes; lost only the one caused by the request itself"),
  (lambda s: True,
   "failure-handling/03-retry-with-escalation",
   "failures have more than one cause and some are request-shaped",
   "recovered 4 of 4 recoverable shapes and spent zero escalations on the "
   "ones a plain retry already fixed"),
 ],
 "decomposition": [
  (lambda s: s["no_single_design_covers_range"],
   "decomposition/04-portfolio",
   "no one design covers the input range you actually see",
   "answered correctly at 256 units where two of its three candidates hit "
   "their horizon, and refuses rather than publishing the least bad one"),
  (lambda s: s["workers"] > 1 and s["units_vary"],
   "decomposition/03-recursive-split",
   "workers are available and input size varies between runs",
   "32 times the parallelism for 12 percent more calls at 256 units, because "
   "the threshold sizes a piece of work rather than counting workers"),
  (lambda s: s["workers"] > 1,
   "decomposition/02-fixed-split",
   "workers are available and you know how many",
   "cut serial depth to the group count for 3 extra calls; the ratio stays at "
   "the group count whatever the input size"),
  (lambda s: True,
   "decomposition/01-single-pass",
   "one worker, or strictly ordered work",
   "fewest total calls of any arm, because nothing pays a per-group final "
   "call"),
 ],
}

PAIRINGS = [
 (lambda picks: picks["failure-handling"].endswith("04-skip-and-continue")
  and not picks["verification"].endswith("03-independent-recompute"),
  "skip-and-continue returns an answer for a run it could not complete. "
  "Without independent recompute beside it, that failure is invisible."),
 (lambda picks: picks["memory"].endswith("03-cross-run-cache"),
  "a cross-run cache serves whatever was written to it. If anything other "
  "than the run can write, use the governed journal instead."),
 (lambda picks: picks["decomposition"].endswith("04-portfolio")
  and picks["verification"].endswith("01-self-report"),
  "a portfolio is only as good as its checker. With self-report it publishes "
  "the first plausible answer rather than the first correct one."),
]


def situation(args) -> dict:
    return {
        "units": args.units, "window": args.window, "workers": args.workers,
        "stakes": args.stakes, "repeats": args.repeats,
        "multi_writer": args.multi_writer, "long_runs": args.long_runs,
        "untrusted_steps": args.untrusted_steps,
        "needs_real_boundary": args.needs_real_boundary,
        "order_depends_on_content": args.order_depends_on_content,
        "fixed_prompt_size_required": args.fixed_prompt_size,
        "rare_deep_lookups": args.rare_deep_lookups,
        "needs_raw_recent": args.needs_raw_recent,
        "partial_results_useful": args.partial_results_useful,
        "failures_are_transient_only": args.transient_failures_only,
        "no_single_design_covers_range": args.mixed_input_range,
        "units_vary": args.units_vary,
    }


def choose(state: dict) -> dict:
    picks = {}
    for family, rules in RULES.items():
        for index, (predicate, chosen, why, evidence) in enumerate(rules):
            if predicate(state):
                runner_up = (rules[index + 1][1]
                             if index + 1 < len(rules) else "")
                picks[family] = {"id": chosen, "why": why,
                                 "evidence": evidence, "instead": runner_up}
                break
    return picks


def check_rules_against_disk() -> list:
    """A rule that names a folder which no longer exists is a broken rule."""
    on_disk = {entry["id"] for entry in registry.discover(load_modules=False)}
    missing = []
    for family, rules in RULES.items():
        for _, chosen, _, _ in rules:
            if chosen not in on_disk:
                missing.append(f"{family}: rule names {chosen}, which is not "
                               f"on disk")
    known = {body["family"] for body in registry.families()}
    for family in RULES:
        if family not in known:
            missing.append(f"{family}: no family.json")
    for family in known:
        if family not in RULES:
            missing.append(f"{family}: has no rules, so it is never "
                           f"recommended")
    return missing


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--units", type=int, default=100,
                        help="how many units of work a run handles")
    parser.add_argument("--window", type=int, default=16000,
                        help="context window in bytes")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--stakes", choices=("low", "medium", "high"),
                        default="medium",
                        help="high means something acts on the answer without "
                             "a person reading it")
    parser.add_argument("--repeats", action="store_true",
                        help="the same task comes round again")
    parser.add_argument("--multi-writer", action="store_true",
                        help="more than one thing can write to shared memory")
    parser.add_argument("--long-runs", action="store_true",
                        help="runs are long enough that interruption is normal")
    parser.add_argument("--untrusted-steps", action="store_true",
                        help="the step body is generated or not yours")
    parser.add_argument("--needs-real-boundary", action="store_true",
                        help="steps must not share memory, but need no "
                             "containment")
    parser.add_argument("--order-depends-on-content", action="store_true")
    parser.add_argument("--fixed-prompt-size", action="store_true",
                        help="prompt size per call must be fixed and auditable")
    parser.add_argument("--rare-deep-lookups", action="store_true",
                        help="a few steps need something rare and large")
    parser.add_argument("--needs-raw-recent", action="store_true",
                        help="recent observations must stay verbatim")
    parser.add_argument("--partial-results-useful", action="store_true")
    parser.add_argument("--transient-failures-only", action="store_true")
    parser.add_argument("--mixed-input-range", action="store_true",
                        help="no single design covers the sizes you see")
    parser.add_argument("--units-vary", action="store_true",
                        help="input size changes a lot between runs")
    parser.add_argument("--explain", action="store_true",
                        help="print the whole rule table, not one path")
    parser.add_argument("--check", action="store_true",
                        help="only verify the rules against what is on disk")
    args = parser.parse_args(argv)

    broken = check_rules_against_disk()
    if broken:
        for problem in broken:
            print(f"  BROKEN RULE {problem}")
        if args.check:
            return 1
    elif args.check:
        print("choose: every rule names a folder that exists")
        return 0

    if args.explain:
        for family, rules in RULES.items():
            print(f"\n{family}")
            for _, chosen, why, evidence in rules:
                print(f"  {chosen.split('/')[-1]:26s} when {why}")
                print(f"  {'':26s}      {evidence}")
        return 0

    picks = choose(situation(args))
    print("\nFor this situation:\n")
    for family, pick in picks.items():
        print(f"  {family:22s} {pick['id'].split('/')[-1]}")
        print(f"  {'':22s} because {pick['why']}")
        print(f"  {'':22s} measured: {pick['evidence']}")
        if pick["instead"]:
            print(f"  {'':22s} otherwise: {pick['instead'].split('/')[-1]}")
        print()
    warnings = [note for predicate, note in PAIRINGS
                if predicate({key: value["id"] for key, value in picks.items()})]
    if warnings:
        print("Read these together:\n")
        for note in warnings:
            print(f"  - {note}")
        print()
    print("Each line links to a folder with the full argument for and against.")
    print("Run `python3 registry.py run --family <name>` to re-measure any of "
          "it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
