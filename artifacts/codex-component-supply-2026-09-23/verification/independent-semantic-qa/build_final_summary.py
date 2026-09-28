"""Bind the final tested payload trees without running or approving any candidate."""
import ast
from collections import Counter
from datetime import datetime,timezone
import json
from pathlib import Path
from sandbox import bindings,digest
HERE=Path(__file__).resolve().parent
SUPPLY=HERE.parents[1]
REPORTS=['root-independent-successor-3.json','systems-independent-successor-2.json',
         'data-independent-execution-1.json','data-csv-independent-successor-2.json']
latest={}
for name in REPORTS:
 r=json.loads((HERE/name).read_text())
 for package in r['packages']:
  latest[package['identity']]={**package,'evidence_report':name}
rows=[];hashes=[];kinds=Counter();total_bytes=0
for identity,package in sorted(latest.items()):
 root=SUPPLY/'authored'/identity
 current=bindings(root)
 if not package['passed'] or not package['bytes_unchanged_during_check'] or current!=package['bindings']:
  raise ValueError('unverified_or_changed_package:'+identity)
 source=(root/'tools'/f'{identity}.py').read_text();syntax=ast.parse(source)
 imports=[]
 for item in ast.walk(syntax):
  if isinstance(item,ast.Import):imports.extend(alias.name for alias in item.names)
  elif isinstance(item,ast.ImportFrom):imports.append(item.module)
 for file in current['files']:
  name=file['path'];kinds['instruction' if name=='AGENTS.md' else 'license' if name=='LICENSE' else 'tool' if name.startswith('tools/') else 'contract' if name.startswith('contracts/') else 'example' if name.startswith('examples/') else 'verification_fixture' if name.startswith('verification/') else 'other']+=1
  hashes.append(file['digest']);total_bytes+=file['size_bytes']
 rows.append({'identity':identity,'independent_cases':len(package['cases']),
              'evidence_report':package['evidence_report'],'script_imports':sorted(set(imports)),
              'tree_binding_sha256':current['tree_binding_sha256'],'files':current['files']})
summary={'record_type':'codex_component_supply_independent_engineering_qa/v1',
         'at':datetime.now(timezone.utc).isoformat(),'source_tooling_revision':'231f51bb1facab517fbe915b08ea9ac85f913347',
         'packages':rows,'package_count':len(rows),'payload_file_paths':len(hashes),
         'distinct_payload_file_hashes':len(set(hashes)),'payload_bytes':total_bytes,
         'payload_file_categories':dict(sorted(kinds.items())),
         'independent_cases':sum(row['independent_cases'] for row in rows),
         'independent_wrong_algorithm_controls':2,'unresolved_findings':[],
         'exact_current_trees_match_execution_evidence':True,
         'candidate_admission_performed':False,'native_harness_qualification_performed':False,
         'model_provider_calls':0,'live_service_requests':0,
         'limits':'Finite fixture and source review, not a proof over all allowed inputs, all Python versions, maximum-volume workloads, or native harness loading.',
         'evidence_files':{name:digest((HERE/name).read_bytes()) for name in REPORTS},
         'qa_source_files':{name:digest((HERE/name).read_bytes()) for name in ['sandbox.py','verify_cases.py','build_final_summary.py','wrong_algorithm_controls.py']}}
with (HERE/'final-independent-summary-1.json').open('x') as stream:
 json.dump(summary,stream,indent=2);stream.write('\n')
print({key:summary[key] for key in ['package_count','payload_file_paths','distinct_payload_file_hashes','payload_bytes','independent_cases','payload_file_categories']})
