"""Offline checks for the standalone solution export.

The checks cover file and specification refusals, the rendered project,
container, and Job files, the written manifest, the refusal of a non-empty
target, verification in an isolated interpreter including tampering and a
leaked import, and the exported text conformance solution running its own
tests and conforming a file with loop_engine absent.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .solution_export import (_FORBIDDEN_IMPORT, ContainerSpec, ExportedFile, ExportVerificationPolicy, SolutionExportError,
                              SolutionExportSpec, export_solution, render_dockerfile,
                              render_kubernetes_job, render_pyproject,
                              text_conformance_export_spec, verify_export)


def _refuses(action) -> bool:
    try:
        action()
    except SolutionExportError:
        return True
    return False


def run_checks() -> dict:
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    init = ExportedFile("__init__.py", '"""fixture"""\n')
    main = ExportedFile("__main__.py", "def main():\n    print('ran')\n    return 0\n\n"
                                       "if __name__ == '__main__':\n    raise SystemExit(main())\n")
    check("exported_files_refuse_traversal_absolute_paths_loop_engine_imports_and_secret_shapes",
          _refuses(lambda: ExportedFile("../x.py", "x"))
          and _refuses(lambda: ExportedFile("/etc/x.py", "x"))
          and _refuses(lambda: ExportedFile("x.py", "from loop_engine.core import x\n"))
          and _refuses(lambda: ExportedFile("x.py", "import loop_engine\n"))
          and _refuses(lambda: ExportedFile("x.py", "token = '" + "sk-" + "a" * 26 + "'\n"))
          and ExportedFile("pkg/x.py", "import json\n").path == "pkg/x.py")
    check("the_specification_refuses_bad_names_versions_missing_init_and_dependency_conflicts",
          _refuses(lambda: SolutionExportSpec("Bad-Name", "1.0.0", "s", (init,)))
          and _refuses(lambda: SolutionExportSpec("pkg", "1.0", "s", (init,)))
          and _refuses(lambda: SolutionExportSpec("pkg", "1.0.0", "", (init,)))
          and _refuses(lambda: SolutionExportSpec("pkg", "1.0.0", "s", (main,)))
          and _refuses(lambda: SolutionExportSpec("pkg", "1.0.0", "s", (init,), console_script="pkg"))
          and _refuses(lambda: SolutionExportSpec("pkg", "1.0.0", "s", (init,), dependencies=("requests",)))
          and _refuses(lambda: SolutionExportSpec("pkg", "1.0.0", "s", (init,), isolation="anywhere"))
          and _refuses(lambda: ContainerSpec(image_digest="sha256:short"))
          and SolutionExportSpec("pkg", "1.0.0", "s", (init,), dependencies=("requests",),
                                 isolation="site_packages").dependencies == ("requests",))
    spec = SolutionExportSpec("fixture_solution", "0.1.0", "A fixture solution.", (init, main),
                              console_script="fixture-solution",
                              container=ContainerSpec(arguments=("--input", "/work/in.csv")))
    pyproject = render_pyproject(spec)
    dockerfile = render_dockerfile(spec)
    job = render_kubernetes_job(spec)
    check("rendered_pyproject_dockerfile_and_job_carry_the_declared_identity",
          'name = "fixture-solution"' in pyproject and 'fixture-solution = "fixture_solution.__main__:main"' in pyproject
          and "FROM python:3.12-slim\n" in dockerfile and "not digest-pinned" in dockerfile
          and 'ENTRYPOINT ["fixture-solution"]' in dockerfile
          and "kind: Job" in job and "name: fixture-solution" in job and '"/work/in.csv"' in job
          and "backoffLimit: 0" in job)
    pinned = ContainerSpec(image_digest="sha256:" + "0" * 64)
    check("a_pinned_image_digest_reaches_the_dockerfile",
          "@sha256:" + "0" * 64 in render_dockerfile(
              SolutionExportSpec("pkg", "1.0.0", "s", (init,), container=pinned))
          and pinned.pinned and not spec.container.pinned)
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / "export"
        record = export_solution(spec, str(target))
        manifest = json.loads((target / "MANIFEST.json").read_text("utf-8"))
        check("export_writes_the_package_manifest_container_and_job_files",
              record.file_count == 7 and record.manifest_digest == manifest["manifest_digest"]
              and (target / "src/fixture_solution/__init__.py").is_file()
              and (target / "k8s/job.yaml").is_file() and (target / "Dockerfile").is_file()
              and set(manifest["files"]) == {"src/fixture_solution/__init__.py",
                                             "src/fixture_solution/__main__.py", "pyproject.toml",
                                             "README.md", "Dockerfile", "k8s/job.yaml", ".dockerignore"}
              and manifest["spec_digest"] == spec.digest)
        check("export_refuses_a_non_empty_target",
              _refuses(lambda: export_solution(spec, str(target))))
        policy = ExportVerificationPolicy(True, record.manifest_digest)
        verification = verify_export(str(target), run_arguments=(), policy=policy)
        check("a_clean_export_verifies_in_an_isolated_interpreter",
              verification.passed and [item["check"] for item in verification.checks]
              == ["manifest_identity_is_verified", "manifest_digests_match_files", "no_loop_engine_import_and_no_secret_shape",
                  "executable_sources_are_declared", "exact_local_execution_authority",
                  "package_imports_in_isolation", "entry_point_runs_in_isolation",
                  "expected_artifacts_exist"],
              json.dumps(verification.checks))
        (target / "src/fixture_solution/__init__.py").write_text('"""tampered"""\n', "utf-8")
        tampered = verify_export(str(target))
        check("a_tampered_file_fails_the_manifest_check",
              not tampered.passed
              and not next(item for item in tampered.checks if item["check"] == "manifest_digests_match_files")["passed"])
        (target / "src/fixture_solution/__init__.py").write_text(
            '"""fixture"""\nimport loop_engine\n', "utf-8")
        from unittest.mock import patch
        with patch("loop_engine.code_nodes.solution_export._run_isolated") as execute:
            leaking = verify_export(str(target), policy=policy)
            invoked = execute.called
        check("an_export_that_imports_loop_engine_fails_verification",
              not leaking.passed and not invoked,
              "integrity failure prevents execution rather than relying on the import to fail")
        # The tampered file above stops at its digest, so it no longer reaches
        # the content scan or the interpreter. Exercise both directly. Here the
        # manifest is re-issued for the offending file, so integrity passes and
        # only the content scan can refuse it.
        from .solution_export import ISOLATION_MODES, _digest, _digest_bytes, _run_isolated
        relative = "src/fixture_solution/__init__.py"
        reissued = json.loads((target / "MANIFEST.json").read_text("utf-8"))
        reissued["files"][relative] = _digest_bytes((target / relative).read_bytes())
        reissued["manifest_digest"] = _digest({key: value for key, value in reissued.items() if key != "manifest_digest"})
        (target / "MANIFEST.json").write_text(json.dumps(reissued), "utf-8")
        with patch("loop_engine.code_nodes.solution_export._run_isolated") as execute:
            scanned = verify_export(str(target), policy=ExportVerificationPolicy(True, reissued["manifest_digest"]))
            outcome = {item["check"]: item["passed"] for item in scanned.checks}
            check("a_consistent_manifest_cannot_hide_an_engine_import_from_the_content_scan",
                  not scanned.passed and outcome.get("manifest_digests_match_files") is True
                  and outcome.get("no_loop_engine_import_and_no_secret_shape") is False and not execute.called,
                  json.dumps(scanned.checks, default=str))
        # The strict interpreter must not see the engine even though the
        # interpreter running these checks can import it. The mode that admits
        # installed packages makes no such promise: there the content scan
        # above is the guard, so only the strict mode is asserted here.
        import loop_engine  # noqa: F401  (proves the host interpreter has it)
        probe = _run_isolated(target, ISOLATION_MODES[0], "import loop_engine", 60.0)
        check("strict_isolated_interpreter_cannot_import_the_engine",
              probe.returncode != 0 and "No module named 'loop_engine'" in probe.stderr, probe.stderr[-300:])
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / "export"
        record = export_solution(spec, str(target))
        with patch("loop_engine.code_nodes.solution_export._run_isolated") as execute:
            unapproved = verify_export(str(target))
            check("static_verification_does_not_authorize_host_execution",
                  not unapproved.passed and not execute.called)
            wrong_policy = ExportVerificationPolicy(True, "0" * 64)
            wrong = verify_export(str(target), policy=wrong_policy)
            check("local_verification_authority_is_bound_to_the_exact_manifest",
                  not wrong.passed and not execute.called)
            manifest = json.loads((target / "MANIFEST.json").read_text("utf-8"))
            manifest["package_name"] = "bad;raise RuntimeError"
            (target / "MANIFEST.json").write_text(json.dumps(manifest), "utf-8")
            check("a_manifest_cannot_inject_an_import_or_name_an_unknown_isolation",
                  _refuses(lambda: verify_export(str(target))) and not execute.called)
            manifest["package_name"] = spec.package_name
            manifest["isolation"] = "unrecognized"
            (target / "MANIFEST.json").write_text(json.dumps(manifest), "utf-8")
            check("an_unknown_interpreter_isolation_is_refused_before_execution",
                  _refuses(lambda: verify_export(str(target))) and not execute.called)
    from dataclasses import replace
    check("the_export_specification_identity_covers_execution_and_resource_settings",
          spec.digest != replace(spec, container=replace(spec.container, cpu="2")).digest
          and spec.digest != replace(spec, container=replace(spec.container, arguments=("different",))).digest
          and spec.digest != replace(spec, python_requires=">=3.11").digest)
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / "export"
        record = export_solution(spec, str(target))
        policy = ExportVerificationPolicy(True, record.manifest_digest)
        outside = Path(folder) / "outside.py"
        outside.write_text("raise RuntimeError('must not execute')\n", "utf-8")
        package_init = target / "src/fixture_solution/__init__.py"
        package_init.unlink()
        package_init.symlink_to(outside)
        with patch("loop_engine.code_nodes.solution_export._run_isolated") as execute:
            check("export_verification_refuses_symbolic_links_before_reading_or_execution",
                  _refuses(lambda: verify_export(str(target), policy=policy))
                  and not execute.called)
            package_init.unlink()
            package_init.write_text(init.content, "utf-8")
            (target / "src/undeclared.py").write_text("raise RuntimeError('undeclared')\n", "utf-8")
            extra = verify_export(str(target), policy=policy)
            check("undeclared_executable_source_cannot_enter_verification",
                  not extra.passed and not execute.called
                  and not next(row for row in extra.checks
                               if row["check"] == "executable_sources_are_declared")["passed"])
            check("expected_artifacts_cannot_escape_the_export_directory",
                  _refuses(lambda: verify_export(str(target), policy=policy,
                                                  expected_artifacts=("../outside.py",)))
                  and not execute.called)
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / "export"
        record = export_solution(spec, str(target))
        outside_tests = Path(folder) / "outside_tests"
        outside_tests.mkdir()
        (outside_tests / "test_outside.py").write_text("raise RuntimeError('outside')\n", "utf-8")
        (target / "tests").symlink_to(outside_tests, target_is_directory=True)
        with patch("loop_engine.code_nodes.solution_export._run_isolated") as execute:
            check("unlisted_test_directory_symlinks_cannot_enter_unittest_discovery",
                  _refuses(lambda: verify_export(str(target), policy=ExportVerificationPolicy(
                      True, record.manifest_digest))) and not execute.called)
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / "export"
        record = export_solution(spec, str(target))
        manifest_path = target / "MANIFEST.json"
        manifest = json.loads(manifest_path.read_text("utf-8"))
        manifest["summary"] = "changed manifest"
        manifest_path.write_text(json.dumps(manifest), "utf-8")
        from .solution_export import _digest
        actual = _digest({key: value for key, value in manifest.items() if key != "manifest_digest"})
        with patch("loop_engine.code_nodes.solution_export._run_isolated") as execute:
            changed = verify_export(str(target), policy=ExportVerificationPolicy(True, actual))
            check("the_manifest_digest_is_verified_before_any_execution",
                  not changed.passed and not execute.called
                  and not changed.checks[0]["passed"])

    from .text_conformance import ConformancePolicy, ConformanceRule, load_packaged_catalogs, merge_layers
    rules = (ConformanceRule("whitespace", "whitespace_normalize", ("name",)),
             ConformanceRule("case", "case_normalize", ("name",)),
             ConformanceRule("suffix", "suffix_canonicalize", ("name",)))
    catalogs = merge_layers([load_packaged_catalogs()])
    conformance = text_conformance_export_spec(rules, ConformancePolicy(), catalogs,
                                               package_name="company_conformance",
                                               solution_ref="fixture.solution")
    check("the_conformance_export_ships_the_operations_module_verbatim_without_loop_engine",
          {item.path for item in conformance.files}
          == {"__init__.py", "operations.py", "solution.py", "__main__.py", "rules.json", "catalogs.json"}
          and not _FORBIDDEN_IMPORT.search(next(item.content for item in conformance.files
                                                if item.path == "operations.py"))
          and conformance.isolation == "stdlib_only" and conformance.console_script == "company-conformance")
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / "conformance"
        record = export_solution(conformance, str(target))
        (target / "input.csv").write_text(
            'name\nACME CORPORATION\n"  mcdouglas & sons, inc.  "\nAA CAREERS\nABC Consulting Inc.\n', "utf-8")
        verification = verify_export(str(target), run_arguments=("--input", "input.csv", "--output-dir", "out"),
                                     policy=ExportVerificationPolicy(True, record.manifest_digest),
                                     expected_artifacts=("out/conformed.csv", "out/corrections.jsonl",
                                                         "out/escalations.jsonl", "out/report.json"))
        conformed = (target / "out/conformed.csv").read_text("utf-8").splitlines() if verification.passed else []
        report = json.loads((target / "out/report.json").read_text("utf-8")) if verification.passed else {}
        check("the_exported_conformance_solution_runs_its_tests_and_conforms_a_file_without_loop_engine",
              verification.passed and conformed[1:] == ["Acme Corp", "McDouglas & Sons Inc", "AA CAREERS",
                                                         "ABC Consulting Inc"]
              and report.get("overall", {}).get("held") == 1 and report.get("rows") == 4,
              json.dumps(verification.checks)[:1500])
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "solution_export_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
