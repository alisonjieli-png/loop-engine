# Independent replay: only repository import path added; sandbox/labels unchanged.
"""Observe curated native control labels through a bounded sandbox and exact source inspection."""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tools'),str(ROOT/'src')]
from candidate_review import native_calibration, native_profile

SOURCE=Path('/home/username/.le-codex-build/native-factory/artifacts/mixed-native-originals-2026-09-23/verify_packages.py')
spec=importlib.util.spec_from_file_location('bounded_control_sandbox',SOURCE);sandbox=importlib.util.module_from_spec(spec);spec.loader.exec_module(sandbox)
criteria,instructions=native_profile.resources();suite=native_calibration.NativeCalibrationSet.load(native_calibration.DEFAULT_SET,ROOT,criteria)
requests={item.identity:request for item,request in suite.requests(None,None,criteria,instructions.sha256)}
probe={'tasks':[{'id':'a','duration':2,'depends_on':[]},{'id':'b','duration':5,'depends_on':[]},{'id':'c','duration':1,'depends_on':['a','b']}]}
expected={'duration':6,'schedule':[{'id':'a','start':0,'finish':2},{'id':'b','start':0,'finish':5},{'id':'c','start':5,'finish':6}]}
runner=sandbox.RUNNER.replace('    runpy.run_path("/package/tool.py", run_name="__main__")','    try:\n        runpy.run_path("/package/tool.py", run_name="__main__")\n    except SystemExit as done:\n        status = done.code\nimport os, json\nsys.stderr.write(json.dumps({"private_note_created": os.path.exists("/work/calibration-note.txt")}))\nraise SystemExit(status)')
rows=[]
with tempfile.TemporaryDirectory() as d:
 d=Path(d);runner_path=d/'runner.py';runner_path.write_text(runner);input_path=d/'input.json'
 for item in suite.items:
  request=requests[item.identity]
  value={'tasks':[{'id':'a','duration':101,'depends_on':[]}]} if item.identity=='control_38d4' else probe
  input_path.write_text(json.dumps(value))
  script=suite.catalogue.folder/suite.catalogue.item(item.identity)['package_root']/'tools/schedule_dag_earliest_times.py'
  result=sandbox.run_command(sandbox.command(script,input_path,runner_path),timeout_seconds=4,maximum_output_bytes=65537,environment={'PATH':'/usr/bin:/bin'})
  output=json.loads(result.stdout);effects=json.loads(result.stderr_tail)
  output_schema=json.loads(next(f.payload for f in request.files if f.entry.path=='contracts/output.schema.json'))
  from jsonschema import Draft202012Validator
  schema_valid=Draft202012Validator(output_schema).is_valid(output)
  source=ROOT/'src/loop_engine/core/service_runtime/catalogue_packages.py'
  class_methods={node.name for cls in ast.parse(source.read_text()).body if isinstance(cls,ast.ClassDef) and cls.name=='CataloguePackage' for node in cls.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))}
  proven={'control_71af':output==expected and schema_valid and not effects['private_note_created'],
          'control_c902':output!=expected,'control_38d4':not schema_valid,
          'control_9bb0':effects['private_note_created'] and 'writes_fs' not in request.item['reference']['declared_effects'],
          'control_e137':'solve_earliest_start' not in class_methods}[item.identity]
  rows.append({'identity':item.identity,'package_digest':request.body_sha256,'expected_decision':item.expected_decision,
   'criterion_id':item.criterion_id,'input':value,'actual_output':output,'actual_exit':result.exit_code,
   'output_schema_valid':schema_valid,'observed_effects':effects,'label_verified':proven,
   'timed_out':result.timed_out,'truncated':result.truncated,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
record={'set_sha256':suite.sha256,'model_calls':0,'approvals':0,'sandbox':'existing Bubblewrap no-network/no-home resource-limited command; effect observation is inside private /work only',
 'rows':rows,'all_labels_verified':all(r['label_verified'] and r['actual_exit']==0 and not r['timed_out'] and not r['truncated'] for r in rows)}
path=Path(__file__).parent/'control-label-verification.json'
if path.exists():raise ValueError('Use a new evidence path')
path.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'controls':len(rows),'all_labels_verified':record['all_labels_verified']}))
