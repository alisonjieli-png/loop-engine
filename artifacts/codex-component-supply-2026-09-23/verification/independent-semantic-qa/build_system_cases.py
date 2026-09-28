"""Independent expected results from six contracts, before implementations exist."""
import copy,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
packages=[]
def sha(text):return hashlib.sha256(text.encode()).hexdigest()
def request(identity,**fields):return {'record_type':identity+'_request/v1',**fields}
def result(identity,**fields):return {'record_type':identity+'_result/v1',**fields}
def good(name,value,expected,why):return {'name':name,'input':value,'expected':expected,'expected_exit':0,'input_schema_valid':True,'rationale':why}
def bad(name,value,why,code='invalid_input',schema_valid=None):
 row={'name':name,'input':value,'expected':{'error':code},'expected_exit':2,'rationale':why}
 if schema_valid is not None:row['input_schema_valid']=schema_valid
 return row
def raw(name,text,why,schema_valid=None):
 row={'name':name,'raw_hex':text.hex() if isinstance(text,bytes) else text.encode().hex(),'expected':{'error':'invalid_input'},'expected_exit':2,'rationale':why}
 if schema_valid is not None:row['input_schema_valid']=schema_valid
 return row
def raw_controls(seed):
 text=json.dumps(seed,separators=(',',':'))
 return [raw('duplicate_record_type',text[:-1]+',"record_type":'+json.dumps(seed['record_type'])+'}','Duplicate keys cannot be silently overwritten.'),
         raw('trailing_bytes',text+'x','Consume one complete document.'),
         raw('invalid_utf8',b'\xff'+text.encode(),'Invalid encoding must give a typed refusal.'),
         raw('wire_byte_ceiling',' '*(65537-len(text))+text,'Input byte limit includes leading whitespace.',True)]
identity='compare_file_inventories'
def entry(path,digest='a'*64,size=1,executable=False):return {'path':path,'digest':digest,'size_bytes':size,'executable':executable}
seed=request(identity,before=[entry('old'),entry('exec'),entry('same'),entry('size'),entry('digest')],after=[entry('new'),entry('same'),entry('exec',executable=True),entry('size',size=2),entry('digest',digest='b'*64)])
expected=result(identity,added=['new'],removed=['old'],unchanged=['same'],changed=[{'path':'digest','fields':['digest']},{'path':'exec','fields':['executable']},{'path':'size','fields':['size_bytes']}])
rows=[good('all_metadata_axes_and_no_rename_guess',seed,expected,'Identical bytes at old/new paths are still removal/addition; exact metadata changes are distinguished.')]
value=copy.deepcopy(seed);value['before'].reverse();value['after'].reverse();rows.append(good('declaration_permutation',value,expected,'Inventory order is not semantic.'))
value=request(identity,before=[entry('a',size=1.0)],after=[entry('a',size=1)]);rows.append(good('integral_size',value,result(identity,added=[],removed=[],unchanged=['a'],changed=[]),'Mathematically integral JSON sizes agree.'))
value=request(identity,before=[entry('a'),entry('a')],after=[]);rows.append(bad('duplicate_path',value,'An inventory cannot contain two records for the same path.',schema_valid=True))
value=request(identity,before=[entry('../a')],after=[]);rows.append(bad('parent_path',value,'A reference path must be normalized and relative.',schema_valid=False))
packages.append({'identity':identity,'cases':rows+raw_controls(seed)})
identity='resolve_selected_dependency_closure'
def package(name,requires=()):return {'id':name,'requires':list(requires)}
seed=request(identity,roots=['a'],packages=[package('a',['c','b']),package('b',['d']),package('c',['d']),package('d'),package('z',['absent'])])
rows=[good('diamond_and_unreachable_missing',seed,result(identity,selected=['a','b','c','d'],cyclic_components=[]),'Shared dependencies appear once; unreachable missing references do not affect selected closure.')]
value=request(identity,roots=['a'],packages=[package('a',['b']),package('b',['a']),package('z',['z'])]);rows.append(good('reachable_cycle_reported_not_unreachable_cycle',value,result(identity,selected=['a','b'],cyclic_components=[['a','b']]),'The method reports selected strongly connected components; it does not require an acyclic world.'))
value=request(identity,roots=['a'],packages=[package('a',['a'])]);rows.append(good('selected_self_loop',value,result(identity,selected=['a'],cyclic_components=[['a']]),'A single vertex with a self-loop is cyclic.'))
value=request(identity,roots=[],packages=[package('z',['absent'])]);rows.append(good('empty_roots',value,result(identity,selected=[],cyclic_components=[]),'Do not include unrelated declared packages.'))
value=request(identity,roots=['a'],packages=[package('a',['missing'])]);rows.append(bad('reachable_missing',value,'Selected closure cannot invent an unavailable dependency.','missing_dependency',True))
value=request(identity,roots=['absent'],packages=[]);rows.append(bad('missing_root',value,'An unknown root is a missing selected dependency.','missing_dependency',True))
value=request(identity,roots=['a'],packages=[package('a'),package('a',['b'])]);rows.append(bad('ambiguous_duplicate_package',value,'Duplicate package IDs cannot select one declaration by accident.',schema_valid=True))
packages.append({'identity':identity,'cases':rows+raw_controls(seed)})
identity='assign_digest_shards'
def shard_result(ids,n):
 assignments=[]
 for value in sorted(ids):
  digest=hashlib.sha256(value.encode()).digest(); remainder=0
  for byte in digest:remainder=(remainder*256+byte)%n
  assignments.append({'id':value,'sha256':digest.hex(),'shard':remainder})
 return result(identity,shard_count=n,assignments=assignments)
seed=request(identity,ids=['z','é','e\u0301','alpha'],shard_count=7)
rows=[good('whole_digest_modulo_and_distinct_unicode',seed,shard_result(seed['ids'],7),'Oracle accumulates digest bytes modulo seven, without int(hex) or Unicode normalization.')]
value=copy.deepcopy(seed);value['ids'].reverse();rows.append(good('input_permutation',value,shard_result(seed['ids'],7),'Assignments have stable lexical ID order.'))
value=request(identity,ids=['a','b'],shard_count=1.0);rows.append(good('one_integral_shard',value,shard_result(value['ids'],1),'All IDs map to shard zero; 1.0 is a valid schema integer.'))
value=request(identity,ids=[],shard_count=4096);rows.append(good('empty_ids_max_shards',value,shard_result([],4096),'No fabricated assignments for an empty set.'))
rows.append(bad('boolean_shard_count',request(identity,ids=['a'],shard_count=True),'Boolean is not an integer.',schema_valid=False))
rows.append(bad('duplicate_id',request(identity,ids=['a','a'],shard_count=7),'Duplicate identifiers are not silently deduplicated.',schema_valid=False))
rows.append(raw('near_integer_shard_count',json.dumps(request(identity,ids=['a'],shard_count=1)).replace('"shard_count": 1','"shard_count": 1.00000000000000001'),'Do not round a noninteger wire number into the valid range.',False))
rows.append(raw('lone_surrogate_id','{"record_type":"assign_digest_shards_request/v1","ids":["\\ud800"],"shard_count":1}','Unpaired surrogate must be a typed refusal before UTF-8 hashing.'))
packages.append({'identity':identity,'cases':rows+raw_controls(seed)})
identity='validate_event_precedence'
constraints=[{'before':'a','after':'b'},{'before':'a','after':'c'},{'before':'b','after':'d'},{'before':'c','after':'d'}]
seed=request(identity,events=['a','c','b','d'],constraints=constraints)
rows=[good('legal_diamond_permutation',seed,result(identity,satisfied=True,violations=[]),'Independent siblings need no artificial total order.')]
value=request(identity,events=['a','b','c','d'],constraints=constraints);rows.append(good('other_legal_diamond_order',value,result(identity,satisfied=True,violations=[]),'Both topological sibling orders are legal.'))
value=request(identity,events=['a','b'],constraints=[{'before':'b','after':'a'}]);rows.append(good('backward_event',value,result(identity,satisfied=False,violations=[{'before':'b','after':'a','before_index':1,'after_index':0,'reason':'not_before'}]),'Existing events can violate the requested order.'))
value=request(identity,events=['a'],constraints=[{'before':'absent','after':'a'}]);rows.append(good('missing_event_reported',value,result(identity,satisfied=False,violations=[{'before':'absent','after':'a','before_index':None,'after_index':0,'reason':'missing_event'}]),'Missing event is a reported violation, not fabricated index zero.'))
value=request(identity,events=['a'],constraints=[{'before':'a','after':'a'}]);rows.append(good('self_precedence_unsatisfied',value,result(identity,satisfied=False,violations=[{'before':'a','after':'a','before_index':0,'after_index':0,'reason':'not_before'}]),'Strict precedence cannot include equality.'))
rows.append(bad('duplicate_event',request(identity,events=['a','a'],constraints=[]),'Repeated IDs make a single event position ambiguous.',schema_valid=False))
packages.append({'identity':identity,'cases':rows+raw_controls(seed)})
identity='apply_nonoverlapping_text_edits'
def edit_result(original,text,count):return result(identity,text=text,source_sha256=sha(original),result_sha256=sha(text),edits_applied=count)
seed=request(identity,text='a😀bc',edits=[{'start':3,'end':4,'replacement':'ZZ'},{'start':2,'end':2,'replacement':'Y'},{'start':1,'end':2,'replacement':'X'}],expected_sha256=sha('a😀bc'))
rows=[good('original_codepoint_coordinates_and_adjacent_insertion',seed,edit_result(seed['text'],'aXYbZZ',3),'Offsets count Unicode code points against the original text; insertion at a prior range end is permitted.')]
value=copy.deepcopy(seed);value['edits'].reverse();rows.append(good('edit_declaration_permutation',value,edit_result(seed['text'],'aXYbZZ',3),'Sort by original offset without changing meaning.'))
value=request(identity,text='abc',edits=[{'start':1.0,'end':2.0,'replacement':''}]);rows.append(good('integral_indices_delete',value,edit_result('abc','ac',1),'Integral JSON indices agree with the schema.'))
value=request(identity,text='',edits=[{'start':0,'end':0,'replacement':'x'}]);rows.append(good('empty_document_insertion',value,edit_result('','x',1),'The original end position supports insertion.'))
value=copy.deepcopy(seed);value['expected_sha256']='0'*64;rows.append(bad('stale_source_digest',value,'Never apply edits to a changed source.','source_digest_mismatch',True))
value=request(identity,text='abc',edits=[{'start':1,'end':3,'replacement':'x'},{'start':2,'end':2,'replacement':'y'}]);rows.append(bad('insertion_inside_range',value,'Insertion inside a replaced range is an overlap.','overlapping_edits',True))
value=request(identity,text='abc',edits=[{'start':1,'end':1,'replacement':'x'},{'start':1,'end':1,'replacement':'y'}]);rows.append(bad('same_insertion_position',value,'Same-start insertions are ambiguous by declared policy.','overlapping_edits',True))
value=request(identity,text='abc',edits=[{'start':0,'end':4,'replacement':'x'}]);rows.append(bad('beyond_original_end',value,'A structurally valid bound can exceed this particular source.',schema_valid=True))
packages.append({'identity':identity,'cases':rows+raw_controls(seed)})
identity='detect_portable_path_collisions'
def collision_result(free,collisions=(),parents=()):return result(identity,platform_model='unicode_nfc_casefold/v1',unicode_version='16.0.0',collision_free=free,collisions=list(collisions),parent_file_collisions=list(parents))
seed=request(identity,paths=['Straße','STRASSE','é','e\u0301'],platform_model='unicode_nfc_casefold/v1',expected_unicode_version='16.0.0')
rows=[good('full_casefold_and_canonical_unicode',seed,collision_result(False,[{'normalized_path':'strasse','indices':[0,1],'paths':['Straße','STRASSE']},{'normalized_path':'é','indices':[2,3],'paths':['é','e\u0301']}]),'ASCII lowercase alone misses both length-changing casefold and NFC equivalence.')]
value=request(identity,paths=['A','a/x','ab/y'],platform_model='unicode_nfc_casefold/v1');rows.append(good('path_component_parent_not_text_prefix',value,collision_result(False,parents=[{'parent':'a','child':'a/x','parent_indices':[0],'child_indices':[1]}]),'a conflicts with a/x, but not with ab/y.'))
value=request(identity,paths=['x','x'],platform_model='unicode_nfc_casefold/v1');rows.append(good('exact_duplicate_preserves_indices',value,collision_result(False,[{'normalized_path':'x','indices':[0,1],'paths':['x','x']}]),'Repeated input paths remain a detected duplicate group.'))
value=request(identity,paths=['aux.txt','ab/y','a'],platform_model='unicode_nfc_casefold/v1');rows.append(good('declared_model_is_not_windows_security_validator',value,collision_result(True),'No normalization collision exists; reserved-name security is explicitly outside this abstract model.'))
value=copy.deepcopy(seed);value['expected_unicode_version']='0.0.0';rows.append(bad('stale_unicode_model',value,'Reject a requested Unicode table mismatch.','unicode_version_mismatch',True))
value=copy.deepcopy(seed);value['paths']=['a/../x'];rows.append(bad('parent_traversal',value,'Normalized lexical paths cannot contain dot-dot segments.',schema_valid=False))
packages.append({'identity':identity,'cases':rows+raw_controls(seed)})
with (HERE/'systems-cases-before-source-v1.json').open('x') as stream:
 json.dump({'record_type':'independent_component_cases/v1','design_basis':'Author interface messages and frozen schemas, before implementation files exist.','packages':packages},stream,indent=2,ensure_ascii=True);stream.write('\n')
print(sum(len(p['cases']) for p in packages))
