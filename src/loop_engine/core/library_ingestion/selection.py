"""Engine slots of the library ingestion component and their selection, recorded before use.

Each slot declares its protocol, its closed engine kinds, whether it picks
one engine or runs every eligible one, and its declared order (the initial
choice, then the ordered fallbacks). Selection is effect-free: it reads each
engine's own availability, removes every engine that is switched off or
cannot run with a named reason, keeps the declared order among the rest,
and returns a library_engine_selection/v1 decision before anything is
dispatched. A decision never grants network, file, model or spending
authority. This follows the engine design (docs/architecture/
ENGINES-BEHIND-FIXED-EDGES.md, sections 4 and 8) ahead of the shared
framework, whose records can replace this one without changing an engine.
"""
from __future__ import annotations

from dataclasses import dataclass

from .record_rules import LibraryRecordError, canonical_digest, now_utc

SELECTION_RECORD_TYPE = "library_engine_selection/v1"
ONE_OF, SET_OF = "one_of", "set_of"
INELIGIBLE_REASONS = ("switched_off", "dependency_missing", "not_configured", "authority_missing",
                      "not_installed", "schema_digest_changed")


@dataclass(frozen=True)
class EngineSlot:
    """One swap point: its edge protocol, engine kinds, selection mode and declared order."""

    slot_id: str
    slot_version: str
    protocol: str
    kinds: tuple
    selection_mode: str
    declared_order: tuple
    required: bool = True

    def __post_init__(self) -> None:
        if self.selection_mode not in (ONE_OF, SET_OF) or not self.declared_order:
            raise LibraryRecordError("invalid_slot", f"{self.slot_id} needs a mode and a declared order")


def select_engines(slot: EngineSlot, factories: dict, settings: dict, *, switched_off=()):
    """Return (decision, engine classes chosen), without constructing or running anything."""
    rows, chosen = [], []
    for engine_id in slot.declared_order:
        factory = factories.get(engine_id)
        if factory is None:
            rows.append({"engine_id": engine_id, "engine_version": None, "eligible": False,
                         "reason": "not_installed"})
            continue
        if engine_id in switched_off:
            eligible, reason = False, "switched_off"
        else:
            eligible, reason = factory.availability(settings)
        if factory.engine_kind not in slot.kinds:
            eligible, reason = False, "not_installed"
        if not eligible and reason not in INELIGIBLE_REASONS:
            raise LibraryRecordError("invalid_availability", f"{engine_id} gave the reason {reason!r}")
        rows.append({"engine_id": engine_id, "engine_version": factory.engine_version,
                     "eligible": bool(eligible), "reason": reason})
        if eligible and (slot.selection_mode == SET_OF or not chosen):
            chosen.append(factory)
    if slot.required and not chosen:
        raise LibraryRecordError("no_eligible_engine", f"no engine of {slot.slot_id} can run here")
    decision = {"record_type": SELECTION_RECORD_TYPE, "slot_id": slot.slot_id,
                "slot_version": slot.slot_version, "selection_mode": slot.selection_mode,
                "declared_order": list(slot.declared_order), "eligibility": rows,
                "chosen": [factory.engine_id for factory in chosen], "authority_granted": False,
                "decided_at": now_utc(),
                "settings_digest": canonical_digest({key: str(value) for key, value in settings.items()})}
    decision["decision_digest"] = canonical_digest(decision)
    return decision, tuple(chosen)
