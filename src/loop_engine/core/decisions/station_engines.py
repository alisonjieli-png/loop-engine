"""The station engine factory table: every engine kind of the typed_decision slot.

This table names engine classes and defines none. Decision endpoints keep
their host configuration (decision_host_configuration/v2); the table only
lists which classes implement each kind, so a new engine is added with one
adapter module and one row here, without changing a station's caller.
"""
from __future__ import annotations

from .configuration import ADAPTER_FACTORIES
from .rules_engine import RulesDecisionEngine
from .stations import StationEngine

STATION_ENGINE_FACTORIES = {
    "decision_endpoint": tuple(dict.fromkeys(factory for _settings, factory in ADAPTER_FACTORIES.values())),
    "deterministic_rules": (RulesDecisionEngine,),
}


def built_in_installations():
    """The engines every host has without configuration: the rules engine,
    served on its contract checks (proof level local_contract)."""
    return (StationEngine("rules", "deterministic_rules", RulesDecisionEngine(), qualification="local_contract"),)
