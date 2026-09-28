"""Execute only frozen candidate bytes through the prequalified minimal bwrap runner."""
from pathlib import Path
import argparse
from collections import Counter
import hashlib
import json
import sys

sys.dont_write_bytecode = True
TRUSTED_QA = Path('/home/username/loop-engine/artifacts/codex-component-supply-2026-09-23/verification/independent-semantic-qa')
sys.path.insert(0,str(TRUSTED_QA))
from sandbox import bindings, digest, run_bytes, strict_loads, TRUSTED_SOURCE
from verify_cases import refuse_external_references
from jsonschema import Draft202012Validator


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--cases',type=Path,required=True);parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    if args.report.exists():raise ValueError('preserve_prior_report')
    root=Path(__file__).resolve().parents[1]/'audit_wikilink_resolution'
    before=bindings(root);script=(root/'tools/audit_wikilink_resolution.py').read_bytes()
    input_schema=strict_loads((root/'contracts/input.schema.json').read_bytes())
    output_schema=strict_loads((root/'contracts/output.schema.json').read_bytes())
    for schema in (input_schema,output_schema):
        refuse_external_references(schema);Draft202012Validator.check_schema(schema)
    iv,ov=Draft202012Validator(input_schema),Draft202012Validator(output_schema)
    cases=strict_loads(args.cases.read_bytes())['cases'];observations=[]
    for case in cases:
        raw=bytes.fromhex(case['raw_hex']) if 'raw_hex' in case else json.dumps(case['input'],ensure_ascii=False,separators=(',',':')).encode()
        got=run_bytes(script,raw,output_limit_bytes=131073)
        output=got['output'];checks={'exit':got['exit_code']==case['expected_exit'],
            'bounded':not got['timed_out'] and not got['launcher_truncated'] and got['stdout_bytes']<=131072,
            'output_schema':ov.is_valid(output),'no_stderr':got['stderr_bytes']==0}
        if case['expected_error']:
            checks['exact_refusal']=output=={'error':case['expected_error']}
        else:
            links=output.get('links',[]) if isinstance(output,dict) else []
            checks['expected_link_count']=len(links)==len(case['expected_links'])
            checks['expected_link_fields']=checks['expected_link_count'] and all(all(actual.get(k)==v for k,v in expected.items()) for actual,expected in zip(links,case['expected_links']))
            checks['source_binding']=isinstance(output,dict) and output.get('source_path')==case['input']['source_path'] and output.get('source_sha256')==digest(case['input']['text'].encode()) and output.get('complete_markdown_audit') is False
            counts=Counter(x.get('status') for x in links)
            checks['counts']=isinstance(output,dict) and output.get('counts')=={key:counts[key] for key in ('resolved','missing','ambiguous','unsupported')}
            span_checks=[];text=case['input']['text'];last_end=-1
            for actual in links:
                start,end=actual.get('start'),actual.get('end')
                valid=type(start) is int and type(end) is int and 0<=start<end<=len(text) and start>=last_end
                if valid:
                    valid=actual.get('line')==text[:start].count('\n')+1 and actual.get('column')==start-text.rfind('\n',0,start)
                    if actual.get('status')!='unsupported':valid=valid and text[start:end].startswith('[[') and text[start:end].endswith(']]') and actual.get('raw')==text[start+2:end-2]
                    last_end=end
                span_checks.append(valid)
            checks['original_codepoint_spans']=all(span_checks)
        try:input_valid=iv.is_valid(strict_loads(raw))
        except (ValueError,UnicodeError):input_valid=None
        observations.append({'name':case['name'],'passed':all(checks.values()),'checks':checks,'input_schema_valid':input_valid,'observation':got})
    after=bindings(root)
    report={'record_type':'independent_wikilink_execution/v1','case_sha256':digest(args.cases.read_bytes()),'payload_binding':before,'unchanged_tree':before==after,
        'trusted_sandbox_source_sha256':digest((TRUSTED_QA/'sandbox.py').read_bytes()),'process_owner_sha256':digest((TRUSTED_SOURCE/'src/loop_engine/core/library_ingestion/processes.py').read_bytes()),
        'sandbox':{'network':'unshared','home':'absent','cpu_seconds':2,'address_space_bytes':268435456,'wall_seconds':4,'output_capture_bytes':131073},
        'cases':observations,'passed':sum(r['passed'] for r in observations),'total':len(observations),'model_calls':0,'approval':'not_performed'}
    with args.report.open('x') as stream:json.dump(report,stream,indent=2,ensure_ascii=True);stream.write('\n')
    print(json.dumps({'cases':len(observations),'passed':report['passed'],'unchanged_tree':before==after,'failures':[r['name'] for r in observations if not r['passed']]}))


if __name__=='__main__':main()
