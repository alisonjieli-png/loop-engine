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

from .solution_export import (_FORBIDDEN_IMPORT, ContainerSpec, ExportedFile, SolutionExportError,
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
        verification = verify_export(str(target), run_arguments=())
        check("a_clean_export_verifies_in_an_isolated_interpreter",
              verification.passed and [item["check"] for item in verification.checks]
              == ["manifest_digests_match_files", "no_loop_engine_import_and_no_secret_shape",
                  "package_imports_in_isolation", "entry_point_runs_in_isolation",
                  "expected_artifacts_exist"],
              json.dumps(verification.checks))
        (target / "src/fixture_solution/__init__.py").write_text('"""tampered"""\n', "utf-8")
        tampered = verify_export(str(target))
        check("a_tampered_file_fails_the_manifest_check",
              not tampered.passed and tampered.checks[0]["check"] == "manifest_digests_match_files"
              and not tampered.checks[0]["passed"])
        (target / "src/fixture_solution/__init__.py").write_text(
            '"""fixture"""\nimport loop_engine\n', "utf-8")
        leaking = verify_export(str(target))
        check("an_export_that_imports_loop_engine_fails_verification",
              not leaking.passed and not leaking.checks[1]["passed"]
              and not leaking.checks[2]["passed"]
              and "No module named 'loop_engine'" in leaking.checks[2]["detail"],
              "the isolated interpreter cannot import loop_engine even when the package tries")

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
        export_solution(conformance, str(target))
        (target / "input.csv").write_text(
            'name\nACME CORPORATION\n"  mcdouglas & sons, inc.  "\nAA CAREERS\nABC Consulting Inc.\n', "utf-8")
        verification = verify_export(str(target), run_arguments=("--input", "input.csv", "--output-dir", "out"),
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
