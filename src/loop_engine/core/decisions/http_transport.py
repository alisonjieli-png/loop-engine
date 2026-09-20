"""One bounded, fixed-binding HTTP attempt for a configured decision provider.

No redirect, environment proxy, retry or provider selection occurs here.
Transport limits are not model capacities. The operator supplies an existing
endpoint; no model server is launched or privately extended by this client.
"""
from __future__ import annotations

import time
from .contracts import DecisionProtocolError, strict_json


def send_http(payload, secret, timeout, response_limit, *, endpoint):
    import httpx
    deadline = time.monotonic() + timeout
    with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
        with client.stream("POST", endpoint, content=payload,
                           headers={"Authorization": "Bearer " + secret, "Content-Type": "application/json"}) as response:
            if response.status_code != 200:
                code = ("authentication_failed" if response.status_code in (401, 403)
                        else "rate_limited" if response.status_code == 429
                        else "payment_required" if response.status_code == 402
                        else "provider_unavailable" if response.status_code >= 500 else "provider_http_failure")
                raise DecisionProtocolError(code)
            chunks, size = [], 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > response_limit or time.monotonic() > deadline:
                    raise DecisionProtocolError("provider_response_allowance_exceeded")
                chunks.append(chunk)
            return strict_json(b"".join(chunks))
