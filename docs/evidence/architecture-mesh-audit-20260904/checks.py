"""Save existing read-only architecture checks with explicit scope."""
import json
from pathlib import Path
from loop_engine_devtools.assurance import RepositoryAssuranceRequest,run_repository_assurance
from loop_engine.conformance_report import run_conformance

root=Path('/home/username/loop-engine')
out=Path('/tmp/loop-engine-architecture-audit.UBvdFH')
assurance=run_repository_assurance(RepositoryAssuranceRequest(repository_root=root,write_evidence=False))
(out/'assurance.json').write_text(json.dumps(assurance,indent=2,sort_keys=True,default=str)+'\n')
conformance=run_conformance()
(out/'conformance.json').write_text(json.dumps(conformance,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'assurance_verdict':assurance['verdict'],
  'assurance_findings':len(assurance['findings']),
  'assurance_warnings':len(assurance['warnings']),
  'assurance_files_indexed':assurance['evidence']['files_indexed'],
  'assurance_files_in_full_audit':assurance['evidence']['files_in_full_audit'],
  'api_shape_scan':{k:v for k,v in assurance['evidence']['parameter_boundary'].items() if k in ['files_scanned','callables_scanned','unapproved_by_rule','unapproved_violations']},
  'conformance_summary':{k:v for k,v in conformance.items() if k in ['all_passed','zero_tolerance_gates','files_scanned','passed']}
 },indent=2,sort_keys=True))
