"""Owner bounded revision audit. Run with parent-root and candidate-root arguments.
No production imports. PyYAML required only for config structural comparison.
"""
from pathlib import Path
from fractions import Fraction as F
import json,hashlib,struct,math,ast,re,sys,subprocess,tempfile,yaml
old=Path(sys.argv[1]);new=Path(sys.argv[2]);checks={}
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(c,n):
 assert c,n
 checks[n]='PASS'
def bits(r):
 f=float.fromhex(r['hex']);require(struct.pack('>d',f).hex()==r['bits_hex'],'IEEE_hex_bits_consistent');require(int(r['bits_hex'],16)>>63==r['sign_bit'],'IEEE_sign_consistent')
 expected=F(r.get('displayed_binary64_fraction',r['fraction']))
 require(F.from_float(f)==expected,'IEEE_dyadic_or_explicit_display_consistent')
 # JSON float must preserve zero's sign too.
 require(struct.pack('>d',r['float']).hex()==r['bits_hex'],'JSON_float_bits_consistent')
def walk(x):
 if isinstance(x,dict):
  if 'bits_hex' in x:bits(x)
  for y in x.values():walk(y)
 elif isinstance(x,list):
  for y in x:walk(y)
def real(v,q,a,e):
 delta=a*(q-v)
 return delta/max(e,1-v if delta>0 else v) if delta else F(0)
for name in ['ORACLE_FIXTURES_C6.json','F35_FIXTURES_C6.json','SIGNED_ZERO_FIXTURES_C6.json','SELF_CHECK_C6.json']:walk(load(new/name))
s=load(new/'NUMERIC_EVIDENCE_SCHEMA_C6.json');forbidden=s['fixture_contract']['unknown_origin_forbidden_actual']
known=[];unknown=[]
a=load(old/'ORACLE_FIXTURES_C6.json');b=load(new/'ORACLE_FIXTURES_C6.json')
require(len(a)==len(b)==45,'scalar_count_45')
for x,y in zip(a,b):
 require(x['id']==y['id'] and x['label']==y['label'] and x['ideal_input_known']==y['ideal_input_known'],'inherited_fixture_identity_and_labels')
 for k in x['nodes']:
  if isinstance(x['nodes'][k],dict):require(x['nodes'][k]['fraction']==y['nodes'][k]['fraction'] and x['nodes'][k]['hex']==y['nodes'][k]['hex'],'inherited_scalar_nodes_unchanged')
  else:require(x['nodes'][k]==y['nodes'][k],'inherited_identity_flag_unchanged')
 for k in ['real_on_rounded_inputs','arithmetic_error','arithmetic_bound']:require(x[k]['fraction']==y[k]['fraction'],'inherited_R_arithmetic_residual_bound_unchanged')
 r=y['rounded_inputs'];R=real(*[F(r[k]['fraction']) for k in ['v','q','alpha','epsilon']]);B=F(y['nodes']['u']['fraction'])
 require(R==F(y['real_on_rounded_inputs']['fraction']) and B-R==F(y['arithmetic_error']['fraction']),'scalar_R_B_minus_R_recomputed_without_reference_import')
 require(abs(B-R)<=F(y['arithmetic_bound']['fraction']),'scalar_arithmetic_bounds')
 if y['ideal_input_known']:
  known.append(y['id']);require(x['ideal_inputs']==y['ideal_inputs'],'known_original_exact_rationals_preserved')
  require(y['original_exact_tokens']['v_rational']==x['ideal_inputs']['v'] and y['original_exact_tokens']['q_rational']==x['ideal_inputs']['q'],'known_exact_token_lineage')
  I=real(*[F(y['ideal_inputs'][k]) for k in ['v','q','alpha','epsilon']]);require(I==F(y['scientific_ideal']['fraction']),'known_I_recomputed')
  require(R-I==F(y['input_error']['fraction']) and B-I==F(y['total_error']['fraction']),'known_exact_residual_decomposition')
  require(abs(R-I)<=F(y['input_bound']['fraction']) and abs(B-I)<=F(y['total_bound']['fraction']),'known_applicable_input_total_bounds')
  for k in ['scientific_ideal','input_error','total_error']:require(x[k]['fraction']==y[k]['fraction'],'known_original_diagnostics_unchanged')
 else:
  unknown.append(y['id']);require(not any(k in y for k in forbidden),'unknown_actual_I_and_input_total_absent');require(y['actual_ideal_status'].startswith('unavailable'),'unknown_explicit_unavailable')
require(len(known)==17 and len(unknown)==28,'known17_unknown28_full_audit')
require(b[0]['scientific_ideal']['fraction']=='7/40' and b[1]['scientific_ideal']['fraction']=='-7/40','scientific_plus_minus_7_40_unchanged')
f_old=load(old/'F35_FIXTURES_C6.json');f_new=load(new/'F35_FIXTURES_C6.json');appraisal_count=0
require(len(f_new)==len(f_old)==840,'F35_count_840')
for x,y in zip(f_old,f_new):
 for k in ['adapter','offer','v_hex','p','z','action','category']:require(x[k]==y[k],'F35_inputs_votes_categories_actions_unchanged')
 for k in ['N','P','D']:require(x[k]['fraction']==y[k]['fraction'] and x[k]['hex']==y[k]['hex'],'F35_N_P_D_unchanged')
 require(not y['ideal_input_known'] and not any(k in y for k in forbidden),'F35_unknown_origin_no_actual_I')
 o=y['offer'];balance=1.0-abs(10.0-2.0*o)/10.0
 raw={'accept':(o/8.0,balance,1.0,1.0),'reject':(0.0,1.0-balance if y['adapter']=='N' else 0.0 if y['adapter']=='A' else .5,.5 if y['adapter']=='B' else 0.0,1.0-o/8.0)}
 data=y['candidate_appraisal_diagnostics'];v=F.from_float(float.fromhex(y['v_hex']));aB=F.from_float(.35);eB=F.from_float(1e-6)
 for action_name,action in data.items():
  for (channel,r),q in zip(action.items(),raw[action_name]):
   require(real(v,F.from_float(q),aB,eB)==F(r['real_on_rounded_inputs']['fraction']),'F35_R_recomputed_independently_from_literal_adapter')
   appraisal_count+=1;require(not any(k in r for k in forbidden),'F35_nested_unknown_no_actual_I')
   require(F(r['executable_B']['fraction'])-F(r['real_on_rounded_inputs']['fraction'])==F(r['arithmetic_error']['fraction']),'F35_nested_R_B_residual_decomposition')
   require(abs(F(r['arithmetic_error']['fraction']))<=F(r['arithmetic_bound']['fraction']),'F35_nested_arithmetic_bounds')
old_neighbors=load(old/'SELF_CHECK_C6.json')['branch_neighbors'];new_neighbors=load(new/'SELF_CHECK_C6.json')['branch_neighbors']
for x,y in zip(old_neighbors,new_neighbors):
 for k in ['label','action']:require(x[k]==y[k],'branch_neighbor_labels_actions_unchanged')
 for k in ['N','D']:
  if k in x:require(x[k]['fraction']==y[k]['fraction'] and x[k]['hex']==y[k]['hex'],'branch_neighbor_N_D_unchanged')
require(new_neighbors[0]['N']['bits_hex']=='0000000000000000' and new_neighbors[0]['category']=='tie_reject','exact_zero_tie_positive_zero_bits')
require([F(r['N']['fraction']) for r in new_neighbors[1:3]]==[F(1,2**52),F(1,2**53)],'two_legal_one_sided_neighbor_N_values')
zero=load(new/'SIGNED_ZERO_FIXTURES_C6.json');require(len(zero['fixtures'])==28 and len(zero['material_only_copy_checks'])==4,'signed_zero_28_and_copy4')
for row in zero['fixtures']:
 require(not row['ideal_input_known'] and not any(k in row for k in forbidden),'signed_zero_unknown_no_actual_I')
 for k,w in row['expected_bits'].items():require(row['nodes'][k]['bits_hex']==w,'signed_zero_explicit_expected_words')
 if row['nodes']['identity']:require(row['nodes']['current']['bits_hex']==row['rounded_inputs']['v']['bits_hex'],'identity_preserves_input_v_bits')
 require(abs(F(row['arithmetic_error']['fraction']))<=F(row['arithmetic_bound']['fraction']),'signed_zero_arithmetic_bound')
for path in ['candidate','realized_full']:
 rows=[r for r in zero['fixtures'] if r['path']==path and r['nodes']['identity']]
 require(len(rows)==4 and len({(r['rounded_inputs']['v']['bits_hex'],r['rounded_inputs']['q']['bits_hex']) for r in rows})==4,'all_four_identity_zero_pairs_'+path)
for row in zero['material_only_copy_checks']:require(row['v']['bits_hex']==row['q_star']['bits_hex'],'material_only_bit_copy')
g=load(new/'GAP_SEPARATION_DERIVATION_C6.json');require(len(g['pairs'])==84 and g['minima']=={'N':'1/5','A':'1/4','B':'1/10'},'exact_gap_minima_84_pairs')
require(all(F(v['fraction'])>0 for v in g['uniform_margins'].values()),'all_adapter_uniform_margins_positive')
require(F(g['uniform_margins']['B']['fraction'])==F(g['alpha_B'])/10-2*F(g['total_perturbation_per_projection']),'global_margin_exact_recomputed')
for row in g['static_boundary_identity_epsilon_checks']:require(abs(F(row['signed_appraisal_gap']))>=F(row['real_gap_floor'])>0,'rational_boundary_identity_epsilon_floors')
# Exact scientific spec sections pinned v1.0->v1.1, except only S00 and S03-U.
def sections(p):
 text=p.read_text();parts=re.split(r'(?m)(?=^#{2,3} S)',text);return {re.search(r'^#{2,3} (S[\w-]+)',t).group(1):t for t in parts[1:]}
aS=sections(old/'MODEL_SPEC_JOURNAL_V1_R1C6.md');bS=sections(new/'MODEL_SPEC_JOURNAL_V1_R1C6.md')
changed=[k for k in aS if aS[k]!=bS[k]];require(set(changed)=={'S00','S03-U'},'spec_only_authority_and_linked_qualification_changed')
for line in (old/'MODEL_SPEC_JOURNAL_V1_R1C6.md').read_text().splitlines():
 if line.startswith('**F-'):require(line in (new/'MODEL_SPEC_JOURNAL_V1_R1C6.md').read_text(),'all_scientific_formula_lines_unchanged')
aY=yaml.safe_load((old/'PARAMETER_TABLE_R1C6.yaml').read_text());bY=yaml.safe_load((new/'PARAMETER_TABLE_R1C6.yaml').read_text())
allowed={'/schema_id','/specification_id','/serialization/result_schema_id','/serialization/observation_schema_id','/serialization/numeric_policy_id','/serialization/identity_projection','/serialization/scientific_numeric_residuals','/serialization/reference_ieee_metadata'};ydiffs=[]
def yd(a,b,p=''):
 if isinstance(a,dict) and isinstance(b,dict):
  for k in a.keys()|b.keys():
   if k not in a or k not in b:ydiffs.append(p+'/'+k)
   else:yd(a[k],b[k],p+'/'+k)
 elif a!=b:ydiffs.append(p)
yd(aY,bY);require(set(ydiffs)==allowed,'YAML_only_version_zero_provenance_metadata_changed')
for sub in ['UPSTREAM_C5','AUTHORITY_SOURCES']:
 for p in (old/sub).rglob('*'):
  if p.is_file():require(sha(p)==sha(new/p.relative_to(old)),'immutable_inherited_'+sub+'_byte_hashes')
for source in ['reference_binary64.py','derive_gap_proof.py']:
 tree=ast.parse((new/source).read_text());imports=[]
 for node in ast.walk(tree):
  if isinstance(node,ast.Import):imports.extend(a.name.split('.')[0] for a in node.names)
  if isinstance(node,ast.ImportFrom):imports.append(node.module.split('.')[0])
 require(all(i in sys.stdlib_module_names for i in imports),'stdlib_only_no_production_imports_'+source)
with tempfile.TemporaryDirectory() as td:
 subprocess.run([sys.executable,str((new/'reference_binary64.py').resolve()),td],check=True,stdout=subprocess.DEVNULL)
 for name in ['ORACLE_FIXTURES_C6.json','F35_FIXTURES_C6.json','SIGNED_ZERO_FIXTURES_C6.json','SELF_CHECK_C6.json']:require(sha(Path(td)/name)==sha(new/name),'fresh_reference_reproduction_'+name)
 subprocess.run([sys.executable,str((new/'derive_gap_proof.py').resolve()),td+'/gaps.json'],check=True,stdout=subprocess.DEVNULL)
 require(sha(Path(td)/'gaps.json')==sha(new/'GAP_SEPARATION_DERIVATION_C6.json'),'fresh_gap_derivation_reproduction')
report={'package_id':'EMBORA-R0PKG-2026-10-04-C6-v1.1','status':'OWNER_CHECK_PASS_PENDING_INDEPENDENT_RECHECK','checks':checks,'known_rows_audited':known,'all_28_unknown_rows_audited':unknown,'F35_unknown_rows_audited':840,'F35_nested_R_B_appraisals_audited':appraisal_count,'signed_zero_unknown_rows_audited':28,'signed_copy_vectors':4,'gap_pairs':84,'rational_boundary_identity_epsilon_cases':len(g['static_boundary_identity_epsilon_checks']),'spec_sections_unchanged':{k:hashlib.sha256(aS[k].encode()).hexdigest() for k in aS if k not in changed},'spec_changed_sections':changed,'YAML_changed_paths':sorted(ydiffs),'dependencies':{'python':sys.version,'PyYAML':yaml.__version__},'production_patch':False,'production_conformance':'NOT_RUN','trajectories_pilot_full_sensitivity_runs':0,'independent_closure':False,'author_adoption':False}
(new/'REVISION_CHECKS_C6_v1.1.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['checks','known_rows_audited','all_28_unknown_rows_audited','spec_sections_unchanged']},indent=2));print('CHECK_GROUPS',len(checks))
