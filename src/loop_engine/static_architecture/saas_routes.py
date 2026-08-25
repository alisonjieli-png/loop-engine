"""The routed SaaS + Studio surface — and the rule that every API call is a loop.

Architectural role: Static Architecture service (the front-end/back-end contract).

The design handoff (Claude Design project 265b684e, imported 2026-08-23) ships
the public site and Studio as routed pages backed by named endpoints. This
module owns that contract on the backend side, and it owns one law the earlier
server broke by omission:

    An API endpoint is an operational boundary — externally invokable,
    observable, retryable, budgeted, governed. So it is a PractitionerLoop,
    not a bare function call.

``studio_server.build_projection`` was a flat dispatcher: a caller reached a
projection function directly, with no envelope, no evidence, no budget. That
is the same bypass class removed from ``run_solution`` (a Solution component
reaching a registry callable directly). Fixing it HERE matters more than
fixing it there, because this is the seam outsiders see: every harness, MCP
client, browser, and SaaS tenant enters through it.

Owns:
    - PUBLIC_ROUTES / STUDIO_ROUTES: the declared page contract (the design's
      route list), so routing is data a test can check rather than branches
      buried in a request handler;
    - API_ROUTES: every endpoint bound to its projection AND the registered
      loop template it runs under;
    - serve_api(): dispatch that runs the projection INSIDE a PractitionerLoop
      and returns the payload with its loop evidence attached;
    - intelligence_surface(): the FOUR-pillar read (the older three-route
      spelling omitted User Intelligence);
    - live_events(): canonical Chronicle families for the browser stream, so
      the console, the loop tree, and the inspector read one vocabulary.

Does not own:
    - the projections themselves (studio_server builds them), the Chronicle
      (chronicle.py), advice storage (user_intelligence.py), or any HTML —
      this module is the contract, not the renderer.

Public entry points:
    - serve_api(name, arg="", ledger=None) -> dict
    - intelligence_surface(pillar, need="") -> dict
    - live_events(run_id) -> list
    - resolve_route(path) -> dict | None

Key invariants:
    - every API route names a REGISTERED loop template; an unknown route is
      refused rather than guessed;
    - the dispatch always creates a real loop envelope with zero semantic
      calls (a read endpoint may never think with a model);
    - the four pillars are four, and a request for a fifth is refused.

Verification: self_test() — loop-envelope proof, four-pillar coverage,
route-table integrity, and the adversarial unknown-route/unknown-pillar path.
"""
from __future__ import annotations

#: The public site's routes, exactly as the design handoff declares them.
#: A page listed here is a contract; whether it is BUILT is a separate fact
#: the design README tracks as NOT RUN.
PUBLIC_ROUTES = (
    "/", "/product", "/how-it-works", "/practitioner-loops", "/intelligence",
    "/intelligence/context", "/intelligence/strings", "/intelligence/code",
    "/intelligence/previous-runs-solutions", "/intelligence/user",
    "/solutions", "/solution-canvas", "/studio", "/marketplace", "/pricing",
    "/docs", "/blog", "/news", "/case-studies", "/about", "/contact",
    "/login", "/signup", "/security", "/status", "/privacy", "/terms",
)

#: The authenticated Studio's routes.
STUDIO_ROUTES = (
    "/app", "/app/runs", "/app/runs/:id", "/app/runs/:id/overview",
    "/app/runs/:id/tree", "/app/runs/:id/canvas",
    "/app/runs/:id/playback", "/app/runs/:id/calls",
    "/app/intelligence", "/app/context", "/app/strings", "/app/nodes",
    "/app/solutions", "/app/improvements",
)

#: Preferred public routes for the four persistent layers. Compatibility
#: aliases stay separate so an "all" request still returns exactly four.
LAYER_ROUTES = {"context": "string_intelligence", "code": "code_intelligence",
                "history": "past_run_intelligence",
                "user": "user_intelligence"}
LAYER_ROUTE_ALIASES = {"strings": "context", "string": "context"}
PILLAR_ROUTES = LAYER_ROUTES

#: endpoint -> {projection, template, method}.  The template is REGISTERED:
#: a read endpoint runs under atomic_code_only (one act, zero semantic calls),
#: so no API call can quietly become a model call.
API_ROUTES = {
    "summary": {"projection": "summary", "template": "atomic_code_only",
                "method": "GET", "about": "Studio overview strip"},
    "runs": {"projection": "runs", "template": "atomic_code_only",
             "method": "GET", "about": "the runs table"},
    "run": {"projection": "run", "template": "atomic_code_only",
            "method": "GET", "about": "one run's detail + loop tree"},
    "strings": {"projection": "strings", "template": "atomic_code_only",
                "method": "GET", "about": "legacy Context catalog route"},
    "context": {"projection": "context", "template": "atomic_code_only",
                "method": "GET", "about": "Context Intelligence catalog"},
    "intelligence": {"projection": "intelligence",
                     "template": "atomic_code_only", "method": "GET",
                     "about": "the four categorized intelligence layers"},
    "loops": {"projection": "loops", "template": "atomic_code_only",
              "method": "GET", "about": "Code Intelligence catalog"},
    "solutions": {"projection": "solutions", "template": "atomic_code_only",
                  "method": "GET", "about": "Solution Library"},
    "improvements": {"projection": "improvements",
                     "template": "atomic_code_only", "method": "GET",
                     "about": "staged improvement candidates"},
}


class RouteError(KeyError):
    """An endpoint or pillar that is not declared. Refused, never guessed."""


def resolve_route(path: str) -> "dict | None":
    """Match a request path against the declared page contract. Returns the
    route record, or None — the caller decides what a miss means."""
    p = "/" + path.strip("/") if path.strip("/") else "/"
    for kind, table in (("public", PUBLIC_ROUTES), ("studio", STUDIO_ROUTES)):
        if p in table:
            return {"path": p, "kind": kind, "declared": True}
        for pattern in table:
            if ":" not in pattern:
                continue
            pp, rp = pattern.strip("/").split("/"), p.strip("/").split("/")
            if len(pp) == len(rp) and all(
                    a.startswith(":") or a == b for a, b in zip(pp, rp)):
                params = {a[1:]: b for a, b in zip(pp, rp)
                          if a.startswith(":")}
                return {"path": pattern, "kind": kind, "declared": True,
                        "params": params}
    return None


def serve_api(name: str, arg: str = "", *, ledger=None,
              projection_fn=None) -> dict:
    """Serve one API endpoint AS A PRACTITIONERLOOP.

    The payload is what the browser renders; ``loop`` is the evidence that it
    crossed a real boundary — loop id, beats run, and the semantic-call count,
    which is asserted to be zero because a read endpoint may never think with
    a model. An undeclared endpoint raises rather than resolving to something
    plausible.
    """
    route = API_ROUTES.get(name)
    if route is None:
        raise RouteError(f"/api/{name} is not a declared endpoint — "
                         f"declared: {sorted(API_ROUTES)}")
    from ..loop.encapsulate import as_practitioner_loop
    from ..loop.loop_templates import TEMPLATE_LIBRARY
    body = {t["template_id"]: t for t in TEMPLATE_LIBRARY}.get(
        route["template"])
    if body is None or body.get("maturity") != "registered":
        raise RouteError(f"endpoint {name!r} names template "
                         f"{route['template']!r}, which is not registered")
    if projection_fn is None:
        from .studio_server import build_projection as projection_fn

    run = as_practitioner_loop(f"serve /api/{name}",
                               lambda: projection_fn(name, arg),
                               ledger=ledger)
    if run["model_calls"] != 0:                       # unreachable by config
        raise RouteError("a read endpoint made a semantic call")
    return {"endpoint": name, "arg": arg, "payload": run["value"],
            "loop": {"loop_id": run["loop_id"], "template": route["template"],
                     "steps_run": run["steps_run"],
                     "model_calls": run["model_calls"],
                     "stopped": run["stopped"]}}


def intelligence_surface(pillar: str, need: str = "", *,
                         layer_records=None, ledger=None) -> dict:
    """Read one of four layers, or all four when ``pillar`` is ``all``."""
    requested = str(pillar)
    pillar = LAYER_ROUTE_ALIASES.get(requested, requested)
    if pillar != "all" and pillar not in LAYER_ROUTES:
        raise RouteError(f"layer {requested!r} is not one of the four; "
                         f"declared: {sorted(LAYER_ROUTES)} (or 'all')")
    wanted = (tuple(LAYER_ROUTES) if pillar == "all" else (pillar,))
    layers = {LAYER_ROUTES[w] for w in wanted}
    if layer_records is None:
        return {"public_layers": sorted(wanted), "pillars": sorted(wanted),
                "layers": sorted(layers),
                "hits": [], "need": need,
                "note": "no corpus supplied — the surface is declared, the "
                        "read is empty (an empty read is not a missing pillar)"}
    from .intelligence_layers import query_intelligence, normalize_layer_records
    normalized_records = normalize_layer_records(layer_records)
    scoped = {k: v for k, v in normalized_records.items() if k in layers}
    out = query_intelligence(need, scoped) if need else {
        "need": "", "hits": [], "unqueried": sorted(layers - set(scoped))}
    return {"public_layers": sorted(wanted), "pillars": sorted(wanted),
            "layers": sorted(layers), **out}


def live_events(run_id: str, ledger_events=None) -> dict:
    """The browser's event stream, in the ONE canonical vocabulary.

    The console, the loop tree, and the inspector are three projections of
    this list — never three counters maintained separately (the drift the
    Chronicle doctrine exists to prevent).

    Rows arrive in TWO forms and both are first-class: a live run hands over
    raw ledger kinds, while a saved run hands over the Chronicle's stored
    ``event_type`` buckets. Projecting the stored form through the raw map
    silently produced ``x.loop_init``-style passthrough — a live run and a
    replayed one describing the same history in different words, which is
    precisely the drift this seam exists to prevent. Each row is now
    projected by the vocabulary it actually belongs to.
    """
    from .chronicle import (to_canonical_events, family_of, EVENT_FAMILIES,
                            _CANONICAL_EVENT_MAP, EVENT_TYPES)
    raw, out = list(ledger_events or ()), []
    for row in raw:
        kind = row.get("event", "custom")
        if kind in _CANONICAL_EVENT_MAP:
            out.append(to_canonical_events([row])[0])
        elif kind in EVENT_TYPES:
            out.append({"type": family_of(kind), "source": row})
        else:
            out.append({"type": f"x.{kind}", "source": row})
    return {"run_id": run_id, "events": out, "count": len(out),
            "vocabulary_size": len(EVENT_FAMILIES),
            "families_present": sorted({e["type"] for e in out})}


def route_contract() -> dict:
    """What the front end may rely on — declared, countable, testable."""
    return {"record_type": "saas_route_contract/v1",
            "public_routes": len(PUBLIC_ROUTES),
            "studio_routes": len(STUDIO_ROUTES),
            "api_endpoints": sorted(API_ROUTES),
            "layers": sorted(LAYER_ROUTES),
            "pillars": sorted(LAYER_ROUTES),
            "every_api_endpoint_runs_as_a_loop": True,
            "read_endpoints_make_zero_semantic_calls": True}


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    from ..loop.recursive_loop import LoopLedger

    # 1. THE LAW AT THE SEAM: an API call crosses into a real PractitionerLoop
    # — a loop envelope on the ledger, beats run, zero semantic calls.  A flat
    # dispatcher would return the same payload with no evidence that anything
    # was governed.
    lg = LoopLedger()
    served = serve_api("summary", ledger=lg,
                       projection_fn=lambda n, a: {"stub": n})
    envelopes = [e for e in lg.events if e.get("event") == "init"]
    check("every_api_call_crosses_into_a_practitioner_loop",
          served["payload"] == {"stub": "summary"}
          and served["loop"]["loop_id"] and served["loop"]["model_calls"] == 0
          and served["loop"]["stopped"] == "done"
          and served["loop"]["template"] == "atomic_code_only"
          and len(envelopes) == 1,
          f"loop {served['loop']['loop_id']} on "
          f"{served['loop']['template']}, 0 semantic calls")

    # 2. every declared endpoint names a REGISTERED template — an endpoint
    # bound to a candidate template could not run, and one bound to nothing
    # would be a dispatcher branch pretending to be a contract.
    from ..loop.loop_templates import TEMPLATE_LIBRARY
    registered = {t["template_id"] for t in TEMPLATE_LIBRARY
                  if t.get("maturity") == "registered"}
    check("every_endpoint_binds_to_a_registered_template",
          all(r["template"] in registered for r in API_ROUTES.values())
          and len(API_ROUTES) >= 7,
          f"{len(API_ROUTES)} endpoints, all on registered templates")

    # 3. Four preferred layers, with the old strings route as an alias.
    allp = intelligence_surface("all")
    user = intelligence_surface("user")
    context = intelligence_surface("context")
    legacy_context = intelligence_surface("strings")
    check("the_read_surface_exposes_all_four_layers",
          len(allp["public_layers"]) == 4
          and "context" in allp["public_layers"]
          and "user" in allp["public_layers"]
          and user["layers"] == ["user_intelligence"]
          and context["layers"] == legacy_context["layers"]
          and set(PILLAR_ROUTES.values()) == {
              "string_intelligence", "code_intelligence",
              "past_run_intelligence", "user_intelligence"},
          f"layers: {allp['public_layers']}")

    # 4. the page contract resolves, including parameterised Studio routes.
    home = resolve_route("/")
    playback_route = resolve_route("/app/runs/run-7/playback")
    intelligence_route = resolve_route("/app/intelligence")
    context_route = resolve_route("/intelligence/context")
    check("declared_routes_resolve_including_parameters",
          home and home["kind"] == "public"
          and playback_route and playback_route["kind"] == "studio"
          and playback_route["params"]["id"] == "run-7"
          and intelligence_route and intelligence_route["kind"] == "studio"
          and context_route and context_route["kind"] == "public"
          and len(PUBLIC_ROUTES) >= 26,
          f"{len(PUBLIC_ROUTES)} public + {len(STUDIO_ROUTES)} studio routes")

    # 5. the browser stream speaks the ONE vocabulary: canonical families,
    # lossless, and no kind we own escaping as an untyped passthrough.
    lg5 = LoopLedger()
    lg5.record(loop_id="l1", event="init", framework="five_step")
    lg5.record(loop_id="l1", event="run_step", step="act", mode="deterministic")
    lg5.record(loop_id="l1", event="terminal", reason="done")
    ev = live_events("run-9", lg5.events)
    check("the_browser_stream_speaks_the_canonical_vocabulary",
          ev["count"] == 3 and ev["vocabulary_size"] == 59
          and ev["families_present"] == ["loop.completed", "loop.initialized",
                                         "loop.iteration.completed"]
          and not [f for f in ev["families_present"] if f.startswith("x.")],
          f"{ev['count']} events -> {ev['families_present']}")

    # 5b. REGRESSION: a SAVED run hands over the Chronicle's stored
    # event_type buckets, not raw ledger kinds.  Projecting those through the
    # raw map produced x.loop_init-style passthrough — a replayed run
    # describing the same history in different words than the live one.  Both
    # forms must land on the same canonical families.
    from .chronicle import EVENT_TYPES
    stored = [{"event": "run_started"}, {"event": "loop_init",
                                         "loop_id": "l1"},
              {"event": "iteration", "loop_id": "l1", "step": "act"},
              {"event": "model_invocation", "loop_id": "l1"}]
    replayed = live_events("saved", stored)
    check("saved_and_live_runs_project_into_the_same_vocabulary",
          replayed["count"] == 4
          and not [f for f in replayed["families_present"]
                   if f.startswith("x.")]
          and set(replayed["families_present"]) == {
              "run.started", "loop.initialized", "loop.iteration.completed",
              "model.invocation.completed"}
          and len(EVENT_TYPES) == 18,
          f"stored buckets -> {replayed['families_present']}")

    # 6. ADVERSARIAL: an undeclared endpoint and an undeclared pillar are
    # REFUSED, not served from the nearest plausible thing.  A router that
    # guesses is a router that will one day serve the wrong tenant's data.
    bad_ep = bad_pillar = False
    try:
        serve_api("everything", projection_fn=lambda n, a: {})
    except RouteError:
        bad_ep = True
    try:
        intelligence_surface("vibes")
    except RouteError:
        bad_pillar = True
    unknown_page = resolve_route("/app/admin/secrets")
    check("undeclared_endpoints_pillars_and_pages_are_refused",
          bad_ep and bad_pillar and unknown_page is None,
          "unknown endpoint + unknown pillar raise; unknown page does not "
          "resolve")

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
