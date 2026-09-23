"""Engine connection_schema_validator of the library_format_validation engine slot.

It validates two of the three connection files against the schemas their
harnesses publish: Codex's config.schema.json (Apache-2.0, openai/codex at
a pinned commit) for the config.toml table, and OpenCode's config.json (MIT,
anomalyco/opencode, pinned by digest) for opencode.json. Claude Code
publishes no schema for .mcp.json, so the built-in rules check it alone.
The schemas are read by the run with their digests checked against the
curated source list; a missing schema makes the engine not_configured and a
changed digest makes it schema_digest_changed, so a schema never changes
silently. jsonschema (MIT) is a base dependency of this package.
"""
from __future__ import annotations

import json

from .record_rules import bytes_digest

try:
    import tomllib as _toml
except ImportError:  # Python 3.10 reads TOML through the tomli package the environment ships
    import tomli as _toml

SCHEMA_FILES = {"codex": "codex_config", "opencode": "opencode_config"}


class ConnectionSchemaValidator:
    """The published JSON schemas of Codex and OpenCode, applied to the rendered files."""

    engine_id = "connection_schema_validator"
    engine_version = "1.0.0"
    engine_kind = "format_rules"
    effects = ("pure",)
    third_party = "jsonschema (MIT); Codex config schema (Apache-2.0); OpenCode config schema (MIT)"
    applies_to = ("tool",)

    def __init__(self, schemas: dict) -> None:
        import jsonschema

        self._validators = {}
        for harness, schema_id in SCHEMA_FILES.items():
            if bytes_digest(schemas[schema_id]["bytes"]) != schemas[schema_id]["sha256"]:
                raise ValueError(f"the {schema_id} schema is not the pinned bytes")
            schema = json.loads(schemas[schema_id]["bytes"])
            validator = jsonschema.validators.validator_for(schema)
            self._validators[harness] = validator(schema)

    @classmethod
    def availability(cls, settings: dict):
        digests = settings.get("schema_digests") or {}
        for schema_id in SCHEMA_FILES.values():
            row = digests.get(schema_id)
            if not row or not row.get("observed"):
                return False, "not_configured"
            if row["observed"] != row.get("expected"):
                return False, "schema_digest_changed"
        return True, "available"

    @classmethod
    def from_settings(cls, settings: dict, resources: dict):
        """Construct from declared settings and the run's resources; nothing starts here."""
        return cls(resources["schemas"])

    def describe(self) -> dict:
        return {"engine_id": self.engine_id, "engine_version": self.engine_version,
                "harnesses": sorted(self._validators)}

    def validate_package(self, document: dict) -> list:
        problems = []
        for row in document.get("files", ()):
            validator = self._validators.get(row["harness"])
            if validator is None:
                continue
            try:
                value = _toml.loads(row["text"]) if row["harness"] == "codex" else json.loads(row["text"])
            except (ValueError, _toml.TOMLDecodeError):
                problems.append(f"{row['harness']}: the file does not parse")
                continue
            for error in sorted(validator.iter_errors(value), key=lambda item: list(item.path))[:3]:
                location = "/".join(str(part) for part in error.path) or "(root)"
                problems.append(f"{row['harness']}: {location}: {error.message[:160]}")
        return problems
