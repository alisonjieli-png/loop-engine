"""Declared HTTP header profiles for the existing research executors.

These are passive configuration, not new engines. They reuse the web-read
profile contract. A profile changes request identity, never the executor's
quota or hold identity. There is no retry, rotation or fallback here.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from loop_engine.core.web_fetch import WebHttpClientProfile

CONFIGURATION = "research_query_http_profiles/v1"
OBSERVATION = "research_query_http_client_observation/v1"
ENVIRONMENT = "QUERY_MULTIPLIER_HTTP_PROFILES"
HTTP_ACCESS = ("https_get", "https_post_key", "https_get_key")
USER_AGENT = "loop-engine query-multiplier/1.0 (read-only research probes; https://github.com/alisonjieli-png/loop-engine)"
DEFAULT_PROFILE = WebHttpClientProfile("baltor-query-multiplier", "1.0.0", USER_AGENT)
MAXIMUM_CONFIGURATION_BYTES = 64 * 1024
_TRUSTED_BOT_CLAIM = re.compile(r"(?i)\b(?:googlebot|bingbot|gptbot|chatgpt-user|cloudflarebrowserrenderingcrawler)\b")


def validate_profile(profile):
    """Keep profiles public, canonical and transparently attributed to Baltor."""
    if not isinstance(profile, WebHttpClientProfile):
        raise ValueError("query_http_profile_not_typed")
    # The shared reader validates version, digest, ASCII, bounds and common
    # credential markers. Leading/trailing whitespace is not a new identity.
    WebHttpClientProfile.from_record(profile.to_record())
    if any(value != value.strip() for value in (profile.user_agent, profile.accept_language)):
        raise ValueError("query_http_profile_whitespace")
    if not any(name in profile.user_agent.lower() for name in ("baltor", "loop-engine")):
        raise ValueError("query_http_profile_requires_baltor_attribution")
    if _TRUSTED_BOT_CLAIM.search(profile.user_agent):
        raise ValueError("query_http_profile_trusted_bot_claim_refused")
    return profile


def selected_profile(executor):
    profile = getattr(executor, "http_client_profile", None)
    if profile is not None:
        if executor.access not in HTTP_ACCESS:
            raise ValueError("query_http_profile_access_unsupported")
        return validate_profile(profile)
    return DEFAULT_PROFILE if executor.access in HTTP_ACCESS else None


def request_profile_matches(executor, request):
    """A saved query may run only under the exact explicit profile it names."""
    profile = getattr(executor, "http_client_profile", None)
    expected = profile.to_record() if profile is not None else None
    return request.get("http_client_profile") == expected


def configure_executors(value, executors):
    """Validate the entire file before changing any fresh registry instance."""
    if (type(value) is not dict or set(value) != {"record_type", "bindings"}
            or value.get("record_type") != CONFIGURATION or type(value["bindings"]) is not dict):
        raise ValueError("query_http_profiles_record_invalid")
    bindings = value["bindings"]
    if len(bindings) > len(executors):
        raise ValueError("query_http_profiles_bound")
    prepared = {}
    for name, record in bindings.items():
        executor = executors.get(name)
        if executor is None:
            raise ValueError("query_http_profile_executor_unknown")
        if not executor.available or executor.access not in HTTP_ACCESS:
            raise ValueError("query_http_profile_access_unsupported")
        prepared[name] = validate_profile(WebHttpClientProfile.from_record(record))
    for name, profile in prepared.items():
        executors[name].http_client_profile = profile


def _unique_object(pairs):
    value = {}
    for name, item in pairs:
        if name in value:
            raise ValueError("query_http_profiles_duplicate_field")
        value[name] = item
    return value


def load_configuration(explicit_path=None, *, environment=None):
    """An explicit CLI path wins over the optional environment path; neither is a key."""
    environment = os.environ if environment is None else environment
    path = explicit_path if explicit_path is not None else environment.get(ENVIRONMENT)
    if path is None:
        return None
    if not isinstance(path, (str, Path)) or not str(path).strip() or str(path) != str(path).strip():
        raise ValueError("query_http_profiles_path_invalid")
    with Path(path).open("rb") as source:
        raw = source.read(MAXIMUM_CONFIGURATION_BYTES + 1)
    if len(raw) > MAXIMUM_CONFIGURATION_BYTES:
        raise ValueError("query_http_profiles_file_too_large")
    try:
        return json.loads(raw, object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        # Never echo a line containing a mistakenly pasted credential.
        raise ValueError("query_http_profiles_json_invalid") from error


def observation(profile):
    profile = validate_profile(profile)
    return {"record_type": OBSERVATION, "profile": profile.to_record(),
            "client_realization": "http_headers_only"}


def validate_observation(value, request):
    if value is None:
        if request.get("http_client_profile") is not None:
            raise ValueError("query_http_profile_observation_missing")
        return None
    if (type(value) is not dict or set(value) != {"record_type", "profile", "client_realization"}
            or value.get("record_type") != OBSERVATION or value.get("client_realization") != "http_headers_only"):
        raise ValueError("query_http_profile_observation_invalid")
    profile = validate_profile(WebHttpClientProfile.from_record(value["profile"]))
    if profile.to_record() != request.get("http_client_profile", DEFAULT_PROFILE.to_record()):
        raise ValueError("query_http_profile_observation_mismatch")
    return observation(profile)
