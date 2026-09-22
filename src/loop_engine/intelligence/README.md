# Intelligence

The persistent intelligence held by this line, and the single place a
developer enables another kind.

Owner direction, September 21, 2026: the main line serves **harness
intelligence**, and only the harness family. The other families — Loop-native
and Open Knowledge Format — remain in the library and the records, and are
**off** here. Serving them is a host decision, never a silent default.

```text
intelligence
├── Served on main: the harness family
│   └── drop-in files a standard harness reads (SKILL.md, AGENTS.md,
│       plugin declarations, protocol server configurations)
├── Declared but off on main
│   ├── loop_native — material built for the Loop runtime
│   └── open_knowledge — generalized knowledge in open formats
└── Add or toggle without changing the serving path
    ├── a family is named in the host configuration's
    │   `intelligence_family_policy` record (typed, versioned), or
    └── an engine or harness is added as a recipe and adapter behind
        `HarnessProcessSpec`, by declared tested profile
```

Do not add a second runtime, scheduler, credential store or catalogue
authority. An item whose family the host does not declare is refused before
its body is opened; the refusal names the family the item serves and the
families the host accepts. The conservative default is the harness family
alone (`service_host_family_policy/v1`), mirroring the licence policy.

The full-capability tree, with every family served, is frozen on
`checkpoint/full-capability-2026-09-21` at revision `a3bd0f1`. Restore is a
recorded owner decision implemented behind the typed boundary the
[harness-first decision record](../../../docs/architecture/ADR-HARNESS-FIRST-SERVING-AND-EXECUTION.md)
names, never a silent merge.
