"""5: A real Kaggle competition, end to end.

    python -m pip install "https://github.com/alisonjieli-png/loop-engine/archive/refs/heads/main.zip"
    # put your kaggle.json at ~/.kaggle/kaggle.json  (Account -> Create New Token)
    python3 examples/05_kaggle_competition/run.py --competition titanic

Download, solve, score locally, and optionally submit. The loop runs on the
deterministic rail by default: this whole example spends zero tokens unless
you pass --model.

The honest part, which matters more than the score: the local cross-validation
number and the leaderboard number are DIFFERENT measurements, and this prints
both without pretending either predicts the other. A local score is what your
own split told you; a leaderboard score is what held-out data told you. When
they disagree, the leaderboard is right and your split was optimistic.
"""

import argparse
import os
import subprocess
import sys
import tempfile

from loop_engine import LoopLedger
from loop_engine.code_nodes.smoke_ladder import run_smoke_loop
from loop_engine.code_nodes.loop_report import (report_from_ledger, render_text,
                                                write_report)


def download(competition, directory):
    """Uses the official kaggle CLI, so it honours your existing credentials."""
    print(f"downloading {competition} ...")
    r = subprocess.run(
        ["kaggle", "competitions", "download", "-c", competition,
         "-p", directory, "--quiet"],
        capture_output=True, text=True)
    if r.returncode != 0:
        detail = (r.stderr or r.stdout).strip()[:300]
        raise SystemExit(
            f"download failed: {detail}\n\n"
            "Common causes: no ~/.kaggle/kaggle.json, or you have not accepted "
            f"this competition's rules at\n"
            f"  https://www.kaggle.com/c/{competition}/rules")
    import zipfile
    for name in os.listdir(directory):
        if name.endswith(".zip"):
            with zipfile.ZipFile(os.path.join(directory, name)) as z:
                z.extractall(directory)
    return sorted(f for f in os.listdir(directory) if f.endswith(".csv"))


def pick_files(directory, files):
    """Resolve roles by evidence, not by assuming filenames."""
    def find(*words):
        for f in files:
            if any(w in f.lower() for w in words):
                return os.path.join(directory, f)
        return None
    train = find("train")
    test = find("test")
    sample = find("sample", "submission")
    missing = [n for n, v in (("train", train), ("test", test),
                              ("sample submission", sample)) if not v]
    if missing:
        raise SystemExit(f"could not identify: {', '.join(missing)}. "
                         f"Files present: {files}")
    return train, test, sample


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--competition", default="titanic")
    ap.add_argument("--model", action="store_true",
                    help="permit ONE model call for the research step "
                         "(needs a provider: see example 03)")
    ap.add_argument("--submit", action="store_true",
                    help="actually submit to the leaderboard")
    ap.add_argument("--report", metavar="PATH",
                    help="write an HTML loop report to PATH")
    ap.add_argument("--out", metavar="PATH",
                    help="keep the generated submission CSV at PATH")
    args = ap.parse_args()

    advise = None
    if args.model:
        from loop_engine import configure, advice_function
        access = configure()
        advise = advice_function(access)
        if advise is None:
            print(access.explain())
            raise SystemExit("--model was requested but no provider is "
                             "reachable. Refusing to run a 'model' arm that "
                             "would never reach a model.")

    with tempfile.TemporaryDirectory() as d:
        files = download(args.competition, d)
        train, test, sample = pick_files(d, files)
        out_csv = args.out or os.path.join(d, "submission.csv")
        if args.out:
            os.makedirs(os.path.dirname(os.path.abspath(args.out)),
                        exist_ok=True)
        ledger = LoopLedger()

        run_result = run_smoke_loop(
            f"solve the {args.competition} competition",
            train_csv=train, test_csv=test, sample_csv=sample,
            out_csv=out_csv, ledger=ledger,
            advice_store=None if advise else _warm_store(),
            advice_fn=advise)

        trace = run_result.get("trace", {})
        calls = trace.get("model_calls", [])
        tokens = sum(c.get("prompt_tokens", 0) + c.get("eval_tokens", 0)
                     for c in calls)

        print()
        print("=== what the loop did ===")
        print(f"  estimator     : {trace.get('estimator')}")
        print(f"  engineered    : {trace.get('engineered') or 'none'}")
        print(f"  local cv score: {trace.get('cv_score')}   "
              "<- YOUR split; not a leaderboard number")
        print(f"  model calls   : {len(calls)}  ({tokens} tokens)")
        print(f"  submission    : {out_csv}")

        if args.report:
            write_report(report_from_ledger(
                ledger.events, run_id=f"kaggle-{args.competition}"),
                args.report)
            print(f"  report        : {args.report}")
        else:
            print()
            print(render_text(report_from_ledger(
                ledger.events, run_id=f"kaggle-{args.competition}")))

        if args.submit:
            print()
            print("submitting to the leaderboard ...")
            msg = (f"loop-engine: {trace.get('estimator')}, "
                   f"{len(calls)} model call(s)")
            r = subprocess.run(
                ["kaggle", "competitions", "submit", "-c", args.competition,
                 "-f", out_csv, "-m", msg], capture_output=True, text=True)
            print((r.stdout or r.stderr).strip()[:300])
            print()
            print("The leaderboard score arrives in a minute or two:")
            print(f"  kaggle competitions submissions -c {args.competition}")
            print()
            print("When it differs from the local cv score above, the "
                  "leaderboard is the honest number: your split was "
                  "optimistic, and that gap is the thing worth studying.")
        else:
            print()
            if args.out:
                print("Not submitted. The generated CSV was kept at:")
                print(f"  {out_csv}")
                print("Submit only after reviewing it:")
                print(f"  kaggle competitions submit -c {args.competition} "
                      f"-f {out_csv} -m 'loop-engine'")
            else:
                print("Not submitted. The temporary CSV was not retained.")
                print("Use --out PATH to keep it for review.")


def _warm_store():
    """Deterministic advice, so the zero-model arm has a research answer.

    Worth knowing: a store hit OUTRANKS a model call by design (cheapest
    first). Passing both a warm store and a model means the store answers and
    the model is never reached: which is correct behaviour, and a trap if you
    are trying to measure whether the model helps."""
    from loop_engine.core.store_serve import (SolverStore,
                                                             StoreRecord)
    return SolverStore(core_records=[
        StoreRecord("n.tabular", "node",
                    "orient act fit predict tabular classification baseline",
                    body={}, tags=("fit",))])


if __name__ == "__main__":
    sys.exit(main())
