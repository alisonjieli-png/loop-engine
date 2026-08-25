"""Live run demo — watch a real PractitionerLoop execute in real time.

Architectural role: code_nodes (an observation surface over the canonical
runtime; owner ask 2026-08-24: "see it start the first practitioner loop,
see it pull down intelligence... in real time with a visual indication of
what it is doing as well as logs out to a console").

Owns:
    - TappedLedger: the shared LoopLedger with a per-event callback, so
      every step, mode choice, spawn, and terminal transition is observed
      the moment it is recorded — the SAME event stream the Chronicle is
      built from, not a parallel telemetry path;
    - run_live_demo(): runs the stage-0 deterministic fixture through the
      REAL Loop in a background thread while a localhost page shows the
      current step on the loop rail, the intelligence pulled, and a live
      console — and mirrors every event to stdout;
    - the /events.json polling endpoint (since=N incremental slices).

Does not own:
    - the runtime (recursive_loop), the smoke lane (smoke_ladder — the
      demo runs ITS fixture), or Studio (studio_server) — this is the
      one-command "see it run" surface; Studio's Runs tab is the routed
      product version of the same stream.

Public entry points:
    - run_live_demo(port=8770, pace_seconds=0.5, serve_forever=False)
    - TappedLedger(on_event=...)

Key invariants:
    - events reach the tap in recorded order, exactly once;
    - demo pacing is DECLARED on the page ("demo pacing"), never hidden —
      pace 0 runs at true speed;
    - localhost only; the surface is declared in forbidden_paths
      network_allowed like studio_server.

Verification: self_test() — ordered tap relay, incremental event serving
over a real socket, terminal event visibility, page carries the rail.
"""
from __future__ import annotations

import json
import os
import threading
import time

from ..loop.recursive_loop import LoopLedger

STEP_LABELS = ("orient", "research", "decide", "act", "verify", "commit")


class TappedLedger(LoopLedger):
    """The canonical ledger with a live observer: every record() call
    also invokes ``on_event`` (after appending), so a viewer sees the
    run exactly as the evidence stream sees it."""

    def __init__(self, on_event=None):
        super().__init__()
        self._on_event = on_event

    def record(self, **kw) -> None:
        super().record(**kw)
        if self._on_event is not None:
            self._on_event(self.events[-1])


def _console_line(e: dict) -> str:
    step = e.get("step") or e.get("event", "?")
    mode = e.get("mode", "")
    out = str(e.get("output") or e.get("goal") or e.get("note") or "")[:110]
    return f"[{e.get('loop_id','?')}] {step}" + (f" ({mode})" if mode else "") \
           + (f" — {out}" if out else "")


_PAGE = """<!doctype html><meta charset="utf-8"><title>Loop Engine live run</title>
<style>body{font:14px/1.5 system-ui;margin:0;background:#12161b;color:#e8edf2}
.wrap{max-width:880px;margin:0 auto;padding:20px}
h1{font-size:1.2rem}.pace{color:#93a0ac;font-size:.8rem}
.rail{display:flex;gap:6px;flex-wrap:wrap;margin:14px 0}
.rail span{border:1.5px solid #2a323b;border-radius:8px;padding:.4em .8em;font-size:.82rem;color:#93a0ac}
.rail span.on{border-color:#4ec0ae;color:#4ec0ae;background:rgba(78,192,174,.12)}
.pull{margin:10px 0;font-size:.85rem;color:#4fb0d6}
pre{background:#0c0f13;border:1px solid #2a323b;border-radius:10px;padding:12px;
font:12px/1.6 ui-monospace,monospace;height:320px;overflow:auto;white-space:pre-wrap}
.done{color:#66bb6a;font-weight:600}</style>
<div class="wrap"><h1>Loop Engine — a real PractitionerLoop, live</h1>
<div class="pace">Deterministic stage-0 fixture · zero model calls · demo
pacing PACE_S s/step (pace 0 = true speed) · every line below is the same
event stream the run record is built from</div>
<div class="rail" id="rail">RAIL_SPANS</div>
<div class="pull" id="pull"></div><pre id="log"></pre>
<div id="st" class="pace">running…</div>
<div style="margin-top:14px;display:flex;gap:8px">
<input id="adv" placeholder="Advise this loop, like a coworker on Slack — 'try the rapidfuzz package'"
 style="flex:1;background:#0c0f13;border:1px solid #2a323b;border-radius:8px;color:#e8edf2;padding:.6em .8em;font:13px system-ui">
<button onclick="sendAdvice()" style="background:#4ec0ae;color:#0c0f13;border:0;border-radius:8px;padding:.6em 1em;font-weight:600;cursor:pointer">Advise</button>
<button onclick="fetch('/restart').then(()=>{since=0;log.textContent='';tick()})"
 style="background:transparent;color:#4fb0d6;border:1.5px solid #4fb0d6;border-radius:8px;padding:.6em 1em;font-weight:600;cursor:pointer">Run again</button>
</div>
<div class="pace" id="advst" style="margin-top:6px">Your advice becomes User
Intelligence: it is consulted (and recorded) at the start of each run.</div>
</div>
<script>
var since=0, log=document.getElementById('log');
function tick(){fetch('/events.json?since='+since).then(r=>r.json()).then(d=>{
 d.events.forEach(function(e){
  since++; log.textContent+=e.line+"\\n"; log.scrollTop=log.scrollHeight;
  if(e.step){document.querySelectorAll('#rail span').forEach(function(s){
    s.classList.toggle('on', s.dataset.s===e.step);});}
  if(e.pull){var p=document.getElementById('pull');
    p.textContent='intelligence pulled: '+e.pull;}
 });
 if(d.done){document.getElementById('st').innerHTML=
   '<span class="done">run complete</span> — '+since+' events recorded';}
 else setTimeout(tick, 400);
});}
tick();
function sendAdvice(){var v=document.getElementById('adv').value;
 fetch('/advice',{method:'POST',body:JSON.stringify({text:v})}).then(r=>r.json())
 .then(d=>{document.getElementById('advst').textContent = d.ok ?
  'Advice on file: '+d.on_file+' — consulted at the start of each run (press Run again to see it).' :
  'Refused: '+d.error; if(d.ok) document.getElementById('adv').value='';});}
</script>"""


def run_live_demo(port: int = 8770, pace_seconds: float = 0.5,
                  serve_forever: bool = False) -> dict:
    """Serve the live view on 127.0.0.1:``port`` and run the stage-0
    deterministic fixture through the real Loop in a background thread.
    Returns {"port", "events", "done"} handles; with serve_forever=True
    blocks until interrupted (the CLI path)."""
    import tempfile
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from .smoke_ladder import run_smoke_loop, _fixture
    from ..static_architecture.user_intelligence import AdviceStore

    state = {"events": [], "raw": [], "done": False, "runs": 0}
    advice = AdviceStore(os.path.join(
        tempfile.mkdtemp(prefix="live_demo_advice_"), "user_advice.jsonl"))

    def on_event(e):
        line = _console_line(e)
        print(line, flush=True)                      # the console log
        rec = {"line": line, "step": e.get("step", ""),
               "mode": e.get("mode", "")}
        out = str(e.get("output", ""))
        if e.get("step") in ("orient", "research") and out:
            rec["pull"] = out[:90]
        state["events"].append(rec)
        state["raw"].append(dict(e))
        if pace_seconds:
            time.sleep(pace_seconds)

    def runner():
        state["done"] = False
        state["runs"] += 1
        workdir = tempfile.mkdtemp(prefix="live_demo_")
        train, test, sample, out = _fixture(workdir)
        ledger = TappedLedger(on_event=on_event)
        from ..static_architecture.runtime_memory import RunNoteBoard
        board = RunNoteBoard(f"live-demo-{state['runs']}", ledger=ledger)
        board.write(f"run {state['runs']} starting — fixture ready",
                    loop_id="live", topic="status")
        # the loop's guidance check: consult USER INTELLIGENCE before the
        # run decides anything — recorded on the ledger, visible live.
        from ..loop.intelligence_loops import consult_guidance_as_loop
        hits = consult_guidance_as_loop(advice, "task", "live-demo",
                                        loop_id="live", ledger=ledger)["value"]
        for h in hits:
            print(f"[demo] your advice on file: {h['text'][:80]}", flush=True)
        run_smoke_loop("live demo: solve the deterministic fixture",
                       train_csv=train, test_csv=test, sample_csv=sample,
                       out_csv=out, ledger=ledger)
        state["done"] = True
        print("[demo] run complete —", len(state["events"]),
              "events recorded", flush=True)

    page = _PAGE.replace("PACE_S", str(pace_seconds)).replace(
        "RAIL_SPANS", "".join(f'<span data-s="{s}">{s}</span>'
                              for s in STEP_LABELS))

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):                   # keep stdout for events
            pass

        def do_POST(self):
            if self.path == "/advice":
                n = int(self.headers.get("Content-Length", 0))
                try:
                    text = json.loads(self.rfile.read(n)).get("text", "")
                    from ..loop.intelligence_loops import (
                        guidance_for_as_loop, leave_guidance_as_loop)
                    leave_guidance_as_loop(advice, text, scope="task",
                                           target="live-demo")
                    on_file = guidance_for_as_loop(advice, "task",
                                                   "live-demo")["value"]
                    body = json.dumps({"ok": True,
                                       "on_file": len(on_file)}).encode()
                    code = 200
                except ValueError as e:
                    body = json.dumps({"ok": False,
                                       "error": str(e)}).encode()
                    code = 400
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(404); self.end_headers()

        def do_GET(self):
            if self.path == "/restart" and state["done"]:
                threading.Thread(target=runner, daemon=True).start()
                body, ctype = b'{"ok": true}', "application/json"
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path == "/api/runs":
                body = json.dumps([{"run_id": "live",
                                    "runs_completed": state["runs"],
                                    "done": state["done"],
                                    "events": len(state["raw"])}]).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path == "/api/runs/live/events":
                from ..static_architecture.chronicle import to_canonical_events
                body = json.dumps(to_canonical_events(state["raw"]),
                                  default=str).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path == "/events/sse":
                # ONE vocabulary, another transport: the same events the
                # polling page reads, streamed as Server-Sent Events.
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                sent = 0
                try:
                    while True:
                        while sent < len(state["events"]):
                            payload = json.dumps(state["events"][sent])
                            self.wfile.write(
                                f"data: {payload}\n\n".encode())
                            self.wfile.flush()
                            sent += 1
                        if state["done"] and sent >= len(state["events"]):
                            self.wfile.write(b"event: done\ndata: {}\n\n")
                            self.wfile.flush()
                            return
                        time.sleep(0.15)
                except (BrokenPipeError, ConnectionResetError):
                    return
            if self.path.startswith("/events.json"):
                q = self.path.partition("since=")[2]
                since = int(q) if q.isdigit() else 0
                body = json.dumps({"events": state["events"][since:],
                                   "done": state["done"]}).encode()
                ctype = "application/json"
            else:
                body, ctype = page.encode(), "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    threading.Thread(target=runner, daemon=True).start()
    print(f"[demo] watch the run live at http://127.0.0.1:{port}", flush=True)
    if serve_forever:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    return {"port": port, "state": state, "server": srv}


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    # The demo drives a TABULAR run and then reads its output over a socket.
    # Without the declared dependencies the run cannot start, and the socket read
    # BLOCKS until it times out — a missing dependency surfacing as a
    # network hang, which is the least diagnosable failure shape there is.
    # Declare the dependency up front and fail fast with the remedy instead.
    try:
        import numpy                                       # noqa: F401
        import pandas                                      # noqa: F401
    except ImportError as exc:
        return {"tests": [{
            "test": "live_run_demo_self_test", "passed": False,
            "missing_dependency": exc.name,
            "detail": f"FAILED: missing {exc.name}. Reinstall Loop Engine."}],
            "passed": 0, "total": 1, "all_passed": False}

    # 1. the tap relays events in recorded order, exactly once.
    seen = []
    led = TappedLedger(on_event=lambda e: seen.append(e))
    from ..loop.recursive_loop import Loop, LoopConfig
    Loop("tap check", LoopConfig(framework="five_step", power="small"),
         ledger=led).run(max_steps=6)
    check("tap_relays_every_event_in_order",
          len(seen) == len(led.events)
          and [e.get("event") for e in seen[:1]] == ["init"]
          and any(e.get("event") == "terminal" for e in seen),
          f"{len(seen)} events, init first, terminal seen")

    # 2. a REAL live demo at pace 0: the server serves incremental slices
    # over a real socket and reports done with a terminal event visible.
    import urllib.request
    d = run_live_demo(port=0, pace_seconds=0)
    for _ in range(100):
        if d["state"]["done"]:
            break
        time.sleep(0.05)
    base = f"http://127.0.0.1:{d['port']}"
    runs = json.loads(urllib.request.urlopen(base + "/api/runs",
                                             timeout=5).read())
    canon = json.loads(urllib.request.urlopen(
        base + "/api/runs/live/events", timeout=5).read())
    import http.client
    conn = http.client.HTTPConnection("127.0.0.1", d["port"], timeout=5)
    conn.request("GET", "/events/sse")
    resp = conn.getresponse()
    sse_data, sse_done = 0, False
    for _ in range(400):
        line = resp.fp.readline().decode()
        if line.startswith("data:"):
            sse_data += 1
        if line.startswith("event: done"):
            sse_done = True
            break
    conn.close()
    check("api_and_sse_serve_the_one_event_stream",
          runs[0]["done"] and runs[0]["events"] == len(canon)
          and any(c["type"] == "loop.completed" for c in canon)
          and sse_done and sse_data >= len(d["state"]["events"]),
          f"/api/runs ok; {len(canon)} canonical events (lossless parity); "
          f"SSE streamed {sse_data} events to done")
    first = json.loads(urllib.request.urlopen(
        base + "/events.json?since=0", timeout=5).read())
    rest = json.loads(urllib.request.urlopen(
        base + f"/events.json?since={len(first['events'])}",
        timeout=5).read())
    page = urllib.request.urlopen(base + "/", timeout=5).read().decode()
    d["server"].shutdown()
    check("live_demo_serves_incremental_events_to_done",
          d["state"]["done"] and first["events"] and first["done"]
          and rest["events"] == [] and "terminal" in
          " ".join(e["line"] for e in first["events"]),
          f"{len(first['events'])} events served, terminal visible")
    # 2b. USER INTELLIGENCE through the live surface: POST advice, restart,
    # and the next run's event stream shows the guidance consultation.
    import urllib.request as _u
    d2 = run_live_demo(port=0, pace_seconds=0)
    for _ in range(100):
        if d2["state"]["done"]:
            break
        time.sleep(0.05)
    b2 = f"http://127.0.0.1:{d2['port']}"
    req = _u.Request(b2 + "/advice", method="POST",
                     data=json.dumps({"text": "try the rapidfuzz package"
                                      }).encode())
    posted = json.loads(_u.urlopen(req, timeout=5).read())
    _u.urlopen(b2 + "/restart", timeout=5).read()
    for _ in range(120):
        if d2["state"]["done"] and d2["state"]["runs"] == 2:
            break
        time.sleep(0.05)
    lines = " ".join(e["line"] for e in d2["state"]["events"])
    d2["server"].shutdown()
    check("advice_posted_then_consulted_on_next_run",
          posted["ok"] and posted["on_file"] == 1
          and d2["state"]["runs"] == 2 and "user_guidance" in lines,
          "POST /advice -> /restart -> user_guidance event in the stream")

    check("live_page_carries_the_step_rail",
          all(s in page for s in STEP_LABELS) and "demo\npacing" in page
          or all(s in page for s in STEP_LABELS) and "demo" in page,
          "rail + pacing declaration present")

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
