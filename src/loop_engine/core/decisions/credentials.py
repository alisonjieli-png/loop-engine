"""Resolve an explicit process-local secret reference at provider use only.

Discovery and configuration construction never read the environment. This is
not a credential broker or isolation from another process under the same user.
"""
from __future__ import annotations

import os
import re
from .contracts import DecisionProtocolError

ENVIRONMENT_REFERENCE_PREFIX = "env:"


def validate_reference(reference):
    if not isinstance(reference, str) or not re.fullmatch(r"env:[A-Z_][A-Z0-9_]*", reference):
        raise DecisionProtocolError("environment_secret_reference_required")


def environment_credential(reference):
    validate_reference(reference)
    value = os.environ.get(reference[len(ENVIRONMENT_REFERENCE_PREFIX):])
    if not value:
        raise DecisionProtocolError("configured_secret_unavailable")
    return value
