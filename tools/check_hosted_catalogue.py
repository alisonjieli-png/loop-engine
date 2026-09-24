"""Check that the deployed service serves the approved catalogue and nothing else.

The review record decides what may be served, the generated manifest is what
the release carries, and this command asks the running service what it actually
answers with. It reads only: it lists the items one account may see, searches
for them, and asks for each rejected item by its exact identity to confirm the
service refuses. It makes no body read and adds no usage record. It also reads
the public homepage and asks the service for the manifest of each item the
homepage demonstration names, because the page prints each item's digest as a
recorded fact from the served library. Since September 24, 2026 it does the
same for the demonstration page at /demo, whose five steps print the digest of
every reference they show.

The account credential resolves from this workstation's system keyring. It is
looked up by the origin's hostname, or by --credential-host when one deployment
answers on several hostnames and the account key is registered once under the
name the service was first reached by. The credential never appears in an
argument, in the report or in the output. This is a transport and disclosure
check, not a customer-task benchmark.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REVIEW_RECORD = "examples/29_intelligence_service/starter-catalogue/reviews.json"
RELEASE_MANIFEST = "examples/29_intelligence_service/starter-catalogue/host-release/manifest.json"


#: Six catalogue disclosure checks and the digest checks of the homepage and of the demonstration page.
PLANNED_CHECKS = 8
#: One item of the homepage demonstration: its identity and the digest prefix it prints.
DEMONSTRATION_ITEM = re.compile(r'data-demo-item="([a-z0-9_]+)"[^>]*>.*?data-fact="digest">([0-9a-f]{8})<', re.S)
#: One view of the one page, from its opening tag to the next view or the end of the main part.
VIEW = r'<section data-view="{}"[^>]*>.*?(?=\n\s*<section data-view="|</main>)'


def demonstration_digests(page):
    """Each item the homepage demonstration names, with the digest prefix it prints."""
    return dict(DEMONSTRATION_ITEM.findall(page))


def demonstration_page_digests(page, view="demo"):
    """Each item one view names, with the digest prefix it prints, read from that view only."""
    found = re.search(VIEW.format(re.escape(view)), page, re.S)
    return demonstration_digests(found.group(0)) if found else {}


def demonstration_mismatches(shown, served):
    """Every item whose printed digest is not the start of the digest the service serves for it.

    On September 24, 2026 release 24 re-anchored the starter catalogue, which changes
    every body digest, and the homepage printed the new digests while the service
    still served the previous catalogue release. The browser checks passed, because
    they compare the page with the manifest packaged in the image, not with the
    running service.
    """
    return {identity: {"shown": prefix, "served": (served.get(identity) or "")[:8]}
            for identity, prefix in sorted(shown.items())
            if not (served.get(identity) or "").startswith(prefix)}


class RefuseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError("redirect_refused")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--account", required=True)
    parser.add_argument("--credential-host",
                        help="The keyring hostname the account key is registered under. "
                             "Defaults to the origin's hostname.")
    parser.add_argument("--query", action="append", default=[],
                        help="Repeat for each plain query a customer might type.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    origin = urllib.parse.urlsplit(args.origin)
    if (origin.scheme != "https" or not origin.hostname or origin.username or origin.password
            or origin.path not in ("", "/") or origin.query or origin.fragment or args.output.exists()):
        parser.error("an HTTPS origin and a new report path are required")
    queries = args.query or ["find duplicate customer records", "clean a messy text column",
                             "check a result before handing it over"]

    review = json.loads((ROOT / REVIEW_RECORD).read_text("utf-8"))
    approved = sorted(row["identity"] for row in review["rows"] if row["outcome"] == "approved")
    rejected = sorted(row["identity"] for row in review["rows"] if row["outcome"] == "rejected")
    released = json.loads((ROOT / RELEASE_MANIFEST).read_text("utf-8"))
    packaged = sorted(row["reference"]["identity"] for row in released["items"])

    credential_host = args.credential_host or origin.hostname
    import secretstorage
    collection = secretstorage.get_default_collection(secretstorage.dbus_init())
    held = list(collection.search_items({"application": "loop-engine", "service": credential_host,
                                         "account": args.account, "purpose": "service-access"}))
    if len(held) != 1:
        raise RuntimeError("named_credential_unavailable")
    key = held[0].get_secret().decode()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), RefuseRedirect())
    calls = 0

    def request(path, body=None):
        nonlocal calls
        fields = {"Accept": "application/json", "Authorization": "Bearer " + key}
        if body is not None:
            fields["Content-Type"] = "application/json"
        selected = urllib.request.Request(args.origin.rstrip("/") + path,
            None if body is None else json.dumps(body).encode(), fields)
        calls += 1
        try:
            response = opener.open(selected, timeout=30)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read(4_000_000))

    checks = []

    def check(name, passed, detail=""):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    served, withheld, hits_by_query, refusals = [], [], {}, {}
    try:
        check("the_release_manifest_carries_exactly_the_approved_items", packaged == approved,
              f"{len(packaged)} packaged, {len(approved)} approved")
        status, listing = request("/api/v1/provisioning",
            {"record_type": "service_provisioning_request/v1", "operation": "list"})
        if status != 200:
            raise RuntimeError(f"the listing was refused with status {status}")
        served = sorted(row["identity"] for row in listing["result"]["items"])
        # An item that declares an effect is withheld from a request that holds
        # no authority for it. Both lists come from the registered catalogue.
        withheld = sorted(row["identity"] for row in listing["result"]["withheld"])
        check("the_service_registered_exactly_the_approved_items",
              sorted(served + withheld) == approved,
              f"{len(served)} offered, {len(withheld)} withheld for undeclared authority")
        check("no_rejected_item_is_registered", not (set(served + withheld) & set(rejected)))
        found = set()
        for query in queries:
            status, result = request("/api/v1/retrieval", {"record_type": "service_retrieval_request/v2",
                "query": query, "mode": "lexical", "top_n": 50})
            if status != 200:
                raise RuntimeError(f"the search for {query!r} was refused with status {status}")
            identities = sorted(hit["reference"]["identity"] for hit in result["result"]["hits"])
            hits_by_query[query] = identities
            found.update(identities)
            if result["result"]["bodies_loaded"] is not False:
                raise RuntimeError("the search loaded a body")
        check("every_search_returns_approved_items_and_loads_no_body",
              bool(found) and found <= set(approved),
              f"{len(found)} distinct items over {len(queries)} queries")
        check("no_search_returns_a_rejected_item", not (found & set(rejected)))
        for identity in rejected:
            status, refusal = request("/api/v1/provisioning",
                {"record_type": "service_provisioning_request/v1", "operation": "manifest",
                 "identity": identity})
            refusals[identity] = {"status": status, "code": refusal.get("error", {}).get("code")}
        check("every_rejected_item_is_refused_by_direct_address",
              all(row["status"] in (403, 404) for row in refusals.values()),
              json.dumps(sorted({row["code"] for row in refusals.values()})))
        # The public homepage and the demonstration page are read without the account key.
        def public_page(path):
            nonlocal calls
            calls += 1
            with opener.open(urllib.request.Request(args.origin.rstrip("/") + path, None,
                                                    {"Accept": "text/html"}), timeout=30) as response:
                return response.read(4_000_000).decode("utf-8", "replace")
        home_page = public_page("/")
        # Each check reads the view that printed the digest: the homepage's own step, and the demonstration
        # page's five steps, read from /demo.
        shown = demonstration_page_digests(home_page, "home")
        steps = demonstration_page_digests(public_page("/demo"), "demo")
        served_digests = {}
        for identity in sorted(set(shown) | set(steps)):
            status, manifest = request("/api/v1/provisioning",
                {"record_type": "service_provisioning_request/v1", "operation": "manifest",
                 "identity": identity})
            served_digests[identity] = str(manifest.get("result", {}).get("digest", "")) if status == 200 else ""
        mismatched = demonstration_mismatches(shown, served_digests)
        check("the_homepage_demonstration_prints_the_digests_the_service_serves",
              bool(shown) and not mismatched, json.dumps(mismatched or sorted(shown)))
        mismatched_steps = demonstration_mismatches(steps, served_digests)
        check("the_demonstration_page_prints_the_digests_the_service_serves",
              bool(steps) and not mismatched_steps, json.dumps(mismatched_steps or sorted(steps)))
    except Exception as error:  # noqa: BLE001 - an interrupted check is reported, not hidden
        checks.append({"name": "remaining_checks_interrupted", "passed": False,
                       "error_type": type(error).__name__, "detail": str(error)[:300]})

    report = {"record_type": "hosted_catalogue_disclosure_check/v1",
              "checked_at": datetime.now(timezone.utc).isoformat(), "origin": args.origin,
              "account": args.account, "credential_host": credential_host, "queries": queries,
              "approved_items": len(approved), "rejected_items": len(rejected),
              "offered_items": len(served), "withheld_for_undeclared_authority": len(withheld),
              "rejected_identities": rejected, "refusals": refusals,
              "search_hits": hits_by_query,
              "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "review_record": REVIEW_RECORD, "release_manifest": RELEASE_MANIFEST,
              "checks": checks, "passed": sum(row["passed"] for row in checks),
              "executed": len(checks), "planned_checks": PLANNED_CHECKS,
              "all_passed": len(checks) == PLANNED_CHECKS and all(row["passed"] for row in checks),
              "http_calls": calls, "body_reads": 0, "usage_records_added": 0,
              "physical_model_calls": 0, "credential_printed": False}
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps({key: report[key] for key in
                      ("passed", "executed", "planned_checks", "all_passed", "origin",
                       "offered_items", "withheld_for_undeclared_authority")}))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
