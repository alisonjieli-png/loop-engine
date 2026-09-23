"""Read-only readiness snapshot. Never stores credential values or provider bodies."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import operator_credentials as credentials

OUT = Path(__file__).parent / "public-state-1.json"
if OUT.exists():
    raise SystemExit("Use a new evidence path")
rows = []
identity = None
with httpx.Client(timeout=12, follow_redirects=False, trust_env=False) as client:
    for path in ("/api/v1/capabilities", "/api/v1/account/identity"):
        url = "https://baltor.ai" + path
        try:
            response = client.get(url)
            data = response.json() if response.status_code == 200 else {}
            result = data.get("result", {})
            if path.endswith("capabilities"):
                public = {key: result.get(key) for key in ("record_type", "api_version", "website", "protocol")}
            else:
                identity = result
                keys = ("record_type", "project_url", "registration_enabled", "email_signup_enabled",
                        "signup_available", "recovery_available", "minimum_password_length", "redirect_url")
                public = {key: result.get(key) for key in keys}
                public["publishable_key_present"] = bool(result.get("publishable_key"))
            rows.append({"url": url, "http_status": response.status_code, "selected_fields": public})
        except (httpx.HTTPError, ValueError) as error:
            rows.append({"url": url, "unavailable": type(error).__name__})
    data = credentials.references()
    project = data["api_keys"]["supabase-publishable"]["account"]
    expected_origin = "https://" + project + ".supabase.co"
    if identity and identity.get("project_url") == expected_origin:
        try:
            key = credentials.resolve("supabase-publishable")
            url = expected_origin + "/auth/v1/settings"
            response = client.get(url, headers={"apikey": key})
            data = response.json() if response.status_code == 200 else {}
            allowed = ("disable_signup", "mailer_autoconfirm", "phone_autoconfirm",
                       "password_min_length", "password_required_characters",
                       "security_update_password_require_reauthentication")
            public = {name: data[name] for name in allowed if name in data and type(data[name]) in (bool, int)}
            external = data.get("external", {})
            public["email_provider_enabled"] = external.get("email") if type(external.get("email")) is bool else None
            rows.append({"url": url, "http_status": response.status_code, "selected_fields": public,
                         "unavailable_requested_fields": [name for name in allowed if name not in data],
                         "credential_reference": "supabase-publishable", "secret_values_recorded": False})
        except (credentials.CredentialError, httpx.HTTPError, ValueError) as error:
            rows.append({"operation": "provider_public_settings", "unavailable": type(error).__name__})
    else:
        rows.append({"operation": "provider_public_settings", "unavailable": "public_identity_origin_not_bound"})
record = {"record_type": "signup_readonly_public_readiness/v1", "observed_at": datetime.now(timezone.utc).isoformat(),
          "requests": rows, "mutations": 0, "emails_sent": 0, "logins": 0, "secret_values_recorded": False}
OUT.write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
