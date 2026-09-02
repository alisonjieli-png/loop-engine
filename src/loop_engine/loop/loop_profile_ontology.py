"""Resolve, validate, bind, and compare versioned loop profiles.

The immutable built-in definitions live in ``loop_profile_catalog``. This
module applies their parent relationships, checks the full tree, validates one
typed binding request, and builds the existing ``LoopConfig`` through the
existing Loop Template library. It does not define another runtime.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from .loop_contract import LoopContract
from .loop_profile_catalog import (
    INTELLIGENCE_BRANCH_IDS,
    LOOP_PROFILE_ONTOLOGY,
    MODEL_MODES,
    PROFILE_ONTOLOGY_VERSION,
    ROLE_PROFILE_ALIASES,
    ROOT_PROFILE_ID,
    TOP_BRANCH_IDS,
    LoopProfileError,
    LoopProfileRef,
    LoopProfileSpec,
    _normalized_strings,
    _spec,
    _version_tuple,
    profile_catalog,
    resolve_profile_alias,
)
from .loop_role import (LOOP_RELATIONSHIP_KINDS, LoopRelationship, LoopRole,
                        LoopRoleIdentity)
from .loop_templates import (TEMPLATE_LIBRARY, config_from_template,
                             validate_template)
from .recursive_loop import (MODEL_THINKING_POWER_LEVELS, MODES, POWER_LEVELS,
                             LoopConfig, default_loop_condition)


def _ordered_union(groups) -> tuple[str, ...]:
    output: list[str] = []
    for group in groups:
        for value in group:
            if value not in output:
                output.append(value)
    return tuple(output)


@dataclass(frozen=True)
class ResolvedLoopProfile:
    """A profile after parent requirements have been applied."""

    spec: LoopProfileSpec
    lineage: tuple[LoopProfileRef, ...]
    required_fields: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    allowed_logical_kinds: tuple[str, ...]
    allowed_modes: tuple[str, ...]
    step_template_id: str
    loop_condition: str
    exit_condition: str
    thinking_power_policy: str

@dataclass(frozen=True)
class OntologyValidationResult:
    """The result of a complete ontology validation pass."""

    valid: bool
    violations: tuple[str, ...] = ()

    def explain(self) -> str:
        return "valid" if self.valid else "; ".join(self.violations)


@dataclass(frozen=True)
class LoopProfileBindingRequest:
    """One object for selecting and configuring a runnable profile.

    The contract carries typed inputs and outputs. ``available_fields`` names
    other typed objects supplied by the caller, such as a query or a canvas.
    ``capabilities`` names compatible services available to run the profile.
    """

    profile: LoopProfileRef
    goal: str
    contract: LoopContract
    available_fields: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    modes: tuple[str, ...] = ("deterministic",)
    preferred_modes: tuple[str, ...] = ()
    delegated_modes: tuple[str, ...] = MODES
    logical_kind: str = ""
    effort: str = "standard"
    llm_thinking_power: str = ""
    max_depth: "int | None" = None
    relationship: LoopRelationship = field(
        default_factory=LoopRelationship.starting)

    def __post_init__(self) -> None:
        if not self.goal.strip():
            raise LoopProfileError("a profile binding needs a goal")
        if not isinstance(self.contract, LoopContract):
            raise LoopProfileError("contract must be a LoopContract")
        for name in ("available_fields", "capabilities", "modes",
                     "preferred_modes", "delegated_modes"):
            object.__setattr__(
                self, name, _normalized_strings(name, getattr(self, name)))
        if not self.modes:
            raise LoopProfileError("modes cannot be empty")
        if not self.delegated_modes:
            raise LoopProfileError("delegated_modes cannot be empty")
        if self.effort not in POWER_LEVELS:
            raise LoopProfileError(f"effort must be one of {POWER_LEVELS}")
        if (self.max_depth is not None
                and (not isinstance(self.max_depth, int)
                     or isinstance(self.max_depth, bool)
                     or self.max_depth < 0)):
            raise LoopProfileError(
                "max_depth must be non-negative when provided")
        if not isinstance(self.relationship, LoopRelationship):
            raise LoopProfileError("relationship must be a LoopRelationship")


@dataclass(frozen=True)
class BoundLoopProfile:
    """A validated profile plus the existing runtime configuration."""

    profile: ResolvedLoopProfile
    contract: LoopContract
    config: LoopConfig
    identity: LoopRoleIdentity
    relationship: LoopRelationship


@dataclass(frozen=True)
class LoopProfileRequirement:
    """The profile and version range a consumer accepts."""

    profile_id: str
    minimum_version: str = PROFILE_ONTOLOGY_VERSION
    compatible_major: int = 1

    def __post_init__(self) -> None:
        LoopProfileRef(self.profile_id, self.minimum_version)
        if self.compatible_major < 0:
            raise LoopProfileError("compatible_major cannot be negative")
        if _version_tuple(self.minimum_version)[0] != self.compatible_major:
            raise LoopProfileError(
                "minimum_version major must match compatible_major")


@dataclass(frozen=True)
class LoopProfileHandshakeResult:
    """Machine-readable compatibility between two profile requirements."""

    compatible: bool
    provided: LoopProfileRef
    required: LoopProfileRequirement
    lineage: tuple[LoopProfileRef, ...] = ()
    violations: tuple[str, ...] = ()

    def explain(self) -> str:
        return "compatible" if self.compatible else "; ".join(self.violations)


def _registry(
        profiles=LOOP_PROFILE_ONTOLOGY
) -> dict[tuple[str, str], LoopProfileSpec]:
    return {profile.ref.key: profile for profile in profiles}


def get_profile(ref: LoopProfileRef, *,
                profiles=LOOP_PROFILE_ONTOLOGY) -> LoopProfileSpec:
    """Return one exact profile version or fail closed."""
    try:
        return _registry(profiles)[ref.key]
    except KeyError as exc:
        raise LoopProfileError(
            f"profile {ref.profile_id}@{ref.version} is not registered") from exc


def resolve_profile(ref: LoopProfileRef, *,
                    profiles=LOOP_PROFILE_ONTOLOGY) -> ResolvedLoopProfile:
    """Apply explicit parent requirements to one profile."""
    registry = _registry(profiles)
    lineage: list[LoopProfileSpec] = []
    seen: set[tuple[str, str]] = set()
    current = ref
    while True:
        if current.key in seen:
            raise LoopProfileError(
                f"profile inheritance cycle at {current.profile_id}")
        seen.add(current.key)
        try:
            spec = registry[current.key]
        except KeyError as exc:
            raise LoopProfileError(
                f"profile {current.profile_id}@{current.version} is missing") from exc
        lineage.append(spec)
        if spec.parent is None:
            break
        current = spec.parent
    lineage.reverse()
    leaf = lineage[-1]
    step_template_id = next(
        (profile.step_template_id for profile in reversed(lineage)
         if profile.step_template_id), "")
    template_frameworks = {
        body["template_id"]: body["framework"] for body in TEMPLATE_LIBRARY}
    loop_condition = (
        default_loop_condition(template_frameworks[step_template_id])
        if step_template_id in template_frameworks else "")
    return ResolvedLoopProfile(
        spec=leaf, lineage=tuple(profile.ref for profile in lineage),
        required_fields=_ordered_union(
            profile.required_fields for profile in lineage),
        required_capabilities=_ordered_union(
            profile.required_capabilities for profile in lineage),
        allowed_logical_kinds=leaf.allowed_logical_kinds,
        allowed_modes=leaf.allowed_modes,
        step_template_id=step_template_id,
        loop_condition=loop_condition,
        exit_condition=next(
            (profile.exit_condition for profile in reversed(lineage)
             if profile.exit_condition), ""),
        thinking_power_policy=leaf.thinking_power_policy)


def identity_for_profile(
        ref: LoopProfileRef, *, profiles=LOOP_PROFILE_ONTOLOGY
        ) -> LoopRoleIdentity:
    """Bind one exact role profile identity without inferring relationship."""
    profile = resolve_profile(ref, profiles=profiles)
    try:
        role = LoopRole(profile.spec.family)
        return LoopRoleIdentity(role, ref.profile_id, ref.version)
    except ValueError as exc:
        raise LoopProfileError(str(exc)) from exc


def validate_profile_ontology(
        profiles=LOOP_PROFILE_ONTOLOGY) -> OntologyValidationResult:
    """Validate position, inheritance, templates, and mode rules."""
    violations: list[str] = []
    keys = [profile.ref.key for profile in profiles]
    if len(keys) != len(set(keys)):
        violations.append("profile references must be unique")
    registry = _registry(profiles)
    roots = [profile for profile in profiles if profile.parent is None]
    if [profile.profile_id for profile in roots] != [ROOT_PROFILE_ID]:
        violations.append("the ontology needs one root profile named loop")
    root_ref = LoopProfileRef(ROOT_PROFILE_ID)
    top = {profile.profile_id for profile in profiles
           if profile.parent == root_ref}
    if top != set(TOP_BRANCH_IDS):
        violations.append(
            "loop must branch directly into practitioner, intelligence, "
            "and solution")
    intelligence_ref = LoopProfileRef("intelligence")
    pillars = {profile.profile_id for profile in profiles
               if profile.parent == intelligence_ref
               and profile.state == "abstract"}
    if pillars != set(INTELLIGENCE_BRANCH_IDS):
        violations.append(
            "intelligence must branch into Context, Code, Runtime History and "
            "Solution, and User Feedback profiles")

    templates = {body["template_id"]: body for body in TEMPLATE_LIBRARY}
    for alias, target in ROLE_PROFILE_ALIASES:
        if LoopProfileRef(target).key not in registry:
            violations.append(
                f"profile alias {alias!r} targets missing profile {target!r}")
    for profile in profiles:
        if profile.parent is not None and profile.parent.key not in registry:
            violations.append(
                f"{profile.profile_id} has missing parent "
                f"{profile.parent.profile_id}@{profile.parent.version}")
            continue
        try:
            resolved = resolve_profile(profile.ref, profiles=profiles)
        except LoopProfileError as exc:
            violations.append(str(exc))
            continue
        if profile.profile_id != ROOT_PROFILE_ID and len(resolved.lineage) > 1:
            expected_family = resolved.lineage[1].profile_id
            if profile.family != expected_family:
                violations.append(
                    f"{profile.profile_id} family {profile.family!r} does not "
                    f"match branch {expected_family!r}")
        elif profile.profile_id != ROOT_PROFILE_ID:
            violations.append(
                f"{profile.profile_id} is not connected to the loop root")
        if profile.parent is not None:
            parent = registry[profile.parent.key]
            if not set(profile.allowed_modes) <= set(parent.allowed_modes):
                violations.append(
                    f"{profile.profile_id} expands its parent's run modes")
            if not set(profile.allowed_logical_kinds) <= set(
                    parent.allowed_logical_kinds):
                violations.append(
                    f"{profile.profile_id} expands its parent's logical kinds")
        if profile.state != "abstract":
            template = templates.get(resolved.step_template_id)
            if template is None:
                violations.append(
                    f"{profile.profile_id} names missing step template "
                    f"{resolved.step_template_id!r}")
            elif not validate_template(template)["valid"]:
                violations.append(
                    f"{profile.profile_id} names an invalid step template")
            elif (profile.state == "registered"
                  and template.get("maturity") != "registered"):
                violations.append(
                    f"{profile.profile_id} uses an unregistered step template")
        if (profile.profile_id == "practitioner.self_improvement"
                and "practitioner" not in
                [item.profile_id for item in resolved.lineage]):
            violations.append(
                "self-improvement must remain a Practitioner task")
    return OntologyValidationResult(not violations, tuple(violations))


def _contract_runtime_modes(contract: LoopContract) -> tuple[str, ...]:
    mode_names = {"code_only": "deterministic", "hybrid": "hybrid",
                  "model_led": "non_deterministic"}
    return tuple(mode_names[mode] for mode in contract.mode_waterfall)


def bind_profile(request: LoopProfileBindingRequest, *,
                 profiles=LOOP_PROFILE_ONTOLOGY) -> BoundLoopProfile:
    """Validate one profile selection and build the existing ``LoopConfig``."""
    ontology = validate_profile_ontology(profiles)
    if not ontology.valid:
        raise LoopProfileError("invalid profile ontology: " + ontology.explain())
    profile = resolve_profile(request.profile, profiles=profiles)
    identity = identity_for_profile(request.profile, profiles=profiles)
    if profile.spec.state != "registered":
        raise LoopProfileError(
            f"profile {profile.spec.profile_id!r} has state "
            f"{profile.spec.state!r} and cannot run")
    if any(mode not in profile.allowed_modes for mode in request.modes):
        raise LoopProfileError(
            f"requested modes must be a subset of {profile.allowed_modes}")
    if (request.preferred_modes
            and any(mode not in request.modes
                    for mode in request.preferred_modes)):
        raise LoopProfileError("preferred_modes must be a subset of modes")
    if any(mode not in MODES for mode in request.delegated_modes):
        raise LoopProfileError(f"delegated_modes must use {MODES}")
    logical_kind = request.logical_kind or profile.allowed_logical_kinds[0]
    if logical_kind not in profile.allowed_logical_kinds:
        raise LoopProfileError(
            f"logical_kind must be one of {profile.allowed_logical_kinds}")

    automatic_fields = {"loop_contract", "loop_condition", "exit_condition",
                        "step_profile", "mode_policy"}
    available = automatic_fields | set(request.available_fields)
    missing_fields = [field for field in profile.required_fields
                      if field not in available]
    if missing_fields:
        raise LoopProfileError(
            f"profile is missing required fields {missing_fields}")
    missing_capabilities = [capability
                            for capability in profile.required_capabilities
                            if capability not in request.capabilities]
    if missing_capabilities:
        raise LoopProfileError(
            "profile is missing required capabilities "
            f"{missing_capabilities}")

    uses_model = any(mode in MODEL_MODES for mode in request.modes)
    if request.llm_thinking_power not in (
            "", *MODEL_THINKING_POWER_LEVELS):
        raise LoopProfileError(
            "llm_thinking_power must be small, medium, high, max, or "
            "specialized")
    if uses_model and profile.thinking_power_policy == "forbidden":
        raise LoopProfileError(
            "this profile forbids hybrid and non_deterministic modes")
    if (uses_model
            and profile.thinking_power_policy == "required_for_model_modes"
            and not request.llm_thinking_power):
        raise LoopProfileError(
            "llm_thinking_power is required when hybrid or "
            "non_deterministic mode is selected")
    if not uses_model and request.llm_thinking_power:
        raise LoopProfileError(
            "llm_thinking_power is allowed only with hybrid or "
            "non_deterministic mode")

    contract_modes = _contract_runtime_modes(request.contract)
    if not set(contract_modes) <= set(request.modes):
        raise LoopProfileError(
            f"contract mode path {contract_modes} exceeds selected "
            f"modes {request.modes}")

    template = next(
        dict(body) for body in TEMPLATE_LIBRARY
        if body["template_id"] == profile.step_template_id)
    template["allowed_modes"] = request.modes
    template["logical_kind"] = logical_kind
    template["loop_condition"] = profile.loop_condition
    template["exit_condition"] = profile.exit_condition
    config = config_from_template(
        template, power=request.effort, max_depth=request.max_depth)
    config = replace(
        config,
        preferred_modes=request.preferred_modes or request.modes,
        delegated_modes=request.delegated_modes,
        llm_thinking_power=request.llm_thinking_power)
    return BoundLoopProfile(
        profile=profile, contract=request.contract, config=config,
        identity=identity, relationship=request.relationship)


def profile_handshake(
        provided: LoopProfileRef, requirement: LoopProfileRequirement, *,
        profiles=LOOP_PROFILE_ONTOLOGY) -> LoopProfileHandshakeResult:
    """Check profile ancestry and semantic-version compatibility."""
    violations: list[str] = []
    try:
        resolved = resolve_profile(provided, profiles=profiles)
        lineage = resolved.lineage
    except LoopProfileError as exc:
        return LoopProfileHandshakeResult(
            False, provided, requirement, violations=(str(exc),))
    lineage_ids = {item.profile_id for item in lineage}
    if requirement.profile_id not in lineage_ids:
        violations.append(
            f"{provided.profile_id} does not extend {requirement.profile_id}")
    provided_version = _version_tuple(provided.version)
    minimum_version = _version_tuple(requirement.minimum_version)
    if provided_version[0] != requirement.compatible_major:
        violations.append(
            f"provided major {provided_version[0]} is not accepted major "
            f"{requirement.compatible_major}")
    if provided_version < minimum_version:
        violations.append(
            f"provided version {provided.version} is older than "
            f"{requirement.minimum_version}")
    return LoopProfileHandshakeResult(
        not violations, provided, requirement, lineage,
        tuple(violations))


def self_test() -> dict:
    """Run deterministic catalog, binding, and compatibility checks."""
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    validation = validate_profile_ontology()
    check("ontology_has_one_root_and_three_clear_branches",
          validation.valid, validation.explain())

    required_profiles = {
        "practitioner.reference_nine_step",
        "practitioner.compact_five_step",
        "practitioner.research",
        "practitioner.solver",
        "practitioner.verifier",
        "practitioner.self_improvement",
        "practitioner.code_execution",
        "intelligence.search", "intelligence.materialize",
        *INTELLIGENCE_BRANCH_IDS,
        "solution.atomic_component", "solution.pipeline",
        "solution.router_fallback", "solution.ensemble",
        "solution.validator",
    }
    profile_ids = {profile.profile_id for profile in LOOP_PROFILE_ONTOLOGY}
    solution_profiles = [profile for profile in LOOP_PROFILE_ONTOLOGY
                         if profile.profile_id.startswith("solution.")]
    # Every role shares the one mode contract: all three modes declared,
    # model modes gated by an explicit thinking-power policy. The role is
    # never the reason a mode is unavailable.
    check("required_profile_families_are_registered",
          required_profiles <= profile_ids
          and all(profile.allowed_modes == ("deterministic", "hybrid",
                                            "non_deterministic")
                  and profile.thinking_power_policy
                  == "required_for_model_modes"
                  for profile in solution_profiles),
          f"{len(LOOP_PROFILE_ONTOLOGY)} profiles; Solution profiles declare "
          "all three modes like every role, with governed model authority")

    catalog = profile_catalog()
    aliases = {
        name: resolve_profile_alias(name).profile_id
        for name, _target in ROLE_PROFILE_ALIASES
    }
    check("profiles_are_relationship_neutral_and_keep_role_aliases",
          all(item["supported_relationship_kinds"]
              == list(LOOP_RELATIONSHIP_KINDS)
              for item in catalog if item["family"] != "universal")
          and next(item for item in catalog
                   if item["family"] == "universal")
          ["supported_relationship_kinds"]
          == []
          and aliases["researcher"] == "practitioner.research"
          and aliases["intelligence.materialize"]
          == "intelligence.materialize"
          and aliases["solution.fallback"] == "solution.router_fallback"
          and all("exit_condition" in item for item in catalog),
          "semantic relationships are independent of role profiles")

    code_profile = resolve_profile(
        LoopProfileRef("intelligence.code.invoke"))
    check("spawned_profiles_inherit_required_fields_and_capabilities",
          code_profile.required_fields == (
              "loop_contract", "loop_condition", "exit_condition",
              "step_profile", "mode_policy", "code_asset_ref", "code_contract",
              "operation_ref")
          and code_profile.loop_condition == "steps_remain"
          and code_profile.exit_condition == "accepted_success"
          and "intelligence_reference" in code_profile.required_capabilities
          and "code_execution" in code_profile.required_capabilities,
          "resolved through loop, intelligence, code, invoke")

    deterministic_power_refused = False
    try:
        bind_profile(LoopProfileBindingRequest(
            profile=LoopProfileRef("solution.atomic_component"),
            goal="normalize one row",
            contract=LoopContract(
                "normalize", "code_only", input_roles=("row/v1",),
                output_roles=("row/v1",)),
            available_fields=("operation_ref",),
            capabilities=("solution_canvas", "component_execution"),
            llm_thinking_power="high"))
    except LoopProfileError:
        deterministic_power_refused = True
    check("deterministic_profile_refuses_llm_thinking_power",
          deterministic_power_refused)

    missing_power_refused = False
    try:
        bind_profile(LoopProfileBindingRequest(
            profile=LoopProfileRef("practitioner.solver"),
            goal="repair the import",
            contract=LoopContract(
                "repair", "hybrid", input_roles=("failure/v1",),
                output_roles=("patch/v1",)),
            available_fields=("acceptance_test",),
            capabilities=("loop_spawn", "run_history_write",
                          "solution_build", "independent_verification"),
            modes=("deterministic", "hybrid")))
    except LoopProfileError:
        missing_power_refused = True
    check("model_mode_requires_llm_thinking_power", missing_power_refused)

    bound = bind_profile(LoopProfileBindingRequest(
        profile=LoopProfileRef("practitioner.solver"),
        goal="repair the import",
        contract=LoopContract(
            "repair", "hybrid", input_roles=("failure/v1",),
            output_roles=("patch/v1",)),
        available_fields=("acceptance_test",),
        capabilities=("loop_spawn", "run_history_write", "solution_build",
                      "independent_verification"),
        modes=("deterministic", "hybrid"),
        preferred_modes=("deterministic", "hybrid"),
        llm_thinking_power="high"))
    check("profile_binding_builds_the_existing_loop_config",
          isinstance(bound.config, LoopConfig)
          and bound.config.framework == "custom"
          and bound.config.custom_steps[0] == "understand_minimum"
          and bound.config.allowable_modes == ("deterministic", "hybrid")
          and bound.config.llm_thinking_power == "high"
          and bound.config.loop_condition == "steps_remain"
          and bound.config.exit_condition == "steps_complete"
          and bound.relationship == LoopRelationship.starting()
          and bound.identity.role == LoopRole.PRACTITIONER)

    spawned_bound = bind_profile(LoopProfileBindingRequest(
        profile=LoopProfileRef("intelligence.materialize"),
        goal="load one selected context item",
        contract=LoopContract(
            "materialize", "code_only", output_roles=("item/v1",)),
        available_fields=("intelligence_ref", "expected_digest"),
        capabilities=(
            "intelligence_reference", "intelligence_materialize",
            "digest_verify"),
        relationship=LoopRelationship.retrieved_by("loop17")))
    check("profile_identity_is_separate_from_semantic_relationship",
          spawned_bound.relationship == LoopRelationship.retrieved_by("loop17")
          and spawned_bound.identity.role == LoopRole.INTELLIGENCE)

    improvement = resolve_profile(
        LoopProfileRef("practitioner.self_improvement"))
    check("self_improvement_is_a_practitioner_task",
          improvement.spec.family == "practitioner"
          and improvement.lineage[1].profile_id == "practitioner"
          and improvement.allowed_logical_kinds == ("search_improvement",))

    accepted = profile_handshake(
        LoopProfileRef("intelligence.context.search"),
        LoopProfileRequirement("intelligence.context"))
    rejected = profile_handshake(
        LoopProfileRef("solution.pipeline"),
        LoopProfileRequirement("intelligence.context"))
    stale = profile_handshake(
        LoopProfileRef("intelligence.context.search"),
        LoopProfileRequirement(
            "intelligence.context", minimum_version="1.1.0",
            compatible_major=1))
    check("profile_handshake_checks_ancestry_and_version",
          accepted.compatible and not rejected.compatible and not stale.compatible,
          f"accepted: {accepted.explain()}; rejected: {rejected.explain()}; "
          f"stale: {stale.explain()}")

    candidate = _spec(
        "solution.candidate_component", "Candidate component", "solution",
        "Used only to test candidate isolation.", parent="solution",
        state="candidate", template="atomic_code_only",
        exit_condition="accepted_success",
        kinds=("execution",), modes=("deterministic",),
        fields=("operation_ref",), capabilities=("component_execution",),
        thinking="forbidden")
    candidate_refused = False
    try:
        bind_profile(LoopProfileBindingRequest(
            profile=candidate.ref,
            goal="try candidate",
            contract=LoopContract(
                "candidate", "code_only", output_roles=("value/v1",)),
            available_fields=("operation_ref",),
            capabilities=("solution_canvas", "component_execution")),
            profiles=LOOP_PROFILE_ONTOLOGY + (candidate,))
    except LoopProfileError:
        candidate_refused = True
    check("candidate_profile_cannot_run", candidate_refused)

    bad_spawned = _spec(
        "practitioner.invalid_expansion", "Invalid expansion", "practitioner",
        "Used only to test fail-closed validation.",
        parent="practitioner.code_execution", template="atomic_code_only",
        exit_condition="accepted_success", kinds=("execution",), modes=MODES)
    adversarial = validate_profile_ontology(
        LOOP_PROFILE_ONTOLOGY + (bad_spawned,))
    check("spawned_profile_cannot_expand_parent_modes",
          not adversarial.valid
          and any("expands its parent's run modes" in item
                  for item in adversarial.violations),
          adversarial.explain())

    passed = sum(1 for test in tests if test["passed"])
    return {"record_type": "loop_profile_ontology_self_test",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
