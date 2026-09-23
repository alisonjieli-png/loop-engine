"""Named checks for the harness recipe catalogue and the runner that reads it.

Owns: the known-wrong cases of plan package X1 (roadmap S-6.31): a recipe
style spelled as a literal in the process runner or its relay, a recipe module
edited without its catalogue digest or reached through a link, a catalogue
file that repeats a key, the unsupported ``freebuff`` host file, the modules
one run mounts and digests, the Pi and Aider special cases read from the
record, and the relay's wire choice and framing names read from the record.
Does not own: the real Bubblewrap run of a fixture recipe, which lives in
``harness_process_checks.qualification_checks`` because it starts processes.
These checks start no process, open no socket and call no provider.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

#: The eighteen styles the closed tuple held before the catalogue existed.
#: The literal scan uses them as well as the catalogue's own styles, so a
#: broken or empty catalogue cannot make the scan pass by listing nothing.
HISTORICAL_TEXT_RESPONSE_STYLES = (
    "aider", "continue", "pi", "qwen_code", "gemini_cli", "goose", "opencode",
    "mini_swe_agent", "mistral_vibe", "gptme", "cline", "kilo", "nanocode",
    "trae_agent", "codex", "openinterpreter_rust", "hermes_agent", "forgecode")

#: The runner files that may never name a recipe style.
DISPATCH_FILES = ("harness_process.py", "harness_process_relay.py")

_HERE = Path(__file__).resolve().parent


def style_literals_in_source(source: str, styles) -> list:
    """Every string constant in ``source`` that equals a recipe style.

    A style spelled in the runner or the relay means a recipe still needs a
    core edit; the catalogue is the only place a style may be named."""
    wanted = set(styles)
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in wanted:
            found.append((node.lineno, node.value))
    return sorted(found)


def _mounted_relay_modules(arguments) -> set:
    """The recipe and codec modules a sandbox argument list mounts at /relay."""
    names = set()
    for index, value in enumerate(arguments):
        if value == "--ro-bind" and index + 2 < len(arguments):
            target = arguments[index + 2]
            if target.startswith("/relay/") and target.endswith(".py") and target != "/relay/run.py":
                names.add(target[len("/relay/"):-len(".py")])
    return names


def _setenv(arguments) -> dict:
    return {arguments[index + 1]: arguments[index + 2] for index, value in enumerate(arguments)
            if value == "--setenv" and index + 2 < len(arguments)}


@contextmanager
def _fixture_root():
    with tempfile.TemporaryDirectory(prefix="le-recipe-check-") as temporary:
        root = Path(temporary)
        for name in ("software", "work", "run"):
            (root / name).mkdir()
        (root / "software" / "identity.txt").write_text("passive fixture software")
        yield root


def _spec(style, root, catalog=None):
    from .harness_process import HarnessProcessSpec
    return HarnessProcessSpec("process_fixture", "1.0.0", (sys.executable,),
                              (str(root / "software"),), style, catalog=catalog)


def _request(spec, root, **changes):
    from .harness_process import HarnessProcessRequest
    values = dict(spec=spec, prompt="fixture task", model="fixture-model", output_capacity=64,
                  output_allowance=16, timeout_seconds=5.0, work_dir=str(root / "work"),
                  socket_directory=str(root.parent), context_capacity=4096)
    values.update(changes)
    return HarnessProcessRequest(**values)


def _launch(spec, root, maximum_output_bytes=4096):
    from .harness_process import SandboxLaunch
    return SandboxLaunch(spec=spec, run_directory=str(root / "run"),
                         socket_path=str(root / "run" / "broker.sock"),
                         request_values=(("maximum_output_bytes", maximum_output_bytes),))


def _catalog_variant(change):
    """A copy of the release catalogue with one declared change applied."""
    from .harness_recipes import HarnessRecipeCatalog, release_recipe_catalog
    release = release_recipe_catalog()
    value = json.loads(json.dumps(release.to_dict()))
    change(value)
    return HarnessRecipeCatalog.from_dict(value, module_directory=release.module_directory)


def _recipe_value(value, style):
    return next(item for item in value["recipes"] if item["style"] == style)


def _refuses(operation, error) -> bool:
    """True only for the typed refusal; any other exception is not a refusal."""
    try:
        operation()
    except error:
        return True
    except Exception:  # a KeyError or TypeError means the reader did not refuse cleanly
        return False
    return False


def _repeated_key_refused(release) -> bool:
    """A catalogue file that writes one key twice is refused, never read as
    whichever of the two values the YAML reader happens to keep."""
    from .harness_recipes import HarnessRecipeError, load_recipe_catalog
    with tempfile.TemporaryDirectory(prefix="le-recipe-reader-") as temporary:
        path = Path(temporary) / "harness_recipes.yaml"
        path.write_text("record_type: harness_recipe_catalog/v1\nversion: 1.0.0\nversion: 2.0.0\n"
                        "wire_codecs: []\nrecipes: []\nfresh_instance_recipes: []\n",
                        encoding="utf-8")
        return _refuses(lambda: load_recipe_catalog(path, module_directory=release.module_directory),
                        HarnessRecipeError)


def _reader_checks(check):
    from .harness_recipes import (HarnessRecipe, HarnessRecipeCatalog, HarnessRecipeError,
                                  HarnessWireCodec, release_recipe_catalog)
    release = release_recipe_catalog()
    value = release.to_dict()
    recipe = dict(value["recipes"][0])
    wire = dict(value["wire_codecs"][0])
    wrong_cases = {
        "recipe_with_an_extra_key": lambda: HarnessRecipe.from_dict({**recipe, "shell": "yes"}),
        "recipe_of_a_newer_version": lambda: HarnessRecipe.from_dict(
            {**recipe, "record_type": "harness_recipe/v2"}),
        "recipe_missing_a_key": lambda: HarnessRecipe.from_dict(
            {key: item for key, item in recipe.items() if key != "module_sha256"}),
        "wire_codec_with_an_extra_key": lambda: HarnessWireCodec.from_dict({**wire, "retry": 3}),
        "catalogue_of_a_newer_version": lambda: HarnessRecipeCatalog.from_dict(
            {**value, "record_type": "harness_recipe_catalog/v2"},
            module_directory=release.module_directory),
        "catalogue_with_an_unknown_section": lambda: HarnessRecipeCatalog.from_dict(
            {**value, "host_recipes": []}, module_directory=release.module_directory),
    }
    refused = {name: _refuses(case, HarnessRecipeError) for name, case in wrong_cases.items()}
    refused["catalogue_file_with_a_repeated_key"] = _repeated_key_refused(release)
    round_trip = HarnessRecipeCatalog.from_dict(
        json.loads(json.dumps(value)), module_directory=release.module_directory)
    check("every_recipe_record_refuses_unknown_keys_and_unsupported_versions",
          all(refused.values()) and round_trip.digest == release.digest,
          str({name: flag for name, flag in refused.items() if not flag}))
    import loop_engine.core.harness_recipes as recipes
    with patch.object(recipes, "_exact_keys", lambda value, keys, name: None):
        accepted = not _refuses(wrong_cases["recipe_with_an_extra_key"], HarnessRecipeError)
    check("removed_unknown_key_refusal_is_detected", accepted,
          "with the exact key rule removed the extra key must be accepted")


def _digest_checks(check):
    from .harness_recipes import (HarnessRecipeCatalog, HarnessRecipeError, module_file_sha256,
                                  release_recipe_catalog)
    release = release_recipe_catalog()
    problems = []
    named = [(item.style, item.module, item.module_sha256,
              (item.prepare_function, item.extract_function)) for item in release.recipes]
    named += [(item.wire_protocol, item.module, item.module_sha256,
               (item.decode_function, item.encode_function))
              for item in release.wire_codecs if item.module is not None]
    for owner, module, sha256, functions in named:
        path = Path(release.module_directory) / (module + ".py")
        if not path.is_file() or module_file_sha256(path) != sha256:
            problems.append(f"{owner}: {module} digest differs from the catalogue")
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        defined = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
        problems += [f"{owner}: {module}.{name} is not defined" for name in functions
                     if name not in defined]
    with tempfile.TemporaryDirectory(prefix="le-recipe-digest-") as temporary:
        copied = Path(temporary)
        for path in Path(release.module_directory).glob("harness_*recipe*.py"):
            (copied / path.name).write_bytes(path.read_bytes())
        edited = copied / (release.recipe("goose").module + ".py")
        edited.write_text(edited.read_text(encoding="utf-8") + "\n# edited after release\n",
                          encoding="utf-8")
        stale = HarnessRecipeCatalog.from_dict(release.to_dict(), module_directory=str(copied))
        edited_refused = _refuses(lambda: stale.mounted_modules(stale.recipe("goose")),
                                  HarnessRecipeError)
    renamed = _catalog_variant(
        lambda value: _recipe_value(value, "goose").update(extract_function="extract_nothing"))
    missing_function = _refuses(lambda: renamed.mounted_modules(renamed.recipe("goose")),
                                HarnessRecipeError)
    check("every_recipe_names_resolvable_functions_and_its_module_digest",
          not problems and edited_refused and missing_function,
          str(problems[:4]) + f" edited_refused={edited_refused} missing_function={missing_function}")


def _link_checks(check):
    """A recipe module reached through a link is refused: the digest binds the
    file the module folder holds, never whatever a link points at."""
    from .harness_recipes import HarnessRecipeCatalog, HarnessRecipeError, release_recipe_catalog
    release = release_recipe_catalog()
    module = release.recipe("goose").module + ".py"
    with tempfile.TemporaryDirectory(prefix="le-recipe-link-") as temporary:
        folder = Path(temporary)
        (folder / module).symlink_to(Path(release.module_directory) / module)
        linked = HarnessRecipeCatalog.from_dict(release.to_dict(), module_directory=str(folder))
        refused = _refuses(lambda: linked.mounted_modules(linked.recipe("goose")),
                           HarnessRecipeError)
    check("a_recipe_module_reached_through_a_link_is_refused", refused)


def _literal_checks(check):
    styles = set(HISTORICAL_TEXT_RESPONSE_STYLES)
    try:
        from .harness_recipes import release_recipe_catalog
        styles |= {item.style for item in release_recipe_catalog().recipes}
    except Exception:  # the scan must still run when the catalogue cannot load
        pass
    found = {name: style_literals_in_source((_HERE / name).read_text(encoding="utf-8"), styles)
             for name in DISPATCH_FILES}
    check("adding_a_process_harness_recipe_needs_no_core_dispatch_edit",
          not any(found.values()), str({name: hits[:6] for name, hits in found.items() if hits}))
    known_wrong = 'google = config["style"] == "gemini_cli"\n'
    check("a_style_literal_in_the_runner_is_detected",
          style_literals_in_source(known_wrong, styles) == [(1, "gemini_cli")])


def _unsupported_style_checks(check, root):
    from .harness_configuration import load_harness_binding
    from .harness_process import HarnessSetupUnavailable, HarnessProcessError
    reason = ""
    try:
        _spec("freebuff", root)
    except HarnessSetupUnavailable as exc:
        reason = exc.reason_code
    host_file = root / "freebuff-harness.json"
    host_file.write_text(json.dumps({
        "schema_version": 1, "harness_id": "freebuff", "package_version": "0.0.172",
        "style": "freebuff", "command_prefix": [sys.executable],
        "read_only_paths": [str(root / "software")]}))
    strict_refused = _refuses(lambda: load_harness_binding(
        str(host_file), work_root=str(root / "work"), socket_directory=str(root.parent)),
        HarnessProcessError)
    tolerant = load_harness_binding(str(host_file), work_root=str(root / "work"),
                                    socket_directory=str(root.parent), allow_unavailable=True)
    info = tolerant.registry.get("freebuff").info()
    check("unsupported_style_is_refused_with_its_named_reason",
          reason == "unsupported_style" and strict_refused and info.available is False
          and info.availability_reason == "unsupported_style",
          f"reason={reason!r} strict={strict_refused} tolerant={info.availability_reason!r}")
    import loop_engine.core.harness_recipes as recipes
    fixture = recipes.release_recipe_catalog()
    borrowed = fixture.recipe("aider")
    with patch.object(recipes.HarnessRecipeCatalog, "recipe", lambda self, style: borrowed):
        bound = not _refuses(lambda: _spec("freebuff", root), HarnessSetupUnavailable)
    check("removed_style_refusal_is_detected", bound,
          "a lookup that answers every style must let the freebuff file bind")
    served_elsewhere = _catalog_variant(
        lambda value: _recipe_value(value, "opencode").update(variant="agent_protocol"))
    other_reason = ""
    try:
        _spec("opencode", root, catalog=served_elsewhere)
    except HarnessSetupUnavailable as exc:
        other_reason = exc.reason_code
    check("a_record_served_by_another_engine_is_not_bound_by_the_text_relay_runner",
          other_reason == "unsupported_style", other_reason)


def _fixture_codec_catalog():
    """A recipe whose own module is Goose's and whose wire codec lives in
    another module, the case the release catalogue does not hold today."""
    def change(value):
        recipe = _recipe_value(value, "goose")
        recipe.update(style="fixture_cross_module_codec", wire_protocols=["anthropic_messages"])
        value["recipes"] = [recipe]
    return _catalog_variant(change)


def _mount_checks(check, root):
    from .harness_process import _identity_payload, sandbox_arguments
    from .harness_recipes import HarnessRecipeCatalog, release_recipe_catalog
    release = release_recipe_catalog()
    expected = {
        "codex": {"harness_responses_recipes"},
        "gemini_cli": {"harness_additional_recipes"},
        "nanocode": {"harness_lightweight_recipes"},
        "openinterpreter_rust": {"harness_responses_recipes"},
        "aider": {"harness_builtin_recipes"},
        "goose": {"harness_goose_recipe"},
    }
    cross = _fixture_codec_catalog()
    cross_expected = {"harness_goose_recipe", "harness_lightweight_recipes"}

    def observe(style, catalog=None):
        spec = _spec(style, root, catalog=catalog)
        mounted = _mounted_relay_modules(sandbox_arguments(_launch(spec, root)))
        request = _request(spec, root)
        digested = set(_identity_payload(request, root / "run", ())["recipe_module_digests"])
        return mounted, digested

    def all_hold():
        results = {style: observe(style) for style in expected}
        results["fixture_cross_module_codec"] = observe("fixture_cross_module_codec", cross)
        wanted = {**expected, "fixture_cross_module_codec": cross_expected}
        return all(results[name] == (wanted[name], wanted[name]) for name in wanted), results

    holds, results = all_hold()
    check("recipe_module_mount_and_digest_follow_the_selected_recipe_and_its_wire_codec",
          holds, str({name: sorted(value[0]) for name, value in results.items()}))

    def every_module(self, recipe):
        seen = {}
        for item in self.recipes:
            for module in original(self, item):
                seen[module.module] = module
        return tuple(seen[name] for name in sorted(seen))

    def own_module_only(self, recipe):
        return tuple(item for item in original(self, recipe) if item.module == recipe.module)

    original = HarnessRecipeCatalog.mounted_modules
    with patch.object(HarnessRecipeCatalog, "mounted_modules", every_module):
        everything_detected = not all_hold()[0]
    with patch.object(HarnessRecipeCatalog, "mounted_modules", own_module_only):
        codec_detected = not all_hold()[0]
    check("removed_selected_module_restriction_is_detected", everything_detected,
          "mounting every recipe module must fail the mount check")
    check("removed_codec_mount_is_detected", codec_detected,
          "dropping the codec module of a declared wire must fail the mount check")
    check("the_release_catalogue_mounts_no_module_it_does_not_name",
          all(module.module in {item.module for item in release.recipes}
              | {item.module for item in release.wire_codecs if item.module}
              for recipe in release.recipes for module in release.mounted_modules(recipe)))


def _binding_drift_checks(check, root):
    """A module edited after the spec was bound is refused before the process starts."""
    from .harness_process import HarnessProcessError
    from .harness_recipes import HarnessRecipeCatalog, release_recipe_catalog
    release = release_recipe_catalog()
    folder = root / "bound-modules"
    folder.mkdir()
    module = release.recipe("goose").module + ".py"
    source = Path(release.module_directory) / module
    (folder / module).write_bytes(source.read_bytes())
    catalog = HarnessRecipeCatalog.from_dict(release.to_dict(), module_directory=str(folder))
    spec = _spec("goose", root, catalog=catalog)
    unchanged = not _refuses(spec.validate_unchanged, HarnessProcessError)
    (folder / module).write_text(source.read_text(encoding="utf-8") + "\n# edited after binding\n",
                                 encoding="utf-8")
    check("a_recipe_module_changed_after_binding_is_refused_before_the_process_starts",
          unchanged and _refuses(spec.validate_unchanged, HarnessProcessError))


def _special_case_checks(check, root):
    from .harness_process import HarnessProcessError, sandbox_arguments
    pi = _spec("pi", root)
    pi_refused = _refuses(lambda: _request(pi, root, context_capacity=None), HarnessProcessError)
    relaxed = _catalog_variant(
        lambda value: _recipe_value(value, "pi").update(requires_context_capacity=False))
    relaxed_accepted = not _refuses(
        lambda: _request(_spec("pi", root, catalog=relaxed), root, context_capacity=None),
        HarnessProcessError)
    aider = _setenv(sandbox_arguments(_launch(_spec("aider", root), root, 2048)))
    codex = _setenv(sandbox_arguments(_launch(_spec("codex", root), root, 2048)))
    bare = _catalog_variant(lambda value: _recipe_value(value, "aider").update(sandbox_environment=[]))
    aider_without = _setenv(sandbox_arguments(_launch(_spec("aider", root, catalog=bare), root, 2048)))
    check("special_cases_come_from_the_record",
          pi_refused and aider.get("COLUMNS") == "2048" and "COLUMNS" not in codex
          and "COLUMNS" not in aider_without,
          f"pi_refused={pi_refused} aider={aider.get('COLUMNS')!r} codex={codex.get('COLUMNS')!r}")
    check("removed_context_capacity_rule_is_detected", relaxed_accepted,
          "a record that stops requiring the capacity must let Pi start without one")


def _wire_checks(check):
    from .harness_process_relay import _select_wire
    from .harness_recipes import release_recipe_catalog
    release = release_recipe_catalog()

    def wires(style):
        return [item.to_dict() for item in release.wires_for(release.recipe(style))]

    def chosen(style, path):
        selected = _select_wire(wires(style), path)
        return selected["wire_protocol"] if selected else None

    observed = {
        ("openinterpreter_rust", "/v1/responses"): chosen("openinterpreter_rust", "/v1/responses"),
        ("openinterpreter_rust", "/v1/chat/completions"): chosen("openinterpreter_rust", "/v1/chat/completions"),
        ("codex", "/v1/responses"): chosen("codex", "/v1/responses"),
        ("codex", "/v1/chat/completions"): chosen("codex", "/v1/chat/completions"),
        ("gemini_cli", "/v1beta/models/m:streamGenerateContent?alt=sse"):
            chosen("gemini_cli", "/v1beta/models/m:streamGenerateContent?alt=sse"),
        ("nanocode", "/v1/messages"): chosen("nanocode", "/v1/messages"),
        ("aider", "/chat/completions"): chosen("aider", "/chat/completions"),
        ("aider", "/v1/responses"): chosen("aider", "/v1/responses"),
    }
    wanted = {
        ("openinterpreter_rust", "/v1/responses"): "openai_responses",
        ("openinterpreter_rust", "/v1/chat/completions"): "openai_chat_completions",
        ("codex", "/v1/responses"): "openai_responses",
        ("codex", "/v1/chat/completions"): None,
        ("gemini_cli", "/v1beta/models/m:streamGenerateContent?alt=sse"): "google_generate_content",
        ("nanocode", "/v1/messages"): "anthropic_messages",
        ("aider", "/chat/completions"): "openai_chat_completions",
        ("aider", "/v1/responses"): None,
    }
    check("the_relay_chooses_the_wire_from_the_record", observed == wanted,
          str({key: value for key, value in observed.items() if wanted[key] != value}))
    # The relay runs standalone in the sandbox and cannot import the catalogue
    # reader, so it keeps its own copy of the framing names; the two must agree.
    from .harness_process_relay import _FRAMINGS
    from .harness_recipes import STREAM_FRAMINGS
    check("the_relay_frames_exactly_the_catalogue_stream_framings",
          tuple(_FRAMINGS) == tuple(STREAM_FRAMINGS),
          str(sorted(set(_FRAMINGS) ^ set(STREAM_FRAMINGS))))


def _declaration_checks(check):
    from .harness_recipes import HarnessRecipeError
    cases = {
        "an_undeclared_wire": lambda value: _recipe_value(value, "aider").update(
            wire_protocols=["openai_realtime"]),
        "overlapping_wire_paths": lambda value: value["wire_codecs"].append(
            {**value["wire_codecs"][0], "wire_protocol": "openai_chat_duplicate"})
            or _recipe_value(value, "aider").update(
                wire_protocols=["openai_chat_completions", "openai_chat_duplicate"]),
        "a_layout_variable_override": lambda value: _recipe_value(value, "aider").update(
            sandbox_environment=[{"variable": "HOME", "value_from": "maximum_output_bytes"}]),
        "an_unknown_environment_source": lambda value: _recipe_value(value, "aider").update(
            sandbox_environment=[{"variable": "COLUMNS", "value_from": "prompt"}]),
        "a_delegated_completion": lambda value: _recipe_value(value, "aider")["native_controls"][
            "ownership"].update(completion_and_output_publication="delegated_within_authority"),
        "a_missing_native_control": lambda value: _recipe_value(value, "aider")["native_controls"][
            "ownership"].pop("retry_and_fallback"),
        "an_unknown_instruction_style": lambda value: _recipe_value(value, "aider").update(
            instruction_style="claude_desktop"),
        "a_duplicate_style": lambda value: value["recipes"].append(dict(_recipe_value(value, "aider"))),
        "an_unknown_distribution_kind": lambda value: _recipe_value(value, "aider")[
            "distribution"].update(kind="curl_pipe_shell"),
        "a_module_outside_the_folder": lambda value: _recipe_value(value, "aider").update(
            module="../escape"),
    }
    refused = {name: _refuses(lambda change=change: _catalog_variant(change), HarnessRecipeError)
               for name, change in cases.items()}
    check("a_recipe_declares_only_catalogued_wires_known_controls_and_safe_environment",
          all(refused.values()), str([name for name, flag in refused.items() if not flag]))


def _host_file_checks(check, root):
    from .harness_configuration import load_harness_binding
    base = {"schema_version": 1, "harness_id": "aider", "package_version": "1.0.0",
            "style": "aider", "command_prefix": [sys.executable],
            "read_only_paths": [str(root / "software")]}
    refused = {}
    for key in ("recipe", "catalog", "module"):
        path = root / f"host-{key}.json"
        path.write_text(json.dumps({**base, key: "harness_goose_recipe"}))
        refused[key] = _refuses(lambda path=path: load_harness_binding(
            str(path), work_root=str(root / "work"), socket_directory=str(root.parent)), ValueError)
    check("a_host_file_cannot_name_a_recipe_module_or_a_catalogue", all(refused.values()),
          str(refused))


def _relay_integrity_checks(check):
    from .harness_process_relay import _load_mounted_module
    from .harness_recipes import release_recipe_catalog
    release = release_recipe_catalog()
    recipe = release.recipe("goose")
    loaded = _load_mounted_module(recipe.module, recipe.module_sha256, release.module_directory)
    refused = _refuses(lambda: _load_mounted_module(
        recipe.module, hashlib.sha256(b"another release").hexdigest(), release.module_directory),
        ValueError)
    check("the_relay_refuses_a_mounted_module_whose_digest_differs",
          callable(getattr(loaded, recipe.prepare_function, None)) and refused)


def _coverage_checks(check):
    from .harness_recipes import TEXT_RESPONSE_VARIANT, release_recipe_catalog
    release = release_recipe_catalog()
    styles = sorted(item.style for item in release.recipes if item.variant == TEXT_RESPONSE_VARIANT)
    check("the_catalogue_holds_one_text_response_record_for_each_of_the_eighteen_styles",
          styles == sorted(HISTORICAL_TEXT_RESPONSE_STYLES), str(styles))
    from .harness_process import _output
    response = {"choices": [{"message": {"role": "assistant", "content": "answer"}}]}
    check("extraction_is_chosen_by_the_record",
          _output("aider", "banner\nanswer\n", response) == "answer"
          and _output("goose", '{"type":"message","message":{"role":"assistant",'
                      '"content":[{"type":"text","text":"answer"}]}}\n{"type":"complete"}',
                      response) == "answer"
          and _output("freebuff", "answer", response) == "")


def self_test() -> dict:
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": str(detail)[:400]})

    def guarded(label, run, *arguments):
        try:
            run(check, *arguments)
        except Exception as exc:  # a missing catalogue fails its checks, never the suite
            check(label, False, f"{type(exc).__name__}: {exc}")

    guarded("recipe_reader_checks_ran", _reader_checks)
    guarded("recipe_digest_checks_ran", _digest_checks)
    guarded("recipe_link_checks_ran", _link_checks)
    guarded("style_literal_checks_ran", _literal_checks)
    guarded("wire_choice_checks_ran", _wire_checks)
    guarded("recipe_declaration_checks_ran", _declaration_checks)
    guarded("relay_integrity_checks_ran", _relay_integrity_checks)
    guarded("catalogue_coverage_checks_ran", _coverage_checks)
    with _fixture_root() as root:
        guarded("unsupported_style_checks_ran", _unsupported_style_checks, root)
        guarded("mount_checks_ran", _mount_checks, root)
        guarded("special_case_checks_ran", _special_case_checks, root)
        guarded("binding_drift_checks_ran", _binding_drift_checks, root)
        guarded("host_file_checks_ran", _host_file_checks, root)
    return {"record_type": "harness_recipe_catalog_checks/v1", "tests": tests,
            "passed": sum(item["passed"] for item in tests), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}
