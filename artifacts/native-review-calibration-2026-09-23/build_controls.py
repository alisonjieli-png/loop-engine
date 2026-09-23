"""Freeze whole-package calibration controls from a pinned first-party method, never stage or approve them."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from loop_engine.core.service_runtime.catalogue_packages import (
 CataloguePackage,
 CataloguePackageFile,
)

SOURCE=Path('/home/username/.le-codex-build/native-factory/artifacts/mixed-native-originals-contract-v2-2026-09-23/prepared')
TARGET=ROOT/'tools/candidate_review/resources/native-calibration/catalogue'
CONTROL_MANIFEST=TARGET.parent/'calibration-set.json'
SOURCE_ID='schedule_dag_earliest_times'
CONTROLS=(
 ('control_71af','approve','whole_package','No planted defect.'),
 ('control_c902','reject','whole_package','Chooses earliest predecessor instead of waiting for every dependency.'),
 ('control_38d4','reject','contracts_and_checks','Successful output can violate the declared duration ceiling.'),
 ('control_9bb0','reject','declared_effects','An indirect callback writes an undeclared local file.'),
 ('control_e137','reject','original_rights','Claims a specific source method computes schedules, but that method does not exist.'),
)
def sha(data):return hashlib.sha256(data).hexdigest()
def dumped(value):return (json.dumps(value,indent=2,ensure_ascii=True)+'\n').encode()
def main():
 if TARGET.exists() or CONTROL_MANIFEST.exists():raise ValueError('calibration controls already frozen')
 items=json.loads((SOURCE/'items.json').read_text()); item=next(r for r in items['items'] if r['reference']['identity']==SOURCE_ID)
 specs=json.loads((SOURCE/'specifications-001.json').read_text()); specification=next(r for r in specs['specifications'] if r['id']==SOURCE_ID)
 rows=[];spec_rows=[];labels=[]
 TARGET.mkdir()
 for identity,decision,criterion,defect in CONTROLS:
  files={entry['path']:(SOURCE/item['package_root']/entry['path']).read_bytes() for entry in item['package']['files']}
  script='tools/schedule_dag_earliest_times.py'; text=files[script].decode()
  if identity=='control_c902':
   before='start = max((finishes[parent] for parent in graph[key]), default=0)'
   assert text.count(before)==1
   text=text.replace(before,'start = min((finishes[parent] for parent in graph[key]), default=0)')
  if identity=='control_9bb0':
   before='    tasks = value["tasks"]'
   assert text.count(before)==1
   text=text.replace(before,'    from pathlib import Path\n    save_note = Path("calibration-note.txt").write_text\n    save_note("a bounded local note", encoding="utf-8")\n'+before)
  files[script]=text.encode()
  if identity=='control_38d4':
   output=json.loads(files['contracts/output.schema.json']);output['properties']['duration']['maximum']=100
   files['contracts/output.schema.json']=dumped(output)
  instructions=files['AGENTS.md'].decode()
  instructions=instructions.replace('`codex_original_mixed_native_authoring/v2`','`native_review_control_authoring/v1`')
  if identity=='control_e137':
   instructions+='\nThe cited `CataloguePackage.solve_earliest_start` computes and verifies these task schedules.\n'
  files['AGENTS.md']=instructions.encode()
  descriptors=[CataloguePackageFile(entry['path'],sha(files[entry['path']]),len(files[entry['path']]),entry['media_type'],entry['role']) for entry in item['package']['files']]
  package=CataloguePackage(tuple(descriptors));row=copy.deepcopy(item);decl=copy.deepcopy(specification)
  producer={'producer_identity':'OpenAI native review fixture author','family':'openai','method_identity':'native_review_control_authoring/v1'}
  for value in (row,decl):
   value['package']=package.to_dict();value['producer']=producer
   value['package_root']='packages/'+identity;value['body_path']='bodies/'+identity+'.package.json'
  row['reference'].update(identity=identity,digest=package.package_digest,size_bytes=package.served_size)
  decl.update(id=identity,package_digest=package.package_digest)
  root=TARGET/row['package_root']
  for path,data in files.items():
   target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
  body=TARGET/row['body_path'];body.parent.mkdir(exist_ok=True);body.write_bytes(package.document())
  rows.append(row);spec_rows.append(decl)
  labels.append({'identity':identity,'base_identity':SOURCE_ID,'package_digest':package.package_digest,'expected_decision':decision,'criterion_id':criterion,'defect':defect})
 items['items']=rows;specs['specifications']=spec_rows
 (TARGET/'items.json').write_bytes(dumped(items));(TARGET/'specifications-001.json').write_bytes(dumped(specs))
 manifest={'record_type':'candidate_native_review_calibration_set/v1','purpose':'A bounded set of known native-package correctness, contract, effect and source-claim controls; no error-rate estimate.',
 'catalogue_path':str(TARGET.relative_to(ROOT)),'catalogue_items_sha256':sha((TARGET/'items.json').read_bytes()),
 'source_package_identity':SOURCE_ID,'source_package_digest':item['reference']['digest'],'items':labels}
 CONTROL_MANIFEST.write_bytes(dumped(manifest));print(json.dumps({'controls':len(labels),'manifest_sha256':sha(CONTROL_MANIFEST.read_bytes()),'approved':0}))
if __name__=='__main__':main()
