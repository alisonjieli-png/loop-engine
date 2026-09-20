"""The adaptive Practitioner's existing capability descriptions.

This module owns the single descriptor constant previously in the runtime
records module. Descriptions do not grant authority or execute a capability.
Dispatch, eligibility, effects, and permissions remain at their typed owners.
"""

from ...strings.capability_resources import GENERATED_PROJECT_PURPOSE_RENDER

WEB_SEARCH_CREDENTIALS = "web_search_credentials"
OPERATOR_VERIFIER = "operator_verifier"
CAPABILITY_DIRECTORY = "capability_directory"


ADAPTIVE_CAPABILITIES = (
    {
        "capability_ref": "core.source.inspect",
        "purpose": (
            "USE THIS FIRST whenever local sources were supplied: this runtime refuses to generate a project until supplied sources have been selected here. Inspect supplied local source manifests and selected text bodies "
            "before deciding how to solve or repair the task."),
        "arguments": {
            "paths": "optional exact relative source paths",
            "query": "optional lexical query for source selection",
            "include_contents": "false for manifest only, true for bodies",
        },
        "required_permissions": ["source_read"],
        "effects": ["reads_fs"],
    },
    {
        "capability_ref": "core.workspace.read",
        "purpose": (
            "USE THIS WHEN a command failed, a test failed, or a verification rejected your work -- read back what you ACTUALLY wrote before repairing, because repairing a file you have not looked at is guessing. Read back a file this run produced, with interpreter line "
            "numbers, so generated code can be repaired from what it "
            "actually says rather than from memory of what was intended. "
            "Reads only inside this run's workspace; supplied input files "
            "stay with core.source.inspect."),
        "arguments": {
            "path": ("optional workspace-relative path; omit it to list "
                     "every file this run has produced"),
            "first_line": "optional 1-based line to start from",
        },
        "required_permissions": ["workspace_write"],
        "effects": ["reads_fs"],
    },
    {
        "capability_ref": "core.capability.call",
        "required_bindings": (CAPABILITY_DIRECTORY,),
        "purpose": (
            "USE THIS WHEN the work matches a capability this engine already "
            "ships -- conforming text columns, finding duplicate records, "
            "recovering spoiled contact values, splitting address lines -- "
            "because a registered capability runs exactly and costs no model "
            "call. Name the surface and the operation you need; the reply "
            "lists every surface this run has, so ask once with a surface you "
            "saw there. A surface that writes files is not callable here."),
        "arguments": {
            "surface": "the registered surface name, for example text_conformance",
            "operation": "one operation that surface declares, for example run",
            "arguments": "optional mapping forwarded to the surface unchanged",
        },
        "required_permissions": [],
        "effects": ["pure"],
    },
    {
        "capability_ref": "core.web.search",
        "required_bindings": (WEB_SEARCH_CREDENTIALS,),
        "purpose": (
            "Search public web sources and return ranked candidates. Search "
            "results are not evidence until a selected URL is fetched."),
        "arguments": {
            "query": "one search query",
            "purpose": "why candidate sources are needed",
            "maximum_results": "optional positive integer owner limit",
        },
        "required_permissions": ["network_read"],
        "effects": ["network_read"],
    },
    {
        "capability_ref": "core.web.get",
        "purpose": "Read one public HTTPS resource and retain its exact body.",
        "arguments": {
            "url": "public HTTPS URL",
            "purpose": "why this source is needed",
            "maximum_bytes": "optional positive integer",
        },
        "required_permissions": ["network_read"],
        "effects": ["network_read"],
    },
    {
        "capability_ref": "core.generated_project",
        "purpose": GENERATED_PROJECT_PURPOSE_RENDER.text,
        "purpose_resource": GENERATED_PROJECT_PURPOSE_RENDER.to_dict(),
        "arguments": {
            "constraint": "optional engine-owned check named per expected "
                          "artifact: 'schedule/v1' or 'json_collection/v1'",
        },
        "required_permissions": ["workspace_write", "sandbox_command"],
        "effects": ["writes_fs", "spawns_process"],
    },
    {
        "capability_ref": "core.verify.differential",
        "purpose": (
            "USE THIS WHEN your own tests pass but you are not certain the code is right, or when you have produced more than one implementation -- it is the only check here you did not author. Verify a produced module WITHOUT any expected value you supply. "
            "Prefer this over asserting hand-computed constants: your code is "
            "more reliable than your arithmetic, so an assertion you compute "
            "by hand is the weakest link in your own work. Two oracles. "
            "'differential' runs two or more independently written "
            "implementations of the same contract over the same inputs and "
            "reports any input where they disagree; agreement is the "
            "evidence and no constant is consulted. 'metamorphic' asserts "
            "relations between calls that hold by construction, such as "
            "f(\'PT60S\') == f(\'PT1M\'), without knowing either answer. "
            "Each candidate runs in its own process. A verdict of "
            "UNVERIFIED means the oracle could not decide and is never "
            "success."),
        "arguments": {
            "oracle": "'differential' (default) or 'metamorphic'",
            "implementations": "differential: two or more workspace-relative "
                               "paths to modules implementing the same "
                               "contract",
            "implementation": "metamorphic: one workspace-relative module path",
            "entry_point": "required; the function name to call in each module",
            "arguments": "differential: list of inputs to pass, one per call",
            "relations": "metamorphic: list of [left, right] input pairs whose "
                         "results must be equal",
        },
        "required_permissions": ["workspace_write", "sandbox_command"],
        "effects": ["reads_fs", "spawns_process"],
    },
    {
        "capability_ref": "core.source.profile",
        "purpose": (
            "USE THIS BEFORE designing around data you have not measured: it reports shape, columns and sample rows without spending a model call on reading the file. Profile selected text sources deterministically: line counts, "
            "column structure for CSV and JSON shapes, key fields, and "
            "sample rows, without sending any content to a model."),
        "arguments": {
            "paths": "optional exact relative source paths; omit to profile "
                     "every supplied source",
            "maximum_sample_bytes": "optional positive integer owner limit",
        },
        "required_permissions": ["source_read"],
        "effects": ["reads_fs"],
    },
    {
        "capability_ref": "core.environment.describe",
        "purpose": (
            "USE THIS BEFORE assuming a package, tool or sandbox capability exists -- one call here is cheaper than a failed pass. Describe the current runtime environment deterministically: "
            "available execution capabilities, sandbox availability, "
            "configured providers without secrets, and task authority "
            "grants. Effect-free discovery for orientation."),
        "arguments": {},
        "required_permissions": [],
        "effects": [],
    },
    {
        "capability_ref": "core.verifier.execute",
        "required_bindings": (OPERATOR_VERIFIER,),
        "purpose": (
            "Run the operator-declared verifier script against the run's "
            "current artifacts and return its score and output as an "
            "observation for replanning. The score never accepts the task "
            "by itself; acceptance stays with verification. Only the "
            "explicit declared path ever runs."),
        "arguments": {},
        "required_permissions": ["workspace_write", "sandbox_command"],
        "effects": ["spawns_process"],
    },
    {
        "capability_ref": "core.intelligence.search",
        "purpose": (
            "Search the supplied Practitioner Context Intelligence portfolio "
            "or the packaged context catalogue through existing retrieval. "
            "Results are references and candidates, never authority."),
        "arguments": {
            "query": "one retrieval query",
            "kinds": "optional list of record kinds to filter",
        },
        "required_permissions": [],
        "effects": [],
    },
)
