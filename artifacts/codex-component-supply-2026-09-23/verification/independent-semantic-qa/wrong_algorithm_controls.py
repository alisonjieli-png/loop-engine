"""Independent wrong methods, written without reading the candidate implementations."""
import json
from pathlib import Path
from sandbox import run_bytes
from verify_cases import semantic_json_equal

HERE=Path(__file__).resolve().parent
CASES=json.loads((HERE/'root-cases-before-source-v2.json').read_text())
WRONG_SIGN=b'''import json,sys,math
from fractions import Fraction
v=json.load(sys.stdin); w=l=t=m=0
for p in v["pairs"]:
 if p["a"] is None or p["b"] is None: m+=1; continue
 a,b=Fraction(p["a"]),Fraction(p["b"])
 if a==b: t+=1
 elif (b>a)==(v["direction"]=="higher"): w+=1
 else: l+=1
n=w+l+t
prob=min(Fraction(1),Fraction(2*sum(math.comb(n,i) for i in range(min(w,l)+1)),2**n)) if n else None
print(json.dumps({"wins":w,"losses":l,"ties":t,"missing":m,"evaluated":w+l+t,"p_two_sided":None if prob is None else {"numerator":str(prob.numerator),"denominator":str(prob.denominator)}}))
'''
WRONG_TOPOLOGY=b'''import json,sys
v=json.load(sys.stdin); held={b["id"]:b for b in v["blocks"]};done=[]
while len(done)<len(held):
 batch=sorted(name for name,b in held.items() if name not in done and set(b["depends_on"])<=set(done))
 if not batch: raise ValueError("cycle")
 done.extend(batch)
cost=sum(held[x]["cost"] for x in done)
print(json.dumps({"selected":done,"omitted":[],"total_cost":cost,"remaining":v["budget"]-cost,"blocks":[held[x] for x in done]}))
'''
rows=[]
for identity,name,source,wrong_probability in [
 ('paired_sign_test','ties_missing_and_exact_decimal',WRONG_SIGN,{'numerator':'5','denominator':'8'}),
 ('select_context_blocks','newly_ready_b_precedes_previously_ready_z',WRONG_TOPOLOGY,None)]:
 package=next(p for p in CASES['packages'] if p['identity']==identity)
 case=next(c for c in package['cases'] if c['name']==name)
 observed=run_bytes(source,json.dumps(case['input']).encode())
 deliberate=(observed['output'].get('p_two_sided')==wrong_probability if wrong_probability else observed['output'].get('selected')==['a','z','b']) if isinstance(observed['output'],dict) else False
 rows.append({'identity':identity,'case':name,'completed_wrong_algorithm':observed['exit_code']==0 and deliberate,
              'detected':not semantic_json_equal(observed['output'],case['expected']),'observation':observed})
record={'record_type':'independent_wrong_algorithm_controls/v1','rows':rows,
        'passed':all(r['completed_wrong_algorithm'] and r['detected'] for r in rows)}
with (HERE/'wrong-algorithm-controls-1.json').open('x') as stream:
 json.dump(record,stream,indent=2);stream.write('\n')
print({'passed':record['passed'],'controls':len(rows)})
