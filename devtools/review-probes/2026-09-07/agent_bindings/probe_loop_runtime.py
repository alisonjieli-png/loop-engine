"""Part 2 re-probe (a)-(d) against the canonical Loop at HEAD. No model calls."""
import json, sys, traceback
from loop_engine.loop.recursive_loop import Loop, LoopConfig, StepOutcome, LoopError

def events(loop, kinds=("run_step", "fallback", "model_boundary_deferred", "terminal", "iteration_started", "custom")):
    out = []
    for e in loop.ledger.events:
        if e.get("loop_id") == loop.loop_id and e.get("event") in kinds:
            out.append({k: e.get(k) for k in ("event", "step", "mode", "output", "accepted", "reason", "from_mode", "to_mode", "custom_kind", "note", "iteration") if k in e})
    return out

print("===== (a) no fabricated recovered outcomes =====")
calls = []
def always_fails(loop, step, context):
    calls.append(context.get("requested_mode"))
    return StepOutcome(output=f"attempt failed ({context.get('requested_mode') or 'hybrid'})", mode=context.get("requested_mode") or "hybrid", confidence=0.0, failed=True)
fab = Loop("no fabricated recovery", LoopConfig(framework="custom", custom_steps=("act",), allowable_modes=("hybrid", "deterministic"), preferred_modes=("hybrid", "deterministic")))
r = fab.run(handler=always_fails)
print("handler invocations (requested_mode):", calls)
print("result:", dict(terminal_code=r.terminal_code, stopped=r.stopped, accepted=r.accepted, accepted_successes=r.accepted_successes, output=r.output))
for e in events(fab): print("  ", e)
print("any run_step accepted=True?", any(e.get("accepted") for e in events(fab) if e["event"] == "run_step"))
print("any 'recovered' text?", any("recovered" in str(e.get("output","")) for e in fab.ledger.events))

print("\n--- (a2) deterministic fails first, semantic fallback deferred, still fails ---")
calls = []
def det_fails(loop, step, context):
    calls.append(context.get("requested_mode"))
    return StepOutcome(output=f"fail@{context.get('requested_mode') or 'deterministic'}", mode=context.get("requested_mode") or "deterministic", confidence=0.0, failed=True)
d = Loop("deferred", LoopConfig(framework="custom", custom_steps=("act",), allowable_modes=("deterministic", "hybrid"), preferred_modes=("deterministic", "hybrid")))
r = d.run(handler=det_fails)
print("handler invocations:", calls)
print("result:", dict(terminal_code=r.terminal_code, stopped=r.stopped, accepted=r.accepted, accepted_successes=r.accepted_successes, output=r.output, steps_run=r.steps_run))
for e in events(d): print("  ", e)

print("\n===== (b) bounded iteration under accepted_success =====")
print("--- (b1) identical failure ---")
churn = Loop("never succeeds", LoopConfig(framework="custom", custom_steps=("act",), allowable_modes=("deterministic",), preferred_modes=("deterministic",), exit_condition="accepted_success"))
r = churn.run(handler=lambda loop, step, context: StepOutcome(output="nope", mode="deterministic", confidence=0.0, failed=True))
print("result:", dict(terminal_code=r.terminal_code, stopped=r.stopped, steps_run=r.steps_run))

CAP = 3000
class Cap(Exception): pass
for label, mk in (
        ("varying_output_failed", lambda n: StepOutcome(output=f"nope#{n}", mode="deterministic", confidence=0.0, failed=True)),
        ("not_failed_low_confidence", lambda n: StepOutcome(output="meh", mode="deterministic", confidence=0.0, failed=False)),
        ("not_failed_low_confidence_varying", lambda n: StepOutcome(output=f"meh#{n}", mode="deterministic", confidence=0.1, failed=False)),
        ("alternating_failures", lambda n: StepOutcome(output=f"nope#{n % 2}", mode="deterministic", confidence=0.0, failed=True))):
    n = [0]
    def h(loop, step, context, mk=mk):
        n[0] += 1
        if n[0] > CAP: raise Cap(f"handler invoked {n[0]} times without a runtime stop")
        return mk(n[0])
    lp = Loop(label, LoopConfig(framework="custom", custom_steps=("act",), allowable_modes=("deterministic",), preferred_modes=("deterministic",), exit_condition="accepted_success"))
    try:
        r = lp.run(handler=h)
        print(f"--- (b2:{label}) STOPPED by runtime: terminal_code={r.terminal_code} stopped={r.stopped} steps_run={r.steps_run} attempts={n[0]}")
    except Cap as exc:
        print(f"--- (b2:{label}) NO CEILING: {exc}; is_terminal={lp.is_terminal}; supervision={lp.config.supervision.to_dict()}; max_iterations={lp.config.max_iterations}")
    except Exception as exc:
        print(f"--- (b2:{label}) raised {type(exc).__name__}: {str(exc)[:200]} after {n[0]} handler calls")

print("\n--- (b3) same with power=standard nine_step (default LoopConfig) + accepted_success ---")
n = [0]
def h2(loop, step, context):
    n[0] += 1
    if n[0] > CAP: raise Cap(f"handler invoked {n[0]} times")
    return StepOutcome(output=f"x{n[0]}", mode="deterministic", confidence=0.0, failed=True)
lp = Loop("nine", LoopConfig(exit_condition="accepted_success", allowable_modes=("deterministic",), preferred_modes=("deterministic",)))
try:
    r = lp.run(handler=h2); print("STOPPED:", r.terminal_code, r.stopped, r.steps_run)
except Cap as exc:
    print("NO CEILING:", exc)

print("\n===== (c) RecursionError is not masked =====")
import loop_engine.loop.loop_profile_ontology as ontology
orig = ontology.resolve_profile
def boom(*a, **k): raise RecursionError("synthetic recursion in profile resolution")
ontology.resolve_profile = boom
try:
    Loop("recursion probe", LoopConfig(framework="custom", custom_steps=("act",)))
    print("constructed?! (unexpected)")
except RecursionError as exc:
    print("RecursionError PROPAGATED with its own type:", exc)
except Exception as exc:
    print("MASKED as", type(exc).__name__, ":", str(exc)[:200], "| cause:", type(exc.__cause__).__name__ if exc.__cause__ else None)
finally:
    ontology.resolve_profile = orig
deep = Loop("recurse", LoopConfig(framework="custom", custom_steps=("act",)))
try:
    deep.run(handler=lambda loop, step, context: StepOutcome(output="spawn", mode="deterministic", spawn_goal="deeper"))
    print("deep spawn finished without error (unexpected)")
except LoopError as exc:
    print("deep spawn -> typed LoopError:", str(exc)[:160])
except RecursionError as exc:
    print("deep spawn -> raw RecursionError:", str(exc)[:160])

print("\n===== (d) contract coercion on compatibility constructor =====")
from loop_engine.loop.loop_contract import LoopContract, LoopContractError, execution_mode_for_runtime_mode, validate_loop_connection, LoopConnectionSpec, LoopPortBinding
for v in ("code_with_model_assistance", "model_led", "", None, "deterministic"):
    try: print(f"execution_mode_for_runtime_mode({v!r}) ->", execution_mode_for_runtime_mode(v))
    except LoopContractError as exc: print(f"execution_mode_for_runtime_mode({v!r}) REFUSED:", str(exc)[:80])
# contract mode disagrees with config modes
c = LoopContract("hybrid contract", "hybrid", output_roles=("thing/v1",))
try:
    lp = Loop("coerce me", LoopConfig(framework="custom", custom_steps=("act",), allowable_modes=("deterministic",), preferred_modes=("deterministic",)), contract=c)
    init = next(e for e in lp.ledger.events if e.get("event") == "init" and e.get("loop_id") == lp.loop_id)
    print("compat Loop built; contract.execution_mode:", lp.contract.execution_mode, "output_roles:", lp.contract.output_roles, "| init coercion fields:", {k: v for k, v in init.items() if "coerc" in k or "compatib" in k or k in ("baseline_terminal_mode","output_roles")})
except Exception as exc:
    print("compat Loop REFUSED:", type(exc).__name__, str(exc)[:200])
# role coercion
c2 = LoopContract("solution contract", "code_only", output_roles=("thing/v1",), role="solution")
try:
    lp = Loop("role coerce", LoopConfig(framework="custom", custom_steps=("act",), allowable_modes=("deterministic",), preferred_modes=("deterministic",)), contract=c2)
    init = next(e for e in lp.ledger.events if e.get("event") == "init" and e.get("loop_id") == lp.loop_id)
    print("role compat Loop built; contract.role:", repr(lp.contract.role), "identity:", lp.identity.role.value, "| init coercion fields:", {k: v for k, v in init.items() if "coerc" in k})
except Exception as exc:
    print("role compat Loop REFUSED:", type(exc).__name__, str(exc)[:200])
# port incompatibility
prod = LoopContract("p", "code_only", output_roles=("a/v1",))
cons = LoopContract("c", "code_only", input_roles=("b/v1",), output_roles=("r/v1",))
res = validate_loop_connection(LoopConnectionSpec(prod, cons, (LoopPortBinding("a/v1", "b/v1"),)))
print("mismatched ports without adapter -> compatible:", res.compatible, "|", res.explain())
res = validate_loop_connection(LoopConnectionSpec(prod, cons))
print("mismatched ports, implicit same-name bindings -> compatible:", res.compatible, "|", res.explain())
res = validate_loop_connection(LoopConnectionSpec(prod, LoopContract("c", "code_only", input_roles=("a/v1",), output_roles=("r/v1",)), (LoopPortBinding("a/v1", "a/v1"),)))
print("matching ports -> compatible:", res.compatible)
