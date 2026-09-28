"""Write typed schemas and explicit examples/counterexamples before implementations."""
import hashlib
import json
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
IDS=('inspect_python_symbol_dependencies','select_graph_context_neighborhood','plan_targeted_test_selection')
SCHEMA='https://json-schema.org/draft/2020-12/schema'

def obj(props,required=None):
 return {'type':'object','properties':props,'required':list(props) if required is None else required,'additionalProperties':False}
def arr(items,maximum,minimum=0,unique=False):
 return {'type':'array','items':items,'minItems':minimum,'maxItems':maximum,**({'uniqueItems':True} if unique else {})}
def string(maximum=128,minimum=1):return {'type':'string','minLength':minimum,'maxLength':maximum,'not':{'pattern':r'[\x00-\x1f\x7f]'}}
def integer(maximum,minimum=0):return {'type':'integer','minimum':minimum,'maximum':maximum}
def nullable(value):return {'anyOf':[value,{'type':'null'}]}
IDENT=string();SHA={'type':'string','minLength':64,'maxLength':64,'pattern':'^[0-9a-f]{64}$'}
PATH={'type':'string','minLength':4,'maxLength':256,'pattern':r'^(?!/)(?!.*(?:^|/)\.{1,2}(?:/|$))(?!.*//)[^\\\x00-\x1f\x7f]+\.py$','not':{'pattern':r'[\x00-\x1f\x7f]'}}
MODULE={'type':'string','minLength':1,'maxLength':128,'pattern':r'^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$'}
EDGE=obj({'source':IDENT,'target':IDENT,'kind':IDENT})
schemas={}
ast_id,graph_id,test_id=IDS
schemas[ast_id]=(
 obj({'record_type':{'const':ast_id+'_request/v1'},'syntax_profile':{'const':'python_ast_feature_3_10/v1'},
      'files':arr(obj({'path':PATH,'module':MODULE,'source':{'type':'string','maxLength':16384}}),16,1)}),
 obj({'record_type':{'const':ast_id+'_result/v1'},'syntax_profile':{'const':'python_ast_feature_3_10/v1'},'complete_runtime_dependency_graph':{'const':False},
      'files':arr(obj({'path':PATH,'module':MODULE,'source_sha256':SHA,'parse_status':{'enum':['parsed','syntax_error','analysis_limit']},'error_line':nullable(integer(16385,1))}),16),
      'symbols':arr(obj({'id':IDENT,'module':MODULE,'path':PATH,'name':string(16384),'lexical_name':string(16384),'kind':{'enum':['module','function','async_function','class']},'owner_id':nullable(IDENT),'line':integer(16385),'column_utf8':integer(65536),'end_line':nullable(integer(16385,1)),'end_column_utf8':nullable(integer(65536))}),2048),
      'imports':arr(obj({'module':MODULE,'path':PATH,'owner_id':IDENT,'line':integer(16385,1),'column_utf8':integer(65536),'evaluation_context':{'enum':['module','definition_time','function_body','class_body']},'requested_module':nullable(string(16384)),'imported_name':nullable(string(16384)),'asname':nullable(string(16384)),'level':integer(16384),'candidate_module_ids':arr(IDENT,16),'resolution':{'enum':['candidate','unresolved']}}),2048),
      'calls':arr(obj({'module':MODULE,'path':PATH,'owner_id':IDENT,'line':integer(16385,1),'column_utf8':integer(65536),'end_line':nullable(integer(16385,1)),'end_column_utf8':nullable(integer(65536)),'callee':nullable(string(16384)),'evaluation_context':{'enum':['module','definition_time','function_body','class_body']},'resolution':{'enum':['candidate','unresolved','dynamic']},'reason':{'enum':['name_definition_candidate','local_binding_may_shadow','ambiguous_or_rebound','name_not_indexed','attribute_requires_runtime','callee_expression_requires_runtime']},'same_module_definition_ids':arr(IDENT,2048),'certain':{'const':False}}),2048)}))
schemas[graph_id]=(
 obj({'record_type':{'const':graph_id+'_request/v1'},'nodes':arr(IDENT,512,unique=True),'edges':arr(EDGE,2048,unique=True),'seeds':arr(IDENT,32,1,True),'direction':{'enum':['outgoing','incoming','both']},'edge_types':arr(IDENT,32,unique=True),'node_budget':integer(256,1),'max_hops':integer(32)}),
 obj({'record_type':{'const':graph_id+'_result/v1'},'coverage':{'const':'bounded_neighborhood'},'selected':arr(obj({'id':IDENT,'distance':integer(32)}),256),'selected_edges':arr(EDGE,2048),'adjacent_omissions':arr(obj({'id':IDENT,'distance':integer(33,1),'reason':{'enum':['node_budget','hop_limit']}}),512),'not_selected_count':integer(512)}))
testrecord=obj({'id':IDENT,'depends_on':arr(IDENT,256,unique=True),'priority':integer(100),'estimated_ms':integer(3600000)})
schemas[test_id]=(
 obj({'record_type':{'const':test_id+'_request/v1'},'changed_symbols':arr(IDENT,128,unique=True),'tests':arr(testrecord,256),'max_tests':integer(128),'max_estimated_ms':integer(1000000000)}),
 obj({'record_type':{'const':test_id+'_result/v1'},'coverage_basis':{'const':'supplied_mapping_only'},'complete_test_safety':{'const':False},
      'selected_tests':arr(obj({'id':IDENT,'matched_symbols':arr(IDENT,128),'newly_covered_symbols':arr(IDENT,128),'priority':integer(100),'estimated_ms':integer(3600000)}),128),
      'not_selected_impacted_tests':arr(obj({'id':IDENT,'matched_symbols':arr(IDENT,128),'reason':{'enum':['count_budget','time_budget']}}),256),
      'unmapped_changed_symbols':arr(IDENT,128),'mapped_but_uncovered_symbols':arr(IDENT,128),'total_estimated_ms':integer(1000000000)}))

def root(identity):return BASE/'packages'/identity/'skills'/identity.replace('_','-')
def write(identity,path,value):
 p=root(identity)/path;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')

for identity,(ins,outs) in schemas.items():
 ins['$schema']=SCHEMA
 errors=['invalid_input','output_limit_exceeded']+(['fact_limit_exceeded'] if identity==ast_id else ['seed_budget_exceeded'] if identity==graph_id else [])
 out={'$schema':SCHEMA,'oneOf':[outs,obj({'error':{'enum':errors}})]}
 write(identity,'contracts/input.schema.json',ins);write(identity,'contracts/output.schema.json',out)

cases={identity:[] for identity in IDS}
def case(identity,name,request,expected,error=False):
 cases[identity].append({'name':name,'input':request,'expected':expected,'expected_exit':2 if error else 0})
def graph(nodes,edges,seeds,**kwargs):
 return {'record_type':graph_id+'_request/v1','nodes':nodes,'edges':[{'source':a,'target':b,'kind':k} for a,b,k in edges],'seeds':seeds,'direction':kwargs.get('direction','outgoing'),'edge_types':kwargs.get('edge_types',['call']),'node_budget':kwargs.get('node_budget',8),'max_hops':kwargs.get('max_hops',8)}
def gres(selected,edges=(),omissions=(),not_selected=0):
 return {'record_type':graph_id+'_result/v1','coverage':'bounded_neighborhood','selected':[{'id':n,'distance':d} for n,d in selected],'selected_edges':[{'source':a,'target':b,'kind':k} for a,b,k in edges],'adjacent_omissions':[{'id':n,'distance':d,'reason':why} for n,d,why in omissions],'not_selected_count':not_selected}
g=graph(['a','b','c','d'],[('a','c','call'),('a','b','call'),('b','d','call')],['a'],node_budget=2)
go=gres([('a',0),('b',1)],[('a','b','call')],[('c',1,'node_budget'),('d',2,'node_budget')],2)
case(graph_id,'lexical_partial_layer_reports_budget',g,go)
case(graph_id,'incoming_direction',graph(['a','b','c'],[('a','b','call'),('b','c','call')],['b'],direction='incoming'),gres([('b',0),('a',1)],[('a','b','call')],not_selected=1))
case(graph_id,'outgoing_direction',graph(['a','b','c'],[('a','b','call'),('b','c','call')],['b']),gres([('b',0),('c',1)],[('b','c','call')],not_selected=1))
case(graph_id,'both_direction',graph(['a','b','c'],[('a','b','call'),('b','c','call')],['b'],direction='both'),gres([('b',0),('a',1),('c',1)],[('a','b','call'),('b','c','call')]))
case(graph_id,'zero_hops_seeds_only',graph(['a','b'],[('a','b','call')],['a'],max_hops=0),gres([('a',0)],omissions=[('b',1,'hop_limit')],not_selected=1))
case(graph_id,'edge_type_filter_consistent',graph(['a','b','c'],[('a','b','call'),('a','c','import'),('b','a','import')],['a']),gres([('a',0),('b',1)],[('a','b','call')],not_selected=1))
case(graph_id,'empty_edge_type_selects_only_seeds',graph(['a','b'],[('a','b','call')],['a'],edge_types=[]),gres([('a',0)],not_selected=1))
case(graph_id,'all_seeds_mandatory',graph(['a','b'],[],['b','a'],node_budget=1),{'error':'seed_budget_exceeded'},True)
case(graph_id,'unknown_unreachable_endpoint_refuses',graph(['a'],[('x','y','call')],['a']),{'error':'invalid_input'},True)
case(graph_id,'unknown_seed_refuses',graph(['a'],[],['b']),{'error':'invalid_input'},True)
case(graph_id,'duplicate_edge_refuses',graph(['a','b'],[('a','b','call'),('a','b','call')],['a']),{'error':'invalid_input'},True)
case(graph_id,'cycle_and_self_loop',graph(['b','a'],[('b','a','call'),('a','b','call'),('a','a','call')],['a']),gres([('a',0),('b',1)],[('a','a','call'),('a','b','call'),('b','a','call')]))
case(graph_id,'integral_float_budget',graph(['a'],[],['a'],node_budget=1.0,max_hops=0.0),gres([('a',0)]))
case(graph_id,'boolean_budget_refuses',graph(['a'],[],['a'],node_budget=True),{'error':'invalid_input'},True)
case(graph_id,'input_permutation_does_not_reorder',graph(['d','c','b','a'],[('b','d','call'),('a','b','call'),('a','c','call')],['a'],node_budget=2),go)

def treq(changes,tests,**kwargs):
 return {'record_type':test_id+'_request/v1','changed_symbols':changes,'tests':[{'id':i,'depends_on':d,'priority':p,'estimated_ms':m} for i,d,p,m in tests],'max_tests':kwargs.get('max_tests',16),'max_estimated_ms':kwargs.get('max_estimated_ms',1000)}
def tres(selected=(),omitted=(),unmapped=(),uncovered=()):
 return {'record_type':test_id+'_result/v1','coverage_basis':'supplied_mapping_only','complete_test_safety':False,'selected_tests':[{'id':i,'matched_symbols':m,'newly_covered_symbols':n,'priority':p,'estimated_ms':t} for i,m,n,p,t in selected],'not_selected_impacted_tests':[{'id':i,'matched_symbols':m,'reason':r} for i,m,r in omitted],'unmapped_changed_symbols':list(unmapped),'mapped_but_uncovered_symbols':list(uncovered),'total_estimated_ms':sum(x[4] for x in selected)}
t=treq(['a','b','c','unknown'],[('ab',['a','b'],5,10),('a',['a'],99,1),('c',['c'],1,20)],max_tests=2)
to=tres([('ab',['a','b'],['a','b'],5,10),('c',['c'],['c'],1,20)],[('a',['a'],'count_budget')],['unknown'])
case(test_id,'new_coverage_beats_redundant_high_priority',t,to)
case(test_id,'fitting_alternative_survives_expensive_test',treq(['a','b'],[('costly',['a','b'],100,100),('cheap',['a'],1,2)],max_estimated_ms=2),tres([('cheap',['a'],['a'],1,2)],[('costly',['a','b'],'time_budget')],uncovered=['b']))
case(test_id,'zero_time_test_fits_zero_budget',treq(['a'],[('free',['a'],1,0)],max_estimated_ms=0),tres([('free',['a'],['a'],1,0)]))
case(test_id,'zero_test_limit_reports_count_budget',treq(['a','u'],[('t',['a'],1,5)],max_tests=0,max_estimated_ms=0),tres(omitted=[('t',['a'],'count_budget')],unmapped=['u'],uncovered=['a']))
case(test_id,'lexical_tie_break',treq(['a'],[('z',['a'],1,5),('b',['a'],1,5)],max_tests=1),tres([('b',['a'],['a'],1,5)],[('z',['a'],'count_budget')]))
case(test_id,'unaffected_tests_are_not_impacted',treq(['a'],[('other',['b'],100,1)]),tres(unmapped=['a']))
case(test_id,'empty_changes_select_nothing',treq([],[('t',['a'],1,1)]),tres())
case(test_id,'overlap_retained_after_full_mapping_coverage',treq(['a'],[('one',['a'],2,1),('two',['a'],1,1)]),tres([('one',['a'],['a'],2,1),('two',['a'],[],1,1)]))
case(test_id,'integral_float_estimates',treq(['a'],[('t',['a'],1.0,2.0)],max_tests=1.0),tres([('t',['a'],['a'],1,2)]))
case(test_id,'duplicate_test_id_refuses',treq(['a'],[('t',['a'],1,1),('t',['a'],2,2)]),{'error':'invalid_input'},True)
case(test_id,'duplicate_dependency_refuses',treq(['a'],[('t',['a','a'],1,1)]),{'error':'invalid_input'},True)
case(test_id,'boolean_estimate_refuses',treq(['a'],[('t',['a'],1,True)]),{'error':'invalid_input'},True)

def module_id(module):return 'py-module-'+hashlib.sha256(module.encode()).hexdigest()
def symbol_id(module,name,kind,line,col):return 'py-symbol-'+hashlib.sha256(f'{module}\0{name}\0{kind}\0{line}\0{col}'.encode()).hexdigest()
def areq(files):return {'record_type':ast_id+'_request/v1','syntax_profile':'python_ast_feature_3_10/v1','files':[{'path':p,'module':m,'source':s} for p,m,s in files]}
def afile(path,module,source,status='parsed',error=None):return {'path':path,'module':module,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'parse_status':status,'error_line':error}
def sym(module,path,name,kind='module',line=0,col=0,end_line=None,end_col=None,owner=None,lexical=None):
 lexical=lexical or name
 return {'id':module_id(module) if kind=='module' else symbol_id(module,lexical,kind,line,col),'module':module,'path':path,'name':name,'lexical_name':lexical,'kind':kind,'owner_id':owner,'line':line,'column_utf8':col,'end_line':end_line,'end_column_utf8':end_col}
def call(module,path,line,col,end,callee,owner=None,context='module',resolution='unresolved',reason='name_not_indexed',definitions=()):
 return {'module':module,'path':path,'owner_id':owner or module_id(module),'line':line,'column_utf8':col,'end_line':line,'end_column_utf8':end,'callee':callee,'evaluation_context':context,'resolution':resolution,'reason':reason,'same_module_definition_ids':list(definitions),'certain':False}
def ares(files,symbols,calls=(),imports=()):return {'record_type':ast_id+'_result/v1','syntax_profile':'python_ast_feature_3_10/v1','complete_runtime_dependency_graph':False,'files':files,'symbols':symbols,'imports':list(imports),'calls':list(calls)}
a=areq([('m.py','m','def f(): pass\nf()\n')]);f=symbol_id('m','f','function',1,0)
ao=ares([afile('m.py','m',a['files'][0]['source'])],[sym('m','m.py','<module>'),sym('m','m.py','f','function',1,0,1,13,module_id('m'))],[call('m','m.py',2,0,3,'f',resolution='candidate',reason='name_definition_candidate',definitions=[f])])
case(ast_id,'single_definition_is_only_a_candidate',a,ao)
case(ast_id,'empty_module',areq([('m.py','m','')]),ares([afile('m.py','m','')],[sym('m','m.py','<module>')]))
source='def target(): pass\ndef run(x=target()):\n    return target()\n';target=symbol_id('m','target','function',1,0);run=symbol_id('m','run','function',2,0)
case(ast_id,'default_expression_belongs_to_enclosing_owner',areq([('m.py','m',source)]),ares([afile('m.py','m',source)],[sym('m','m.py','<module>'),sym('m','m.py','target','function',1,0,1,18,module_id('m')),sym('m','m.py','run','function',2,0,3,19,module_id('m'))],[call('m','m.py',2,10,18,'target',context='definition_time',resolution='candidate',reason='name_definition_candidate',definitions=[target]),call('m','m.py',3,11,19,'target',owner=run,context='function_body',resolution='candidate',reason='name_definition_candidate',definitions=[target])]))
source='def target(): pass\ndef run(target):\n    return target()\n'
case(ast_id,'parameter_shadow_is_unresolved',areq([('m.py','m',source)]),ares([afile('m.py','m',source)],[sym('m','m.py','<module>'),sym('m','m.py','target','function',1,0,1,18,module_id('m')),sym('m','m.py','run','function',2,0,3,19,module_id('m'))],[call('m','m.py',3,11,19,'target',owner=run,context='function_body',reason='local_binding_may_shadow',definitions=[target])]))
source='import os\nos.system("not executed")\n'
case(ast_id,'dangerous_looking_source_is_inert',areq([('m.py','m',source)]),ares([afile('m.py','m',source)],[sym('m','m.py','<module>')],[call('m','m.py',2,0,25,'os.system',reason='attribute_requires_runtime')],[{'module':'m','path':'m.py','owner_id':module_id('m'),'line':1,'column_utf8':0,'evaluation_context':'module','requested_module':'os','imported_name':None,'asname':None,'level':0,'candidate_module_ids':[],'resolution':'unresolved'}]))
case(ast_id,'syntax_error_does_not_drop_other_file',areq([('bad.py','bad','def :\n'),('good.py','good','')]),ares([afile('bad.py','bad','def :\n','syntax_error',1),afile('good.py','good','')],[sym('good','good.py','<module>')]))
source='é = 1; missing()\n'
case(ast_id,'unicode_column_is_utf8_bytes',areq([('m.py','m',source)]),ares([afile('m.py','m',source)],[sym('m','m.py','<module>')],[call('m','m.py',1,8,17,'missing')]))
case(ast_id,'duplicate_module_refuses',areq([('a.py','m',''),('b.py','m','')]),{'error':'invalid_input'},True)
case(ast_id,'parent_path_refuses',areq([('../a.py','m','')]),{'error':'invalid_input'},True)
case(ast_id,'keyword_module_refuses',areq([('a.py','class','')]),{'error':'invalid_input'},True)

for identity in IDS:
 for name,raw in [('duplicate_json_key','{"x":1,"x":2}'),('nonfinite','{"x":NaN}'),('wire_limit',' '*65537)]:
  cases[identity].append({'name':name,'raw_input':raw,'expected_exit':2,'expected':{'error':'invalid_input'}})
 cases[identity].append({'name':'invalid_utf8','input_hex':'ff','expected_exit':2,'expected':{'error':'invalid_input'}})
 req=dict(cases[identity][0]['input']);req['unexpected']=True
 case(identity,'unknown_field_refuses',req,{'error':'invalid_input'},True)
 write(identity,'verification/cases.json',cases[identity]);write(identity,'examples/input.json',cases[identity][0]['input']);write(identity,'examples/output.json',cases[identity][0]['expected'])

manifest={'record_type':'gemma4_components_contracts_before_code/v1','cases':{i:len(cases[i]) for i in IDS},'files':{str(p.relative_to(BASE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE/'packages').rglob('*') if p.is_file()},'executables_exist':any((BASE/'packages').rglob('*.py'))}
(BASE/'authors/contracts-first.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'cases':manifest['cases'],'executables_exist':manifest['executables_exist']}))
