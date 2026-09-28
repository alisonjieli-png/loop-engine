"""Execute only authored systems candidates inside a minimal no-network bwrap sandbox."""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import sys
import tempfile

CANONICAL=Path('/home/username/.le-codex-build/integration')
sys.path.insert(0,str(CANONICAL/'src'))
from loop_engine.core.library_ingestion.processes import run_command
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]
RUNNER='''import resource,runpy,sys
resource.setrlimit(resource.RLIMIT_CPU,(2,2))
resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
resource.setrlimit(resource.RLIMIT_NOFILE,(32,32))
resource.setrlimit(resource.RLIMIT_FSIZE,(131073,131073))
sys.argv=["/package/tool.py"]
with open("/input.json","r",encoding="utf-8") as stream:
    sys.stdin=stream
    runpy.run_path("/package/tool.py",run_name="__main__")
'''
ALLOWED={'json','sys','decimal','hashlib','unicodedata'}
MUTANTS={
 'compare_file_inventories':('sorted(right - left)','sorted(left - right)'),
 'resolve_selected_dependency_closure':('pending.extend(graph[current])','pending.extend(())'),
 'assign_digest_shards':('int(digest, 16) % count','int(digest[:8], 16) % count'),
 'validate_event_precedence':('left >= right','left > right'),
 'apply_nonoverlapping_text_edits':('pieces.extend((source[cursor:start], replacement))','pieces.extend((source[cursor:end], replacement))'),
 'detect_portable_path_collisions':('child.startswith(parent + "/")','child.startswith(parent) and child != parent'),
}

def command(script,source,runner):
 return ('/usr/bin/bwrap','--unshare-all','--die-with-parent','--new-session','--clearenv',
         '--ro-bind','/usr','/usr','--symlink','usr/bin','/bin','--symlink','usr/lib','/lib',
         '--symlink','usr/lib64','/lib64','--dev','/dev','--proc','/proc','--tmpfs','/tmp','--dir','/work',
         '--ro-bind',str(script),'/package/tool.py','--ro-bind',str(source),'/input.json',
         '--ro-bind',str(runner),'/runner.py','--chdir','/work','--setenv','HOME','/tmp',
         '--setenv','PATH','/usr/bin:/bin','--','/usr/bin/python3','-I','-S','-B','/runner.py')

def execute(script,case,folder,validator):
 source=folder/'input.json';runner=folder/'runner.py'
 data=(case['raw_input'].encode('utf-8') if 'raw_input' in case else
       bytes.fromhex(case['input_hex']) if 'input_hex' in case else
       json.dumps(case['input'],ensure_ascii=False,allow_nan=False).encode('utf-8'))
 source.write_bytes(data);runner.write_text(RUNNER)
 result=run_command(command(script.resolve(),source,runner),timeout_seconds=4,
                    maximum_output_bytes=131073,environment={'PATH':'/usr/bin:/bin'})
 try:observed=json.loads(result.stdout)
 except (ValueError,UnicodeError):observed=None
 length=len(result.stdout) if isinstance(result.stdout,bytes) else len(result.stdout.encode('utf-8'))
 errors=list(validator.iter_errors(observed)) if observed is not None else ['invalid JSON']
 return {'name':case['name'],'expected_exit':case['expected_exit'],'exit_code':result.exit_code,
         'matches_expected':observed==case['expected'],'schema_valid':not errors,'stdout_utf8_bytes':length,
         'timed_out':result.timed_out,'truncated':result.truncated,'stderr_empty':not result.stderr_tail,
         'passed':result.exit_code==case['expected_exit'] and observed==case['expected'] and not errors
                  and not result.timed_out and not result.truncated and not result.stderr_tail and length<=131072,
         **({'observed':observed,'expected':case['expected']} if observed!=case['expected'] else {})}

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--report',type=Path,required=True);parser.add_argument('--mutants',action='store_true');args=parser.parse_args()
 if args.report.exists():raise ValueError('Use a new report path')
 metadata=json.loads((ROOT/'authors/systems-metadata.json').read_text());results=[];mutants=[]
 with tempfile.TemporaryDirectory(prefix='baltor-systems-qa-',dir='/home/username/.le-ci-tmp') as tmp:
  folder=Path(tmp)
  for identity in metadata:
   package=ROOT/identity;script=package/'tools'/f'{identity}.py';source=script.read_text()
   modules=set()
   for node in ast.walk(ast.parse(source)):
    if isinstance(node,ast.Import):modules.update(x.name.split('.')[0] for x in node.names)
    elif isinstance(node,ast.ImportFrom):modules.add(node.module.split('.')[0])
   if not modules<=ALLOWED:raise ValueError('Unexpected imports '+identity)
   schemas=[json.loads((package/'contracts'/f'{kind}.schema.json').read_text()) for kind in ('input','output')]
   for schema in schemas:Draft202012Validator.check_schema(schema)
   cases=json.loads((package/'verification/cases.json').read_text());validator=Draft202012Validator(schemas[1])
   checks=[execute(script,case,folder,validator) for case in cases]
   results.append({'identity':identity,'script_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),
                   'file_count':sum(path.is_file() for path in package.rglob('*')),'checks':checks,'passed':all(c['passed'] for c in checks)})
   if args.mutants:
    old,new=MUTANTS[identity]
    if old not in source:raise ValueError('Missing mutant anchor '+identity)
    mutant=folder/'mutant.py';mutant.write_text(source.replace(old,new,1))
    failures=[c['name'] for c in cases if not execute(mutant,c,folder,validator)['passed']]
    mutants.append({'identity':identity,'mutation':old+' -> '+new,'detected':bool(failures),'failing_cases':failures})
  if args.mutants:
   identity='assign_digest_shards';script=ROOT/identity/'tools'/f'{identity}.py';source=script.read_text()
   mutant=folder/'unicode-mutant.py';mutant.write_text(source.replace('len(encoded) <= OUTPUT_BYTES','len(encoded.decode("utf-8")) <= OUTPUT_BYTES'))
   case=next(c for c in json.loads((ROOT/identity/'verification/cases.json').read_text()) if c['name']=='unicode_output_byte_limit')
   answer=execute(mutant,case,folder,Draft202012Validator(json.loads((ROOT/identity/'contracts/output.schema.json').read_text())))
   mutants.append({'identity':identity,'mutation':'Unicode character count replaces UTF-8 output byte count','detected':not answer['passed'],'failing_cases':[case['name']] if not answer['passed'] else []})
 report={'record_type':'original_systems_sandbox_qa/v1','canonical_revision':'231f51bb1facab517fbe915b08ea9ac85f913347',
         'sandbox':'bwrap unshare-all; clearenv; read-only /usr and exact tool/input/runner mounts; no network; no task workspace or credentials mounted;2CPU seconds/256MiB/4wall seconds',
         'packages':results,'mutants':mutants,'passed':all(r['passed'] for r in results) and all(m['detected'] for m in mutants),
         'approval_count':0,'native_client_qualification':False,'external_provider_calls':0}
 args.report.parent.mkdir(parents=True,exist_ok=True)
 with args.report.open('x') as stream:json.dump(report,stream,indent=2,ensure_ascii=False);stream.write('\n')
 print(json.dumps({'packages':len(results),'checks':sum(len(r['checks']) for r in results),'passed':report['passed'],'failures':[(r['identity'],c['name']) for r in results for c in r['checks'] if not c['passed']],'mutants':len(mutants),'undetected':[m['identity'] for m in mutants if not m['detected']]}))
 return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
