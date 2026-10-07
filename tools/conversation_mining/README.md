# Private conversation signal extraction

This operator tool reads local owner-message corpora and produces a private
keyword index. It does not create components, grant effect authority, execute
queries or publish source content. The roadmap owners are S-6.214 and S-6.217.
It adapts preserved pending work whose original bytes remain in the October 7
private repository audit.

`connectors.py` reads Codex and Claude JSONL, a ChatGPT JSON/ZIP export or a
plain prompt log. `extract.py` identifies candidate phrases and safe public
references. `records.py` screens and validates `owner_signal_record/v2`.
`map_dimensions.py` suggests dimension associations; these are keyword hints,
not measured relevance. `integrate.py` preserves source references while
grouping identical phrase/reference sets into a private proposed-work queue.

The miner uses actual message timestamps for `--hours` and `--days`, and
excludes undated records when a time window is requested. It records read
errors, time exclusions, capped files and clipped turns. Ordinary titles do
not enter opaque locators. Automatic task notifications are context, not
owner requests. The earlier version-1 index lacks the current reference and
screening contract and is refused by the queue reader; retain it as history.

```sh
PYTHONPATH=src:tools python -m conversation_mining.mine \
  --root /absolute/private/intake-folder \
  --codex /absolute/approved/session-folder --hours 36
```

The command writes private files only to the selected folder. It refuses
existing result names, the repository, a home/filesystem root and symbolic
link destinations. Source files are unchanged. A fresh run should use a new
folder or unique output names; a crash does not authorize overwriting an
earlier result.

The current connector bounds JSON/ZIP documents at 64 MiB and JSONL lines at
four million characters. It clips each extracted turn at 4,000 characters
and reports that clipping. This index therefore cannot claim to reconcile
every requirement in a long pasted handoff. Review the original privately and
map its sections to existing roadmap tasks. Preserve inaccessible, oversized,
undated and unreviewed source populations explicitly.

Text screening is heuristic. It catches known sensitive patterns, but cannot
decide whether every ordinary phrase is confidential. The index remains
private; any external query, candidate or public description needs its own
source, rights and disclosure checks. A phrase classified as a decision is
not authorization to act on that phrase.

Run `PYTHONPATH=src:tools python -m unittest tools.test_conversation_mining` for
synthetic malformed input, provenance, privacy, source-reference, timestamp
and vocabulary generation checks. No real transcript or credential is in
those fixtures.
