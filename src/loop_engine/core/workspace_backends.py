"""Public workspace boundary and its focused backend implementations.

Every file or command action remains work performed by a Loop. A workspace
backend supplies the bounded service used by that Loop. Importing this module
starts no process, network call, container, or remote workspace.
"""
from __future__ import annotations

import json

from .workspace_contracts import (
    BackendAvailability,
    CommandRequest,
    CommandResult,
    FileOperation,
    FileRequest,
    FileResult,
    SnapshotRequest,
    WorkspaceBackend,
    WorkspaceRef,
    WorkspaceSnapshotRef,
    WorkspaceSpec,
)
from .workspace_local import RestrictedLocalWorkspace, _local_test_cases
from .workspace_optional import (
    DeclaredRemoteWorkspace,
    DockerWorkspace,
    DockerWorkspaceDeclaration,
    DockerResourceLimits,
    E2BWorkspaceDeclaration,
    ModalWorkspaceDeclaration,
    verify_live_docker_workspace,
    _optional_test_cases,
)
from .workspace_operations import (
    WorkspaceApprovalPlan, WorkspaceOperationError,
    WorkspaceOperationService)

__all__ = (
    "BackendAvailability",
    "CommandRequest",
    "CommandResult",
    "DeclaredRemoteWorkspace",
    "DockerWorkspace",
    "DockerWorkspaceDeclaration",
    "DockerResourceLimits",
    "E2BWorkspaceDeclaration",
    "FileOperation",
    "FileRequest",
    "FileResult",
    "ModalWorkspaceDeclaration",
    "RestrictedLocalWorkspace",
    "SnapshotRequest",
    "WorkspaceBackend",
    "WorkspaceApprovalPlan",
    "WorkspaceOperationError",
    "WorkspaceOperationService",
    "WorkspaceRef",
    "WorkspaceSnapshotRef",
    "WorkspaceSpec",
    "verify_live_docker_workspace",
)


def self_test() -> dict:
    """Exercise confinement and inert optional adapters offline."""
    results = [*_local_test_cases(), *_optional_test_cases()]
    passed = sum(1 for item in results if item["passed"])
    return {
        "suite": "workspace_backends",
        "total": len(results),
        "passed": passed,
        "all_passed": passed == len(results),
        "tests": results,
        "failed": [item for item in results if not item["passed"]],
        "results": results,
    }


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
