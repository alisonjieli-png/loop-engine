# First-party harness candidates, wave 5

Kind: candidate packages and their pre-check records. Nothing here is approved,
served or published. Every package still needs the independent review panel:
three approvals from three model families other than the producer's
(`anthropic`), and no rejection.

Wave 5 planned 75 original multi-file packages in 15 assignments of 5. It
covers harness file kinds the earlier waves did not: executable data-cleanup
tools, competition modeling tools, ticket tools, unattended guard hooks,
focused subagents, step commands, local data protocol servers, path-scoped
rules, step packets for tickets, data work and competitions, session plugins,
result verifiers, permission settings and root instruction fragments.
[`SPEC.md`](SPEC.md) holds the generation rules and
[`GAP-MATRIX.md`](GAP-MATRIX.md) the gaps it filled. The source revision was
`a1fc7432`.

## State on September 24, 2026

The deterministic pre-check ([`check_package.py`](check_package.py),
`check-all`, report
[`reports/precheck-all-20260924T114954425867Z.json`](reports/precheck-all-20260924T114954425867Z.json))
read all 75 packages:

| Result | Packages |
|---|---|
| Passed the deterministic pre-checks | 56 |
| Refused | 19 |

A pass means the listed checks found nothing to refuse: layout, inventory,
text hygiene, vocabulary, static safety, secrets, parse, entry shape,
placements, declared effects, static network use, duplicates, the review note,
and the package's own tests, hooks and servers run in a sandbox with no
network. It is not an approval, a rights decision, a native loading result or
a usefulness claim.

The 19 refusals come from repairs that the session's usage limit interrupted.
All 19 have inventory drift, where a file changed after its digest was
recorded. Some also have cached `.pyc` files in the payload, render
placeholders that differ from the markers used, a missing variant file or a
failing package test. None was refused by the secrets or static network
checks. Each package's `review/` folder holds its newest pre-check report,
and `precheck-logs/` keeps the logs that generators wrote outside their
package folders.

## Next steps

1. Repair the 19 refused packages, run `fill` and `check` on each, and keep the
   refused report beside the passing one.
2. Submit the passing packages to the independent review panel in
   `tools/candidate_review`.

Kept outside this repository, in the session archive on the development
machine: the scout folder, whose duplicate corpus holds text from outside
candidates under other licences, and two snapshot archives of earlier package
states.
