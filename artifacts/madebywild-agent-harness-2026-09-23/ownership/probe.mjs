import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
const [modules,scratch] = process.argv.slice(2);
const load = name => import(pathToFileURL(path.join(modules,name+'.mjs')).href);
const {buildPlan}=await load('planner');
const {ProbeEngine}=await load('writer');
const {resolveHarnessPaths}=await load('paths');
const {sha256,normalizeRelativePath}=await load('utils');
const {substituteSourceText,loadBehavior}=await load('behavior');
const {parseManifest,parseBehaviorMap}=await load('manifest');
const {readSkillFiles,buildGitCloneCommand,toAuthHeader,cloneErrorMessage}=await load('registry-probe');
const {resolvePresetChain}=await load('presets-probe');
const {migrateVersionedObject}=await load('migration-probe');
const results=[];
const record=(id,details)=>results.push({id,verified:true,...details});
await fs.mkdir(scratch,{recursive:true});
const root=async name=>{const r=path.join(scratch,name);await fs.mkdir(r,{recursive:true});return r;};
const manifest=providers=>parseManifest({version:1,providers:{enabled:providers},registries:{default:'local',entries:{local:{type:'local'}}},entities:[]});
const loaded=providers=>({manifest:manifest(providers),diagnostics:[],skills:[],promptSections:[],mcps:[],subagents:[],hooks:[],settings:[],commands:[]});
const artifact=(p,body='desired',provider='codex',owner='fixture')=>({path:p,content:body,provider,ownerEntityId:owner});
const index=paths=>({version:1,managedSourcePaths:[],managedOutputPaths:paths});
async function plan(cwd,artifacts,managed=[],previous=null){globalThis.__artifacts=artifacts;return buildPlan(resolveHarnessPaths(cwd),loaded([...new Set(artifacts.map(a=>a.provider))]),index(managed),previous);}

{
  const r=await root('ownership');await fs.writeFile(path.join(r,'AGENTS.md'),'human edit');
  let p=await plan(r,[artifact('AGENTS.md')]);
  assert(p.diagnostics.some(d=>d.code==='OUTPUT_COLLISION_UNMANAGED'));
  assert.equal((await new ProbeEngine(r,p).apply()).writtenArtifacts.length,0);
  assert.equal(await fs.readFile(path.join(r,'AGENTS.md'),'utf8'),'human edit');
  record('unmanaged_existing_file_refused',{diagnostics:p.diagnostics.map(d=>d.code)});
  p=await plan(r,[artifact('AGENTS.md')],['AGENTS.md']);
  const previous=p.nextLock;
  assert.equal(p.operations[0].type,'update');
  assert.equal(p.nextLock.outputs[0].contentSha256,sha256('desired'));
  await new ProbeEngine(r,p).apply();
  assert.equal(await fs.readFile(path.join(r,'AGENTS.md'),'utf8'),'desired');
  await fs.writeFile(path.join(r,'AGENTS.md'),'second human edit');
  p=await plan(r,[artifact('AGENTS.md')],['AGENTS.md'],previous);
  assert.equal(p.operations[0].type,'update');
  assert.deepEqual(p.nextLock,previous);
  record('managed_drift_updates_without_old_byte_check',{operation:p.operations[0],rendered_digest:p.nextLock.outputs[0].contentSha256,lock_unchanged_despite_disk_drift:true});
  p=await plan(r,[],['AGENTS.md'],previous);assert.equal(p.operations[0].type,'delete');
  await new ProbeEngine(r,p).apply();
  await assert.rejects(fs.stat(path.join(r,'AGENTS.md')),e=>e.code==='ENOENT');
  record('stale_managed_changed_file_deleted',{operation:p.operations[0]});
}
{
  const r=await root('collisions');
  const p=await plan(r,[artifact('x','same','codex','a'),artifact('x','same','codex','b')]);
  assert.deepEqual(p.nextLock.outputs[0].ownerEntityIds,['a','b']);
  const differing=await plan(r,[artifact('x','one'),artifact('x','two')]);
  const providers=await plan(r,[artifact('x','same','codex'),artifact('x','same','claude')]);
  assert(differing.diagnostics.some(d=>d.code==='OUTPUT_PATH_COLLISION'));
  assert(providers.diagnostics.some(d=>d.code==='OUTPUT_PATH_COLLISION'));
  assert.throws(()=>normalizeRelativePath('../escape'));
  record('collisions_and_parent_traversal_refused',{same_bytes_same_provider_owner_merge:true,different_bytes_collision:true,cross_provider_identical_collision:true});
}
{
  const r=await root('plan_race');const p=await plan(r,[artifact('late.txt')]);
  await fs.writeFile(path.join(r,'late.txt'),'other writer after plan');
  await new ProbeEngine(r,p).apply();
  assert.equal(await fs.readFile(path.join(r,'late.txt'),'utf8'),'desired');
  record('post_plan_creation_overwritten',{scope:'Injected precomputed plan preserves real apply method, simulates concurrent creator between plan and effect'});
}
{
  const r=await root('symlink_root');const outside=await root('symlink_sibling');
  await fs.symlink(outside,path.join(r,'native'),'dir');
  const p=await plan(r,[artifact('native/AGENTS.md')]);assert.equal(p.diagnostics.length,0);
  await new ProbeEngine(r,p).apply();
  assert.equal(await fs.readFile(path.join(outside,'AGENTS.md'),'utf8'),'desired');
  record('parent_symlink_not_confined_to_workspace',{scope:'Both workspace and sibling are disposable scratch directories; no host files affected'});
}
{
  const r=await root('partial');const p=await plan(r,[artifact('a.txt'),artifact('z/child.txt')]);
  await fs.writeFile(path.join(r,'z'),'parent path becomes file after plan');
  await assert.rejects(new ProbeEngine(r,p).apply());
  assert.equal(await fs.readFile(path.join(r,'a.txt'),'utf8'),'desired');
  await assert.rejects(fs.stat(path.join(r,'.harness/manifest.lock.json')),e=>e.code==='ENOENT');
  record('batch_failure_leaves_prior_output',{earlier_write_survived:true,lock_not_written:true});
}
{
  const r=await root('delete_error');await fs.writeFile(path.join(r,'stale'),'keep');
  const p=await plan(r,[],['stale']);const original=fs.rm;
  fs.rm=async target=>{if(target===path.join(r,'stale')) throw Object.assign(new Error('fixture access denial'),{code:'EACCES'});return original(target);};
  let applied;try{applied=await new ProbeEngine(r,p).apply();}finally{fs.rm=original;}
  assert.equal(await fs.readFile(path.join(r,'stale'),'utf8'),'keep');
  assert.deepEqual(applied.prunedArtifacts,['stale']);
  assert.deepEqual(JSON.parse(await fs.readFile(path.join(r,'.harness/managed-index.json'),'utf8')).managedOutputPaths,[]);
  record('failed_delete_reported_pruned_and_ownership_removed',{injection:'Only fs.rm of exact scratch stale path throws EACCES',actual_file_remains:true});
}
{
  const r=await root('directory_delete');await fs.mkdir(path.join(r,'stale'));await fs.writeFile(path.join(r,'stale','human.txt'),'keep');
  const p=await plan(r,[],['stale']);await new ProbeEngine(r,p).apply();
  await assert.rejects(fs.stat(path.join(r,'stale')),e=>e.code==='ENOENT');
  record('stale_managed_path_now_directory_removed_recursively',{scope:'Explicitly listed managed path changed to a scratch directory'});
}
{
  const diagnostics=[];const subs={envVars:new Map([['CANARY','fixture-only'],['INJECT','safe","extra":true,"second":"value'],['INDIRECT','{{behavior.mode}}']]),behaviorValues:new Map([['mode','chosen'],['nested','{{CANARY}}']])};
  const literal=substituteSourceText('secret={{CANARY}}',subs,diagnostics,'fixture').result;assert.equal(literal,'secret=fixture-only');
  const changed=JSON.parse(substituteSourceText('{"value":"{{INJECT}}"}',subs,diagnostics,'fixture').result);assert.equal(changed.extra,true);
  const order=substituteSourceText('{{INDIRECT}} / {{behavior.nested}}',subs,diagnostics,'fixture').result;assert.equal(order,'chosen / {{CANARY}}');
  const missing=substituteSourceText('{{MISSING_CANARY}}',subs,diagnostics,'fixture').result;assert.equal(missing,'{{MISSING_CANARY}}');
  assert(diagnostics.some(d=>d.code==='ENV_VAR_UNRESOLVED'&&d.severity==='warning'));
  record('raw_substitution_and_order',{literal_canary_materialized:true,unescaped_json_value_changes_structure:changed.extra,order_result:order,unresolved_severity:'warning'});
}
{
  const r=await root('behavior');const paths=resolveHarnessPaths(r);await fs.mkdir(paths.agentsDir);
  const input={version:1,keys:{mode:{default:'toString',values:{safe:'safe instruction'}}}};
  const parsed=parseBehaviorMap(input);assert.equal(parsed.keys.mode.default,'toString');
  await fs.writeFile(paths.behaviorMapFile,JSON.stringify(input));
  const behavior=await loadBehavior(paths);
  assert.equal(behavior.diagnostics.length,0);assert.equal(typeof behavior.values.get('mode'),'function');
  await fs.writeFile(paths.behaviorMapFile,JSON.stringify({version:1,keys:{mode:{default:'safe',values:{safe:'safe instruction'}}}}));
  await fs.writeFile(paths.behaviorConfigFile,'mode: constructor\n');
  const configured=await loadBehavior(paths);assert.equal(configured.diagnostics.length,0);assert.equal(typeof configured.values.get('mode'),'function');
  record('behavior_inherited_property_accepted',{undeclared_default:'toString',undeclared_config:'constructor',resolved_type:typeof configured.values.get('mode'),diagnostics:[]});
}
{
  const r=await root('binary');await fs.writeFile(path.join(r,'SKILL.md'),'---\nname: fixture\ndescription: fixture\n---\n');
  const bytes=Buffer.from([0,255,128,65]);await fs.writeFile(path.join(r,'asset.bin'),bytes);
  const files=await readSkillFiles(r,'fixture-registry','fixture');const asset=files.find(f=>f.path==='asset.bin');
  const roundtrip=Buffer.from(asset.content,'utf8');assert(!roundtrip.equals(bytes));
  record('registry_skill_binary_utf8_round_trip_changes_bytes',{input_hex:bytes.toString('hex'),output_hex:roundtrip.toString('hex'),raw_sha256:crypto.createHash('sha256').update(bytes).digest('hex'),recorded_sha256:asset.sha256,record_is_decoded_text_hash:asset.sha256===sha256(asset.content)});
}
{
  const token='not-a-secret-probe-canary';const header=toAuthHeader(token);
  const command=buildGitCloneCommand({type:'git',url:'https://example.invalid/repository',ref:'moving-tag'},token,'/scratch/unused');
  assert(command.args.some(a=>a===`http.extraHeader=Authorization: ${header}`));
  const error=cloneErrorMessage(new Error(`${token} ${header}`),token);assert(!error.includes(token));assert(!error.includes(header));
  record('registry_credential_in_clone_argv',{credential_source:'Harmless synthetic canary only',argv_contains_authorization:true,error_redacts_known_token_and_header:true,git_executed:false});
}
{
  const parent={source:'registry',registry:'r',definition:{id:'parent',operations:[{type:'add_skill',id:'s'},{type:'add_prompt_section',id:'p'},{type:'add_hook',id:'guard'},{type:'add_mcp',id:'m'}]},content:{skills:{s:'parent'},hooks:{guard:'guard'}}};
  const child={source:'registry',registry:'r',definition:{id:'child',extends:'parent',operations:[{type:'add_skill',id:'s'}]},content:{skills:{s:'child'}}};
  const result=resolvePresetChain(child,new Map([['parent',parent],['child',child]]));
  assert.deepEqual(result.definition.operations.map(o=>o.type),['add_prompt_section','add_skill']);assert.equal(result.content.skills.s,'child');assert.equal(result.content.hooks,undefined);
  parent.definition.extends='child';assert.throws(()=>resolvePresetChain(child,new Map([['parent',parent],['child',child]])),/PRESET_EXTENDS_CYCLE/);
  record('preset_inheritance_is_selective',{inherited_operations:['add_prompt_section'],child_overrides_skill:true,parent_hook_not_inherited:true,cycle_refused:true});
}
{
  const v0={...manifest([]),version:0};assert.throws(()=>parseManifest(v0));
  const migrated=await migrateVersionedObject('manifest',v0);assert.equal(migrated.version,1);
  const changedOnlyVersion={...v0,version:1};assert.deepEqual(migrated,changedOnlyVersion);
  await assert.rejects(migrateVersionedObject('manifest',{...v0,version:2}),/newer/);
  record('explicit_migration_bumps_unmapped_old_version',{normal_parser_refuses_v0:true,explicit_migration_accepts_shape_compatible_v0:true,named_migration_chain:false,newer_version_refused:true});
}
const report={record_type:'upstream_component_probe_results/v1',upstream_commit:'2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17',scope:'Isolated component source fixtures; native renderer is stubbed; writer plan injected; no CLI lifecycle, network, model, registry fetch, or real workspace effects',results};
await fs.writeFile(path.join(scratch,'results.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
