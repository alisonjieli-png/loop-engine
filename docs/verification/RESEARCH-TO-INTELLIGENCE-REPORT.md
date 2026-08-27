# Research-to-Intelligence verification report

Date: 2026-08-27

Audited branch and revision: `main` at
`6a26978c5e6cd2e3852818c4bb4b2dac23b0da76`, with concurrent uncommitted work
present.

## Verdict

Checkpoint 5 is `REQUIRED_NOT_IMPLEMENTED`.

Loop Engine has a working offline search-capability fixture and a working
candidate source-classification example. It does not have an executable
Research-to-Intelligence Practitioner that takes source material through
selection, fetching, snapshots, extraction, claim records, contradiction
handling, coverage reporting, candidate governance, and Run History playback.

```text
Research-to-Intelligence checkpoint
├── Web Research search boundary
│   └── offline Brave fixture: VERIFIED_WORKING
├── source classification
│   └── four-layer candidate classification: VERIFIED_WORKING
└── end-to-end research application
    ├── selected-source fetch and snapshot: REQUIRED_NOT_IMPLEMENTED
    ├── parse, extract, and claim evidence: REQUIRED_NOT_IMPLEMENTED
    ├── contradiction and coverage report: REQUIRED_NOT_IMPLEMENTED
    ├── governed candidate output: REQUIRED_NOT_IMPLEMENTED
    └── Run History and Studio playback: REQUIRED_NOT_IMPLEMENTED
```

## Executable evidence

### Offline Web Research capability

Command:

```bash
PYTHONPATH=src python3 examples/13_brave_search_plugin/run.py
```

Result: exit 0. Discovery made zero transport calls. One capability Loop ran,
made zero model calls, and returned `ACCEPTED`. The returned source candidate
was explicitly non-persistable. This proves the injected Brave request and
capability-loop boundary. It does not prove live Brave access, page fetching,
source quality, or research synthesis.

### Candidate source classification

Command:

```bash
PYTHONPATH=src python3 examples/17_classify_harness_files/run.py
```

Result: exit 0. One Loop classified four repository sources into Context
Intelligence, Code Intelligence, Runtime History and Solution Intelligence,
and User Feedback Intelligence. All four outputs remained candidates. This
does not fetch or interpret an external source.

### Missing application surface

Reproduction:

```bash
rg -n -i \
  'ResearchToIntelligence|research_to_intelligence' \
  src examples benchmarks
```

Result: no implementation was found. The only current Web Research adapter in
the architecture map is Brave search. Search returns untrusted candidates and
does not fetch a selected page.

## Required checkpoint behaviors not present

- No shared intake accepts URLs, PDFs, websites, repositories, datasets, and
  local files for one research application.
- No selected-source fetch port produces a content-addressed source snapshot.
- No parser or extractor emits typed claims with source spans and retrieval
  times.
- No general contradiction record preserves conflicting source claims.
- No coverage report maps requested topics to found, missing, and disputed
  evidence.
- No candidate package contains definitions, methods, procedures, warnings,
  tests, and Solution Canvas candidates with per-item provenance.
- No complete research campaign can be replayed through the current Studio.

## External boundaries

A live Brave run is an `EXACT_EXTERNAL_BLOCKER` for that one adapter because it
needs network authorization and `BRAVE_SEARCH_API_KEY`. Resolving that blocker
would not complete checkpoint 5 because the downstream research application is
still absent.

The existing live command, when separately authorized, is:

```bash
BRAVE_SEARCH_API_KEY="..." \
PYTHONPATH=src python3 examples/13_brave_search_plugin/run.py --live
```

No live search, provider call, page download, or browser action was performed
during this audit.

## Exact next gate

There is no current end-to-end verification command because the application
does not exist. The next implementation must first add an offline, frozen
source bundle that runs through a Research Practitioner Loop and emits source
snapshots, claim evidence, contradiction and coverage records, candidate
outputs, and Run History. A live provider run must remain a separate gate.
