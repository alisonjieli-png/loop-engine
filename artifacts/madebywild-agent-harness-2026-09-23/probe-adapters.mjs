// Research only: transpile pinned upstream pure renderers and inspect outputs.
// No upstream CLI, workspace apply, shell hooks, MCP connection or model call.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';

const [source, scratch, output] = process.argv.slice(2);
if (!source || !scratch || !output) throw Error('usage: node probe-adapters.mjs UPSTREAM SCRATCH OUTPUT');
const revision = execFileSync('git', ['rev-parse', 'HEAD'], {cwd: source, encoding:'utf8'}).trim();
if (revision !== '2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17') throw Error('Unreviewed upstream revision');
const {default:ts} = await import(pathToFileURL(path.join(scratch,'node_modules/typescript/lib/typescript.js')));
const relativeFiles = ['utils.ts', 'hooks.ts', ...(await fs.readdir(path.join(source, 'packages/toolkit/src/provider-adapters'))).filter(x=>x.endsWith('.ts')).map(x=>'provider-adapters/'+x)];
const files = [];
for (const relative of relativeFiles) {
  const body = await fs.readFile(path.join(source, 'packages/toolkit/src', relative));
  const target = path.join(scratch, 'modules', relative.replace(/\.ts$/, '.js'));
  await fs.mkdir(path.dirname(target), {recursive:true});
  await fs.writeFile(target, ts.transpileModule(body.toString(), {compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText);
  files.push({path:'packages/toolkit/src/'+relative, sha256:crypto.createHash('sha256').update(body).digest('hex')});
}
await fs.writeFile(path.join(scratch,'modules/package.json'), '{"type":"module"}\n');
const {buildProviderAdapters} = await import(pathToFileURL(path.join(scratch,'modules/provider-adapters/registry.js')));
const adapters = buildProviderAdapters(new Map([['sample', [{path:'SKILL.md', content:'---\nname: sample\ndescription: SAMPLE_SKILL_DESCRIPTION\n---\nSAMPLE_SKILL_BODY\n'},{path:'scripts/sample.py',content:'print("sample")\n'}]]]));
const sections = [{id:'z-first',body:'FIRST_REQUIREMENT'},{id:'a-second',body:'SECOND_REQUIREMENT'},{id:'pkg',body:'PACKAGE_REQUIREMENT',target:'packages/api'}];
const mcp = [{id:'connection',json:{mcpServers:{sample:{type:'stdio',command:'/usr/bin/false',env:{ONLY_SYNTHETIC:'yes'}}}}}];
const subagent = {id:'reviewer',name:'reviewer',description:'Synthetic reviewer',body:'REVIEWER_BODY',metadata:{}};
const hooks = [{id:'gate',mode:'strict',events:{pre_tool_use:[{type:'command',command:'echo synthetic',matcher:'Read'}]}}];
const base = {mcps:[],subagents:[],hooks:[]};
const rows = [];
for (const [provider,adapter] of Object.entries(adapters)) {
  rows.push({provider,
    prompt: adapter.renderPromptSections ? await adapter.renderPromptSections(sections) : null,
    skill: await adapter.renderSkill({id:'sample',files:[],target:'packages/api'}),
    mcp: await adapter.renderMcp(mcp),
    subagent: adapter.renderProviderState && provider==='codex' ? await adapter.renderProviderState({...base,subagents:[subagent]}) : await adapter.renderSubagent(subagent)
  });
}
const observations = [];
async function observe(name,action) {try {observations.push({name,result:await action(),error:null});}catch(error){observations.push({name,result:null,error:String(error.message)});}}
await observe('duplicate_mcp_conflict',()=>adapters.claude.renderMcp([...mcp,{id:'other',json:{mcpServers:{sample:{command:'/usr/bin/true'}}}}]));
await observe('copilot_strict_matcher',()=>adapters.copilot.renderHooks(hooks));
await observe('copilot_best_effort_matcher',()=>adapters.copilot.renderHooks([{...hooks[0],mode:'best_effort'}]));
await observe('codex_settings_override',()=>adapters.codex.renderProviderState({...base,mcps:mcp,settings:{id:'codex',provider:'codex',sourceFormat:'toml',payload:{mcp_servers:{sample:{command:'/usr/bin/true'}}}}}));
await observe('claude_root_prompt',()=>adapters.claude.renderPromptSections([{id:'sample',body:'ONE'}]));
const report = {schema:'baltor.research-render-observations/v1',created_at:new Date().toISOString(),revision,node:process.version,model_calls:0,source_files:files,providers:rows,observations,limits:['Pure upstream renderer functions, with synthetic in-memory canonical inputs.','No end-to-end importer, planner, native hook or subagent execution qualification.']};
await fs.mkdir(path.dirname(output),{recursive:true});
await fs.writeFile(output,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({output,providers:rows.length,observations:observations.length,errors:observations.filter(x=>x.error).map(x=>({name:x.name,error:x.error}))},null,2));
