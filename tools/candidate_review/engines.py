"""The factory tables: the only code that names concrete engine classes.

Adding an engine means adding its module, one row here, its identity to the
configuration's closed engine vocabulary and its checks. No neighbour changes:
the panel reaches every engine through the pre-check edge or the reviewer edge.
A named check keeps this table and the configuration's vocabulary equal.
"""
from __future__ import annotations

from .configuration import FIXTURE_ENGINE_KIND
from .native_prechecks import (
    NativeDuplicateRules,
    NativeEffectsRules,
    NativeFormatRules,
    NativeLicenceRules,
    NativeMinHashRules,
    NativeSafetyRules,
    NativeSecretRules,
)
from .prechecks.agent_skills_reference import AgentSkillsReference
from .prechecks.duplicates import ExactShingleJaccard
from .prechecks.effects import EffectRules
from .prechecks.format_rules import FormatRules, vocabulary_patterns
from .prechecks.licence import LicenceRules
from .prechecks.minhash import DatasketchMinHash
from .prechecks.safety_rules import StaticSafetyRules
from .prechecks.secrets import SecretPatterns
from .prechecks.skillspector import SkillSpectorStatic
from .reviewers.binding import BindingReviewer
from .reviewers.command_line import CommandLineReviewer
from .reviewers.fixture import FixtureReviewer
from .reviewers.gateway import GatewayReviewer

PRECHECK_ENGINE_FACTORIES = {
    "builtin_licence_rules": LicenceRules,
    "builtin_format_rules": FormatRules,
    "agent_skills_reference": AgentSkillsReference,
    "builtin_static_rules": StaticSafetyRules,
    "skillspector_static": SkillSpectorStatic,
    "builtin_effect_rules": EffectRules,
    "builtin_secret_patterns": SecretPatterns,
    "exact_shingle_jaccard": ExactShingleJaccard,
    "datasketch_minhash_lsh": DatasketchMinHash,
    "native_licence_rules": NativeLicenceRules,
    "native_format_rules": NativeFormatRules,
    "native_safety_rules": NativeSafetyRules,
    "native_effects_rules": NativeEffectsRules,
    "native_secret_rules": NativeSecretRules,
    "native_duplicate_rules": NativeDuplicateRules,
    "native_minhash_rules": NativeMinHashRules,
}
#: The engines that need no external program and no optional library, so they are always available.
BUILTIN_PRECHECK_ENGINES = frozenset({"builtin_licence_rules", "builtin_format_rules", "builtin_static_rules",
                                      "builtin_effect_rules", "builtin_secret_patterns", "exact_shingle_jaccard"})


def _fixture_reviewer(installation, policy, context):
    scripts = context.fixture_scripts or {}
    return FixtureReviewer(installation, scripts.get(installation.installation_id))


REVIEWER_ENGINE_FACTORIES = {
    "model_gateway": GatewayReviewer,
    "command_line": CommandLineReviewer,
    "provider_binding": BindingReviewer,
    FIXTURE_ENGINE_KIND: _fixture_reviewer,
}


def build_precheck_engines(configuration, *, only_builtin: bool = False, programs=None) -> dict:
    """Every engine the policy names, kind by kind, in the declared order.

    ``programs`` maps an engine identity to the path of its program on this
    machine; it is operator configuration and changes nothing else.
    """
    built = {}
    for kind, engine_ids in configuration.policy.prechecks.items():
        engines = []
        for engine_id in engine_ids:
            if only_builtin and engine_id not in BUILTIN_PRECHECK_ENGINES:
                continue
            settings = configuration.engine_settings(engine_id)
            if programs and engine_id in programs:
                settings["program"] = str(programs[engine_id])
            engines.append(PRECHECK_ENGINE_FACTORIES[engine_id](settings, configuration.policy))
        built[kind] = tuple(engines)
    return built


def build_reviewer(installation, policy, context):
    return REVIEWER_ENGINE_FACTORIES[installation.engine_kind](installation, policy, context)


def format_vocabulary_patterns(configuration) -> tuple:
    """The internal vocabulary the format engine refuses, compiled from the declared settings."""
    return vocabulary_patterns(configuration.engine_settings("builtin_format_rules"))
