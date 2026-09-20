"""Restore an explicitly authorized pilot backup in a network-isolated container.

The live database is read through SQLite's backup API. Configuration and
declared artifact files are copied, not modified. The private backup is kept
outside Git. Only counts, digests and check outcomes enter the public report.
This is a point-in-time restore exercise, not a regional disaster-recovery SLA.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import time
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True)
    parser.add_argument("--organization", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--administrator", required=True)
    parser.add_argument("--identity", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--authorize-backup", action="store_true")
    options = parser.parse_args()
    if not options.authorize_backup or options.output.exists() or not re.fullmatch(r"[a-z0-9-]+", options.app):
        parser.error("exact pilot identity, backup authority and a new report path are required")
    import secretstorage
    saved = secretstorage.get_default_collection(secretstorage.dbus_init())
    def secret(service, account, purpose):
        items = list(saved.search_items({"application":"loop-engine","service":service,"account":account,"purpose":purpose}))
        if len(items) != 1:
            raise RuntimeError("credential_reference_unavailable")
        return items[0].get_secret().decode()
    checks, volume, container, backup_path = [], None, None, None
    def check(name, passed):
        checks.append({"name":name,"passed":bool(passed)})
    def command(args, *, data=None, environment=None, timeout=60):
        result = subprocess.run(args,input=data,text=True,capture_output=True,env=environment,timeout=timeout)
        if result.returncode:
            raise RuntimeError("operator_command_failed_output_withheld")
        return result.stdout.strip()
    archive_digest, image_id = None, None
    try:
        image_id = json.loads(command(["docker","image","inspect",options.image]))[0]["Id"]
        program = '''import base64,hashlib,json,sqlite3,tempfile
from pathlib import Path
root=Path('/data'); config_path=root/'host.json'
def confined(path):
 p=Path(path)
 if p.resolve()!=p or root not in p.parents or not p.is_file(): raise RuntimeError('unsafe_backup_path')
 return p
config_raw=config_path.read_bytes(); config=json.loads(config_raw)
manifest_path=confined(config['manifest_path']); manifest_raw=manifest_path.read_bytes();manifest=json.loads(manifest_raw)
database=confined(config['runtime']['database_path']); artifacts=Path(manifest['artifact_root'])
paths=[config_path,manifest_path]
for row in manifest['items']: paths.append(confined(artifacts/row['body_path']))
if len(paths)>100 or sum(p.stat().st_size for p in paths)>20_000_000: raise RuntimeError('backup_bound_exceeded')
files={str(p.relative_to(root)):p.read_bytes() for p in paths}
with tempfile.TemporaryDirectory(prefix='loop-backup-') as temporary:
 target=Path(temporary)/'snapshot.db'
 with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(target) as dest: source.backup(dest)
 if target.stat().st_size>20_000_000: raise RuntimeError('database_backup_bound_exceeded')
 files[str(database.relative_to(root))]=target.read_bytes()
if config_path.read_bytes()!=config_raw or manifest_path.read_bytes()!=manifest_raw: raise RuntimeError('configuration_changed_during_backup')
print(json.dumps({'files':{name:{'body':base64.b64encode(body).decode(),'sha256':hashlib.sha256(body).hexdigest()} for name,body in files.items()}}))
'''
        fly = secret("fly.io", options.organization, "organization-deploy")
        raw = command(["fly","ssh","console","--app",options.app,"--command",shlex.join(["python","-c",program])],
            environment={**os.environ,"FLY_API_TOKEN":fly,"FLY_ACCESS_TOKEN":fly},timeout=90)
        lines = [line for line in raw.splitlines() if line.startswith('{"files"')]
        if len(lines) != 1:
            raise RuntimeError("backup_export_not_confirmed")
        archive = json.loads(lines[0]); encoded=json.dumps(archive,sort_keys=True).encode()
        archive_digest=hashlib.sha256(encoded).hexdigest()
        private=Path(__file__).resolve().parents[1]/".loop-engine-dev"/("pilot-restore-"+uuid.uuid4().hex)
        private.mkdir(mode=0o700)
        backup_path=private/"private-backup.json"
        with os.fdopen(os.open(backup_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as stream: stream.write(encoded)
        check("private_backup_saved_with_owner_only_permissions",backup_path.stat().st_mode & 0o777 == 0o600)
        volume="loop-engine-restore-test-"+uuid.uuid4().hex
        command(["docker","volume","create","--label","loop-engine.purpose=isolated-restore-test",volume])
        restore='''import base64,hashlib,json,os,sqlite3,sys
from pathlib import Path
root=Path('/data');archive=json.load(sys.stdin)
for name,row in archive['files'].items():
 path=root/name
 if Path(name).is_absolute() or '..' in Path(name).parts or path.resolve()!=path or root not in path.parents: raise RuntimeError('unsafe_archive')
 body=base64.b64decode(row['body'],validate=True)
 if hashlib.sha256(body).hexdigest()!=row['sha256']: raise RuntimeError('archive_digest_mismatch')
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('xb') as stream: stream.write(body)
for path in [root,*root.rglob('*')]: os.chown(path,65534,65534);os.chmod(path,0o700 if path.is_dir() else 0o600)
config=json.loads((root/'host.json').read_text())
with sqlite3.connect('file:'+config['runtime']['database_path']+'?mode=ro',uri=True) as db: assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
print('restored_and_integrity_checked')
'''
        command(["docker","run","--rm","--interactive","--network","none","--user","0:0","--mount",f"type=volume,src={volume},dst=/data","--entrypoint","python",options.image,"-c",restore],data=encoded.decode())
        check("snapshot_integrity_and_exact_file_digests_pass",True)
        container=command(["docker","run","--detach","--network","none","--read-only","--tmpfs","/tmp:rw,nosuid,nodev,size=128m","--mount",f"type=volume,src={volume},dst=/data",options.image])
        details=json.loads(command(["docker","inspect",container]))[0]
        check("restore_container_has_no_network_or_published_ports",details["HostConfig"]["NetworkMode"]=="none" and not details["HostConfig"].get("PortBindings"))
        probe='''import hashlib,json,sys,urllib.request,urllib.error
cfg=json.load(sys.stdin)
def call(path,token=None,body=None):
 request=urllib.request.Request('http://localhost:8080'+path,data=json.dumps(body).encode() if body else None,headers={**({'Authorization':'Bearer '+token} if token else {}),**({'Content-Type':'application/json'} if body else {})})
 try:
  with urllib.request.urlopen(request,timeout=5) as response: return response.status,json.load(response)
 except urllib.error.HTTPError as error: return error.code,json.load(error)
assert call('/api/v1/session')[0]==401
code,result=call('/api/v1/session',cfg['owner']);assert code==200 and result['result']['principal']['tenant_id']==cfg['owner_name']
assert call('/api/v1/admin/access',cfg['owner'])[0]==403
code,admin=call('/api/v1/admin/access',cfg['administrator']);assert code==200
assert any(row['state']=='revoked' for row in admin['result']['tokens'])
before=call('/api/v1/usage',cfg['owner'])[1]['result']['records']
request={'record_type':'service_provisioning_request/v1','operation':'read','identity':cfg['identity'],'request_id':cfg['request_id']}
code,first=call('/api/v1/provisioning',cfg['owner'],request);assert code==200
code,repeated=call('/api/v1/provisioning',cfg['owner'],request);assert code==200
assert first['result']['metering_acknowledgment']==repeated['result']['metering_acknowledgment']
assert hashlib.sha256(first['result']['body'].encode()).hexdigest()==first['result']['digest']
after=call('/api/v1/usage',cfg['owner'])[1]['result']['records'];assert after==before+cfg['expected_new_records']
print(json.dumps({'authenticated':True,'tenant_scope_preserved':True,'revoked_records_preserved':True,'body_digest_checked':True,'idempotency_preserved':True}))
'''
        credentials={"owner":secret(options.app+".fly.dev",options.owner,"service-access"),"owner_name":options.owner,
                     "administrator":secret(options.app+".fly.dev",options.administrator,"service-access"),
                     "identity":options.identity,"request_id":"restore-test-"+uuid.uuid4().hex,"expected_new_records":1}
        # Poll only readiness. Mutating local acceptance is attempted once per
        # phase, using one durable request identity across restart.
        health="import urllib.request; urllib.request.urlopen('http://localhost:8080/api/v1/health',timeout=2).close()"
        for phase in ("initial", "after_restart"):
            if phase=="after_restart": command(["docker","restart",container]);credentials["expected_new_records"]=0
            deadline=time.monotonic()+35
            while True:
                ready=subprocess.run(["docker","exec",container,"python","-c",health],capture_output=True,timeout=5)
                if ready.returncode==0:break
                if time.monotonic()>deadline:raise RuntimeError("restored_service_not_ready")
                time.sleep(.2)
            observed=json.loads(command(["docker","exec","-i",container,"python","-c",probe],data=json.dumps(credentials)))
            for name,passed in observed.items():check(phase+"_"+name,passed)
    except Exception as error:
        checks.append({"name":"restore_exercise_completed","passed":False,"error_type":type(error).__name__})
    finally:
        for resource,operation in ((container,["docker","rm","--force"]),(volume,["docker","volume","rm"])):
            if resource:
                try:command([*operation,resource]);check("owned_"+("container" if resource==container else "volume")+"_removed",True)
                except Exception:check("owned_test_resource_cleanup",False)
    report={"record_type":"pilot_backup_restore_check/v1","observed_at":datetime.now(timezone.utc).isoformat(),
        "source_application":options.app,"image_reference":options.image,"image_id":image_id,
        "backup_sha256":archive_digest,"private_backup_path":str(backup_path) if backup_path else None,
        "production_data_mutated":False,"new_cloud_resources":0,"checks":checks,
        "passed":sum(row["passed"] for row in checks),"total":len(checks),"all_passed":all(row["passed"] for row in checks),
        "limitations":["Local point-in-time restoration only; no cross-region recovery.","Private backup is permission-restricted, not separately encrypted by this tool.","Reconcile revocations and external payment state before a production restore; old backups can restore old authority.","This does not establish a scheduled off-site backup or recovery-time guarantee."]}
    with options.output.open('x') as stream:json.dump(report,stream,indent=2)
    print(json.dumps({key:report[key] for key in ("passed","total","all_passed","private_backup_path")}))
    return 0 if report["all_passed"] else 1


if __name__=="__main__":raise SystemExit(main())
