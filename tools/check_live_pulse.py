"""A short, read-only pulse of the live service on every hostname, for a scheduled job.

It asks each hostname the site map lists, plus the technical Fly hostname, for the
homepage, the privacy notice, Get started, the health record and the capabilities
record. It passes when every address answers 200, every health record is ready with
its required checks passing, and every hostname reports the same capabilities. It
also asks the identity provider's public health address, with the publishable key
the service itself publishes, because a free identity project pauses after a week
without requests. It sends no credential of its own, signs nothing in and changes
nothing. A slow answer is reported, not failed: a slow network path is not an outage.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_MAP = ROOT / "src/loop_engine/core/service_runtime/web_site_map.json"
TECHNICAL_HOSTNAME = "baltor-pilot.fly.dev"
PAGES = ("/", "/privacy", "/get-started")
HEALTH, CAPABILITIES, IDENTITY = "/api/v1/health", "/api/v1/capabilities", "/api/v1/account/identity"
SLOW_SECONDS = 10.0
RECORD_TYPE = "live_pulse/v1"


class RefuseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def fetch(opener, url, headers=None, timeout=30):
    """Status, seconds and body of one GET; a transport failure is status 0."""
    started = time.monotonic()
    try:
        with opener.open(urllib.request.Request(url, headers=headers or {}), timeout=timeout) as response:
            return response.status, time.monotonic() - started, response.read(2_000_000)
    except urllib.error.HTTPError as error:
        return error.code, time.monotonic() - started, b""
    except Exception:  # noqa: BLE001 - a transport failure is reported as status 0, not raised
        return 0, time.monotonic() - started, b""


def result_of(body):
    try:
        value = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return value.get("result") if isinstance(value, dict) else None


def health_problems(record):
    """Why one health record is not ready, or an empty list when it is."""
    if not isinstance(record, dict) or record.get("record_type") != "service_health/v2":
        return ["the health record is missing or of an unknown version"]
    problems = [] if record.get("ready") is True else ["the service says it is not ready"]
    required = [check for check in record.get("checks", []) if check.get("required")]
    problems += [f"required check {check.get('name')} fails" for check in required if check.get("passed") is not True]
    return problems + ([] if required else ["no required check is reported"])


def pulse(hostnames, opener=None):
    opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), RefuseRedirect())
    rows, problems, capabilities, slow = [], [], {}, []
    for hostname in hostnames:
        origin = "https://" + hostname
        for path in (*PAGES, HEALTH, CAPABILITIES):
            status, seconds, body = fetch(opener, origin + path)
            rows.append({"hostname": hostname, "path": path, "status": status, "seconds": round(seconds, 2)})
            if status != 200:
                problems.append(f"{hostname}{path} answered {status}")
            elif seconds > SLOW_SECONDS:
                slow.append(f"{hostname}{path} took {seconds:.1f} seconds")
            if path == HEALTH and status == 200:
                problems += [f"{hostname}: {text}" for text in health_problems(result_of(body))]
            if path == CAPABILITIES and status == 200:
                capabilities[hostname] = json.dumps(result_of(body), sort_keys=True)
    if len(set(capabilities.values())) > 1:
        problems.append("the hostnames report different capabilities")
    identity_status = "not asked"
    status, _seconds, body = fetch(opener, "https://" + hostnames[0] + IDENTITY)
    identity = result_of(body) if status == 200 else None
    if isinstance(identity, dict) and identity.get("project_url") and identity.get("publishable_key"):
        status, _seconds, _body = fetch(opener, identity["project_url"].rstrip("/") + "/auth/v1/health",
                                        {"apikey": identity["publishable_key"]})
        identity_status = status
        if status != 200:
            problems.append(f"the identity provider's health address answered {status}")
    else:
        problems.append("the service did not publish its identity settings")
    first = next(iter(capabilities.values()), "null")
    website = (json.loads(first) or {}).get("website", {}) if first != "null" else {}
    return {"record_type": RECORD_TYPE, "hostnames": list(hostnames), "rows": rows, "slow": slow,
            "identity_provider_health": identity_status,
            "registration_available": website.get("registration_available"),
            "problems": problems, "passed": not problems}


def site_hostnames(site_map=SITE_MAP):
    listed = [row["hostname"] for row in json.loads(Path(site_map).read_text("utf-8"))["hostnames"]]
    return listed + ([TECHNICAL_HOSTNAME] if TECHNICAL_HOSTNAME not in listed else [])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    report = pulse(site_hostnames())
    arguments.output.write_text(json.dumps(report, indent=2) + "\n", "utf-8")
    print(json.dumps({key: report[key] for key in ("passed", "problems", "slow", "registration_available",
                                                   "identity_provider_health")}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
