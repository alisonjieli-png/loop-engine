"""Narrow operator bridge for disposable identity tests on the selected Fly app.

Only typed service methods touch state. No database rows or existing customer
bindings are rewritten. The application must match the selected origin and
identity project, and public account admission must remain disabled.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shlex
import subprocess
from urllib.parse import urlsplit


def operate(*, application, origin, issuer, run_id, subjects, operation, expected_sources):
    if (not re.fullmatch(r"[a-z0-9-]{1,63}", application)
            or not re.fullmatch(r"[a-f0-9]{32}", run_id) or len(subjects) != 2
            or len(set(subjects)) != 2 or any(not re.fullmatch(r"[a-f0-9-]{36}", value) for value in subjects)
            or operation not in ("prepare", "revoke_first", "cleanup")
            or urlsplit(origin).scheme != "https" or urlsplit(origin).path
            or urlsplit(origin).query or urlsplit(origin).fragment or urlsplit(origin).username
            or not issuer.startswith("https://") or not issuer.endswith(".supabase.co/auth/v1")
            or not isinstance(expected_sources, dict) or len(expected_sources) != 8
            or any(not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value) for value in expected_sources.values())):
        raise ValueError("invalid_hosted_qualification_target")
    payload = {"origin": origin, "issuer": issuer, "run_id": run_id, "subjects": list(subjects), "operation": operation,
               "expected_sources": expected_sources}
    code = '''import json,hashlib,pathlib
import loop_engine.core.service_runtime as package
from loop_engine.core.service_runtime.http_entrypoint import load_host_application,load_host_manifest
from loop_engine.core.service_runtime.records import SubjectTenantRegistration,SubjectBindingRequest,ServiceRuntimeError
from loop_engine.core.provisioning_server import ProvisioningItemBinding
p=json.loads(PAYLOAD)
source_root=pathlib.Path(package.__file__).parent
source={"src/loop_engine/core/service_runtime/"+name:hashlib.sha256((source_root/name).read_bytes()).hexdigest() for name in ("access.py","records.py","runtime.py","storage.py","provisioning.py","http.py","http_auth.py","browser_identity.py")}
assert source==p["expected_sources"], "unqualified deployed source"
app,config=load_host_application("/data/host.json")
assert p["origin"] in config["http"]["allowed_origins"], "unbound origin"
assert app.browser_identity is not None and app.client_access is not None, "account adapters absent"
assert app.browser_identity.configuration.project_url+"/auth/v1"==p["issuer"], "different identity project"
assert app.browser_identity.configuration.registration_enabled is False, "public admission must stay closed"
catalogue,_,_,_=load_host_manifest(config["manifest_path"])
items=sorted(catalogue.items.values(),key=lambda item:item.identity)
assert items, "diagnostic material unavailable"
item=items[0]
requests=[SubjectTenantRegistration(p["issuer"],subject,"qa-"+p["run_id"][:12],starter_bindings=(ProvisioningItemBinding.from_item(item),)) for subject in p["subjects"]]
results=[]
for index,request in enumerate(requests):
 if p["operation"]=="prepare":
  result=app.runtime.ensure_subject_tenant(request)
 elif p["operation"]=="revoke_first" and index==0:
  result=app.runtime.revoke_subject(SubjectBindingRequest(request.tenant_id,request.issuer,request.subject))
 elif p["operation"]=="cleanup":
  try:
   app.runtime.revoke_subject(SubjectBindingRequest(request.tenant_id,request.issuer,request.subject))
   result=app.runtime.set_tenant_enabled(request.tenant_id,False)
  except ServiceRuntimeError as error:
   if error.code!="not_found":raise
   result={"absent":True}
 else:continue
 results.append({"tenant_id":request.tenant_id,"result":result})
print(json.dumps({"operation":p["operation"],"bindings":results,"sample_identity":item.identity,"sample_query":item.purpose,"source_sha256":source}))
'''.replace("PAYLOAD", repr(json.dumps(payload)))
    root = Path(__file__).resolve().parents[1]
    environment = {key: value for key, value in os.environ.items() if key not in ("SUPABASE_SECRET_KEY", "SUPABASE_PUBLISHABLE_KEY")}
    result = subprocess.run(["/usr/bin/python3", str(root / "tools/fly_operator.py"), "--account", "baltor", "--timeout", "60", "--",
                             "ssh", "console", "--app", application, "--command", shlex.join(["python", "-c", code])],
                            capture_output=True, text=True, env=environment, timeout=75)
    if result.returncode:
        raise RuntimeError("hosted_qualification_operation_failed_reconcile_before_retry")
    value = json.loads(result.stdout.strip().splitlines()[-1])
    if value.get("operation") != operation:
        raise RuntimeError("hosted_qualification_acknowledgment_invalid")
    return value
