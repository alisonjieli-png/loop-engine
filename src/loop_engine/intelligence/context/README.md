# Context Intelligence (off on main)

Owner direction, September 21, 2026: the main line serves the harness
family alone. Context Intelligence is one of the Loop-native layers, so its
material is **disabled on main** and no host serves it here.

This folder is kept open for future use. To enable this layer on a host,
declare `loop_native` (or `open_knowledge`, as the material requires) in
that host's `intelligence_family_policy` record — a typed, versioned host
configuration change, not a code change. The refusal that a harness-only
host returns for material of this layer names the family it does not serve.

The working content and its 6229-check qualification are frozen on
`checkpoint/full-capability-2026-09-21` at revision `a3bd0f1`. Do not add
material here to make a main-line host serve it; add it to the checkpoint
behind the typed boundary, then declare the family in the host policy.
