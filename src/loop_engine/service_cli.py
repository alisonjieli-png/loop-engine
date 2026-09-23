"""Public command dispatch for the explicitly configured intelligence service.

This module keeps optional serving imports out of discovery and help. It never
prints configuration values in a failure or retries a possibly committed write.
The host entry point owns configuration, key issuance and serving operations.
"""
from __future__ import annotations

import json


def _service_main(arguments):
    from .core.service_runtime.http_entrypoint import main
    return main(arguments)


def service_command(arguments: list[str]) -> int:
    """Delegate exactly once and preserve an unknown effect outcome on failure."""
    from .core.service_runtime.records import ServiceRuntimeError
    try:
        result = _service_main(arguments)
        if type(result) is int and 0 <= result <= 255:
            return result
        code = "invalid_service_exit_status"
    except ModuleNotFoundError:
        code = "serving_dependency_unavailable"
    except ServiceRuntimeError as error:
        code = "commit_unknown" if error.code == "commit_unknown" else "service_operation_refused"
    except (OSError, ValueError, TypeError):
        code = "service_configuration_or_io_failure"
    except KeyboardInterrupt:
        code = "service_interrupted"
    except Exception:
        code = "service_operation_failed"
    print(json.dumps({"record_type": "service_cli_error/v1", "code": code,
        "effect_commitment": "not_asserted", "automatic_retry": False,
        **({"install_extra": "loop-engine[serving]"}
           if code == "serving_dependency_unavailable" else {})}, sort_keys=True))
    return 130 if code == "service_interrupted" else 1


def self_test() -> dict:
    """Check real root dispatch and failure reporting without starting a server."""
    from contextlib import redirect_stdout
    from io import StringIO
    from unittest.mock import patch
    from .__main__ import main
    from .cli_help import ROOT_HELP
    from .core.service_runtime.records import ServiceCommitUnknown, ServiceRuntimeError

    tests = []
    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed)})

    with patch(__name__ + "._service_main", return_value=7) as entry:
        code = main(["service", "serve", "--config", "/configuration/host.json"])
        check("service_command_dispatches_once_with_exact_arguments_and_exit_status",
              code == 7 and entry.call_count == 1
              and entry.call_args.args == (["serve", "--config", "/configuration/host.json"],))
    output = StringIO()
    with patch(__name__ + "._service_main") as entry, redirect_stdout(output):
        code = main(["service", "--help"])
    check("service_help_is_effect_free_and_lists_explicit_host_commands",
          code == 0 and not entry.called and "{configure|apply-grants|issue-key|serve|failures|publish-catalogue|rollback-catalogue|withdraw-catalogue-item|catalogue-status|follow-catalogue-release}" in output.getvalue()
          and "service smoke" in output.getvalue() and "service" in ROOT_HELP)

    cases = (
        (ModuleNotFoundError("private-fixture-detail"), "serving_dependency_unavailable", 1),
        (ServiceCommitUnknown(), "commit_unknown", 1),
        (ServiceRuntimeError("private-fixture-detail"), "service_operation_refused", 1),
        (ValueError("private-fixture-detail"), "service_configuration_or_io_failure", 1),
        (OSError("private-fixture-detail"), "service_configuration_or_io_failure", 1),
        (KeyboardInterrupt(), "service_interrupted", 130),
        (RuntimeError("private-fixture-detail"), "service_operation_failed", 1),
    )
    for index, (failure, expected, exit_status) in enumerate(cases):
        output = StringIO()
        with patch(__name__ + "._service_main", side_effect=failure) as entry, redirect_stdout(output):
            actual = service_command(["configure", "--config", "/configuration/host.json"])
        report = json.loads(output.getvalue())
        check(f"service_refusal_{index}_is_safe_once_only_and_never_asserts_a_commit",
              actual == exit_status and entry.call_count == 1 and report["code"] == expected
              and report["effect_commitment"] == "not_asserted" and report["automatic_retry"] is False
              and "private-fixture-detail" not in output.getvalue())
    for value in (True, None, -1, 256):
        output = StringIO()
        with patch(__name__ + "._service_main", return_value=value), redirect_stdout(output):
            code = service_command(["smoke"])
        check(f"service_invalid_exit_status_{value!r}_is_not_success",
              code == 1 and json.loads(output.getvalue())["code"] == "invalid_service_exit_status")
    return {"record_type": "service_cli_test/v1", "tests": tests,
            "passed": sum(row["passed"] for row in tests), "total": len(tests),
            "all_passed": all(row["passed"] for row in tests)}
