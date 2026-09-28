"""Independent contract-based examples; candidate implementations did not exist at design time."""
import copy,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
packages=[]
ERROR={'ok':False,'error':{'code':'invalid_input'}}
def good(name,value,result,why):
 return {'name':name,'input':value,'expected':{'ok':True,'result':result},'expected_exit':0,'input_schema_valid':True,'rationale':why}
def bad(name,value,why,schema_valid=None):
 row={'name':name,'input':value,'expected':ERROR,'expected_exit':2,'rationale':why}
 if schema_valid is not None:row['input_schema_valid']=schema_valid
 return row
def raw(name,text,why,schema_valid=None):
 row={'name':name,'raw_hex':text.hex() if isinstance(text,bytes) else text.encode().hex(),'expected':ERROR,'expected_exit':2,'rationale':why}
 if schema_valid is not None:row['input_schema_valid']=schema_valid
 return row
def raw_controls(seed):
 text=json.dumps(seed,separators=(',',':'));key=next(iter(seed))
 return [raw('duplicate_same_value_key',text[:-1]+','+json.dumps(key)+':'+json.dumps(seed[key])+'}','Raw duplicate names must be refused.'),
         raw('trailing_garbage',text+'x','A valid prefix is not a valid complete document.'),
         raw('invalid_utf8',b'\xff'+text.encode(),'Invalid UTF-8 must produce the declared refusal, not a traceback.'),
         raw('wire_byte_limit',' '*(262145-len(text))+text,'Leading whitespace still counts toward the declared input byte limit.',True)]
def col(index,present,missing,empty,maximum):return {'index':index,'present_rows':present,'missing_rows':missing,'empty_cells':empty,'max_chars':maximum}
identity='profile_csv_structure'
seed={'csv':'x,y\r\n"a,b","c""d"\r\n"m\nn",\r\n\r\n','delimiter':',','quotechar':'"','header':True}
rows=[good('quoted_newlines_and_blank_record',seed,{'row_count':3,'column_count':2,'physical_line_count':5,'header':['x','y'],
 'duplicate_header_names':[],'blank_header_indices':[],'width_counts':[{'width':0,'records':1},{'width':2,'records':2}],
 'width_mismatches':[{'row_index':2,'width':0}],'columns':[col(0,2,1,0,3),col(1,2,1,1,3)]},'CSV logical records differ from physical lines; a blank CSV record is not a two-empty-cell row.')]
value={'csv':'b,,b\nx,,z\n','delimiter':',','quotechar':'"','header':True};rows.append(good('exact_duplicate_and_blank_headers',value,{'row_count':1,'column_count':3,'physical_line_count':2,'header':['b','','b'],'duplicate_header_names':[{'name':'b','indices':[0,2]}],'blank_header_indices':[1],'width_counts':[{'width':3,'records':1}],'width_mismatches':[],'columns':[col(0,1,0,0,1),col(1,1,0,1,0),col(2,1,0,0,1)]},'Empty header and empty cell positions remain distinct and positional.'))
value={'csv':'h\nx,y\nz\n','delimiter':',','quotechar':'"','header':True};rows.append(good('extra_fields_do_not_expand_baseline',value,{'row_count':2,'column_count':1,'physical_line_count':3,'header':['h'],'duplicate_header_names':[],'blank_header_indices':[],'width_counts':[{'width':1,'records':1},{'width':2,'records':1}],'width_mismatches':[{'row_index':0,'width':2}],'columns':[col(0,2,0,0,1)]},'Confirmed contract: report extra width but do not invent additional baseline columns.'))
value={'csv':'','delimiter':',','quotechar':'"','header':False};rows.append(good('empty_without_header',value,{'row_count':0,'column_count':0,'physical_line_count':0,'header':None,'duplicate_header_names':[],'blank_header_indices':[],'width_counts':[],'width_mismatches':[],'columns':[]},'Empty document has zero records and no inferred columns.'))
value=copy.deepcopy(seed);value['csv']='a,b\n1,"oops\n';rows.append(bad('unterminated_quote',value,'Strict dialect parser must refuse an unterminated quoted field.',True))
value=copy.deepcopy(seed);value['csv']='a\x00b';rows.append(bad('nul_input',value,'NUL is outside the declared CSV string contract.',False))
packages.append({'identity':identity,'cases':rows+raw_controls(seed)})
identity='reconcile_multiset_rows'
seed={'left':[{'v':1},{'v':1},{'v':True},{},{'v':None}], 'right':[{'v':1.0},{'v':True},{'v':True},{'v':'1'},{'v':None}]}
result={'left_count':5,'right_count':5,'equal':False,'common':[{'row':{'v':1},'count':1},{'row':{'v':None},'count':1},{'row':{'v':True},'count':1}], 'left_only':[{'row':{'v':1},'count':1},{'row':{},'count':1}], 'right_only':[{'row':{'v':'1'},'count':1},{'row':{'v':True},'count':1}]}
rows=[good('multiplicities_types_and_missing',seed,result,'Booleans must not collapse into integers; absent keys differ from null; counts cannot collapse into sets.')]
value=copy.deepcopy(seed);value['left'].reverse();value['right'].reverse();rows.append(good('input_permutation',value,result,'Row order cannot alter canonical multiset reconciliation.'))
value={'left':[{'b':2,'a':1.0}], 'right':[{'a':1,'b':2}]};rows.append(good('field_order_and_integral_numbers',value,{'left_count':1,'right_count':1,'equal':True,'common':[{'row':{'a':1,'b':2},'count':1}],'left_only':[],'right_only':[]},'Canonical key order and exact integer normalization preserve equality.'))
value={'left':[],'right':[]};rows.append(good('empty_multisets',value,{'left_count':0,'right_count':0,'equal':True,'common':[],'left_only':[],'right_only':[]},'Empty bags compare equal.'))
rows.append(bad('nonintegral_row_number',{'left':[{'v':1.5}],'right':[]},'Fractional values require strings under this explicit row contract.',False))
rows.append(raw('rounding_must_not_fabricate_integer','{"left":[{"v":1.00000000000000000001}],"right":[]}','Binary float rounding must not convert a nonintegral wire number into integer 1.',False))
rows.append(raw('nonfinite_number','{"left":[{"v":NaN}],"right":[]}','Nonfinite values are not JSON primitives.'))
packages.append({'identity':identity,'cases':rows+raw_controls(seed)})
identity='compute_weighted_quantiles'
seed={'samples':[{'value':'5','weight':2},{'value':'-1.0','weight':1},{'value':'5.00','weight':1},{'value':'10','weight':1}], 'probabilities':['0.0','0.2','0.200000000001','0.80','0.800000000001','1.0']}
result={'total_weight':5,'distinct_values':3,'cdf':[{'value':'-1','weight':1,'cumulative_weight':1},{'value':'5','weight':3,'cumulative_weight':4},{'value':'10','weight':1,'cumulative_weight':5}], 'quantiles':[{'q':'0','value':'-1'},{'q':'0.2','value':'-1'},{'q':'0.200000000001','value':'5'},{'q':'0.8','value':'5'},{'q':'0.800000000001','value':'10'},{'q':'1','value':'10'}]}
rows=[good('exact_cdf_thresholds_and_duplicate_values',seed,result,'Strictly above a jump differs from exact equality; equal decimal values combine without interpolation.')]
value=copy.deepcopy(seed);value['samples'].reverse();rows.append(good('sample_permutation',value,result,'Input order cannot alter sorted inverse-CDF results.'))
value=copy.deepcopy(seed)
for item in value['samples']:item['weight']*=7
scaled=copy.deepcopy(result);scaled['total_weight']*=7
for item in scaled['cdf']:item['weight']*=7;item['cumulative_weight']*=7
rows.append(good('positive_weight_scale_invariance',value,scaled,'Uniform weight scaling preserves all quantile values exactly.'))
value={'samples':[{'value':'-0.000','weight':2.0}],'probabilities':['0','1']};rows.append(good('negative_zero_and_integral_weight',value,{'total_weight':2,'distinct_values':1,'cdf':[{'value':'0','weight':2,'cumulative_weight':2}],'quantiles':[{'q':'0','value':'0'},{'q':'1','value':'0'}]},'Canonical decimal zero and schema-compatible integral JSON weight.'))
value=copy.deepcopy(seed);value['samples'][0]['weight']=0;rows.append(bad('zero_weight_refused',value,'This method explicitly requires positive integer weights.',False))
value=copy.deepcopy(seed);value['probabilities']=['1.000000000001'];rows.append(bad('probability_above_one',value,'Probability grammar excludes values above one.',False))
rows.append(raw('near_integer_weight_not_rounded','{"samples":[{"value":"1","weight":1.000000000000000001}],"probabilities":["0.5"]}','Exact lexical value is nonintegral despite ordinary binary-float rounding.',False))
packages.append({'identity':identity,'cases':rows+raw_controls(seed)})
with (HERE/'data-first-three-before-source-v1.json').open('x') as stream:
 json.dump({'record_type':'independent_component_cases/v1','design_basis':'Published input/output schemas and author CSV clarification; no implementations existed at case design.','packages':packages},stream,indent=2);stream.write('\n')
print(sum(len(p['cases']) for p in packages))
