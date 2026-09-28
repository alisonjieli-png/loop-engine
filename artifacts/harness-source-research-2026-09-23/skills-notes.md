# Skills research list: 1,000 named skill candidates

Checked September 23, 2026. This is a reproducible research-priority list,
not a global quality leaderboard or a set of approved downloads.

## Evidence and counting

- The public skills.sh page supplied 600 visible serialized leaderboard records,
  including 571 GitHub-source records across 87 repository addresses. Public page bytes
  and the JSON-only extraction are frozen in the external research cache.
- The documented leaderboard API returned HTTP 401. No authentication bypass
  was attempted. Public page data was read as data, without executing scripts.
- Fresh read-only GitHub metadata confirmed 86 accessible repositories were
  public; one source returned 404. Exact commits and recursive file trees were
  pinned. Truncated or unavailable trees were excluded.
- The trees contained 2,007 selected SKILL.md paths after the declared test,
  dependency-directory, size and identical Git-blob exclusions.
- Initial acquisition made 259 GitHub reads and 1,282 anonymous pinned raw-file
  reads. The logical-group refinement made 550 further raw-file reads.
- Across both passes, 1,832 primary instruction files were inspected. They
  supplied 1,466 distinct instruction byte sequences and 1,438 conservative
  same-publisher named groups.
- The final shortlist contains exactly 1,000 named groups, 1,000 distinct
  instruction SHA-256 digests, 81 repository addresses and 80 canonical GitHub repositories. Canonical GitHub repository identifiers identify the observed rename alias; no
  selected same-name group is duplicated under that identifier. A publisher contributes at
  most 40 selected named groups. Native projections remain attached to each
  group and do not count as separate skills.

The first list contained 28 additional native projections of already counted
names. It is preserved in skills-ranked-before-logical-dedup.jsonl; the current
skills-ranked.jsonl is its corrected successor. Grouping by repository and
frontmatter name is conservative: colliding names may hide different methods,
and semantically similar methods with different names may remain. This is not
a completed semantic-duplicate audit.

## Ranking rule

The score combines declared task relevance (up to 20), reported permissive
licence metadata (12), exact primary-source pinning (15), public installation
signal (up to 20), repository stars (up to 10), non-archived status (5), and
primary instruction/required metadata observation (15). Ties use repository
and path. The total is a research-priority score, not a success probability.

Task relevance uses explicit software, data, operations, product and research
terms. Installation counts are skills.sh-reported telemetry; they are not
unique users or task successes. Missing installation counts remain unknown and
receive no popularity bonus. Same-name projections are represented once even
when their text differs; the alternate exact digests remain available for
review. The policy deliberately limits one prolific repository's contribution.

This population is biased toward the repositories visible on the public
leaderboard. It cannot establish the best 1,000 skills across the global
catalogue. A high rank does not establish correctness, safety, rights or native
compatibility. Reported repository licences may not govern every skill or asset.
All license_verified flags remain false.

## What was checked

Each selected instruction was fetched anonymously from its exact commit/path,
hashed with SHA-256 and compared with the pinned Git blob identity. The bytes
were decoded as UTF-8 and inspected for leading frontmatter and nonempty-looking
name/description fields. This is a bounded line-level observation, not full YAML
or Agent Skills specification validation. Complete dependency trees, scripts,
hooks and assets were not executed or qualified.

supporting_file_count means other files under the skill's directory subtree.
It does not prove that those files are needed, sufficient, safe or installed.
Root-level SKILL.md entries use the repository subtree; their initial zero-count
projection was corrected during the logical refinement.

## Reuse and original building

Use these records to select an operation worth understanding. Inspect its exact
source and applicable rights before any code/prose reuse. When rights are unclear,
retain source links and independently implement the functional idea from an
explicit contract and original tests. A paraphrase is not automatically an
independent implementation. Preserve attribution and all required notices where
reuse is permitted.

The original sixteen-package supply includes task-context rendering, context
budget selection, capability evidence comparison, exact paired evaluation and
repository/data methods. These address recurring workflow needs seen in the
research; they are not copies of ranked SKILL.md prose. The separate wikilink
audit is a concrete follow-on from the notes/Obsidian integration research.

## Repeat and handoff

research_skills.py records fresh metadata and pins source commits; it uses the
existing GhCliReader, HttpsGetTransport, RequestBudget, RequestLog and Quarantine.
refine_skill_groups.py preserves the predecessor, groups native projections and
reads further pinned instructions. The scripts refuse existing run/output
snapshots where specified. For another collection date, allocate a new cache
and output folder, preserve these files and record the new script/configuration
digests before fetching. Do not overwrite historical evidence.

The current raw cache is outside the public repository at
/home/username/.le-codex-research-cache/four-catalogues-20260923. The shared
research files contain names, links, measured facts and interpretation, not the
third-party instruction bodies. No source was installed, executed, approved or
served by this research.

Primary routes: [Skills documentation](https://www.skills.sh/docs),
[Skills API](https://www.skills.sh/docs/api),
[public leaderboard](https://www.skills.sh/), and the exact source URLs carried
by every row. Independent engine/package review remains a separate gate.
