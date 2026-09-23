"""Run one read-only, allowlisted host-config observation through the named Fly helper."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent / "host-state-1.json"
if OUT.exists():
    raise SystemExit("Use a new evidence path")
program = r'''
import json,os
with open("/data/host.json","r") as stream: config=json.load(stream)
def chosen(name,fields):
    value=config.get(name)
    if not isinstance(value,dict):return {"present":False}
    result={"present":True}
    for key in fields:
        if key not in value:continue
        entry=value[key]
        if key.endswith("_ref"):
            result[key]=entry if isinstance(entry,str)and entry.startswith("env:")else"<non-reference suppressed>"
        elif type(entry)in(str,int,float,bool)or entry is None:result[key]=entry
    return result
result={"account_email":chosen("account_email",("record_type","provider_profile","identity_origin","identity_service_key_ref","mail_origin","mail_api_key_ref","sender_address","sender_name","signup_enabled","recovery_enabled","allow_network","minimum_password_length","attempts_for_each_address","attempts_for_each_email","attempt_window_seconds")),
"browser_identity":chosen("browser_identity",("record_type","project_url","registration_enabled","email_signup_enabled","allow_network")),
"http":chosen("http",("record_type","public_base_url","display_name"))}
limits=config.get("http",{}).get("request_limits",{})
result["request_limit_address_binding"]={k:limits.get(k)for k in("client_address_source","client_address_header")}
expected=("SUPABASE_PUBLISHABLE_KEY","BALTOR_IDENTITY_SERVICE_KEY","BALTOR_MAIL_API_KEY")
result["expected_environment_names_present"]={k:bool(os.environ.get(k))for k in expected}
print(json.dumps(result))
'''
command = [sys.executable, str(ROOT / "tools/fly_operator.py"), "--account", "baltor", "--timeout", "45", "--",
           "ssh", "console", "--app", "baltor-pilot", "--command", shlex.join(["python", "-B", "-c", program])]
completed = subprocess.run(command, capture_output=True, text=True, timeout=55)
rows = []
for line in completed.stdout.splitlines():
    if line.startswith('{"account_email"'):
        rows.append(json.loads(line))
record = {"record_type": "signup_readonly_host_readiness/v1", "observed_at": datetime.now(timezone.utc).isoformat(),
          "exit_code": completed.returncode, "helper": "tools/fly_operator.py --account baltor",
          "selected_host_fields": rows[0] if completed.returncode == 0 and len(rows) == 1 else None,
          "error": None if completed.returncode == 0 and len(rows) == 1 else "host_observation_unavailable",
          "raw_output_recorded": False, "secret_values_recorded": False, "host_writes": 0}
OUT.write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
