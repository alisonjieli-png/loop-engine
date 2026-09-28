"""Add a distinguishing single-ready-node Kahn control; keep the prior case file."""
import json
from pathlib import Path
here=Path(__file__).resolve().parent
record=json.loads((here/'root-cases-before-source-v1.json').read_text())
package=next(p for p in record['packages'] if p['identity']=='select_context_blocks')
a={'id':'a','cost':1,'priority':0,'required':False,'depends_on':[],'text':'a text'}
b={'id':'b','cost':1,'priority':0,'required':True,'depends_on':['a'],'text':'b text'}
z={'id':'z','cost':1,'priority':10,'required':False,'depends_on':[],'text':'z text'}
package['cases'].append({'name':'newly_ready_b_precedes_previously_ready_z','input':{'budget':3,'blocks':[z,b,a]},
 'expected':{'selected':['a','b','z'],'omitted':[],'total_cost':3,'remaining':0,'blocks':[a,b,z]},
 'expected_exit':0,'input_schema_valid':True,
 'rationale':'Single-node lexical Kahn gives a,b,z; draining the initial ready batch incorrectly gives a,z,b.'})
with (here/'root-cases-before-source-v2.json').open('x') as stream:
 json.dump(record,stream,indent=2);stream.write('\n')
