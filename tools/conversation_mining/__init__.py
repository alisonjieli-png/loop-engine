"""Conversation mining: private, local-only extraction of owner intent from bot transcripts.

Reads Claude Code project JSONL, Codex session rollouts, and ChatGPT export
archives. Emits a local index of `owner_signal_record/v2` rows and normalizes
extracted phrases into query-multiplier dimension assignments. No network,
no publication, no staging, no admission.
"""
