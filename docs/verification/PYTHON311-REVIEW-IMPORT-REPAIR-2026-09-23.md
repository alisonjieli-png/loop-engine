# Review configuration import repair for Python 3.11

Kind: dated release repair, September 23, 2026. Base revision `d2e20413`.

GitHub job 107221057277 in run 35872834266 failed while importing the review
configuration. Python 3.11 rejects its `MappingProxyType({})` dataclass default
as an unhashable default and requests a factory. Seven review test modules
could not load. This is separate from the catalogue timing check repaired in
the preceding commit.

The same failure was reproduced locally with Python 3.11.15 before editing.
The field now uses a default factory that returns a new empty mapping proxy.
It remains immutable and keeps the same value and public record shape. No
review policy, candidate, verdict or approval changes.

- [Before repair](../../artifacts/release-unblock-2026-09-23/python311-before.txt):
  the existing configuration tests cannot import.
- [After repair](../../artifacts/release-unblock-2026-09-23/python311-after.txt):
  all 48 existing configuration tests pass on Python 3.11.15.

Decision: keep the supported Python versions in continuous integration and
repair the default construction. Do not remove the 3.11 job or skip the
review modules. Exact-tree local checks and the committed GitHub run govern
release eligibility; these focused results do not replace them.
