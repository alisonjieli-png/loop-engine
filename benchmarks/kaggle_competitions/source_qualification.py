"""Public facade for private, evidence-bound Kaggle source qualification.

The layer verifies an exact metadata preflight and retrieves source pages. It
does not download competition data, call a model, or submit an artifact.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from source_qualification_records import (
    DOWNLOAD_PLAN_TYPE,
    EVALUATOR_CANDIDATE_TYPE,
    PREFLIGHT_POPULATION_TYPE,
    PREFLIGHT_REPORT_TYPE,
    QUALIFICATION_CAMPAIGN_TYPE,
    QUALIFICATION_RECORD_TYPE,
    QUALIFICATION_STATES,
    HumanLegalReview,
    IndependentEvaluatorReview,
    KaggleDownloadAuthority,
    PageCommandResult,
    QualificationByteBudget,
    QualificationPathBudget,
    QualificationPrivacyPolicy,
    QualificationRunResult,
    SourceQualificationAuthority,
    SourceQualificationError,
    SourceQualificationRequest,
)
from source_qualification_runtime import run_source_qualification_as_loop


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Qualify exact Kaggle source pages without downloading data, "
            "calling a model, or submitting"
        )
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--preflight-report", required=True)
    parser.add_argument("--expected-preflight-report-digest", required=True)
    parser.add_argument("--expected-population-digest", required=True)
    parser.add_argument("--competition", action="append", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--private-artifact-root", required=True)
    parser.add_argument("--runs-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--maximum-preflight-bytes", type=int, default=24 * 1024 * 1024)
    parser.add_argument("--maximum-response-bytes", type=int, default=8 * 1024 * 1024)
    parser.add_argument("--maximum-page-body-bytes", type=int, default=4 * 1024 * 1024)
    parser.add_argument(
        "--maximum-total-private-bytes", type=int, default=32 * 1024 * 1024
    )
    parser.add_argument("--maximum-pages-per-competition", type=int, default=16)
    parser.add_argument("--maximum-path-characters", type=int, default=512)
    parser.add_argument("--authorize-preflight-read", action="store_true")
    parser.add_argument("--authorize-network-page-reads", action="store_true")
    parser.add_argument("--authorize-kaggle-cli-command-execution", action="store_true")
    parser.add_argument("--authorize-kaggle-credential-access", action="store_true")
    parser.add_argument("--authorize-private-artifact-writes", action="store_true")
    parser.add_argument("--authorize-run-history-write", action="store_true")
    parser.add_argument("--authorize-output-record-write", action="store_true")
    parser.add_argument("--authorized-by", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    slugs = tuple(args.competition)
    paths = QualificationPathBudget(
        workspace_root=args.workspace_root,
        preflight_report_path=args.preflight_report,
        private_artifact_root=args.private_artifact_root,
        run_history_root=args.runs_dir,
        output_record_path=args.output,
        maximum_path_characters=args.maximum_path_characters,
    )
    authority = SourceQualificationAuthority(
        authorized_by=args.authorized_by,
        preflight_read_path=args.preflight_report,
        page_read_slugs=slugs,
        private_artifact_write_root=args.private_artifact_root,
        run_history_write_root=args.runs_dir,
        output_record_write_path=args.output,
        allow_preflight_read=args.authorize_preflight_read,
        allow_network_page_reads=args.authorize_network_page_reads,
        allow_kaggle_cli_command_execution=(
            args.authorize_kaggle_cli_command_execution
        ),
        allow_kaggle_credential_access=args.authorize_kaggle_credential_access,
        allow_private_artifact_writes=args.authorize_private_artifact_writes,
        allow_run_history_write=args.authorize_run_history_write,
        allow_output_record_write=args.authorize_output_record_write,
    )
    request = SourceQualificationRequest(
        run_id=args.run_id,
        expected_preflight_report_digest=args.expected_preflight_report_digest,
        expected_population_digest=args.expected_population_digest,
        competition_slugs=slugs,
        as_of=args.as_of,
        paths=paths,
        bytes=QualificationByteBudget(
            maximum_preflight_bytes=args.maximum_preflight_bytes,
            maximum_response_bytes=args.maximum_response_bytes,
            maximum_page_body_bytes=args.maximum_page_body_bytes,
            maximum_total_private_bytes=args.maximum_total_private_bytes,
            maximum_pages_per_competition=args.maximum_pages_per_competition,
        ),
        privacy=QualificationPrivacyPolicy(),
        authority=authority,
        timeout_seconds=args.timeout_seconds,
    )
    result = run_source_qualification_as_loop(request)
    print(
        json.dumps(
            {
                "record_type": "kaggle_source_qualification_summary/v1",
                "run_id": request.run_id,
                "record_digest": result.record["record_digest"],
                "state_counts": result.record["summary"]["state_counts"],
                "physical_page_reads": result.record["summary"]["physical_page_reads"],
                "model_calls": 0,
                "downloads": 0,
                "submissions": 0,
                "run_history_head_digest": result.run_history_head_digest,
                "run_history_chain": result.run_history_chain,
                "output": str(Path(args.output).expanduser().resolve()),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


__all__ = [
    "DOWNLOAD_PLAN_TYPE",
    "EVALUATOR_CANDIDATE_TYPE",
    "PREFLIGHT_POPULATION_TYPE",
    "PREFLIGHT_REPORT_TYPE",
    "QUALIFICATION_CAMPAIGN_TYPE",
    "QUALIFICATION_RECORD_TYPE",
    "QUALIFICATION_STATES",
    "HumanLegalReview",
    "IndependentEvaluatorReview",
    "KaggleDownloadAuthority",
    "PageCommandResult",
    "QualificationByteBudget",
    "QualificationPathBudget",
    "QualificationPrivacyPolicy",
    "QualificationRunResult",
    "SourceQualificationAuthority",
    "SourceQualificationError",
    "SourceQualificationRequest",
    "run_source_qualification_as_loop",
]


if __name__ == "__main__":
    raise SystemExit(main())
