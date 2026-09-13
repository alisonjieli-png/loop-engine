import json, tempfile, runpy, sys
sys.argv = ["x"]
src = open("/tmp/claude-1000/-home-username-loop-engine/6d8b36e1-c0bf-4f98-a765-7be966b7d9c2/scratchpad/agent_bindings/probe_history.py").read()
src = src.split("    hist = {}")[0]  # reuse the run + load, then custom extraction
exec(src)
owner_ids = {e.loop_id for e in log if e.event_type == "custom" and e.detail.get("custom_kind") == "kernel_input_bound"}
print("kernel owner loop ids (kernel_input_bound):", owner_ids)
for lid in sorted(owner_ids):
    its = [(e.step, str(e.detail.get("output"))[:36], e.detail.get("accepted"), e.status, e.mode) for e in log if e.event_type == "iteration" and e.loop_id == lid]
    print(f"persisted 'iteration' events for kernel owner {lid}: n={len(its)}, accepted={sum(1 for x in its if x[2])}")
    for x in its: print("     ", x)
prep = [(e.loop_id, e.detail.get("custom_kind")) for e in log if e.event_type == "custom" and e.detail.get("custom_kind") in ("kernel_preparation_completed", "kernel_preparation_rejected")]
print("spawned kernel loops completed via preparation (no 13-step walk):", prep)
for lid, _ in prep:
    its = [(e.step, str(e.detail.get("output"))[:30], e.detail.get("accepted")) for e in log if e.event_type == "iteration" and e.loop_id == lid]
    print(f"   iteration events for spawned {lid}: n={len(its)}", its[:3])
