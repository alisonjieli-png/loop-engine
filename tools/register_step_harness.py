#!/usr/bin/env python3
"""Register a harness by declaration: validate its manifest, qualify it on the fixture step, show it run.

A harness author writes one step_harness_manifest/v1 (see
docs/components/core-architecture/STEP-EXECUTION.md). This tool is the
repository's way to take that declaration through the path every custom
harness follows:

1. ``validate MANIFEST``: read the manifest with the package's strict reader
   and check its working-folder layout against the installer's
   native_client_layout_profile/v1 profile it names (the skill folder the
   manifest declares must be the profile's native skill location). Nothing
   starts.
2. ``qualify MANIFEST --executable PATH --software PATH``: pin the software,
   run the qualification fixture step in the sandbox (a fresh start with
   decoys above the step and in the real home folder, the step's markers in
   the harness's model requests, and the fixture broker's answer read back
   through the manifest's output rule), and write engine_qualification/v1
   with its run record into a new folder. No model is called.
3. ``demonstrate``: register, qualify and run the packaged fixture harness,
   the custom Loop harness process and the in-process Loop engine through the
   step executor slot with one caller, and Pi as well where Pi is installed
   at the manifest's pinned version, in no-model and fixture mode; write one
   step_harness_demonstration/v1 record.

    PYTHONPATH=src:tools python tools/register_step_harness.py validate path/to/manifest.json
    PYTHONPATH=src:tools python tools/register_step_harness.py demonstrate --output-root DIR
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys

TOOL = Path(__file__).resolve()
ROOT = TOOL.parents[1]
DEMONSTRATION_RECORD_TYPE = "step_harness_demonstration/v1"
LAYOUT_CHECK_RECORD_TYPE = "step_harness_layout_check/v1"


class RegistrationRefused(ValueError):
    """A manifest or an installation this tool refuses, with a stable code."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(code + (": " + detail if detail else ""))
        self.code = code


def read_manifest(path: Path, harness_id: str = ""):
    """A manifest from a JSON or YAML file, read by the package's strict reader.

    A file may hold one manifest, or a manifest catalogue from which --harness picks one."""
    from loop_engine.core.step_execution.harness_manifest import (
        MANIFEST_CATALOG_RECORD_TYPE, StepHarnessManifest, StepHarnessManifestCatalog)
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        import yaml
        value = yaml.safe_load(text)
    else:
        value = json.loads(text)
    if isinstance(value, dict) and value.get("record_type") == MANIFEST_CATALOG_RECORD_TYPE:
        if not harness_id:
            raise RegistrationRefused("harness_required", "a manifest catalogue needs --harness")
        return StepHarnessManifestCatalog.from_dict(value).manifest(harness_id)
    return StepHarnessManifest.from_dict(value)


def layout_check(manifest) -> dict:
    """The manifest's layout against the installer's native layout profile it names."""
    import install_selected_material as installer
    record = {"record_type": LAYOUT_CHECK_RECORD_TYPE, "manifest": manifest.engine_ref,
              "layout_profile": manifest.layout.layout_profile}
    if manifest.layout.layout_profile == "none":
        return {**record, "matches": manifest.layout.skills_directory is None,
                "reason": "no profile: the manifest must place no skill"}
    profile = installer.layout_profile_for(manifest.layout.layout_profile)
    try:
        location = profile.location_for(installer.SKILL_KIND)
        native = "/".join(location.directory_segments)
    except installer.InstallRefusal:
        native = None
    matches = manifest.layout.skills_directory == native
    return {**record, "profile_skill_location": native, "manifest_skills_directory": manifest.layout.skills_directory,
            "matches": matches, "reason": "" if matches else "the skill folder differs from the profile's"}


def require_layout(manifest) -> dict:
    check = layout_check(manifest)
    if not check["matches"]:
        raise RegistrationRefused("layout_differs_from_profile", check["reason"])
    return check


def installed_version(manifest, executable: str) -> "str | None":
    """The installed program's version, read with the manifest's own version command."""
    if manifest.launch.version_pattern is None:
        return None
    done = subprocess.run([executable, *manifest.launch.version_arguments], capture_output=True, text=True,
                          timeout=60, stdin=subprocess.DEVNULL, env={"PATH": "/usr/bin:/bin", "HOME": "/nonexistent"})
    for line in (done.stdout + done.stderr).splitlines():
        match = re.match(manifest.launch.version_pattern, line.strip())
        if match:
            return match.group(1)
    return None


def qualify(manifest, executable: str, software_paths, output: Path) -> dict:
    """Pin, qualify on the fixture step, and write the qualification and its run record."""
    from loop_engine.core.step_execution.declared_harness import DeclaredHarnessStepEngine
    from loop_engine.core.step_execution.harness_launch import HarnessSoftware
    from loop_engine.core.step_execution.launch_checks import installation_for
    from loop_engine.core.step_execution.qualification import qualify_engine
    layout = require_layout(manifest)
    version = installed_version(manifest, executable)
    if manifest.launch.pinned_version is not None and version != manifest.launch.pinned_version:
        raise RegistrationRefused("installed_version_differs_from_pin",
                                  f"installed {version}, pinned {manifest.launch.pinned_version}")
    engine = DeclaredHarnessStepEngine(manifest, HarnessSoftware(executable, tuple(software_paths)))
    installation = installation_for(engine)
    qualification, run = qualify_engine(engine, installation, work_root=output / "work")
    (output / "engine-qualification.json").write_text(json.dumps(qualification.to_dict(), indent=1),
                                                      encoding="utf-8")
    (output / "engine-installation.json").write_text(json.dumps(installation.to_dict(), indent=1),
                                                     encoding="utf-8")
    return {"layout": layout, "installed_version": version, "qualification": qualification.to_dict(),
            "run": run}


def _pi_software():
    from loop_engine.core.step_execution.harness_launch import HarnessSoftware
    found = shutil.which("pi")
    if not found:
        return None
    program = Path(found).resolve()
    for folder in program.parents:
        if folder.parent.name.startswith("@") and folder.parent.parent.name == "node_modules":
            return HarnessSoftware(str(program), (str(folder),))
    return None


def demonstrate(output: Path) -> dict:
    """The end-to-end path for the fixture harness, the Loop harness, the in-process engine and Pi."""
    from loop_engine.core.step_execution.harness_manifest import release_manifest_catalog
    from loop_engine.core.step_execution.launch_checks import run_sandbox_scenarios
    record = {"record_type": DEMONSTRATION_RECORD_TYPE, "started_at": _now(), "model_calls_to_a_real_model": 0,
              "layout_checks": [layout_check(item) for item in release_manifest_catalog().manifests]}
    record["sandbox_scenarios"] = run_sandbox_scenarios(output / "scenarios")
    pi = _pi_software()
    manifest = release_manifest_catalog().manifest("pi.print")
    if pi is None:
        record["pi"] = {"status": "not_tested", "missing_optional_dependencies": ["pi"]}
    else:
        try:
            record["pi"] = {"status": "qualified", **qualify(manifest, pi.executable, pi.software_paths,
                                                             output / "pi")}
        except RegistrationRefused as exc:
            record["pi"] = {"status": "refused", "code": exc.code, "detail": str(exc)}
    record["finished_at"] = _now()
    (output / "demonstration.json").write_text(json.dumps(record, indent=1, sort_keys=True, default=str),
                                               encoding="utf-8")
    return record


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_folder(root: Path, name: str) -> Path:
    folder = root / f"{name}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(3)}"
    folder.mkdir(parents=True)
    return folder


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    validate_parser = commands.add_parser("validate")
    validate_parser.add_argument("manifest", type=Path)
    validate_parser.add_argument("--harness", default="")
    qualify_parser = commands.add_parser("qualify")
    qualify_parser.add_argument("manifest", type=Path)
    qualify_parser.add_argument("--harness", default="")
    qualify_parser.add_argument("--executable", required=True)
    qualify_parser.add_argument("--software", action="append", default=[])
    qualify_parser.add_argument("--output-root", type=Path, default=ROOT / ".loop-engine-dev" / "step-harnesses")
    demo = commands.add_parser("demonstrate")
    demo.add_argument("--output-root", type=Path, default=ROOT / ".loop-engine-dev" / "step-harnesses")
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "validate":
            manifest = read_manifest(arguments.manifest, arguments.harness)
            print(json.dumps({"engine_ref": manifest.engine_ref, "manifest_digest": manifest.content_digest,
                              "executor_profile": manifest.executor_profile().to_dict(),
                              "layout": layout_check(manifest)}, indent=1))
            return 0 if layout_check(manifest)["matches"] else 1
        if arguments.command == "qualify":
            output = _new_folder(arguments.output_root, "qualify")
            report = qualify(read_manifest(arguments.manifest, arguments.harness),
                             str(Path(arguments.executable).resolve()),
                             tuple(arguments.software), output)
            print(json.dumps({"decision": report["qualification"]["decision"],
                              "rung": report["qualification"]["ladder_rung"], "folder": str(output)}, indent=1))
            return 0 if report["qualification"]["decision"] == "approved" else 1
        record = demonstrate(_new_folder(arguments.output_root, "demonstration"))
        failed = [item["name"] for item in record["sandbox_scenarios"] if item["passed"] is False]
        print(json.dumps({"failed": failed, "pi": record["pi"].get("status")}, indent=1))
        return 1 if failed else 0
    except (RegistrationRefused, ValueError) as exc:
        print(json.dumps({"refused": getattr(exc, "code", "manifest_refused"), "detail": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
