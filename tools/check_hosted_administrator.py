"""Exercise one explicitly authorized hosted test-token lifecycle.

Reads an operator credential from the system keyring. Raw credentials never
enter the report. The generated token is revoked before successful completion.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
import uuid


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--administrator", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--authorize-token-lifecycle", action="store_true")
    options = parser.parse_args()
    origin = urllib.parse.urlsplit(options.origin)
    if not options.authorize_token_lifecycle or origin.scheme != "https" or origin.path or origin.query or origin.fragment or origin.username:
        parser.error("an exact HTTPS origin and lifecycle authority are required")
    if options.output.exists():
        parser.error("refusing to overwrite prior evidence")
    import secretstorage
    saved = secretstorage.get_default_collection(secretstorage.dbus_init())
    matches = list(saved.search_items({"application":"loop-engine", "service":origin.hostname,
                                      "account":options.administrator, "purpose":"service-access"}))
    if len(matches) != 1:
        raise SystemExit("A unique administrator credential was not found.")
    administrator = matches[0].get_secret().decode()
    opener = urllib.request.build_opener(NoRedirect())
    def call(path, token=None, body=None):
        request = urllib.request.Request(options.origin + path,
            data=json.dumps(body).encode() if body else None,
            headers={**({"Authorization":"Bearer " + token} if token else {}),
                     **({"Content-Type":"application/json"} if body else {})})
        try:
            with opener.open(request, timeout=20) as response:
                return response.status, {key.lower():value for key,value in response.headers.items()}, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, {key.lower():value for key,value in error.headers.items()}, json.loads(error.read())
    checks, key_id, generated = [], None, None
    request_id, revoke_id = uuid.uuid4().hex, uuid.uuid4().hex
    def check(name, value):
        checks.append({"name":name,"passed":bool(value)})
    try:
        code, _, _ = call("/api/v1/admin/access")
        check("anonymous_administration_refused", code == 401)
        code, _, session = call("/api/v1/session", administrator)
        check("administrator_identity_and_scope_verified", code == 200 and session["result"]["principal"]["tenant_id"] == options.administrator and "access:manage" in session["result"]["principal"]["scopes"])
        code, _, access = call("/api/v1/admin/access", administrator)
        check("configured_test_token_limits_available", code == 200 and options.target in access["result"]["target_tenants"] and access["result"]["maximum_active_tokens"] == 20)
        payload = {"record_type":"service_access_request/v1","operation":"issue","request_id":request_id,
            "tenant_id":options.target,"label":"Live acceptance " + request_id[:8],"scopes":["provisioning:metadata"],"lifetime_seconds":3600}
        code, headers, result = call("/api/v1/admin/access", administrator, payload)
        check("authorized_token_creation_committed", code == 200 and result["result"]["committed"])
        if code != 200:
            raise RuntimeError("creation_not_confirmed")
        generated, key_id = result["result"]["token"], result["result"]["key"]["key_id"]
        check("credential_response_not_cacheable", headers.get("cache-control") == "no-store")
        code, _, duplicate = call("/api/v1/admin/access", administrator, payload)
        check("duplicate_creation_does_not_mint_or_reveal_another_token", code == 200 and duplicate["result"]["replayed"] and duplicate["result"]["token"] is None and duplicate["result"]["key"]["key_id"] == key_id)
        code, _, child = call("/api/v1/session", generated)
        check("new_token_authenticates_with_exact_scope", code == 200 and child["result"]["principal"]["scopes"] == ["provisioning:metadata"])
        code, _, _ = call("/api/v1/admin/access", generated)
        check("new_token_cannot_manage_administration", code == 403)
        code, _, search = call("/api/v1/retrieval", generated, {"record_type":"service_retrieval_request/v2","query":"review","mode":"lexical","top_n":10})
        check("new_token_can_search_authorized_references", code == 200 and len(search["result"]["hits"]) > 0)
        code, _, listing = call("/api/v1/admin/access", administrator)
        check("listing_never_returns_raw_token", code == 200 and generated not in json.dumps(listing) and "key_digest" not in json.dumps(listing))
    except Exception as error:
        checks.append({"name":"live_journey_completed","passed":False,"error_type":type(error).__name__})
    finally:
        if key_id is not None:
            try:
                code, _, revoked = call("/api/v1/admin/access", administrator, {"record_type":"service_access_request/v1",
                    "operation":"revoke","request_id":revoke_id,"tenant_id":options.target,"key_id":key_id})
                check("test_credential_revoked", code == 200 and revoked["result"]["key"]["state"] == "revoked")
                code, _, _ = call("/api/v1/session", generated)
                check("revoked_credential_is_refused", code == 401)
            except Exception as error:
                checks.append({"name":"test_credential_cleanup_confirmed","passed":False,"error_type":type(error).__name__})
    report = {"record_type":"hosted_administrator_acceptance/v1","observed_at":datetime.now(timezone.utc).isoformat(),
        "origin":options.origin,"administrator":options.administrator,"test_key_id":key_id,
        "issue_request_id":request_id,"revoke_request_id":revoke_id,"checks":checks,
        "passed":sum(row["passed"] for row in checks),"total":len(checks),"all_passed":all(row["passed"] for row in checks),
        "checker_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "limitations":"No email, payment, model or native harness qualification."}
    with options.output.open("x") as stream:
        json.dump(report,stream,indent=2)
    print(json.dumps({key:report[key] for key in ("passed","total","all_passed","test_key_id")}))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
