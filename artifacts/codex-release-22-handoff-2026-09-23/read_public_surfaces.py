"""Sequential public GET probes; retain only allowlisted fields and byte hashes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import urllib.error
import urllib.request

HOSTS = ('baltor.ai','www.baltor.ai','app.baltor.ai','baltor-pilot.fly.dev',
         'demo.baltor.ai','examples.baltor.ai','docs.baltor.ai','status.baltor.ai')
PATHS = ('/api/v1/health','/api/v1/capabilities','/','/privacy')
OUTPUT = Path('/home/username/.le-codex-build/release-22-evidence/public-surfaces.json')
if OUTPUT.exists():
    raise SystemExit('Refusing to replace an existing public evidence report')

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
rows = []
for host in HOSTS:
    for path in PATHS:
        row = {'host':host,'path':path,'observed_at':datetime.now(timezone.utc).isoformat()}
        request = urllib.request.Request('https://'+host+path,
            headers={'Accept':'application/json' if path.startswith('/api/') else 'text/html',
                     'User-Agent':'Baltor-public-release-verification/1'})
        try:
            try:
                response = opener.open(request,timeout=20)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                body = response.read(2_000_001)
                row.update(status=response.status,content_type=response.headers.get('Content-Type',''),
                           cache_control=response.headers.get('Cache-Control',''),etag=response.headers.get('ETag',''),
                           content_bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),truncated=len(body)>2_000_000)
            if path.startswith('/api/') and not row['truncated']:
                record = json.loads(body)
                result = record.get('result',{}) if isinstance(record,dict) else {}
                row['record_type'] = record.get('record_type')
                if isinstance(result,dict):
                    row['result_record_type'] = result.get('record_type')
                    for field in ('status','ready','healthy'):
                        if isinstance(result.get(field),(bool,str,int)):
                            row[field] = result[field]
                    if path.endswith('/capabilities'):
                        row['api_version'] = result.get('api_version')
                        selected = {}
                        for section,fields in {
                            'website':('display_name','registration_available','client_access_available','waitlist_available'),
                            'protocol':('transport','versions','handshake_versions','per_request_versions','sdk_version','session_state'),
                            'retrieval':('request_record_type','authority_effects','modes','lexical_backend','vector_backend','semantic_embedding_model_installed'),
                            'delivery':('body_format','package_files','requires_reauthorization')
                        }.items():
                            value = result.get(section,{})
                            if isinstance(value,dict):selected[section] = {field:value[field] for field in fields if field in value}
                        row['capabilities'] = selected
            elif not row['truncated']:
                match = re.search(r'<title>([^<]*)</title>',body.decode('utf-8','replace'),re.I)
                row['http_title'] = match.group(1) if match else None
        except Exception as error:
            row['error_type'] = type(error).__name__
        rows.append(row)
report = {'record_type':'public_release_surfaces/v1','release_revision':'231f51bb1facab517fbe915b08ea9ac85f913347',
          'method':'sequential public GET; no redirects; no service credentials or cookies',
          'service_credentials_used':False,'account_actions':False,'rows':rows,
          'all_http_200':len(rows)==32 and all(row.get('status')==200 and not row.get('error_type') and not row.get('truncated') for row in rows)}
with OUTPUT.open('x') as target:
    json.dump(report,target,indent=2);target.write('\n')
print(json.dumps({'output':str(OUTPUT),'routes':len(rows),'all_http_200':report['all_http_200'],
                  'failures':[{'host':r['host'],'path':r['path'],'status':r.get('status'),'error_type':r.get('error_type')} for r in rows if r.get('status')!=200 or r.get('error_type')]}))
