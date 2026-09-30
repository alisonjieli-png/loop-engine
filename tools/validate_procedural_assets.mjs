/* Independent format check using an explicitly selected local Khronos validator.
   No downloads, network, rendering or admission; the report path must be new. */
import {createRequire} from "node:module";
import {spawnSync} from "node:child_process";
import {existsSync,writeFileSync} from "node:fs";
import {resolve,isAbsolute} from "node:path";
const [validatorPath,output]=process.argv.slice(2),root=resolve(new URL("..",import.meta.url).pathname);
if(!validatorPath||!isAbsolute(validatorPath)||!output||!isAbsolute(output)||existsSync(output))throw new Error("Use an absolute installed validator module path and a new absolute report path");
const validator=createRequire(import.meta.url)(validatorPath);
const source=`import json
from tools.procedural_assets.catalogue import FAMILIES, construct, reference_cases
from tools.procedural_assets.geometry import gltf
print(json.dumps([dict(family=f, case=n, model=gltf(construct(f, **p))) for f in FAMILIES for n,p in reference_cases(f)]))`;
const generated=spawnSync(resolve(root,".venv/bin/python"),["-c",source],{cwd:root,env:{PATH:process.env.PATH,PYTHONPATH:root},maxBuffer:64*1024*1024,encoding:"utf8"});
if(generated.status!==0)throw new Error("Local generator failed: "+generated.stderr.slice(0,1000));
const rows=JSON.parse(generated.stdout),results=[];
for(const row of rows){
  const report=await validator.validateString(JSON.stringify(row.model),{uri:row.family+"/"+row.case+".gltf",maxIssues:20,
    externalResourceFunction:async()=>{throw new Error("External resources are not permitted");}});
  results.push({family:row.family,case:row.case,issues:report.issues});
}
const broken=structuredClone(rows[0].model);broken.meshes[0].primitives[0].attributes.POSITION=999999;
const mutant=await validator.validateString(JSON.stringify(broken),{maxIssues:20});
const errors=results.reduce((n,row)=>n+row.issues.numErrors,0),warnings=results.reduce((n,row)=>n+row.issues.numWarnings,0);
const record={record_type:"procedural_asset_format_validation/v1",validator_version:validator.version(),cases:rows.length,
  errors,warnings,broken_accessor_detected:mutant.issues.numErrors>0,results,
  limits:"Format validation only. Not native-engine import, gameplay, animation or aesthetic qualification."};
writeFileSync(output,JSON.stringify(record,null,2)+"\n");
console.log(JSON.stringify({cases:rows.length,errors,warnings,broken_accessor_detected:record.broken_accessor_detected}));
process.exitCode=errors===0&&record.broken_accessor_detected?0:1;
