# Search effect authority evidence

See [the repair handoff](../../docs/verification/SEARCH-EFFECT-AUTHORITY-REPAIR-2026-09-23.md)
for scope, contract version, tests and integration instructions.

The current focused run is `owning-tests-final.txt`; the complete owning suite
is `http-owning-suite.json`. Earlier failures and successors are preserved.
The request schema, forwarding, default behavior, version and final authority
guard are exercised by `guard-mutations.json`.

The two `docs-delta` guide files are exact proposed successor text for the
restored documentation lane, with before/after hashes. They are not another
public documentation source. Apply the separate patch and rebuild the public
bodies from their canonical guides during integration.
