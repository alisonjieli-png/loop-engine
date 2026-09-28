"""Additional contract-derived cases. Candidate tools remained unread."""
import copy,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
record=json.loads((HERE/'data-first-three-before-source-v1.json').read_text());packages=record['packages']
ERROR={'ok':False,'error':{'code':'invalid_input'}}
def good(name,value,result,why):return {'name':name,'input':value,'expected':{'ok':True,'result':result},'expected_exit':0,'input_schema_valid':True,'rationale':why}
def bad(name,value,why,schema_valid=None):
 r={'name':name,'input':value,'expected':ERROR,'expected_exit':2,'rationale':why}
 if schema_valid is not None:r['input_schema_valid']=schema_valid
 return r
def raw_controls(seed):
 text=json.dumps(seed,separators=(',',':'));key=next(iter(seed))
 return [{'name':name,'raw_hex':raw.hex(),'expected':ERROR,'expected_exit':2,'rationale':why} for name,raw,why in [
 ('duplicate_same_value_key',(text[:-1]+','+json.dumps(key)+':'+json.dumps(seed[key])+'}').encode(),'Reject repeated JSON names.'),
 ('trailing_bytes',(text+'x').encode(),'Consume exactly one full document.'),
 ('invalid_utf8',b'\xff'+text.encode(),'Return a typed encoding refusal.'),
 ('wire_byte_limit',(' '*(262145-len(text))+text).encode(),'Leading whitespace counts toward input bytes.')]]
identity='audit_half_open_interval_overlaps'
def interval(name,a,b):return {'id':name,'start':a,'end':b}
def pair(a,b,start,end):return {'left_id':a,'right_id':b,'start':start,'end':end}
seed={'intervals':[interval('a',0,2),interval('b',2,4),interval('c',1,3),interval('empty',1,1),interval('d',0,4)]}
result={'overlap_count':5,'overlaps':[pair('a','c',1,2),pair('a','d',0,2),pair('b','c',2,3),pair('b','d',2,4),pair('c','d',1,3)],'empty_ids':['empty'],'max_concurrency':3,'union_length':4}
rows=[good('half_open_empty_nested_and_adjacent',seed,result,'Adjacent intervals do not overlap; empty intervals never contribute concurrency or coverage.')]
value=copy.deepcopy(seed)
for item in value['intervals']:item['start']+=7;item['end']+=7
translated=copy.deepcopy(result)
for item in translated['overlaps']:item['start']+=7;item['end']+=7
rows.append(good('coordinate_translation',value,translated,'Translation preserves covered length and concurrency.'))
value={'intervals':[interval('a',0,2),interval('b',0,2)]};rows.append(good('identical_nonempty_intervals',value,{'overlap_count':1,'overlaps':[pair('a','b',0,2)],'empty_ids':[],'max_concurrency':2,'union_length':2},'Equal extents are not duplicate IDs and count twice in concurrency.'))
value={'intervals':[interval('empty',2.0,2)]};rows.append(good('integral_empty_coordinates',value,{'overlap_count':0,'overlaps':[],'empty_ids':['empty'],'max_concurrency':0,'union_length':0},'Integral decimal coordinates agree and empty intervals remain harmless.'))
rows.append(bad('reversed_interval',{'intervals':[interval('a',3,2)]},'A negative extent is invalid.',True))
rows.append(bad('duplicate_interval_id',{'intervals':[interval('a',0,1),interval('a',2,3)]},'Distinct extents cannot reuse one identity.',True))
packages.append({'identity':identity,'cases':rows+raw_controls(seed)})
identity='apply_flat_record_changes'
def present(value):return {'present':True,'value':value}
ABSENT={'present':False}
def change(key,before,after):return {'key':key,'before':before,'after':after}
seed={'record':{'x':1,'n':None},'changes':[change('x',present(1),present(2)),change('n',present(None),ABSENT),change('y',ABSENT,present(False))]}
rows=[good('replace_remove_add_typed_value',seed,{'applied':True,'record':{'x':2,'y':False},'changed_count':3,'conflicts':[]},'Absent and null states are distinct; a false value is still present.')]
value={'record':{'x':1,'n':None},'changes':[change('x',present(1),present(2)),change('n',ABSENT,ABSENT)]};rows.append(good('late_conflict_cancels_every_change',value,{'applied':False,'record':{'x':1,'n':None},'changed_count':0,'conflicts':[{'key':'n','expected':ABSENT,'actual':present(None)}]},'A later precondition failure cannot leave the earlier x edit applied.'))
value={'record':{'x':True},'changes':[change('x',present(1),present(2))]};rows.append(good('boolean_does_not_match_integer',value,{'applied':False,'record':{'x':True},'changed_count':0,'conflicts':[{'key':'x','expected':present(1),'actual':present(True)}]},'Python boolean/integer equality must not leak into typed record matching.'))
value={'record':{'x':1},'changes':[change('x',present(1.0),present(1)),change('missing',ABSENT,ABSENT)]};rows.append(good('noops_are_not_changes',value,{'applied':True,'record':{'x':1},'changed_count':0,'conflicts':[]},'Count actual state/value differences, not requested operations.'))
value=copy.deepcopy(seed);value['changes'].append(change('x',present(2),present(3)));rows.append(bad('repeated_change_key',value,'These are simultaneous unique-key changes, not a sequential patch program.',True))
value={'record':{f'k{i}':i for i in range(32)},'changes':[change('new',ABSENT,present(1))]};rows.append(bad('result_property_bound',value,'Successful result must retain the contract property bound.',True))
packages.append({'identity':identity,'cases':rows+raw_controls(seed)})
identity='reconcile_keyed_tables'
seed={'key':'id','left':[{'id':1,'x':None},{'id':'1','x':True},{'id':'left'}],'right':[{'id':'1','x':1},{'id':1.0},{'id':'right'}]}
result={'counts':{'left_rows':3,'right_rows':3,'matched':2,'unchanged':0,'changed':2,'left_only':1,'right_only':1},'matches':[{'key':1,'left_index':0,'right_index':1,'changed_fields':['x']},{'key':'1','left_index':1,'right_index':0,'changed_fields':['x']}],'left_only':[{'key':'left','left_index':2}],'right_only':[{'key':'right','right_index':2}]}
rows=[good('typed_key_and_missing_value_reconciliation',seed,result,'String and integer keys differ; changed fields distinguish absent/null and true/1.')]
value={'key':'id','left':[{'id':1,'x':2.0}],'right':[{'id':1.0,'x':2}]};rows.append(good('integral_key_and_nonkey_values',value,{'counts':{'left_rows':1,'right_rows':1,'matched':1,'unchanged':1,'changed':0,'left_only':0,'right_only':0},'matches':[{'key':1,'left_index':0,'right_index':0,'changed_fields':[]}],'left_only':[],'right_only':[]},'Exactly integral numeric spellings do not create false differences.'))
rows.append(bad('duplicate_normalized_integer_key',{'key':'id','left':[{'id':1},{'id':1.0}],'right':[]},'One-to-one matching must reject keys that normalize to the same integer.',True))
for name,row in [('missing_key',{}),('null_key',{'id':None}),('boolean_key',{'id':True}),('empty_string_key',{'id':''})]:
 rows.append(bad(name,{'key':'id','left':[row],'right':[]},'This key shape is structurally a flat value but not a valid key under the semantic contract.',True))
packages.append({'identity':identity,'cases':rows+raw_controls(seed)})
for package in packages:package['sandbox_output_bytes']=524289
record['design_basis']='Frozen six data schemas and explicit CSV clarification; implementation contents unread.'
with (HERE/'data-six-before-source-v2.json').open('x') as stream:json.dump(record,stream,indent=2);stream.write('\n')
print(sum(len(p['cases']) for p in packages))
