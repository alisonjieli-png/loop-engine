"""Loop Engine Studio server — the routed application over the Chronicle.

Architectural role: Static Architecture service (a serving adapter, like the
model gateway is for models).

Owns:
    - the local HTTP surface (stdlib http.server — no new dependencies) that
      serves the Studio shell (a passive String at
      ``strings/studio_shell.html``) and the projection APIs;
    - the Chronicle projections computed AT REQUEST TIME (never a generated
      snapshot): runs list, per-run overview/loop-tree/timeline/model-calls,
      per-run stuckness; the intelligence inventory (live harvest of the
      banks + generated candidates + meta pack); the code-node inventory
      (architecture map + docstrings); the solution library (receipts);
      the improvements view (per-run stuckness + candidates awaiting
      validation).

Does not own:
    - any mutation: the Studio is READ-ONLY in this phase — edits become
      ChangeProposals through their own lane, never through HTTP;
    - analytics semantics (run_quality/run_analytics own them) or the
      Chronicle itself (chronicle.py owns the store).

Public entry points:
    - serve(port=8765) — blocking; ``--studio`` in __main__ wraps it
    - build_projection(name, arg) — the API payloads (test-callable without
      a socket)

Key invariants:
    - every payload derives from Chronicle files, live stores, or receipts
      read at request time;
    - the server binds 127.0.0.1 only (a local workbench, not a deployment);
    - unknown API routes 404 with a JSON error, never a traceback page.

Verification: self_test() (folded into the package suite — exercises the
projections and one live request against an ephemeral port).
"""
from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

_PKG = os.path.dirname(os.path.dirname(__file__))
from .chronicle import default_runs_dir

_RUNS = default_runs_dir()


def _load_run_as_historical_loop(run_id: str, *, ledger=None):
    """Read ONE saved run through a Historical Run Loop.

    The owner's ruling (2026-08-24) is that no caller queries Chronicle
    directly — it invokes the loop that owns the history.  The read is
    deterministic, stops after one accepted success, and records
    ``intelligence.history.retrieved`` on the caller's ledger when one is
    given, so "the Studio read the history" is evidence rather than an
    assumption."""
    from .chronicle import Chronicle
    from ..loop.intelligence_loops import serve_historical_intelligence
    return serve_historical_intelligence(
        f"run:{run_id}",
                            lambda: Chronicle.load(_RUNS, run_id),
                            ledger=ledger)["value"]


def _chronicles():
    out = []
    if not os.path.isdir(_RUNS):
        return out
    for rid in sorted(os.listdir(_RUNS)):
        if os.path.exists(os.path.join(_RUNS, rid, "manifest.json")):
            try:
                out.append(_load_run_as_historical_loop(rid))
            except (OSError, KeyError, json.JSONDecodeError):
                continue
    return out


def _run_row(ch) -> dict:
    calls = [e for e in ch.events if e.event_type == "model_invocation"]
    goal = next((e.detail.get("goal", "") for e in ch.events
                 if e.event_type == "loop_init"), "")
    return {"run_id": ch.run_id, "events": len(ch.events),
            "calls": len(calls),
            "tokens": sum(e.prompt_tokens + e.eval_tokens for e in calls),
            "intact": ch.verify_chain()["intact"], "goal": goal}


def _run_detail(rid: str) -> dict:
    from ..code_nodes.run_quality import stuckness_report
    ch = _load_run_as_historical_loop(rid)
    calls, events, iters = [], [], 0
    tree_kids: dict = {}
    goals: dict = {}
    for e in ch.events:
        if e.event_type == "loop_init":
            goals[e.loop_id] = e.detail.get("goal", "")
        elif e.event_type == "loop_spawn":
            tree_kids.setdefault(e.parent_loop_id, []).append(e.loop_id)
        elif e.event_type == "iteration":
            iters += 1
        elif e.event_type == "model_invocation":
            calls.append({"seq": e.sequence_number, "loop": e.loop_id,
                          "step": e.step, "model": e.model,
                          "prompt_tokens": e.prompt_tokens,
                          "eval_tokens": e.eval_tokens})
        events.append({"type": e.event_type, "loop": e.loop_id,
                       "step": e.step, "mode": e.mode,
                       "tokens": e.prompt_tokens + e.eval_tokens or "",
                       "detail": str(e.detail.get("output",
                                     e.detail.get("reason", "")))[:100]})

    def tree(lid, prefix=""):
        lines = [f"{prefix}{lid}  {goals.get(lid, '')[:60]}"]
        kids = tree_kids.get(lid, [])
        for i, k in enumerate(kids):
            last = i == len(kids) - 1
            lines += tree(k, prefix + ("└── " if last else "├── "))
        return lines
    roots = [l for l in goals if not any(l in v for v in tree_kids.values())]
    tree_txt = "\n".join(sum((tree(r) for r in roots), []))

    # STRUCTURED tree + per-loop rollups, so the Studio can render a
    # clickable Loop Tree with an inspector instead of a text blob.  A text
    # tree shows shape; it cannot be selected, and a loop you cannot select
    # is a loop you cannot inspect or advise.
    per_loop: dict = {}
    for e in ch.events:
        if not e.loop_id:
            continue
        row = per_loop.setdefault(e.loop_id, {
            "loop_id": e.loop_id, "goal": goals.get(e.loop_id, ""),
            "parent": "", "iterations": 0, "calls": 0, "tokens": 0,
            "modes": {}, "steps": [], "terminal": ""})
        if e.event_type == "iteration":
            row["iterations"] += 1
            if e.mode:
                row["modes"][e.mode] = row["modes"].get(e.mode, 0) + 1
            row["steps"].append({"step": e.step, "mode": e.mode,
                                 "out": str((e.detail or {}).get("output",
                                                                 ""))[:90]})
        elif e.event_type == "model_invocation":
            row["calls"] += 1
            row["tokens"] += (e.prompt_tokens or 0) + (e.eval_tokens or 0)
        elif e.event_type == "terminal":
            row["terminal"] = str((e.detail or {}).get("reason", ""))
    for parent, kids in tree_kids.items():
        for k in kids:
            if k in per_loop:
                per_loop[k]["parent"] = parent

    def node(lid):
        return {"loop_id": lid, **per_loop.get(lid, {"goal": goals.get(lid, "")}),
                "children": [node(k) for k in tree_kids.get(lid, [])]}

    tree_json = [node(r) for r in roots]
    return {"run_id": rid,
            "goal": next(iter(goals.values()), ""),
            "totals": {"events": len(ch.events), "iterations": iters,
                       "calls": len(calls),
                       "prompt_tokens": sum(c["prompt_tokens"]
                                            for c in calls),
                       "eval_tokens": sum(c["eval_tokens"] for c in calls)},
            "chain_intact": ch.verify_chain()["intact"],
            "stuckness": stuckness_report(ch.events),
            "tree": tree_txt, "tree_json": tree_json,
            "loops": list(per_loop.values()),
            "events": events, "calls": calls}


def _strings_inventory() -> dict:
    from ..loop.loop_templates import template_records
    from ..strings.solution_shaping import solution_shaping_pack
    from ..code_nodes.measurement import measurement_pack
    from ..strings.interrogation import interrogation_bank
    from ..code_nodes.guidance_ledger import BOOTSTRAP_GUIDANCE
    from ..code_nodes.string_foundry import (improvement_seed_records,
                                             load_candidate_bank)
    rows = []

    def add(sid, kind, text, cat, sub, mat, source, job="", prov=""):
        rows.append({"id": sid, "kind": kind, "text": str(text)[:200],
                     "category": cat, "subcategory": sub, "maturity": mat,
                     "source": source, "job_position": job,
                     "provenance": prov})
    for r in template_records():
        add(r.record_id, "loop_template", r.body.get("description", ""),
            "loop_template", r.body.get("framework", ""),
            r.body.get("maturity", ""), "loop_templates")
    for bank, src in ((solution_shaping_pack(), "solution_shaping"),
                      (measurement_pack(), "measurement")):
        for s in getattr(bank, "_by_id", {}).values():
            add(f"{src}.{getattr(s, 'string_id', id(s))}", s.kind, s.text,
                src, "", getattr(s, "maturity", "registered"), src)
    for i, q in enumerate(interrogation_bank()):
        add(f"interrogation.{i}", getattr(q, "kind", "question"),
            getattr(q, "text", q), "interrogation", "",
            getattr(q, "maturity", "registered"), "interrogation")
    for g in BOOTSTRAP_GUIDANCE:
        add(f"guidance.{g['key']}", "guidance", g["text"], "guidance", "",
            "registered", "guidance_ledger")
    for r in improvement_seed_records():
        add(r.record_id, r.body["kind"], r.body["text"], "improvement_meta",
            r.body["facets"]["subcategory"], "registered", "meta_pack")
    for r in load_candidate_bank():
        f = r.body.get("facets", {})
        add(r.record_id, r.body["kind"], r.body["text"],
            f.get("category", ""), f.get("subcategory", ""),
            r.body.get("maturity", "candidate"), "string_foundry",
            f.get("job_position", ""), r.body.get("provenance", ""))
    return {"items": rows, "strings": rows,
            "public_label": "Context Intelligence",
            "facets": sorted({r["category"] for r in rows if r["category"]})}


def _loops_inventory() -> dict:
    import ast
    from ..architecture_map import MODULE_MAP
    rows = []
    for group in ("code_nodes",):
        for m in MODULE_MAP[group]:
            p = os.path.join(_PKG, group, m + ".py")
            if not os.path.exists(p):
                continue
            try:
                doc = (ast.get_docstring(ast.parse(open(p).read()))
                       or "").split("\n")[0][:140]
            except SyntaxError:
                doc = ""
            rows.append({"module": m, "group": group, "loc":
                         sum(1 for _ in open(p)), "purpose": doc})
    return {"loops": rows}


def _intelligence_inventory() -> dict:
    """The four categorized layer populations from the canonical builder."""
    from .intelligence_layers import (build_intelligence_catalog,
                                      catalog_summary, classify_record,
                                      LAYER_PUBLIC_LABEL)
    advice_path = ADVICE_STORE_PATH or os.path.join(
        os.path.dirname(_RUNS), "studio", "user-advice.jsonl")
    catalog = build_intelligence_catalog(runs_dir=_RUNS,
                                         advice_path=advice_path)
    items = []
    for layer, records in catalog.items():
        for record in records:
            classification = classify_record(layer, record)
            items.append({"id": record.record_id, "title": record.title,
                          "layer": layer,
                          "public_layer": LAYER_PUBLIC_LABEL[layer],
                          "classification": classification})
    return {"summary": catalog_summary(catalog), "items": items}


def _solutions_inventory() -> dict:
    out = []
    evid = os.path.join(_PKG, "evidence")
    for f, key in (("chronicle-bootstrap-20260823.json", "solution_assets"),):
        p = os.path.join(evid, f)
        if os.path.exists(p):
            for a in json.load(open(p)).get(key, []):
                out.append({"id": a, "fingerprint": "see asset record",
                            "evidence": "chronicle bootstrap",
                            "maturity": "candidate"})
    p = os.path.join(evid, "openml-real-data-20260823.json")
    if os.path.exists(p):
        d = json.load(open(p))
        for k, r in d.get("results", {}).items():
            out.append({"id": f"solasset.{k}",
                        "fingerprint": f"tabular|classification|"
                                       f"{r['classes']}cls",
                        "evidence": f"sealed-holdout "
                        f"{r['cold']['sealed_holdout_accuracy_LOCAL_REPLICA']:.5f}"
                        " (LOCALLY GRADED REPLICA)",
                        "maturity": "candidate"})
    return {"solutions": out}


def _improvements() -> dict:
    from ..code_nodes.run_quality import stuckness_report
    from ..code_nodes.string_foundry import load_candidate_bank
    stuck = []
    for ch in _chronicles():
        r = stuckness_report(ch.events)
        stuck.append({"run": ch.run_id, "score": r["stuckness_score"],
                      "indicators": ", ".join(i["indicator"] for i in
                                              r["dominant_indicators"])
                      or "none — flowed",
                      "interventions": ", ".join(
                          r["suggested_interventions"]) or "—"})
    bank = load_candidate_bank()
    return {"cards": [
        {"label": "candidates awaiting validation", "value": len(bank)},
        {"label": "runs chronicled", "value": len(stuck)},
        {"label": "stuck runs", "value":
            sum(1 for s in stuck if s["score"] > 0.5)}],
        "stuckness": sorted(stuck, key=lambda s: -s["score"]),
        "honesty": "candidates never self-promote — registration crosses "
                   "the evidence gate after they win on real tasks"}


def _summary() -> dict:
    rows = [_run_row(ch) for ch in _chronicles()]
    intelligence = _intelligence_inventory()["summary"]
    return {"cards": [
        {"label": "runs chronicled", "value": len(rows), "link": "runs"},
        {"label": "semantic calls", "value": sum(r["calls"] for r in rows),
         "link": "runs"},
        {"label": "provider tokens", "value": sum(r["tokens"] for r in rows),
         "link": "runs"},
        {"label": "zero-call runs", "value":
            sum(1 for r in rows if r["calls"] == 0), "link": "runs"},
        {"label": "categorized intelligence",
         "value": intelligence["total_items"],
         "link": "intelligence"},
        {"label": "chains intact", "value":
            f"{sum(1 for r in rows if r['intact'])}/{len(rows)}",
         "link": "runs"}],
        "recent": sorted(rows, key=lambda r: r["run_id"],
                         reverse=True)[:8],
        "honesty": "every number is computed from the Chronicle at request "
                   "time; smoke evidence proves plumbing, never benchmarks"}


def build_projection(name: str, arg: str = "") -> dict:
    if name == "summary":
        return _summary()
    if name == "runs":
        return {"runs": [_run_row(ch) for ch in _chronicles()]}
    if name == "run":
        return _run_detail(arg)
    if name in ("context", "strings"):
        return _strings_inventory()
    if name == "intelligence":
        return _intelligence_inventory()
    if name == "loops":
        return _loops_inventory()
    if name == "solutions":
        return _solutions_inventory()
    if name == "improvements":
        return _improvements()
    raise KeyError(name)


def _ledger_events_for(run_id: str) -> list:
    """The raw ledger rows behind one run, for the canonical projection.
    A saved Chronicle stores canonical events already, so its bodies are
    replayed as their source rows; a run with no saved history streams
    empty rather than inventing activity."""
    for ch in _chronicles():
        if ch.run_id == run_id:
            return [{"event": e.event_type, "loop_id": e.loop_id,
                     "step": e.step, "mode": e.mode, "ts": e.ts,
                     **(e.detail or {})} for e in ch.events]
    return []


#: where Studio writes land.  Overridable so a TEST never writes into the
#: source tree — the first version of this appended to a file inside the
#: package on every suite run, which grew unboundedly and made the repository
#: dirty as a side effect of running tests.
ADVICE_STORE_PATH: "str | None" = None


def _leave_advice(data: dict) -> dict:
    """Store one piece of User Intelligence from the Studio.

    Refuses an empty note, an undeclared scope, and an undeclared guidance
    type — the store's own closed vocabularies, enforced at the edge so a
    malformed request never becomes a malformed record.
    """
    from .user_intelligence import AdviceStore
    text = str(data.get("text", "")).strip()
    if not text:
        raise ValueError("empty advice is refused")
    store = AdviceStore(ADVICE_STORE_PATH
                        or os.path.join(_data_dir(), "user-advice.jsonl"))
    from ..loop.intelligence_loops import leave_guidance_as_loop
    # the envelope carries the loop evidence; the CLIENT gets the advice
    # record it asked for, so the boundary crossing is invisible to the API
    # contract while still being recorded.
    return leave_guidance_as_loop(
        store, text, scope=str(data.get("scope", "loop")),
        target=str(data.get("target", "")),
        author=str(data.get("author", "studio-user")),
        guidance_type=str(data.get("guidance_type", "advice")),
        strength=str(data.get("strength", "suggestion")),
        timing=str(data.get("timing", "next_safe_boundary")))["value"]


def _data_dir() -> str:
    d = os.path.join(os.path.dirname(_RUNS), "studio")
    os.makedirs(d, exist_ok=True)
    return d


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):                    # quiet by design
        pass

    def do_GET(self):
        from .saas_routes import serve_api, live_events, resolve_route
        try:
            if self.path.startswith("/api/"):
                parts = [unquote(p) for p in
                         self.path[5:].split("?")[0].split("/") if p]
                # /api/runs/<id>/events — the browser's live stream, one
                # canonical vocabulary shared with the console and the tree.
                if len(parts) == 3 and parts[0] == "runs" \
                        and parts[2] == "events":
                    payload = live_events(parts[1],
                                          _ledger_events_for(parts[1]))
                else:
                    # EVERY read crosses into a PractitionerLoop; the envelope
                    # rides back as _loop so the front end can SHOW that the
                    # call was governed rather than take it on faith.
                    served = serve_api(parts[0],
                                       parts[1] if len(parts) > 1 else "")
                    payload = served["payload"]
                    if isinstance(payload, dict):
                        payload = {**payload, "_loop": served["loop"]}
                body = json.dumps(payload, default=str).encode()
                ctype = "application/json"
            elif self.path.split("?")[0].rstrip("/") in ("/routes",
                                                          "/api/routes"):
                # the route contract, served as data: a client (or a test)
                # can enumerate what this deployment actually serves rather
                # than discovering it by 404.
                from .saas_routes import route_contract, PUBLIC_ROUTES, \
                    STUDIO_ROUTES
                payload = {**route_contract(),
                           "public": list(PUBLIC_ROUTES),
                           "studio": list(STUDIO_ROUTES)}
                body = json.dumps(payload).encode()
                ctype = "application/json"
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            else:
                route = resolve_route(self.path.split("?")[0])
                body = open(os.path.join(_PKG, "strings",
                                         "studio_shell.html"), "rb").read()
                ctype = "text/html; charset=utf-8"
                if route is None and self.path not in ("/", ""):
                    # an undeclared page is a 404, not a silently-served shell
                    self.send_response(404)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
            self.send_response(200)
        except (KeyError, FileNotFoundError) as e:
            body = json.dumps({"error": str(e)}).encode()
            ctype = "application/json"
            self.send_response(404)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        """The one write the Studio offers: advising a loop.

        A person clicks a loop, sees what it was GIVEN and what it is
        PRODUCING, and types guidance like a message to a coworker. It is
        stored scoped and attributable; it never bypasses a gate, and the
        loop's own disposition of it is a separate record.
        """
        try:
            n = int(self.headers.get("Content-Length") or 0)
            data = json.loads(self.rfile.read(n) or b"{}")
            if not self.path.rstrip("/").endswith("/user-intelligence"):
                raise KeyError(f"no write surface at {self.path}")
            rec = _leave_advice(data)
            body = json.dumps(rec, default=str).encode()
            self.send_response(201)
        except (KeyError, ValueError) as e:
            body = json.dumps({"error": str(e)}).encode()
            self.send_response(400)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(port: int = 8765, *, ready=None, runs_dir: str = "") -> None:
    """Blocking local server (127.0.0.1 only — a workbench, not a deploy)."""
    global _RUNS
    if runs_dir:
        _RUNS = default_runs_dir(runs_dir)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    if ready is not None:
        ready(httpd)                      # test mode: no banner
    else:
        print(f"Loop Engine Studio: http://127.0.0.1:{port}  (Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


def self_test() -> dict:
    import tempfile
    import shutil
    global _RUNS
    previous_runs, _RUNS = _RUNS, tempfile.mkdtemp(prefix="studio_runs_")
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    # A FRESH CLONE HAS NO RUNS. This test used to index runs[0] and passed
    # only because earlier runs happened to be lying around on the developer's
    # disk — so it failed on first checkout, which is the one moment a new user
    # actually runs it (caught 2026-08-24 by building the standalone repo).
    # A test establishes its own preconditions rather than inheriting them.
    if not build_projection("runs")["runs"]:
        from ..loop.encapsulate import as_practitioner_loop
        from ..loop.recursive_loop import LoopLedger
        from .chronicle import Chronicle
        _lg = LoopLedger()
        as_practitioner_loop("studio projection fixture", lambda: "ok",
                             ledger=_lg)
        _ch = Chronicle.from_ledger(_lg.events,
                                    run_id="studio-self-test-fixture")
        _ch.commit()
        _ch.save(_RUNS)          # commit() only marks it; save() writes the run

    # 1. every projection builds from live data (no server needed).
    s = build_projection("summary")
    runs = build_projection("runs")["runs"]
    strings = build_projection("strings")
    intelligence = build_projection("intelligence")
    loops = build_projection("loops")["loops"]
    imp = build_projection("improvements")
    check("projections_compute_from_live_chronicles_and_stores",
          s["cards"] and runs and len(strings["strings"]) > 100
          and len(intelligence["summary"]["layers"]) == 4
          and intelligence["summary"]["total_items"] >= 100
          and len(loops) >= 30 and "honesty" in imp,
          f"{len(runs)} runs, {len(strings['strings'])} strings, "
          f"{len(loops)} loops — at request time")

    # 2. a run detail carries overview + tree + playback events + calls +
    # stuckness, chain-verified.
    d = build_projection("run", runs[0]["run_id"])
    check("run_detail_projects_playback_tree_calls_stuckness",
          d["chain_intact"] and d["events"] and d["tree"]
          and "stuckness_score" in d["stuckness"]
          and d["totals"]["events"] == len(d["events"]))

    # 3. one LIVE request over HTTP: shell + an API route + a clean 404.
    import http.client
    holder = {}
    t = threading.Thread(target=serve, kwargs={
        "port": 0, "ready": lambda h: holder.update(h=h)}, daemon=True)
    t.start()
    import time
    for _ in range(50):
        if "h" in holder:
            break
        time.sleep(0.05)
    port = holder["h"].server_address[1]
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request("GET", "/")
    shell = conn.getresponse().read().decode()
    conn.request("GET", "/api/summary")
    api = json.loads(conn.getresponse().read())
    conn.request("GET", "/api/nope")
    notfound = conn.getresponse()
    nf_body = json.loads(notfound.read())
    # THE SEAM, over a real socket: the read carried its loop envelope back,
    # so the front end can SHOW that the call was governed rather than take
    # it on faith.
    envelope_ok = (isinstance(api.get("_loop"), dict)
                   and api["_loop"]["model_calls"] == 0
                   and api["_loop"]["template"] == "atomic_code_only"
                   and api["_loop"]["loop_id"])

    # the write test uses a TEMP store: a suite run must not modify the
    # source tree, and the first version of this appended to the package on
    # every run.
    global ADVICE_STORE_PATH
    _prev_store, ADVICE_STORE_PATH = ADVICE_STORE_PATH, os.path.join(
        tempfile.mkdtemp(prefix="studio_advice_"), "user-advice.jsonl")

    # THE ONE WRITE: advising a loop, exactly as the Studio design has it —
    # a person types guidance on a specific loop and it is stored scoped and
    # attributable. An empty note is refused at the edge.
    conn.request("POST", "/api/runs/run-1/user-intelligence",
                 body=json.dumps({"text": "try sklearn VIF for collinearity",
                                  "scope": "loop", "target": "loop7",
                                  "guidance_type": "package_suggestion"}),
                 headers={"Content-Type": "application/json"})
    wrote = conn.getresponse()
    advice = json.loads(wrote.read())
    conn.request("POST", "/api/runs/run-1/user-intelligence",
                 body=json.dumps({"text": "   "}),
                 headers={"Content-Type": "application/json"})
    empty = conn.getresponse()
    empty_body = json.loads(empty.read())

    # the browser's event stream speaks the canonical vocabulary — against a
    # REAL saved run, so "no untyped passthrough" is a finding rather than a
    # vacuous truth about an empty list.
    conn.request("GET", "/api/runs")
    all_runs = json.loads(conn.getresponse().read())["runs"]
    real_id = all_runs[0]["run_id"] if all_runs else "run-1"
    conn.request("GET", f"/api/runs/{real_id}/events")
    stream = json.loads(conn.getresponse().read())

    # THE ROUTED SURFACE (D-3): every declared route resolves, an undeclared
    # one 404s, and the contract is served as DATA so a client enumerates
    # what this deployment serves instead of discovering it by 404.
    def _get(path):
        """A FRESH connection per request: the handler closes after each
        response, so reusing one connection across many probes stalls."""
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        c.request("GET", path)
        r = c.getresponse()
        payload, status = r.read(), r.status
        c.close()
        return status, payload

    contract = json.loads(_get("/routes")[1])
    declared_ok = all(_get(p)[0] == 200
                      for p in ("/", "/pricing", "/app", "/app/runs"))
    shell_src = _get("/app/runs")[1].decode()
    undeclared_404 = all(_get(p)[0] == 404
                         for p in ("/app/admin/secrets",
                                   "/definitely-not-a-page"))

    ADVICE_STORE_PATH = _prev_store
    holder["h"].shutdown()
    check("studio_serves_shell_api_and_clean_404s",
          "Loop Engine Studio" in shell and api["cards"]
          and notfound.status == 404 and "error" in nf_body,
          f"live on an ephemeral port ({port})")
    check("reads_cross_into_a_loop_and_say_so_over_the_wire",
          envelope_ok,
          f"_loop {api.get('_loop', {}).get('loop_id')} rode back with the "
          "payload, 0 semantic calls")
    check("a_person_can_advise_a_loop_and_an_empty_note_is_refused",
          wrote.status == 201 and advice["scope"] == "loop"
          and advice["target"] == "loop7"
          and advice["guidance_type"] == "package_suggestion"
          and advice["author"] == "studio-user" and advice["advice_id"]
          and empty.status == 400 and "error" in empty_body,
          f"advice {advice.get('advice_id')} stored scoped + attributable; "
          "empty refused with 400")
    check("the_event_stream_is_the_canonical_vocabulary",
          stream["vocabulary_size"] == 59 and stream["count"] > 0
          and stream["families_present"]
          and not [f for f in stream["families_present"]
                   if f.startswith("x.")],
          f"run {real_id}: {stream['count']} events, "
          f"{len(stream['families_present'])} families, no untyped passthrough")

    # THE VIEWS: a Loop Tree whose loops are SELECTABLE (a loop you cannot
    # select is one you cannot inspect or advise), an inspector, a Solution
    # Canvas distinct from the tree, and keyboard reachability.
    detail = build_projection("run", real_id)
    check("the_studio_renders_a_selectable_loop_tree_with_an_inspector",
          "pickLoop" in shell_src and "looptree" in shell_src
          and 'role="button"' in shell_src and "onkeydown" in shell_src
          and isinstance(detail.get("tree_json"), list)
          and isinstance(detail.get("loops"), list) and detail["loops"]
          and "iterations" in detail["loops"][0]
          and "modes" in detail["loops"][0],
          f"{len(detail['loops'])} loops with per-loop rollups; tree is "
          "clickable and keyboard-reachable")

    check("studio_api_and_shell_agree_on_code_and_four_layer_routes",
          'api("loops")' in shell_src and 'api("nodes")' not in shell_src
          and 'api("intelligence")' in shell_src
          and "intelligence" in contract["api_endpoints"],
          "Code Intelligence uses /api/loops; four layers use /api/intelligence")

    check("the_shell_supports_path_routing_not_only_hash_fragments",
          "currentParts" in shell_src and "popstate" in shell_src
          and "pushState" in shell_src,
          "a Studio URL is shareable and bookmarkable; a hash-only shell "
          "cannot be deep-linked into from outside the page")

    check("the_routed_surface_serves_declared_paths_and_404s_the_rest",
          declared_ok and undeclared_404
          and contract["public_routes"] >= 26
          and contract["studio_routes"] >= 13
          and contract["every_api_endpoint_runs_as_a_loop"] is True
          and "/app/runs/:id/playback" in contract["studio"]
          and "/app/intelligence" in contract["studio"],
          f"{contract['public_routes']} public + {contract['studio_routes']} "
          "studio routes served; unknown paths 404")

    passed = sum(1 for r in results if r["passed"])
    report = {"tests": results, "passed": passed, "total": len(results),
              "all_passed": passed == len(results)}
    shutil.rmtree(_RUNS, ignore_errors=True)
    _RUNS = previous_runs
    return report
