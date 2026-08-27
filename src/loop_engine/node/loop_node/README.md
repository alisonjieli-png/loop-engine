# Legacy `loop_node` record reader

This namespace exists only to load immutable historical records whose
serialized `kind` is `loop_node`.

```text
historical kind: loop_node
→ exact compatibility reader
→ LoopDefinitionRecord
```

It contains no runtime, Node class, graph executor, profile, or current public
alias. New code emits `loop_definition_record`. Executable work uses the sole
public runtime, `Loop`.
