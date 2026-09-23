// Source-only isolated probes. No application startup, SDK calls, install, or network.
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
const [upstream,out,deps] = process.argv.slice(2);
const ts=(await import(pathToFileURL(path.join(deps,'typescript/lib/typescript.js')).href)).default;
const sources=[];
for(const [source,name] of [['apps/server/src/config.ts','config'],['packages/backends/src/openbot.ts','openbot']]){
  const body=await fs.readFile(path.join(upstream,source),'utf8');
  const transformed=body.replace('"zod"',JSON.stringify(pathToFileURL(path.join(deps,'zod/index.js')).href));
  await fs.writeFile(path.join(out,name+'.mjs'),ts.transpileModule(transformed,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText);
  sources.push({path:source,sha256:crypto.createHash('sha256').update(body).digest('hex')});
}
const {readConfig,assertApiDeploymentConfig}=await import(pathToFileURL(path.join(out,'config.mjs')).href);
assert.throws(()=>readConfig(),/requires CPK_INTELLIGENCE_API_KEY/);
assert.throws(()=>assertApiDeploymentConfig({mode:'sample'}),/requires CPK_INTELLIGENCE_API_KEY/);
process.env.CPK_INTELLIGENCE_API_KEY='synthetic-not-real-key';
const config=readConfig();assert.equal(config.mode,'sample');assert.equal(config.intelligenceApiKey,'synthetic-not-real-key');
delete process.env.CPK_INTELLIGENCE_API_KEY;
const {OpenBotAdapter}=await import(pathToFileURL(path.join(out,'openbot.mjs')).href);
let calls=0;
const transport={runtimeUrl:'https://example.invalid/api/copilotkit',request:async()=>{calls++;return new Response('{}',{status:500});}};
const disabled=new OpenBotAdapter({transport});assert.deepEqual(await disabled.probe(),{state:'disabled'});assert.equal(calls,0);
const enabled=new OpenBotAdapter({enabled:true,transport,agentId:'fixture'});
await assert.rejects(enabled.navigate('fixture',{url:'https://example.invalid/page'}),e=>e.outcomeUnknown===true&&e.code==='http_error');assert.equal(calls,1);
await assert.rejects(enabled.snapshot('fixture'),e=>e.outcomeUnknown===false&&e.code==='http_error');assert.equal(calls,2);
assert.equal(enabled.runtime().mode,'intelligence');
const invalid=new OpenBotAdapter({enabled:true,transport:{...transport,request:async()=>new Response('{}',{status:200})}});
await assert.rejects(invalid.navigate('fixture',{url:'https://example.invalid/page'}),e=>e.outcomeUnknown===true&&e.code==='invalid_response');
const report={record_type:'openmuse_component_source_probe/v1',commit:'bb7ce4e1c6e523bf282a655c63621e3ed9e75150',sources,results:[
{id:'sample_requires_intelligence_key',passed:true,scope:'readConfig and createApp precondition helper; no app started'},
{id:'synthetic_key_allows_sample_config_construction',passed:true,scope:'No key validation or service connection'},
{id:'disabled_openbot_no_transport_call',passed:true},
{id:'mutation_500_is_uncertain_and_not_retried',passed:true,physical_injected_calls:1},
{id:'snapshot_500_is_not_mutation_uncertainty',passed:true,physical_injected_calls:1},
{id:'invalid_mutation_response_is_uncertain',passed:true},
{id:'openbot_runtime_identifies_intelligence_transport',passed:true}
],limits:['Synthetic in-process transport; no HTTP, model, database, SDK runtime, browser or Docker started','Does not qualify live OpenBot integration or durable task race behavior','No upstream tests rerun'],model_calls:0};
await fs.writeFile(path.join(out,'results.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
