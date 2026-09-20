"""Bootstrap or copy a service administrator credential through the keyring.

Run with system Python. Credentials travel through captured SSH output and
the unlocked system keyring, never through command arguments or reports.
Bootstrap is an explicit operator action, not a public service operation.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess


def collection():
    import secretstorage
    result = secretstorage.get_default_collection(secretstorage.dbus_init())
    if result.is_locked():
        raise SystemExit("Unlock the system credential store first.")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("bootstrap", "copy-key"))
    parser.add_argument("--app", required=True)
    parser.add_argument("--organization", default="baltor")
    parser.add_argument("--administrator", default="baltor-admin")
    parser.add_argument("--target", action="append", default=[])
    parser.add_argument("--display-name", default="Baltor")
    parser.add_argument("--maximum-active-tokens", type=int, default=20)
    parser.add_argument("--administrator-days", type=int, default=30)
    parser.add_argument("--authorize-bootstrap", action="store_true")
    options = parser.parse_args()
    for value in (options.app, options.organization, options.administrator, *options.target):
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,100}", value):
            parser.error("an exact resource identity is required")
    saved = collection()
    attributes = {"application":"loop-engine", "service":options.app + ".fly.dev",
                  "account":options.administrator, "purpose":"service-access"}
    held = list(saved.search_items(attributes))
    if options.operation == "copy-key":
        if len(held) != 1:
            raise SystemExit("No unique saved administrator credential was found.")
        subprocess.run(["wl-copy", "--type", "text/plain"], input=held[0].get_secret(), check=True, timeout=10)
        print("Administrator credential copied to the local clipboard. Paste it into the service sign-in form.")
        return 0
    if held:
        raise SystemExit("An administrator credential is already saved. Use copy-key; bootstrap was not repeated.")
    if not options.authorize_bootstrap or not options.target or not 1 <= options.administrator_days <= 90:
        parser.error("bootstrap requires explicit authority, target tenants, and a bounded credential lifetime")
    fly = list(saved.search_items({"application":"loop-engine", "service":"fly.io", "account":options.organization, "purpose":"organization-deploy"}))
    if len(fly) != 1:
        raise SystemExit("Expected one configured Fly operator credential.")
    # The deployed package owns tenant and token writes. Configuration is
    # replaced atomically only after its policy and target tenants validate.
    program = '''import json,os,tempfile,time
from pathlib import Path
from dataclasses import asdict
from loop_engine.core.service_runtime.http_entrypoint import load_host_application
from loop_engine.core.service_runtime.access import ServiceAccessPolicy
from loop_engine.core.service_runtime.records import ACCESS_MANAGE_SCOPE,TenantRegistration,TenantKeyIssue,ServiceRuntimeError
settings=SETTINGS
path=Path('/data/host.json')
application,config=load_host_application(str(path))
runtime=application.runtime
policy=ServiceAccessPolicy((settings['administrator'],),tuple(settings['targets']),maximum_active_tokens=settings['maximum'],writes_authorized=True)
with runtime._catalog.store() as store:
 for tenant in policy.target_tenants: runtime._tenant(store,tenant)
 try: runtime._tenant(store,settings['administrator'])
 except ServiceRuntimeError as error:
  if error.code!='not_found': raise
 else: raise RuntimeError('administrator_already_exists; reconcile instead of issuing another credential')
backup=path.with_name('host.before-access-administration.json')
with backup.open('xb') as stream: stream.write(path.read_bytes())
current=path.stat();os.chmod(backup,0o600);os.chown(backup,current.st_uid,current.st_gid)
config['http']['display_name']=settings['display_name'];config['administration']=asdict(policy)
# Validating the policy is separate from explicitly authorizing the writes.
runtime.register_tenant(TenantRegistration(settings['administrator'],settings['administrator']+':private',(ACCESS_MANAGE_SCOPE,)))
issued=runtime.issue_key(TenantKeyIssue(settings['administrator'],'Owner administrator',int(time.time())+settings['days']*86400,(ACCESS_MANAGE_SCOPE,)))
fd,temporary=tempfile.mkstemp(prefix='host-admin-',suffix='.json',dir='/data')
with os.fdopen(fd,'w') as stream:
 json.dump(config,stream,indent=2);stream.flush();os.fsync(stream.fileno())
os.chown(temporary,current.st_uid,current.st_gid);os.chmod(temporary,0o600);os.replace(temporary,path)
print(json.dumps({'tenant_id':issued.tenant_id,'key_id':issued.key_id,'expires_at':issued.expires_at,'key':issued.key,'configuration_updated':True}))
'''.replace("SETTINGS", repr({"administrator":options.administrator,"targets":options.target,
        "maximum":options.maximum_active_tokens,"display_name":options.display_name,"days":options.administrator_days}))
    environment = {**os.environ, "FLY_API_TOKEN":fly[0].get_secret().decode(), "FLY_ACCESS_TOKEN":fly[0].get_secret().decode()}
    result = subprocess.run(["fly","ssh","console","--app",options.app,"--command",shlex.join(["python","-c",program])],
                            env=environment, capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise SystemExit("Bootstrap did not return success. Inspect the tenant and configuration before retrying. Captured output was not printed because it may contain credentials.")
    records = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{"tenant_id"')]
    if len(records) != 1 or not records[0].get("key"):
        raise SystemExit("Bootstrap outcome is unknown. Reconcile remote state; do not repeat blindly.")
    receipt = records[0]
    saved.create_item("Baltor / owner administrator", attributes, receipt["key"].encode(), replace=False)
    confirmation = list(saved.search_items(attributes))
    if len(confirmation) != 1 or confirmation[0].get_secret().decode() != receipt["key"]:
        raise SystemExit("Credential store verification failed. Remote state requires operator recovery.")
    print(json.dumps({key:value for key,value in receipt.items() if key != "key"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
