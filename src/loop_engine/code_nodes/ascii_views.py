"""Compact ASCII trees derived from canonical graph and Run History data.

The renderer owns presentation only. It never infers authority, changes graph
state, or creates another execution model.
"""
from __future__ import annotations

from ..core.run_history import as_ledger_events
from .solution_graph import LoopGraphDefinition


def _walk(root, successors, label, prefix="", last=True, seen=None):
    seen=set() if seen is None else seen
    branch="└─ " if last else "├─ "
    shared=root in seen
    lines=[prefix+branch+label(root)+( " [shared]" if shared else "")]
    if shared: return lines
    seen.add(root)
    next_prefix=prefix+("   " if last else "│  ")
    values=successors.get(root,())
    for index, successor in enumerate(values):
        lines.extend(_walk(successor,successors,label,next_prefix,
                           index==len(values)-1,seen))
    return lines


def render_loop_graph_ascii(graph: LoopGraphDefinition) -> str:
    if not isinstance(graph,LoopGraphDefinition):
        raise TypeError("render_loop_graph_ascii needs LoopGraphDefinition")
    vertices={item.vertex_id:item for item in graph.vertices}
    successors={key:[] for key in vertices}; incoming={key:0 for key in vertices}
    for edge in sorted(graph.edges,key=lambda item:(item.order,item.edge_id)):
        successors[edge.source.vertex_id].append(edge.target.vertex_id)
        incoming[edge.target.vertex_id]+=1
    roots=sorted(key for key,value in incoming.items() if value==0)
    def label(vertex_id):
        item=vertices[vertex_id]
        return (f"{vertex_id} [{item.selected_mode}] {item.purpose} "
                f"{item.definition_ref.content_digest[:10]}")
    lines=[f"Graph {graph.graph_id}@{graph.version} [{graph.content_digest[:12]}]"]
    seen=set()
    for index,root in enumerate(roots):
        lines.extend(_walk(root,successors,label,"",index==len(roots)-1,seen))
    return "\n".join(lines)


def render_run_tree_ascii(events) -> str:
    values=as_ledger_events(events)
    initialized={str(e.get("loop_id")):e for e in values
                 if e.get("event")=="init" and e.get("loop_id")}
    terminal={str(e.get("loop_id")):e for e in values
              if e.get("event")=="terminal" and e.get("loop_id")}
    successors={key:[] for key in initialized}; incoming={key:0 for key in initialized}
    for loop_id,event in initialized.items():
        parents=[]
        for field in ("spawned_by_loop_id","queried_by_loop_id",
                      "retrieved_by_loop_id"):
            if event.get(field): parents.append(str(event[field]))
        parents.extend(str(x) for x in event.get("connected_from_loop_ids",()) or ())
        for parent in parents:
            if parent in successors:
                successors[parent].append(loop_id); incoming[loop_id]+=1
    for key in successors: successors[key]=sorted(set(successors[key]))
    roots=sorted(key for key,value in incoming.items() if value==0)
    def label(loop_id):
        event=initialized[loop_id]
        status=(terminal.get(loop_id) or {}).get("reason","running")
        return (f"{loop_id} {event.get('role','?')}/"
                f"{event.get('mode',event.get('baseline_terminal_mode','?'))} "
                f"[{status}] {str(event.get('goal',''))[:52]}")
    lines=[f"Run tree [{len(initialized)} Loops]"]
    seen=set()
    for index,root in enumerate(roots):
        lines.extend(_walk(root,successors,label,"",index==len(roots)-1,seen))
    return "\n".join(lines)


__all__=("render_loop_graph_ascii","render_run_tree_ascii")
