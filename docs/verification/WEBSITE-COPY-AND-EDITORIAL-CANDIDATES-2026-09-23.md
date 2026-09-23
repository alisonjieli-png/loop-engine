# Website copy and editorial candidates, September 23

Kind: dated local verification. Base source:
`abcad4f8ce346e7d0759ccad703e0111574148a6`. These changes are not deployed.
The existing roadmap owns S-6.33, S-6.36 and S-6.47.

## Homepage claim repair

The live opening said that with a fresh harness, "nothing drifts". The
repository has no evidence for that absolute outcome. The local source now
describes fresh context as the design and limiting drift as its aim. The
fresh harness, focused step and smaller-model purpose remain in the opening.

The new check in
[test_homepage_demonstration.py](../../tools/test_homepage_demonstration.py)
rejected the old opening before the source repair. Three known-wrong
sentences cover absolute drift claims. After the repair, all eight owning
tests passed. Replacing the claim guard with an empty result caused all
three planted claims to escape and the check to fail, as required.

- [Owning test output](../../artifacts/website-copy-review-2026-09-23/owning-tests-after.txt)
- [Removed claim guard](../../artifacts/website-copy-review-2026-09-23/removed-claim-guard.json)
- [Full browser check](../../artifacts/website-copy-review-2026-09-23/browser-after-copy-fix.json):
  495 of 495 checks and 76 of 76 removed-guard controls passed.

The first attempt used the shared checkout's older environment, which lacked
the current protocol package's caching module. An isolated environment in
the review worktree was installed from the current package specification;
the shared environment was not changed. This environment mismatch was not
a product defect.

The [benefit evidence guide](../guides/launch-benefits-and-evidence.md) also
used the superseded North Star. Its local revision now leads with efficient
accepted work under the customer's constraints, appropriate context and
reusable code, while preserving the distinction between an ambition and
measured behavior. It records the recent negative data-cleanup result and
corrects the statement that the documentation hostname does not exist: it
currently serves a homepage alias.

## Blog, Team and logo preview

The [editorial artifact](../../artifacts/editorial-pages-2026-09-23/README.md)
contains a blog index, three complete draft articles, a Team page and a
comparison of existing logo candidates. Taylor Amarel is the sole named
person, as instructed. An initials image and project-focused biography add
no invented personal background.

Twelve page and viewport combinations returned 200 with loaded images, no
page errors and no horizontal overflow. Desktop and phone screenshots were
inspected. The public copy received a separate factual review against the
frozen data-cleanup experiment and current library evidence. Every page is
visibly a draft and has noindex metadata.

The article about the negative phone result needs an exact catalogue
disposition before publication. Removing the item from the homepage did
not remove it from the offered library. The preview deliberately preserves
the experiment's limits and does not infer a production error rate.

Integration belongs in the existing public page registry and shared
application shell. Copying the standalone preview as live pages could
discard the current in-memory sign-in state during navigation. Deep links,
unknown article routes, signed-in navigation and mobile behavior need
integration checks on the final source. No public article, Team route or
logo change was published in this experiment.

An optional Ruff check reported four findings in the existing homepage test
module. Rechecking its unchanged base produced the same four codes and
messages, so no unrelated formatting repair was folded into this change.
The new editorial renderer passes Ruff. The
[baseline comparison](../../artifacts/website-copy-review-2026-09-23/optional-ruff-baseline-comparison.json)
preserves both results.

## Scope of the result

The copy repair has local source and browser evidence. The editorial pages
are concrete reviewable drafts. Neither is a full-repository continuous
integration result or a production release. Claude Code should integrate
the accepted changes against current main and follow the existing exact-tree
verification and release process.
