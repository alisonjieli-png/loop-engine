"""One read-only sender-domain query; no email and no OAuth refresh."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import operator_credentials as credentials

OUT = Path(__file__).parent / "sender-domain-readiness-1.json"
if OUT.exists():
    raise SystemExit("Use a new evidence path")
record = {"record_type": "signup_readonly_sender_readiness/v1", "observed_at": datetime.now(timezone.utc).isoformat(),
          "method": "GET", "url": "https://api.resend.com/domains", "credential_reference": "resend-send",
          "emails_sent": 0, "mutations": 0, "oauth_refreshed": False, "secret_values_recorded": False}
try:
    key = credentials.resolve("resend-send")
    with httpx.Client(timeout=12, follow_redirects=False, trust_env=False) as client:
        response = client.get(record["url"], headers={"Authorization": "Bearer " + key})
    record["http_status"] = response.status_code
    if response.status_code == 200:
        value = response.json()
        record["matching_domains"] = [{k: row.get(k) for k in ("name", "status", "region", "capabilities")}
                                      for row in value.get("data", []) if type(row) is dict
                                      and (row.get("name") == "baltor.ai" or str(row.get("name", "")).endswith(".baltor.ai"))]
        record["has_more"] = value.get("has_more")
    else:
        record["unavailable_gate"] = "saved_sending_credential_does_not_establish_sender_configuration_access"
except (credentials.CredentialError, httpx.HTTPError, ValueError) as error:
    record["unavailable_gate"] = type(error).__name__
OUT.write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
