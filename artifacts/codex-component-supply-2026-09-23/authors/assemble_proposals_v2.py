"""Explicitly assemble the sixteen authored package trees for the existing factory."""
import base64,hashlib,json,subprocess
from pathlib import Path
BASE=Path(__file__).resolve().parent.parent
REPO=Path('/home/username/.le-codex-build/integration')
REV='231f51bb1facab517fbe915b08ea9ac85f913347'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==REV
metadata={}
for relative in ['authors/root-metadata-final.json','authors/data-metadata.json','authored/authors/systems-metadata.json']:
 rows=json.loads((BASE/relative).read_text());assert not set(metadata)&set(rows);metadata.update(rows)
assert len(metadata)==16
source='src/loop_engine/core/service_runtime/catalogue_packages.py'
hash_=lambda raw:hashlib.sha256(raw).hexdigest()
proposals=[];file_digests=[];all_files=[]
for identity,meta in sorted(metadata.items()):
 specs=[('AGENTS.md','text/markdown','instruction_file'),(f'tools/{identity}.py','text/x-python','executable_tool'),('contracts/input.schema.json','application/schema+json','configuration'),('contracts/output.schema.json','application/schema+json','configuration'),('examples/input.json','application/json','other'),('examples/output.json','application/json','other'),('verification/cases.json','application/json','other'),('LICENSE','text/plain','other')]
 folder=BASE/'authored'/identity
 assert sorted(p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file())==sorted(p for p,_,_ in specs)
 files=[]
 for path,media,role in specs:
  p=folder/path;assert not p.is_symlink();raw=p.read_bytes();digest=hash_(raw)
  files.append({'path':path,'digest':digest,'size_bytes':len(raw),'media_type':media,'role':role,'content_base64':base64.b64encode(raw).decode()})
  file_digests.append(digest);all_files.append({'package':identity,'path':path,'digest':digest,'bytes':len(raw)})
 proposals.append({'id':identity,'title':meta['title'],'purpose':meta['purpose'],'sources':[source],'layer':'code','family':'deterministic_native_method','search_tags':meta['search_tags'],'tags':{'language':['en'],'domain':['software','data']},'symbols':['solve'],'kind':'tool','styles':['codex','opencode','pi'],'dependencies':['Python>=3.10 standard library; no third-party packages'],'declared_effects':['reads_fs','spawns_process'],'producer':{'producer_identity':'Codex original working-directory component authoring processes','family':'openai','method_identity':'codex_original_working_directory_components/v1'},'files':files})
record={'record_type':'harness_candidate_batch_proposals/v2','source_revision':REV,'license':{'expression':'MIT','path':'LICENSE','sha256':hash_((REPO/'LICENSE').read_bytes())},'sources':{source:hash_((REPO/source).read_bytes())},'proposals':proposals}
for name,value in [('proposals-v2.json',record),('payload-inventory-v2.json',{'packages':len(proposals),'payload_files':len(file_digests),'unique_payload_digests':len(set(file_digests)),'files':all_files,'metadata_effect_projection':'All sixteen launch profiles explicitly declare reads_fs and spawns_process for interpreter/script loading; no permission is granted.','source_scope':'Pinned CataloguePackage source grounds packaging only, not algorithm correctness.'})]:
 p=BASE/name
 with p.open('x') as stream:json.dump(value,stream,indent=2,ensure_ascii=False);stream.write('\n')
print(json.dumps({'packages':len(proposals),'payload_files':len(file_digests),'unique_payload_digests':len(set(file_digests))}))
