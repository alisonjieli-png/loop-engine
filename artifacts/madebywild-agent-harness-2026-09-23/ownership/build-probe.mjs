// Component source audit only. No upstream CLI, install, or lifecycle invocation.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
const [upstream, output, dependencies] = process.argv.slice(2);
if (!upstream || !output || !dependencies) throw new Error('Expected upstream, output, dependency roots');
const ts = (await import(pathToFileURL(path.join(dependencies, 'typescript/lib/typescript.js')).href)).default;
const records = [];
const hash = body => crypto.createHash('sha256').update(body).digest('hex');
const toolkit = 'packages/toolkit/src/';
async function read(relative) {
  const source = await fs.readFile(path.join(upstream, relative), 'utf8');
  records.push({path:relative, sha256:hash(source)});
  return source;
}
async function write(name, source, notes = 'Full module; type erasure and import location changes only') {
  source = source.replaceAll('"@madebywild/agent-harness-manifest"', '"./manifest.mjs"')
    .replaceAll('"./providers.js"', '"./providers-fixture.mjs"')
    .replaceAll('"./versioning.js"', '"./schema-versioning.mjs"')
    .replaceAll('"zod"', JSON.stringify(pathToFileURL(path.join(dependencies,'zod/index.js')).href))
    .replaceAll('"yaml"', JSON.stringify(pathToFileURL(path.join(dependencies,'yaml/dist/index.js')).href))
    .replace(/(["']\.\/[^"']+)\.js(["'])/g, '$1.mjs$2');
  const compiled = ts.transpileModule(source, {compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}, reportDiagnostics:true});
  const errors = (compiled.diagnostics ?? []).filter(d=>d.category===ts.DiagnosticCategory.Error);
  if(errors.length) throw new Error(JSON.stringify(errors));
  await fs.writeFile(path.join(output,name+'.mjs'), compiled.outputText);
  records.push({compiled:name+'.mjs',sha256:hash(compiled.outputText),scope:notes});
}
await fs.mkdir(output, {recursive:true});
for (const name of ['utils','paths','env','behavior','repository','planner']) await write(name, await read(toolkit+name+'.ts'));
await write('manifest', await read('packages/manifest-schema/src/index.ts'));
await write('schema-versioning', await read('packages/manifest-schema/src/versioning.ts'));
await write('migration-registry', await read(toolkit+'versioning/registry.ts'));
const engine = await read(toolkit+'engine.ts');
const apply = engine.slice(engine.indexOf('  async apply(): Promise<ApplyResult> {'),engine.indexOf('  async watch('));
await write('writer', `import fs from 'node:fs/promises'; import path from 'node:path';
import {ensureParentDir,readTextIfExists,stableStringify} from './utils.js';
import {removeIfExists,writeLock,writeManagedIndex} from './repository.js';
import {resolveHarnessPaths} from './paths.js';
export class ProbeEngine {constructor(cwd,fixturePlan){this.cwd=cwd;this.fixturePlan=fixturePlan;}
async planInternal(){return this.fixturePlan;}
${apply}\n}`, 'Exact HarnessEngine.apply body in fixture wrapper; injected precomputed plan');
const registry = await read(toolkit+'entity-registries.ts');
const errorClass=registry.slice(registry.indexOf('export class RegistryError'),registry.indexOf('export interface FetchedEntityBase'));
const reader=registry.slice(registry.indexOf('async function readSkillFiles('),registry.indexOf('async function readFileWithNotFound('));
const helpers=registry.slice(registry.indexOf('function isSkillOverrideFile('));
await write('registry-probe', `import fs from 'node:fs/promises';import path from 'node:path';
import {listFilesRecursively} from './repository.js';import {normalizeRelativePath,sha256} from './utils.js';
${errorClass}\n${reader}\n${helpers}\nexport {readSkillFiles,buildGitCloneCommand,toAuthHeader,cloneErrorMessage};`, 'Exact registry reader and clone-argument/error helpers; network fetch is excluded');
const presets=await read(toolkit+'presets.ts');
await write('presets-probe',presets.slice(presets.indexOf('const INHERITABLE_OP_TYPES'))+'\nexport {resolvePresetChain};','Exact private inheritance helpers, exported for fixtures');
const migration=await read(toolkit+'versioning/migrate.ts');
await write('migration-probe', `import {detectDocumentVersion,LATEST_VERSION_BY_KIND,parseManifest,parseProviderOverride} from './manifest.mjs';
import {defaultMigrationRegistry,resolveMigrationChain,runMigrationChain} from './migration-registry.mjs';
${migration.slice(migration.indexOf('async function migrateVersionedObject('),migration.indexOf('async function deriveLatestState('))}
export {migrateVersionedObject};`, 'Exact private version migration and parse helper; doctor/file migration excluded');
await fs.writeFile(path.join(output,'providers-fixture.mjs'), `export function buildBuiltinAdapters(){return Object.fromEntries(['codex','claude','copilot','cursor'].map(provider=>[provider,{renderPromptSections:async()=>globalThis.__artifacts.filter(a=>a.provider===provider)}]));}\n`);
await fs.copyFile(path.join(upstream,'LICENSE'),path.join(output,'UPSTREAM-LICENSE'));
await fs.writeFile(path.join(output,'source-fingerprints.json'),JSON.stringify({record_type:'upstream_component_probe_build/v1',dependency:'typescript@5.9.3,zod@4.4.3,yaml@2.8.2',records},null,2)+'\n');
console.log(JSON.stringify({compiled_modules:records.filter(r=>r.compiled).length,output}));
