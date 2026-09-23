"""Independent review panel for harness intelligence candidates (roadmap package LS2).

This package decides whether independent reviewers approve the exact bytes of
one candidate item. It approves nothing by itself and serves nothing: its
output is a dated review record beside ``reviews.json`` that the lead engineer
merges into the served catalogue through the existing carry and manifest tools.

Functional components and their engines:

```text
Candidate review (functional component)
├── Edge: candidate_review_request/v1 in, candidate_review_verdict/v1 out
├── Envelope: panel.ReviewPanel, run by one deterministic operator command
├── Pre-check engine slot (six kinds, each one or more engines, any refusal ends the item)
│   ├── licence: builtin_licence_rules
│   ├── format: builtin_format_rules, agent_skills_reference (skills-ref command)
│   ├── safety: builtin_static_rules, skillspector_static (SkillSpector command)
│   ├── effects: builtin_effect_rules
│   ├── secrets: builtin_secret_patterns
│   └── duplicates: exact_shingle_jaccard, datasketch_minhash_lsh (datasketch library)
└── Reviewer engine slot
    ├── model_gateway: Ollama Cloud models through the repository's model gateway
    ├── command_line: the Codex and Claude Code command lines
    └── fixture: offline scripted reviewers for checks, never in a real record
```

The factory tables in ``engines`` are the only code that names concrete engine
classes. The declared resources live in ``resources/``. See README.md.
"""
