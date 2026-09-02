"""Loop Engine Studio server over saved run history and live state.

Architectural role: internal local viewing service (a serving adapter, like the
model gateway is for models).

Owns:
    - the local HTTP surface (stdlib http.server — no new dependencies) that
      serves the Studio shell (a passive String at
      ``strings/studio_shell.html``) and the projection APIs;
    - saved-run projections computed at request time (never a generated
      snapshot): runs list, per-run overview/loop-tree/timeline/model-calls,
      per-run stuckness and safe runtime controls; the intelligence inventory (live harvest of the
      banks + generated candidates + meta pack); the code-node inventory
      (architecture map + docstrings); the solution library (records);
      the improvements view (per-run stuckness + candidates awaiting
      validation); and read-only harness, MCP, skill, approval, and context
      artifact views when their authoritative live objects are supplied.

Does not own:
    - any mutation: the Studio is READ-ONLY in this phase — edits become
      ChangeProposals through their own lane, never through HTTP;
    - analytics semantics (run_quality/run_analytics own them) or the
      saved event log itself (run_history.py owns the store).

Public entry points:
    - serve(StudioServeRequest(...)) — blocking; ``--studio`` wraps it
    - build_projection(name, arg) — the API payloads (test-callable without
      a socket)

Key invariants:
    - every payload derives from saved-run files, live stores, or records
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
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

_PKG = os.path.dirname(os.path.dirname(__file__))
from .run_history import (
    RunHistoryIntegrityError, SavedRunBundle, default_runs_dir,
    load_saved_run_bundle, saved_run_ids)
from .studio_operational_views import (
    StudioReadSources, project_run_runtime, project_runtime_inventory)

_RUNS = default_runs_dir()
_READ_SOURCES = StudioReadSources()


@dataclass(frozen=True)
class StudioServeRequest:
    """Local port, Run History directory, and optional read-only sources."""

    port: int = 8765
    runs_dir: str = ""
    read_sources: "StudioReadSources | None" = None

    def __post_init__(self) -> None:
        if not 0 <= self.port <= 65535:
            raise ValueError("Studio port must be from 0 through 65535")


def _load_run_bundle_as_historical_loop(run_id: str, *, ledger=None):
    """Read one verified saved-run bundle through a Historical Run Loop.

    No caller reads saved run history
    directly — it invokes the loop that owns the history.  The read is
    deterministic, stops after one accepted success, and records
    ``intelligence.runtime_history_solution.retrieved`` on the caller's ledger when one is
    given, so "the Studio read the history" is evidence rather than an
    assumption."""
    from ..loop.intelligence_loops import serve_historical_intelligence
    value = serve_historical_intelligence(
        f"run:{run_id}",
        lambda: load_saved_run_bundle(_RUNS, run_id), ledger=ledger)["value"]
    if not isinstance(value, SavedRunBundle):
        raise RunHistoryIntegrityError(
            f"saved run {run_id!r} could not be verified")
    return value


def _load_run_as_historical_loop(run_id: str, *, ledger=None):
    """Compatibility helper returning only the verified event history."""
    return _load_run_bundle_as_historical_loop(
        run_id, ledger=ledger).history


def _run_loads() -> tuple[list[SavedRunBundle], list[dict]]:
    bundles, errors = [], []
    if not os.path.isdir(_RUNS):
        return bundles, errors
    from ..loop.recursive_loop import LoopError
    for run_id in saved_run_ids(_RUNS):
        try:
            bundles.append(_load_run_bundle_as_historical_loop(run_id))
        except (OSError, KeyError, ValueError, TypeError, AttributeError,
                json.JSONDecodeError, RunHistoryIntegrityError, LoopError) as exc:
            errors.append({
                "run_id": run_id, "events": 0, "calls": 0, "tokens": 0,
                "intact": False, "goal": "Unreadable saved run",
                "outcome_available": False, "terminal_code": "RUN_INVALID",
                "solved": False, "artifact_count": 0,
                "verification_passed": False,
                "error_code": "RUN_HISTORY_INVALID",
                "error": str(exc)[:240],
            })
    return bundles, errors


def _run_histories():
    bundles, _errors = _run_loads()
    return [bundle.history for bundle in bundles]


def _product_projection(outcome: "dict | None") -> dict:
    if not outcome:
        return {"record_type": "studio_product_outcome/v1",
                "available": False, "terminal_code": "", "solved": False,
                "summary": "", "failure_code": "", "verification": {},
                "artifacts": [], "workspace": "", "limitations": [],
                "questions": [], "next_action": "", "graph_digest": "",
                "selected_canvas": {}}
    workspace = str(outcome.get("workspace") or "")
    artifacts = []
    for item in outcome.get("artifacts", ()):
        path = str(item.get("path") or "")
        relative = path
        if workspace and path:
            try:
                relative = os.path.relpath(path, workspace)
            except ValueError:
                relative = os.path.basename(path)
        artifacts.append({
            "path": path, "relative_path": relative,
            "media_type": str(item.get("media_type") or ""),
            "byte_count": int(item.get("byte_count") or 0),
            "digest": str(item.get("digest") or ""),
            "verified": bool(item.get("verified")),
            "format_valid": bool(item.get("format_valid")),
            "present": bool(path and os.path.isfile(path)),
        })
    return {
        "record_type": "studio_product_outcome/v1", "available": True,
        "terminal_code": str(outcome.get("terminal_code") or ""),
        "solved": bool(outcome.get("solved")),
        "summary": str(outcome.get("summary") or ""),
        "failure_code": str(outcome.get("failure_code") or ""),
        "verification": dict(outcome.get("verification") or {}),
        "artifacts": artifacts, "workspace": workspace,
        "limitations": list(outcome.get("limitations") or ()),
        "questions": list(outcome.get("questions") or ()),
        "next_action": str(outcome.get("next_action") or ""),
        "graph_digest": str(outcome.get("graph_digest") or ""),
        "selected_canvas": dict(outcome.get("selected_canvas") or {}),
    }


def _run_row(bundle: SavedRunBundle) -> dict:
    ch = bundle.history
    calls = [e for e in ch.event_log if e.event_type == "model_invocation"]
    goal = next((e.detail.get("goal", "") for e in ch.event_log
                 if e.event_type == "loop_init"), "")
    product = _product_projection(bundle.outcome)
    verification = product["verification"]
    return {"run_id": ch.run_id, "events": len(ch.event_log),
            "calls": len(calls),
            "tokens": sum(e.prompt_tokens + e.eval_tokens for e in calls),
            "intact": ch.verify_chain()["intact"], "goal": goal,
            "outcome_available": product["available"],
            "terminal_code": product["terminal_code"],
            "solved": product["solved"],
            "artifact_count": len(product["artifacts"]),
            "verification_passed": bool(
                verification.get("passed")
                or verification.get("verdict") == "accept"),
            "error_code": "", "error": ""}


def _run_rows() -> list[dict]:
    bundles, errors = _run_loads()
    return [*[_run_row(bundle) for bundle in bundles], *errors]


def _run_detail(rid: str) -> dict:
    from ..code_nodes.run_quality import stuckness_report
    bundle = _load_run_bundle_as_historical_loop(rid)
    ch = bundle.history
    product = _product_projection(bundle.outcome)
    calls, events, iters = [], [], 0
    spawned_by_owner: dict = {}
    goals: dict = {}
    for e in ch.event_log:
        if e.event_type == "loop_init":
            goals[e.loop_id] = e.detail.get("goal", "")
        elif e.event_type == "loop_spawn":
            spawned_by_owner.setdefault(
                e.spawning_loop_id, []).append(e.loop_id)
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
        spawned = spawned_by_owner.get(lid, [])
        for i, k in enumerate(spawned):
            last = i == len(spawned) - 1
            lines += tree(k, prefix + ("└── " if last else "├── "))
        return lines
    starting_ids = [loop_id for loop_id in goals
                    if not any(loop_id in values
                               for values in spawned_by_owner.values())]
    tree_txt = "\n".join(sum((tree(loop_id)
                              for loop_id in starting_ids), []))

    # STRUCTURED tree + per-loop rollups, so the Studio can render a
    # clickable Loop Tree with an inspector instead of a text blob.  A text
    # tree shows shape; it cannot be selected, and a loop you cannot select
    # is a loop you cannot inspect or advise.
    per_loop: dict = {}
    for e in ch.event_log:
        if not e.loop_id:
            continue
        row = per_loop.setdefault(e.loop_id, {
            "loop_id": e.loop_id, "goal": goals.get(e.loop_id, ""),
            "spawning_loop_id": "", "iterations": 0, "calls": 0,
            "tokens": 0,
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
    for spawning_loop_id, spawned_ids in spawned_by_owner.items():
        for spawned_loop_id in spawned_ids:
            if spawned_loop_id in per_loop:
                per_loop[spawned_loop_id]["spawning_loop_id"] = (
                    spawning_loop_id)

    def node(lid):
        return {"loop_id": lid, **per_loop.get(lid, {"goal": goals.get(lid, "")}),
                "spawned_loops": [node(k)
                                  for k in spawned_by_owner.get(lid, [])]}

    tree_json = [node(loop_id) for loop_id in starting_ids]
    starting_loop_ids = set(starting_ids)
    playback_events = [event for event in events if (
        event["type"] == "model_invocation"
        or (event["loop"] in starting_loop_ids
        and event["type"] in {"loop_init", "iteration", "terminal",
                              "fallback", "budget_stop", "cancel"}))]
    product_events = []
    if product["available"]:
        product_events.extend((
            {"type": "product.verification", "loop": "run", "step": "verify",
             "mode": "deterministic", "tokens": "",
             "detail": ("passed" if product["verification"].get("passed")
                        or product["verification"].get("verdict") == "accept"
                        else "not passed")},
            {"type": "product.terminal", "loop": "run", "step": "route",
             "mode": "deterministic", "tokens": "",
             "detail": product["terminal_code"]},
        ))
        product_events.extend({
            "type": "product.material_question", "loop": "run",
            "step": "route", "mode": "deterministic", "tokens": "",
            "detail": f"[{item.get('answer_slot', '')}] "
                      f"{item.get('question', '')}"}
            for item in product["questions"])
        product_events.extend({
            "type": "product.artifact", "loop": "run", "step": "integrate",
            "mode": "deterministic", "tokens": "",
            "detail": item["relative_path"]}
            for item in product["artifacts"])
    return {"run_id": rid,
            "goal": next(iter(goals.values()), ""),
            "totals": {"events": len(ch.event_log), "iterations": iters,
                       "calls": len(calls),
                       "prompt_tokens": sum(c["prompt_tokens"]
                                            for c in calls),
                       "eval_tokens": sum(c["eval_tokens"] for c in calls)},
            "chain_intact": ch.verify_chain()["intact"],
            "stuckness": stuckness_report(ch.event_log),
            "tree": tree_txt, "tree_json": tree_json,
            "loops": list(per_loop.values()),
            "events": events,
            "playback_events": [*playback_events, *product_events],
            "calls": calls, "product": product,
            "runtime": project_run_runtime(ch.event_log)}


def _strings_inventory() -> dict:
    from ..loop.loop_templates import template_records
    from ..strings.solution_shaping import solution_shaping_pack
    from ..code_nodes.measurement import measurement_pack
    from ..strings.interrogation import interrogation_bank as _interrogation_bank
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
    from ..strings.interrogation import interrogation_bank as _interrogation_bank
    seen_interrogation_ids: dict[str, int] = {}
    for q in _interrogation_bank():
        slug = f"{q.category}.{q.subcategory}" if q.subcategory \
            else q.category
        occurrence = seen_interrogation_ids.get(slug, 0)
        seen_interrogation_ids[slug] = occurrence + 1
        record_id = f"interrogation.{slug}" if not occurrence \
            else f"interrogation.{slug}.{occurrence}"
        add(record_id, "question",
            q.question, "interrogation", q.subcategory or q.category,
            "registered", "interrogation_bank")
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
    for f, key in (("run_history-bootstrap-20260823.json", "solution_assets"),):
        p = os.path.join(evid, f)
        if os.path.exists(p):
            for a in json.load(open(p)).get(key, []):
                out.append({"id": a, "fingerprint": "see asset record",
                            "evidence": "run_history bootstrap",
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
    for ch in _run_histories():
        r = stuckness_report(ch.event_log)
        stuck.append({"run": ch.run_id, "score": r["stuckness_score"],
                      "indicators": ", ".join(i["indicator"] for i in
                                              r["dominant_indicators"])
                      or "none — flowed",
                      "interventions": ", ".join(
                          r["suggested_interventions"]) or "—"})
    bank = load_candidate_bank()
    return {"cards": [
        {"label": "candidates awaiting validation", "value": len(bank)},
        {"label": "saved runs", "value": len(stuck)},
        {"label": "stuck runs", "value":
            sum(1 for s in stuck if s["score"] > 0.5)}],
        "stuckness": sorted(stuck, key=lambda s: -s["score"]),
        "honesty": "candidates never self-promote — registration crosses "
                   "the evidence gate after they win on real tasks"}


def _summary() -> dict:
    rows = _run_rows()
    intelligence = _intelligence_inventory()["summary"]
    return {"cards": [
        {"label": "saved runs", "value": len(rows), "link": "runs"},
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
        "honesty": "every number is computed from saved run history at request "
                   "time; smoke evidence proves plumbing, never benchmarks"}


def build_projection(name: str, arg: str = "") -> dict:
    if name == "summary":
        return _summary()
    if name == "runs":
        return {"runs": _run_rows()}
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
    if name == "runtime":
        return project_runtime_inventory(_READ_SOURCES)
    raise KeyError(name)


def _ledger_events_for(run_id: str) -> list:
    """The raw ledger rows behind one run, for the canonical projection.
    Saved run history stores canonical events already, so its bodies are
    replayed as their source rows; a run with no saved history streams
    empty rather than inventing activity."""
    for ch in _run_histories():
        if ch.run_id == run_id:
            from .run_history import as_ledger_event
            return [as_ledger_event(event) for event in ch.event_log]
    return []


#: Optional read source for previously governed User Feedback Intelligence.
ADVICE_STORE_PATH: "str | None" = None


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):                    # quiet by design
        pass

    def _security_headers(self) -> None:
        """Headers for a local interface that renders saved task content."""
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'none'")

    def do_GET(self):
        from .saas_routes import serve_api, live_events, resolve_route
        try:
            clean_path = self.path.split("?")[0]
            if clean_path.rstrip("/") in ("/routes", "/api/routes"):
                # Serve the route contract before the generic /api dispatcher.
                # Otherwise /api/routes is mistaken for a projection name.
                from .saas_routes import route_contract, PUBLIC_ROUTES, \
                    STUDIO_ROUTES
                payload = {**route_contract(),
                           "public": list(PUBLIC_ROUTES),
                           "studio": list(STUDIO_ROUTES)}
                body = json.dumps(payload).encode()
                ctype = "application/json"
            elif clean_path.startswith("/api/"):
                parts = [unquote(p) for p in
                         clean_path[5:].split("/") if p]
                if not parts:
                    raise KeyError("/api/ is not a declared endpoint")
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
            else:
                route = resolve_route(clean_path)
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
        except (RunHistoryIntegrityError, ValueError) as e:
            body = json.dumps({
                "error": str(e), "error_code": "RUN_HISTORY_INVALID"}).encode()
            ctype = "application/json"
            self.send_response(422)
        except (KeyError, FileNotFoundError) as e:
            body = json.dumps({"error": str(e)}).encode()
            ctype = "application/json"
            self.send_response(404)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        """Studio is read-only. Mutations require a separate governed API."""
        body = json.dumps({
            "error": "Loop Engine Studio is read-only",
            "error_code": "METHOD_NOT_ALLOWED",
            "next_action": (
                "Submit feedback through a separately authorized User "
                "Feedback Intelligence operation.")}).encode()
        self.send_response(405)
        self.send_header("Allow", "GET")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)


def serve(request: StudioServeRequest = StudioServeRequest(), ready=None) -> None:
    """Blocking local server (127.0.0.1 only — a workbench, not a deploy)."""
    global _RUNS, _READ_SOURCES
    if request.runs_dir:
        _RUNS = default_runs_dir(request.runs_dir)
    if request.read_sources is not None:
        _READ_SOURCES = request.read_sources
    httpd = ThreadingHTTPServer(("127.0.0.1", request.port), _Handler)
    actual_port = int(httpd.server_address[1])
    if ready is not None:
        ready(httpd)                      # test mode: no banner
    else:
        print(
            f"Loop Engine Studio: http://127.0.0.1:{actual_port} "
            "(Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


def self_test() -> dict:
    import hashlib
    import tempfile
    import shutil
    global _RUNS, _READ_SOURCES
    previous_runs, _RUNS = _RUNS, tempfile.mkdtemp(prefix="studio_runs_")
    previous_sources, _READ_SOURCES = _READ_SOURCES, StudioReadSources()
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
        from .run_history import RunHistory
        _lg = LoopLedger()
        as_practitioner_loop("studio projection fixture", lambda: "ok",
                             ledger=_lg)
        _ch = RunHistory.from_ledger(_lg.events,
                                    run_id="studio-self-test-fixture")
        _ch.commit()
        _ch.save(_RUNS)          # commit() only marks it; save() writes the run
        fixture_artifact = os.path.join(_RUNS, "result.txt")
        with open(fixture_artifact, "w", encoding="utf-8") as stream:
            stream.write("ok")
        from .run_history import bind_product_outcome
        bind_product_outcome(_RUNS, "studio-self-test-fixture", {
            "record_type": "solve_outcome/v3",
            "run_id": "studio-self-test-fixture",
            "terminal_code": "COMPLETED_VERIFIED",
            "status": "COMPLETED_VERIFIED", "solved": True,
            "summary": "Verified Studio fixture.", "failure_code": "",
            "verification": {"passed": True},
            "artifacts": [{"path": fixture_artifact,
                           "media_type": "text/plain", "byte_count": 2,
                           "digest": hashlib.sha256(b"ok").hexdigest(),
                           "verified": True,
                           "format_valid": True}],
            "workspace": _RUNS, "limitations": [],
            "next_action": "Inspect the result.",
            "graph_digest": "b" * 64,
            "selected_canvas": {"mermaid": "flowchart TD\n  A --> B",
                                "loop_graph": {"vertices": [{
                                    "vertex_id": "solution.a",
                                    "purpose": "component",
                                    "operation_ref": "fixture",
                                    "selected_mode": "deterministic"}]}},
        })

    # 1. every projection builds from live data (no server needed).
    s = build_projection("summary")
    runs = build_projection("runs")["runs"]
    strings = build_projection("strings")
    intelligence = build_projection("intelligence")
    loops = build_projection("loops")["loops"]
    imp = build_projection("improvements")
    runtime = build_projection("runtime")
    check("projections_compute_from_live_run_histories_and_stores",
          s["cards"] and runs and len(strings["strings"]) > 100
          and len(intelligence["summary"]["layers"]) == 4
          and intelligence["summary"]["total_items"] >= 100
          and len(loops) >= 30 and "honesty" in imp
          and len(runtime["harnesses"]["items"]) == 4,
          f"{len(runs)} runs, {len(strings['strings'])} strings, "
          f"{len(loops)} loops — at request time")

    # 2. a run detail carries overview + tree + playback events + calls +
    # stuckness, chain-verified.
    d = build_projection("run", runs[0]["run_id"])
    check("run_detail_projects_playback_tree_calls_stuckness",
          d["chain_intact"] and d["events"] and d["tree"]
          and "stuckness_score" in d["stuckness"]
          and d["totals"]["events"] == len(d["events"])
          and d["runtime"]["record_type"] == "studio_run_runtime/v2"
          and d["product"]["terminal_code"] == "COMPLETED_VERIFIED"
          and d["product"]["artifacts"][0]["relative_path"] == "result.txt"
          and d["product"]["artifacts"][0]["present"] is True
          and d["playback_events"][-1]["type"] == "product.artifact")

    # Safe operational views use allowlists and report missing saved-history
    # emitters instead of starting a second history store.
    from .studio_operational_views import _view_test_cases
    results.extend(_view_test_cases())

    # 3. one LIVE request over HTTP: shell + an API route + a clean 404.
    import http.client
    holder = {}
    t = threading.Thread(target=serve, kwargs={
        "request": StudioServeRequest(port=0),
        "ready": lambda h: holder.update(h=h)}, daemon=True)
    t.start()
    import time
    for _ in range(50):
        if "h" in holder:
            break
        time.sleep(0.05)
    port = holder["h"].server_address[1]
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request("GET", "/")
    shell_response = conn.getresponse()
    shell = shell_response.read().decode()
    conn.request("GET", "/api/summary")
    api = json.loads(conn.getresponse().read())
    conn.request("GET", "/api/runtime")
    runtime_api = json.loads(conn.getresponse().read())
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

    # Candidate User Feedback may be read from an explicit test store. Studio
    # itself remains read-only.
    global ADVICE_STORE_PATH
    _prev_store, ADVICE_STORE_PATH = ADVICE_STORE_PATH, os.path.join(
        tempfile.mkdtemp(prefix="studio_advice_"), "user-advice.jsonl")

    # A POST is refused at the server boundary. User Feedback Intelligence has
    # a separate governed operation and must not hide behind a read-only UI.
    conn.request("POST", "/api/runs/run-1/user-intelligence",
                 body=json.dumps({"text": "try sklearn VIF for collinearity",
                                  "scope": "loop", "target": "loop7",
                                  "guidance_type": "package_suggestion"}),
                 headers={"Content-Type": "application/json"})
    wrote = conn.getresponse()
    write_refusal = json.loads(wrote.read())

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
    api_contract_status, api_contract_body = _get("/api/routes")
    empty_api_status, _empty_api_body = _get("/api/")
    declared_ok = all(_get(p)[0] == 200
                      for p in ("/", "/studio", "/app", "/app/runs",
                                f"/app/runs/{real_id}/result",
                                f"/app/runs/{real_id}/runtime"))
    shell_src = _get("/app/runs")[1].decode()
    undeclared_404 = all(_get(p)[0] == 404
                         for p in ("/pricing", "/login", "/signup",
                                   "/app/admin/secrets",
                                   "/definitely-not-a-page"))

    ADVICE_STORE_PATH = _prev_store
    holder["h"].shutdown()
    check("studio_serves_shell_api_and_clean_404s",
          "Loop Engine Studio" in shell and api["cards"]
          and runtime_api["record_type"] == "studio_runtime_inventory/v1"
          and len(runtime_api["harnesses"]["items"]) == 4
          and notfound.status == 404 and "error" in nf_body
          and shell_response.getheader("X-Content-Type-Options") == "nosniff"
          and "frame-ancestors 'none'" in str(
              shell_response.getheader("Content-Security-Policy") or ""),
          f"live on an ephemeral port ({port})")
    check("reads_cross_into_a_loop_and_say_so_over_the_wire",
          envelope_ok,
          f"_loop {api.get('_loop', {}).get('loop_id')} rode back with the "
          "payload, 0 semantic calls")
    check("studio_is_read_only_and_refuses_hidden_feedback_writes",
          wrote.status == 405
          and wrote.getheader("Allow") == "GET"
          and write_refusal["error_code"] == "METHOD_NOT_ALLOWED",
          "feedback requires a separate governed operation")
    from .event_vocabulary import EVENT_FAMILIES
    check("the_event_stream_is_the_canonical_vocabulary",
          stream["vocabulary_size"] == len(EVENT_FAMILIES)
          and stream["count"] > 0
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
          and "modes" in detail["loops"][0]
          and isinstance(detail.get("product"), dict)
          and isinstance(detail.get("playback_events"), list),
          f"{len(detail['loops'])} loops with per-loop rollups; tree is "
          "clickable and keyboard-reachable")

    check("studio_api_and_shell_agree_on_code_and_four_layer_routes",
          'api("loops")' in shell_src and 'api("nodes")' not in shell_src
          and 'api("intelligence")' in shell_src
          and 'api("runtime")' in shell_src
          and "intelligence" in contract["api_endpoints"],
          "Code Intelligence uses /api/loops; four layers use /api/intelligence")

    check("the_shell_supports_path_routing_not_only_hash_fragments",
          "currentParts" in shell_src and "popstate" in shell_src
          and "pushState" in shell_src,
          "a Studio URL is shareable and bookmarkable; a hash-only shell "
          "cannot be deep-linked into from outside the page")

    check("the_routed_surface_serves_declared_paths_and_404s_the_rest",
          declared_ok and undeclared_404
          and api_contract_status == 200
          and json.loads(api_contract_body) == contract
          and empty_api_status == 404
          and contract["public_routes"] == 2
          and contract["studio_routes"] >= 17
          and contract["every_api_endpoint_runs_as_a_loop"] is True
          and contract["studio_read_only"] is True
          and contract["allowed_http_methods"] == ["GET"]
          and "/app/runs/:id/playback" in contract["studio"]
          and "/app/runs/:id/result" in contract["studio"]
          and "/app/runs/:id/runtime" in contract["studio"]
          and "/app/intelligence" in contract["studio"]
          and "/app/runtime" in contract["studio"]
          and "runtime" in contract["api_endpoints"],
          f"{contract['public_routes']} public + {contract['studio_routes']} "
          "studio routes served; unknown paths 404")

    source_run = os.path.join(_RUNS, real_id)
    corrupt_run = os.path.join(_RUNS, "corrupt-run")
    shutil.copytree(source_run, corrupt_run)
    corrupt_rows = build_projection("runs")["runs"]
    corrupt = next(row for row in corrupt_rows
                   if row["run_id"] == "corrupt-run")
    check("one_corrupt_run_is_isolated_without_breaking_the_runs_list",
          corrupt["error_code"] == "RUN_HISTORY_INVALID"
          and corrupt["intact"] is False
          and any(row["run_id"] == real_id and row["intact"]
                  for row in corrupt_rows),
          "invalid run remains visible; verified siblings remain readable")

    passed = sum(1 for r in results if r["passed"])
    report = {"tests": results, "passed": passed, "total": len(results),
              "all_passed": passed == len(results)}
    shutil.rmtree(_RUNS, ignore_errors=True)
    _RUNS = previous_runs
    _READ_SOURCES = previous_sources
    return report
