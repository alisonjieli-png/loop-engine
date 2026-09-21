"""Create, list, suspend and expire Baltor promotion codes.

A promotion code gives one account the paid service entitlement without a
payment. This command is the operator side of that path. It talks to the
service database that the host configuration names; it makes no network
request, it calls no payment provider and it creates no account.

Create generates the code itself and shows it once, on standard output. The
service stores only the digest of a code, so nothing here and nothing later can
print a code that this run did not just create. Do not pass a code in an
argument: an argument reaches the shell history and the process list.

Creating a code requires the explicit confirmation flag, the same way the other
operator commands in this folder require one before an effect.

Usage, with the host configuration that the service itself serves from:

    python3 tools/promotion_codes.py create --config /data/host.json \\
        --label "invited beta, October" --days 90 --redemptions 25 \\
        --window-days 30 --approved-by reviewer.name --approval-ref review:2026-09-21 \\
        --acknowledge-promotion-grant
    python3 tools/promotion_codes.py list --config /data/host.json
    python3 tools/promotion_codes.py suspend --config /data/host.json --code-id <identity>
    python3 tools/promotion_codes.py expire --config /data/host.json --code-id <identity>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loop_engine.core.service_runtime.http_entrypoint import load_host_application  # noqa: E402
from loop_engine.core.service_runtime.promotions import (  # noqa: E402
    PromotionCodeAdministration, PromotionCodeDefinition, PromotionGrant, PromotionPolicy,
)
from loop_engine.core.service_runtime.records import ServiceRuntimeError  # noqa: E402

#: Letters and digits that cannot be read as one another. I, O, 0 and 1 are out.
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
GROUPS, GROUP_LENGTH = 3, 4
DAY = 24 * 3600
SUMMARY_VERSION = "promotion_code_operation/v1"
EXIT_REFUSED = 2


def generated_code(prefix):
    """A readable code with about sixty bits of randomness behind its prefix.

    The prefix is a name for people to recognise. It decides nothing: every
    effect of a code comes from the separate fields of its stored record.
    """
    body = "-".join("".join(secrets.choice(ALPHABET) for _ in range(GROUP_LENGTH)) for _ in range(GROUPS))
    return prefix + "-" + body


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], allow_abbrev=False)
    parser.add_argument("operation", choices=("create", "list", "suspend", "expire"))
    parser.add_argument("--config", required=True,
                        help="absolute host configuration file that names the service database")
    parser.add_argument("--label", default="promotion code",
                        help="display name for the operator listing; it decides nothing")
    parser.add_argument("--days", type=int, default=30,
                        help="how many days of paid access one redemption grants")
    parser.add_argument("--redemptions", type=int, default=1,
                        help="how many redemptions this code allows in total")
    parser.add_argument("--window-days", type=int, default=30,
                        help="how many days the code can be redeemed for, from now")
    parser.add_argument("--starts-in-days", type=int, default=0,
                        help="how many days from now the code starts working")
    parser.add_argument("--repeat-allowed", action="store_true",
                        help="allow one account to redeem this code more than once")
    parser.add_argument("--prefix", default="BALTOR", help="two to twelve capital letters")
    parser.add_argument("--approved-by", default="", help="who approved this code")
    parser.add_argument("--approval-ref", default="", help="the approval record this code belongs to")
    parser.add_argument("--code-id", default="", help="the code identity that list shows")
    parser.add_argument("--acknowledge-promotion-grant", action="store_true",
                        help="confirm that a new code will grant paid access without a payment")
    return parser


def _require(condition, code):
    if not condition:
        raise ServiceRuntimeError(code)


def _surfaces(arguments):
    application, configuration = load_host_application(arguments.config)
    settings = configuration.get("promotions") or {}
    policy = PromotionPolicy(**settings) if settings else PromotionPolicy()
    return application.runtime, PromotionCodeAdministration(application.runtime, policy)


def create(runtime, administration, arguments):
    _require(arguments.acknowledge_promotion_grant is True,
             "explicit_confirmation_required_no_code_was_created")
    _require(arguments.prefix.isascii() and arguments.prefix.isalpha() and arguments.prefix.isupper()
             and 2 <= len(arguments.prefix) <= 12, "code_prefix_refused")
    _require(arguments.approved_by.strip() and arguments.approval_ref.strip(),
             "an_approver_and_an_approval_reference_are_required")
    _require(1 <= arguments.window_days <= 366 and 0 <= arguments.starts_in_days < arguments.window_days,
             "redemption_window_refused")
    now = int(runtime._now())
    definition = PromotionCodeDefinition(
        code=generated_code(arguments.prefix), label=arguments.label,
        grant=PromotionGrant(seconds=arguments.days * DAY),
        redemptions_allowed=arguments.redemptions,
        repeat_allowed_for_one_account=bool(arguments.repeat_allowed),
        starts_at=now + arguments.starts_in_days * DAY,
        expires_at=now + arguments.window_days * DAY,
        approved_by=arguments.approved_by, approval_ref=arguments.approval_ref)
    record = administration.create(definition, confirmed=True)
    # The code is shown once, here, and is never stored or printed again.
    sys.stdout.write(definition.code + "\n")
    sys.stdout.flush()
    return {**record, "code_displayed": True}


def run(arguments):
    runtime, administration = _surfaces(arguments)
    if arguments.operation == "create":
        return create(runtime, administration, arguments)
    if arguments.operation == "list":
        return administration.inspect()
    _require(bool(arguments.code_id), "a_code_identity_is_required")
    return (administration.suspend(arguments.code_id) if arguments.operation == "suspend"
            else administration.expire(arguments.code_id))


def main(argv=None):
    arguments = build_parser().parse_args(argv)
    try:
        result = run(arguments)
    except ServiceRuntimeError as error:
        sys.stderr.write(json.dumps({"record_type": SUMMARY_VERSION, "operation": arguments.operation,
                                     "refused": error.code}, sort_keys=True) + "\n")
        return EXIT_REFUSED
    sys.stderr.write(json.dumps({"record_type": SUMMARY_VERSION, "operation": arguments.operation,
                                 "result": result}, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
