"""Versioned instruction resources used by capability discovery.

These resources describe existing operations. They grant no permissions,
select no implementation, and do not independently qualify generated work.
"""
from __future__ import annotations

from .prompt_fragments import PromptResourceBundle, PromptResourceComponent


GENERATED_PROJECT_PURPOSE = PromptResourceBundle(
    bundle_id="adaptive.generated_project.purpose", version="1.0.0",
    components=(PromptResourceComponent("purpose", (
        "Create files, execute Python commands in a confined Docker "
        "workspace, run tests, and verify expected artifacts. Put every "
        "source file you want in 'files' with its real content; do not "
        "author one script that writes the others as embedded strings "
        "(that nests source inside a string and corrupts quotes and "
        "escapes). A path in 'files' must not also appear in "
        "'expected_artifacts', which must name at least one file a "
        "command actually WRITES TO DISK. `python3 -m unittest` writes to "
        "stdout and creates NO file, so do not declare its output: add a "
        "command that writes a real file (for example a runner that calls "
        "your module and writes a small result or summary file) and "
        "declare THAT path. Declaring a file nothing writes fails the "
        "run even when the code is correct. An expected artifact may name an "
        "engine-owned 'constraint' check -- 'schedule/v1' (task ordering, "
        "durations, dependencies, cycles) or 'json_collection/v1' -- "
        "which is the only verification here you did not author."), ()),),
    slots=(), output_schema_ref="generated_project_candidate/v1",
    interpreter_profile_ref="practitioner.reference_nine_step@1.0.0",
    policy_ref="core.generated_project",
)
GENERATED_PROJECT_PURPOSE_RENDER = GENERATED_PROJECT_PURPOSE.render({}, provenance={})


def self_test() -> dict:
    """Check exact render identity, immutable composition, and slot refusal."""
    import hashlib
    from dataclasses import replace
    resource = GENERATED_PROJECT_PURPOSE
    rendered = GENERATED_PROJECT_PURPOSE_RENDER
    refused = False
    try:
        resource.render({"undeclared": "must not enter the instruction"}, provenance={})
    except KeyError:
        refused = True
    changed = replace(resource, components=(replace(resource.components[0], template="Changed body"),))
    tests = [
        {"test": "capability_instruction_retains_the_reviewed_text_bytes",
         "passed": hashlib.sha256(rendered.text.encode()).hexdigest()
         == "f96ca4656100e386022b2125a11f6bbed0171c724388ebd262a10544c819f1db"},
        {"test": "capability_instruction_binds_version_and_content",
         "passed": rendered.bundle_ref == resource.bundle_ref
         and rendered.bundle_digest == resource.content_digest
         and changed.content_digest != resource.content_digest},
        {"test": "capability_instruction_refuses_undeclared_slots", "passed": refused},
    ]
    return {"record_type": "capability_resources_test/v1", "tests": tests}
