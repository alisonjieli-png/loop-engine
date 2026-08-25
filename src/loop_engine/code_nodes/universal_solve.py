"""The universal front door — a goal and your data. It works out the rest.

Architectural role: Code Node system (task orientation and routing).

The complaint this answers, in the owner's words: *"this loop should be
intelligent enough to figure out any solution; a user shouldn't have to tell it
that it is a tabular task unless the user wants to."*

That was fair. The previous entry points made the caller do the orienting:

    run_smoke_loop(train_csv=..., test_csv=..., sample_csv=..., out_csv=...)

To call that you must already know the task is tabular, which files play which
role, and that a submission template exists. Every one of those is something
the data can be asked. So:

    solve("predict which customers churn", data="./mydata")

Orientation happens by INSPECTION, at zero model calls: what files are here,
what shapes do they have, which column looks like an identifier, which like a
target, is this a table or a folder of images or a pile of text. The inference
and its evidence are reported, so a caller can disagree — and override any part
of it — without ever being *required* to.

    THE DEFAULT IS INFERENCE. THE OVERRIDE IS OPTIONAL.

    Every inferred field can be passed explicitly, and an explicit value always
    wins. Nothing here guesses silently: `TaskReading.evidence` says what led
    to each conclusion, and low confidence is reported as low confidence rather
    than rounded up to a decision.

Owns:
    - TaskReading: what this task appears to be, and the evidence for it;
    - read_task(): inspect files/directories/frames -> a reading;
    - solve(): the front door — orient, route, execute, report.

Does not own:
    - the executors (kaggle_executor, competition_solver), the loop runtime, or
      any provider.

Key invariants:
    - orientation costs zero model calls and zero network;
    - every inference names its evidence and its confidence;
    - an explicit argument always beats an inference;
    - an unreadable or ambiguous task says so instead of picking a default;
    - a missing declared dependency is named clearly.

Verification: self_test() — tabular/text/image/empty readings from real files,
override precedence, evidence completeness, and the adversarial
"confidently wrong on an ambiguous input" path.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

#: What a task can look like. "unknown" is a real answer, not a failure.
MODALITIES = ("tabular", "text", "image", "audio", "mixed", "unknown")

#: What kind of question is being asked of it.
PROBLEMS = ("classification", "regression", "multilabel", "generation",
            "unknown")

_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
_AUDIO_EXT = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
_TABLE_EXT = {".csv", ".tsv", ".parquet", ".xlsx"}
_TEXT_EXT = {".txt", ".md", ".json", ".jsonl", ".rst"}

#: Column-name hints. WEAK evidence by design — a name suggests a role, it
#: never establishes one. Shape and content decide; names only break ties.
_ID_HINT = re.compile(r"^(id|.*_id|index|key|uuid|.*_key)$", re.I)
_TARGET_HINT = re.compile(
    r"^(target|label|y|class|outcome|result|churn|survived|price|score|"
    r"prediction|is_.*|has_.*)$", re.I)


@dataclass
class TaskReading:
    """What this task appears to be — with the evidence, always."""
    goal: str = ""
    modality: str = "unknown"
    problem: str = "unknown"
    data_path: str = ""
    files: list = field(default_factory=list)
    train_file: str = ""
    test_file: str = ""
    sample_file: str = ""
    id_column: str = ""
    target_column: str = ""
    rows: int = 0
    columns: int = 0
    confidence: float = 0.0
    evidence: list = field(default_factory=list)
    missing_dependency: str = ""
    notes: list = field(default_factory=list)

    @property
    def ready(self) -> bool:
        """Enough was established to route this task somewhere real."""
        return (self.modality != "unknown" and self.confidence >= 0.5
                and not self.missing_dependency)

    def explain(self) -> str:
        """Plain English — what was inferred, and what it was inferred from."""
        lines = [f'Task: "{self.goal}"' if self.goal else "Task: (no goal given)"]
        lines.append(f"  modality   : {self.modality}"
                     + (f"  ({self.problem})"
                        if self.problem != "unknown" else ""))
        if self.rows or self.columns:
            lines.append(f"  shape      : {self.rows} rows x "
                         f"{self.columns} columns")
        if self.id_column or self.target_column:
            lines.append(f"  columns    : id={self.id_column or '?'}  "
                         f"target={self.target_column or '?'}")
        lines.append(f"  confidence : {self.confidence:.2f}"
                     + ("  (low — say what you meant and it will use that)"
                        if self.confidence < 0.5 else ""))
        if self.evidence:
            lines.append("  because:")
            for e in self.evidence:
                lines.append(f"    - {e}")
        if self.missing_dependency:
            lines.append(
                f"  MISSING DEPENDENCY: {self.missing_dependency}. "
                "Reinstall with: python -m pip install --force-reinstall git+https://github.com/alisonjieli-png/loop-engine.git.")
        for n in self.notes:
            lines.append(f"  note: {n}")
        return "\n".join(lines)

    def summary(self) -> dict:
        return {"record_type": "task_reading/v1", "goal": self.goal,
                "modality": self.modality, "problem": self.problem,
                "id_column": self.id_column,
                "target_column": self.target_column,
                "rows": self.rows, "columns": self.columns,
                "confidence": round(self.confidence, 3),
                "evidence": list(self.evidence),
                "missing_dependency": self.missing_dependency,
                "files": [os.path.basename(f) for f in self.files[:20]]}


def _list_files(path: str) -> list:
    if os.path.isfile(path):
        return [path]
    out = []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs
                   if not d.startswith(".") and d != "__pycache__"]
        for f in sorted(files):
            if not f.startswith("."):
                out.append(os.path.join(root, f))
        if len(out) > 5000:
            break
    return out


def _role_of(name: str) -> str:
    """Which role a filename SUGGESTS. Weak evidence, used only alongside
    shape — a file called train.csv with no rows is not training data."""
    low = os.path.basename(name).lower()
    if "sample" in low or "submission" in low:
        return "sample"
    if "train" in low:
        return "train"
    if "test" in low or "valid" in low or "eval" in low:
        return "test"
    return ""


def _sniff_table(path: str, reading: TaskReading) -> None:
    """Read a table's header and a few rows — no full load, no pandas needed
    for the header itself, so orientation stays cheap and dependency-free."""
    import csv as _csv
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            sample = fh.read(64 * 1024)
    except OSError:
        return
    try:
        dialect = _csv.Sniffer().sniff(sample.split("\n", 1)[0] + "\n")
        delim = dialect.delimiter
    except _csv.Error:
        delim = "\t" if path.endswith(".tsv") else ","
    rows = list(_csv.reader(sample.splitlines(), delimiter=delim))
    if not rows:
        return
    header = [c.strip() for c in rows[0]]
    body = rows[1:]
    reading.columns = len(header)
    # count rows cheaply: the sample tells us the average line length
    try:
        total = os.path.getsize(path)
        avg = max(1, len(sample) // max(1, len(rows)))
        reading.rows = max(len(body), total // avg - 1)
    except OSError:
        reading.rows = len(body)

    # identifier: a column whose values are unique across the sample. NAME is
    # a tie-break only — position never establishes identity.
    if body:
        for i, col in enumerate(header):
            vals = [r[i] for r in body[:200] if i < len(r)]
            if vals and len(set(vals)) == len(vals) and len(vals) > 3:
                if _ID_HINT.match(col) or not reading.id_column:
                    reading.id_column = col
                    if _ID_HINT.match(col):
                        break
    # TARGET, by structure first and name last.
    #
    # A name list is the wrong primary signal: it answers "nothing found" for
    # every column it was never told about, and reads like a measurement while
    # doing it. A real corpus said `renewed` and the list said `churn`, so the
    # target was missed and the run only worked by accident.
    #
    # Structure is stronger and domain-free, in descending order of strength:
    #   1. present in train and ABSENT from test  -> that IS the target
    #   2. named by the caller's own goal text    -> they said what they want
    #   3. a low-cardinality trailing column      -> the usual layout
    #   4. a name that looks like a target        -> weakest, a tie-break
    candidates = []
    if reading.test_file and reading.test_file != path:
        try:
            with open(reading.test_file, encoding="utf-8",
                      errors="replace") as th:
                test_header = [c.strip() for c in
                               (th.readline() or "").split(delim)]
            only_in_train = [c for c in header if c and c not in test_header]
            if len(only_in_train) == 1:
                reading.target_column = only_in_train[0]
                reading.evidence.append(
                    f"column {only_in_train[0]!r} is in the training table but "
                    "not the test table -> that is what must be predicted")
                return
            candidates += only_in_train
        except OSError:
            pass

    goal_words = set(re.findall(r"[a-z]+", (reading.goal or "").lower()))
    for col in header:
        stem = re.sub(r"[^a-z]", "", col.lower())
        if not stem or col == reading.id_column:
            continue
        # "will renew" naming the column "renewed": match on a shared prefix
        # rather than equality, so ordinary English reaches the schema
        if any(w.startswith(stem[:5]) or stem.startswith(w[:5])
               for w in goal_words if len(w) > 3):
            reading.target_column = col
            reading.evidence.append(
                f"your goal mentions {col!r} -> using it as the target")
            return

    trailing = [c for c in header[::-1] if c and c != reading.id_column]
    if body and trailing:
        last = trailing[0]
        i = header.index(last)
        vals = [r[i] for r in body[:300] if i < len(r) and r[i] != ""]
        if vals and len(set(vals)) <= max(2, len(vals) // 10):
            reading.target_column = last
            reading.evidence.append(
                f"last column {last!r} has {len(set(vals))} distinct values "
                f"across {len(vals)} sampled rows -> target")
            return

    for col in header:
        if _TARGET_HINT.match(col) and col != reading.id_column:
            reading.target_column = col
            reading.evidence.append(
                f"column name {col!r} reads like a target (weakest signal; "
                "structure found nothing clearer)")
            return


def _classify_problem(path: str, reading: TaskReading) -> None:
    """Classification vs regression, from the target's own values."""
    if not reading.target_column:
        return
    import csv as _csv
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            rd = _csv.DictReader(fh)
            vals = []
            for i, row in enumerate(rd):
                if i >= 500:
                    break
                v = row.get(reading.target_column)
                if v not in (None, ""):
                    vals.append(v)
    except (OSError, _csv.Error):
        return
    if not vals:
        return
    distinct = len(set(vals))
    floats = 0
    for v in vals:
        try:
            float(v)
            floats += 1
        except ValueError:
            pass
    numeric = floats == len(vals)
    if numeric and distinct > 20:
        reading.problem = "regression"
        reading.evidence.append(
            f"target {reading.target_column!r} is numeric with {distinct} "
            "distinct values in the first 500 rows -> regression")
    else:
        reading.problem = "classification"
        reading.evidence.append(
            f"target {reading.target_column!r} has {distinct} distinct "
            f"values -> classification")


#: Files a previous run WROTE. Reading them back as input is how a solver
#: starts training on its own predictions — the shape of leakage that looks
#: like a great score and means nothing. Caught by running solve() twice into
#: the same folder.
_OUTPUT_HINT = re.compile(
    r"^(out|output|prediction|predictions|submission|result|results)"
    r"[-_.]?\d*\.(csv|tsv|json|jsonl)$", re.I)


def read_task(goal: str = "", data: str = "", *, modality: str = "",
              problem: str = "", id_column: str = "",
              target_column: str = "", exclude=()) -> TaskReading:
    """Work out what this task is. Zero model calls, zero network.

    Any field passed explicitly wins outright — inference is the DEFAULT, not
    an imposition."""
    r = TaskReading(goal=goal, data_path=data)

    if not data:
        r.modality = modality or "unknown"
        r.confidence = 1.0 if modality else 0.2
        r.evidence.append("no data path given — this is a reasoning task "
                          "unless you pass data=")
        r.notes.append("a loop with no dataset still runs; it just has "
                       "nothing to orient on")
        return _apply_overrides(r, modality, problem, id_column, target_column)

    if not os.path.exists(data):
        r.evidence.append(f"path does not exist: {data}")
        r.confidence = 0.0
        return _apply_overrides(r, modality, problem, id_column, target_column)

    files = _list_files(data)
    skip = {os.path.abspath(p) for p in exclude}
    dropped = [f for f in files
               if os.path.abspath(f) in skip or _OUTPUT_HINT.match(
                   os.path.basename(f))]
    files = [f for f in files if f not in dropped]
    if dropped:
        r.notes.append(
            "ignored " + ", ".join(sorted(os.path.basename(f)
                                          for f in dropped)[:4])
            + " — these look like a previous run's OUTPUT, and training on "
              "your own predictions produces a great score that means nothing")
    r.files = files
    exts = [os.path.splitext(f)[1].lower() for f in files]
    n_img = sum(1 for e in exts if e in _IMAGE_EXT)
    n_aud = sum(1 for e in exts if e in _AUDIO_EXT)
    n_tab = sum(1 for e in exts if e in _TABLE_EXT)
    n_txt = sum(1 for e in exts if e in _TEXT_EXT)

    # roles, from names AND presence
    for f in files:
        role = _role_of(f)
        if role == "train" and not r.train_file:
            r.train_file = f
        elif role == "test" and not r.test_file:
            r.test_file = f
        elif role == "sample" and not r.sample_file:
            r.sample_file = f
    if not r.train_file:
        tables = [f for f, e in zip(files, exts) if e in _TABLE_EXT]
        if tables:
            r.train_file = tables[0]
            r.evidence.append(
                f"no file named 'train' — using the only/first table "
                f"({os.path.basename(tables[0])})")

    # modality, by majority of what is actually present
    total = max(1, len(files))
    if n_img and n_img >= 0.5 * total:
        r.modality, r.confidence = "image", min(0.95, n_img / total)
        r.evidence.append(f"{n_img} of {total} files are images")
    elif n_aud and n_aud >= 0.5 * total:
        r.modality, r.confidence = "audio", min(0.95, n_aud / total)
        r.evidence.append(f"{n_aud} of {total} files are audio")
    elif n_tab:
        r.modality, r.confidence = "tabular", 0.9
        r.evidence.append(
            f"{n_tab} table file(s) present"
            + (f", including {os.path.basename(r.train_file)}"
               if r.train_file else ""))
        if r.train_file:
            _sniff_table(r.train_file, r)
            if r.columns:
                r.evidence.append(
                    f"{os.path.basename(r.train_file)} has {r.columns} "
                    f"columns and about {r.rows} rows")
            if r.id_column:
                r.evidence.append(
                    f"column {r.id_column!r} is unique across the sampled "
                    "rows -> identifier")
            if r.target_column:
                _classify_problem(r.train_file, r)
            else:
                r.notes.append(
                    "no obvious target column; pass target_column= if the "
                    "task has one")
                r.confidence = 0.65
        if n_img > 0.2 * total:
            r.modality = "mixed"
            r.evidence.append(f"also {n_img} image files -> mixed")
    elif n_txt:
        r.modality, r.confidence = "text", 0.75
        r.evidence.append(f"{n_txt} text/document file(s), no tables")
    else:
        r.modality, r.confidence = "unknown", 0.1
        r.evidence.append(
            f"{total} file(s), none recognised as a table, image, audio or "
            "document")
        r.notes.append("pass modality= to say what this is")

    # the adapter this reading would need, checked rather than assumed
    if r.modality in ("tabular", "image", "mixed") and not r.missing_dependency:
        try:
            import pandas                                   # noqa: F401
        except ImportError:
            r.missing_dependency = "pandas"
    return _apply_overrides(r, modality, problem, id_column, target_column)


def _apply_overrides(r, modality, problem, id_column, target_column):
    """An explicit value always beats an inference, and says so."""
    for name, value in (("modality", modality), ("problem", problem),
                        ("id_column", id_column),
                        ("target_column", target_column)):
        if value:
            setattr(r, name, value)
            r.evidence.append(f"{name} = {value!r} (given explicitly; "
                              "overrides inference)")
            r.confidence = max(r.confidence, 0.95)
    return r


def solve(goal: str, data: str = "", *, out: str = "", modality: str = "",
          problem: str = "", id_column: str = "", target_column: str = "",
          advice_fn=None, ledger=None, dry_run: bool = False,
          knowledge: "dict | None" = None) -> dict:
    """THE front door. Orient first, then route — you name the goal, not the shape.

    One function, three routes, chosen from what you passed:

        solve("goal", data="./x")   -> orient on the data, run the executor
        solve("goal")               -> a reasoning task, via the knowledge solver
        solve("goal", data=...)     -> a shape with no executor yet: oriented,
                                       reported, and honestly not solved

    Returns a dict carrying the reading, the route taken, the record and the
    report."""
    from ..loop.recursive_loop import LoopLedger
    ledger = ledger if ledger is not None else LoopLedger()

    reading = read_task(goal, data, modality=modality, problem=problem,
                        id_column=id_column, target_column=target_column,
                        exclude=(out,) if out else ())
    out_dict = {"record_type": "universal_solve/v1", "goal": goal,
                "reading": reading.summary(), "ran": False, "record": None}

    if dry_run:
        out_dict["explanation"] = reading.explain()
        return out_dict

    if reading.missing_dependency:
        out_dict["explanation"] = reading.explain()
        out_dict["blocked"] = (
            f"this looks like a {reading.modality} task, but the declared "
            f"dependency {reading.missing_dependency!r} is missing. "
            "Reinstall with: python -m pip install --force-reinstall git+https://github.com/alisonjieli-png/loop-engine.git.")
        return out_dict

    if reading.modality in ("tabular", "mixed") and reading.train_file:
        from .smoke_ladder import run_smoke_loop
        test = reading.test_file or reading.train_file
        sample = reading.sample_file or ""
        if not sample:
            sample = _synth_sample(reading, out or "submission.csv")
        record = run_smoke_loop(
            goal, train_csv=reading.train_file, test_csv=test,
            sample_csv=sample, out_csv=out or "predictions.csv",
            ledger=ledger, advice_fn=advice_fn)
        out_dict.update(ran=True, record=record)
    elif not data:
        # NO DATA is not a failure — it is a reasoning task. Hand it to the
        # knowledge solver rather than inventing a second front door: two
        # public functions called `solve` is precisely the confusion this
        # module exists to remove.
        from ..loop.solver import solve as solve_from_knowledge
        res = solve_from_knowledge(goal, **(knowledge or {}))
        out_dict.update(ran=True, record={
                            "trace": {"loop_id": res.loop_id,
                                      "runtime_type": "Loop"},
                            "value": res},
                        route="knowledge")
        out_dict["note"] = ("no data given, so this ran as a reasoning task "
                            "through the knowledge solver")
    else:
        # An executor for this shape does not exist yet. Say so plainly — an
        # honest refusal beats routing a text task through a tabular executor
        # and reporting whatever falls out.
        from ..loop.encapsulate import as_practitioner_loop
        res = as_practitioner_loop(
            goal, lambda: reading.summary(), ledger=ledger)
        out_dict.update(ran=True, record={"trace": {}, "value": res["value"]},
                        route="oriented_only")
        out_dict["note"] = (
            f"no executor is registered for modality {reading.modality!r} yet, "
            "so the loop oriented on the task and returned its reading rather "
            "than pretending to solve it")

    from .loop_report import report_from_ledger, render_text
    rep = report_from_ledger(ledger.events, run_id="universal-solve")
    out_dict["report"] = render_text(rep)
    out_dict["explanation"] = reading.explain()
    return out_dict


def _synth_sample(reading: TaskReading, out_csv: str) -> str:
    """Build a submission template when the task has none — the shape is
    derivable from the identifier and target the reading already found."""
    import csv as _csv
    import tempfile
    path = os.path.join(tempfile.mkdtemp(), "sample_submission.csv")
    src = reading.test_file or reading.train_file
    ids = []
    try:
        with open(src, encoding="utf-8", errors="replace") as fh:
            for i, row in enumerate(_csv.DictReader(fh)):
                if reading.id_column and reading.id_column in row:
                    ids.append(row[reading.id_column])
                else:
                    ids.append(str(i))
    except (OSError, _csv.Error):
        ids = ["0"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = _csv.writer(fh)
        w.writerow([reading.id_column or "id",
                    reading.target_column or "prediction"])
        for i in ids:
            w.writerow([i, 0])
    return path


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    import shutil
    import tempfile
    d = tempfile.mkdtemp()
    try:
        # --- a tabular task, named nothing in particular -------------------
        tab = os.path.join(d, "tab")
        os.makedirs(tab)
        with open(os.path.join(tab, "customers.csv"), "w") as f:
            f.write("customer_id,months,spend,churn\n")
            for i in range(60):
                f.write(f"{1000+i},{i%40},{i*3.5},{i%2}\n")

        r = read_task("predict which customers churn", tab)

        # 1. THE POINT: the caller said only what they WANT. Everything about
        # the shape came from the data.
        check("a_tabular_task_is_recognised_without_being_told",
              r.modality == "tabular" and r.confidence >= 0.65
              and r.id_column == "customer_id"
              and r.target_column == "churn"
              and r.problem == "classification"
              and r.columns == 4 and r.rows >= 50,
              f"{r.modality}/{r.problem}, id={r.id_column}, "
              f"target={r.target_column}")

        # 2. EVERY INFERENCE NAMES ITS EVIDENCE — that is what makes it
        # arguable rather than magic.
        joined = " ".join(r.evidence)
        check("every_conclusion_carries_the_evidence_for_it",
              len(r.evidence) >= 3 and "customer_id" in joined
              and "churn" in joined and "unique" in joined
              and "because:" in r.explain(),
              f"{len(r.evidence)} pieces of evidence")

        # 3. A NAME IS WEAK EVIDENCE. A column called "id" that is NOT unique
        # must not be taken as the identifier on its name alone.
        weak = os.path.join(d, "weak")
        os.makedirs(weak)
        with open(os.path.join(weak, "t.csv"), "w") as f:
            f.write("id,value,label\n")
            for i in range(40):
                f.write(f"7,{i},{i%3}\n")          # 'id' is constant
        rw = read_task("classify", weak)
        check("a_name_alone_never_establishes_a_column_role",
              rw.id_column != "id",
              f"constant 'id' column rejected; chose {rw.id_column!r}")

        # 4. OVERRIDES WIN, and are recorded as overrides.
        ro = read_task("predict spend", tab, target_column="spend",
                       problem="regression")
        check("an_explicit_value_beats_the_inference_and_says_so",
              ro.target_column == "spend" and ro.problem == "regression"
              and any("overrides inference" in e for e in ro.evidence)
              and ro.confidence >= 0.95,
              "inference is the default, never an imposition")

        # 5. OTHER MODALITIES are recognised, not forced into tabular.
        img = os.path.join(d, "img")
        os.makedirs(img)
        for i in range(8):
            open(os.path.join(img, f"pic{i}.png"), "wb").write(b"\x89PNG")
        txt = os.path.join(d, "txt")
        os.makedirs(txt)
        for i in range(5):
            open(os.path.join(txt, f"doc{i}.md"), "w").write("# notes\ntext")
        ri, rt = read_task("classify these", img), read_task("summarise", txt)
        check("image_and_text_tasks_are_not_forced_into_the_tabular_path",
              ri.modality == "image" and rt.modality == "text"
              and ri.modality != "tabular",
              f"image={ri.modality}, text={rt.modality}")

        # 6. ADVERSARIAL — AN UNREADABLE TASK SAYS SO rather than defaulting.
        # Confidently wrong is the failure mode worth preventing here.
        odd = os.path.join(d, "odd")
        os.makedirs(odd)
        open(os.path.join(odd, "thing.bin"), "wb").write(b"\x00\x01\x02")
        ru = read_task("do something", odd)
        missing = read_task("x", os.path.join(d, "nope"))
        nodata = read_task("just think about it")
        check("an_unrecognised_or_absent_task_reports_low_confidence",
              ru.modality == "unknown" and ru.confidence < 0.5
              and not ru.ready
              and missing.confidence == 0.0
              and nodata.modality == "unknown" and not nodata.ready
              and "low" in ru.explain(),
              "no default is invented to look decisive")

        # 7. THE FRONT DOOR routes from the reading alone — goal and data in.
        res = solve("predict which customers churn", tab, dry_run=True)
        check("the_front_door_takes_a_goal_and_data_and_nothing_else",
              res["reading"]["modality"] == "tabular"
              and res["reading"]["target_column"] == "churn"
              and res["ran"] is False
              and "Task:" in res["explanation"],
              "no file roles, no shapes, no modality asked of the caller")

        knowledge_run = solve(
            "build a churn model", knowledge={
                "obligations": ("choose_model",), "run_log_path": None})
        check("knowledge_route_runs_inside_the_canonical_Loop_runtime",
              knowledge_run["route"] == "knowledge"
              and knowledge_run["record"]["trace"]["runtime_type"] == "Loop"
              and knowledge_run["record"]["trace"]["loop_id"].startswith(
                  "loop"),
              "the planning algorithm is a Code Intelligence service inside Loop")

        # 9. a missing dependency is named rather than crashing
        # somewhere deep in an executor
        try:
            import pandas                                   # noqa: F401
            has_pandas = True
        except ImportError:
            has_pandas = False
        blocked = solve("predict churn", tab)
        check("a_missing_dependency_is_named",
              (has_pandas and blocked.get("ran"))
              or (not has_pandas
                  and "pandas" in blocked.get("blocked", "")),
              "dependency name, not a stack trace" if not has_pandas
              else "dependency present; executed")
        # --- 10. THE GOAL NAMES THE TARGET -----------------------------
        # A name list answers "nothing found" for every column it was never
        # told about. A real corpus said `renewed` while the list said
        # `churn`, so the target was missed and the run worked by accident.
        # Ordinary English in the goal must be able to reach the schema.
        goalcol = os.path.join(d, "goalcol")
        os.makedirs(goalcol)
        with open(os.path.join(goalcol, "accounts.csv"), "w") as f:
            f.write("account_ref,tenure,spend,renewed\n")
            for i in range(60):
                f.write(f"ACC{i},{i%40},{i*2.5},{i%2}\n")
        rg = read_task("work out which accounts will renew", goalcol)
        check("ordinary_english_in_the_goal_can_name_the_target_column",
              rg.target_column == "renewed"
              and any("goal mentions" in e for e in rg.evidence)
              and rg.problem == "classification",
              "'will renew' reached the column 'renewed' with no word list")

        # --- 11. ADVERSARIAL: never train on your own output -------------
        # Running solve() twice into the same folder made the second run read
        # the FIRST run's predictions as training data — leakage that produces
        # a great score and means nothing.
        with open(os.path.join(goalcol, "predictions.csv"), "w") as f:
            f.write("account_ref,renewed\n")
            for i in range(60):
                f.write(f"ACC{i},1\n")
        with open(os.path.join(goalcol, "out.csv"), "w") as f:
            f.write("account_ref,renewed\nACC0,1\n")
        r_again = read_task("work out which accounts will renew", goalcol)
        check("a_previous_runs_output_is_never_read_back_as_training_data",
              "accounts.csv" in os.path.basename(r_again.train_file)
              and r_again.columns == 4
              and any("previous run" in n for n in r_again.notes)
              and read_task("x", goalcol,
                            exclude=(os.path.join(goalcol, "accounts.csv"),)
                            ).train_file == "",
              "predictions.csv and out.csv excluded; explicit exclude honoured")

    finally:
        shutil.rmtree(d, ignore_errors=True)

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
