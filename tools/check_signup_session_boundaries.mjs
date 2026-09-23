/* Security regression using the existing browser suite's loopback fixture program.
   The local program is trusted repository test code, never fetched content. */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {spawn} from "node:child_process";
import {createInterface} from "node:readline";
import {readFileSync,writeFileSync,existsSync} from "node:fs";
import {resolve} from "node:path";
import vm from "node:vm";
import {runSignupSessionBoundaries} from "./signup_session_boundary_checks.mjs";
const root=resolve(new URL("..",import.meta.url).pathname),output=resolve(process.argv[2]);
if(!process.argv[2]||existsSync(output))throw new Error("Supply a new evidence path");
const source=readFileSync(resolve(root,"tools/check_service_workspace.mjs"),"utf8");
const declaration=source.slice(source.indexOf("const program=`"),source.indexOf("const child=spawn"));
const program=vm.runInNewContext(declaration+"\nprogram;",{}, {timeout:1000});
const child=spawn(resolve(root,".venv/bin/python"),["-u","-c",program],{cwd:root,env:{...process.env,PYTHONPATH:"src"},stdio:["pipe","pipe","pipe"]});
const lines=createInterface({input:child.stdout});
const fixture=await new Promise((accept,reject)=>{const timer=setTimeout(()=>reject(new Error("fixture startup deadline")),15000);lines.once("line",line=>{clearTimeout(timer);accept(JSON.parse(line))});child.once("exit",code=>reject(new Error("fixture stopped: "+code)));});
const checks=[];let browser,mutationApplied=false;const mutation=process.argv[3]||"";
const check=(name,passed,detail={})=>checks.push({name,passed:passed===true,detail});
try{browser=await chromium.launch({executablePath:"/opt/google/chrome/chrome",headless:true,args:["--no-sandbox"]});
 ({mutationApplied}=await runSignupSessionBoundaries(browser,fixture,check,mutation));}
finally{await browser?.close();child.stdin.end("\n");lines.close();}
writeFileSync(output,JSON.stringify({record_type:"signup_session_boundary_checks/v1",scope:"real browser; loopback identity and email stand-in only",checks,mutation,mutation_applied:mutationApplied,passed:checks.every(c=>c.passed)},null,2)+"\n",{flag:"wx"});console.log(JSON.stringify({checks:checks.length,failed:checks.filter(c=>!c.passed).map(c=>c.name),output}));process.exitCode=checks.every(c=>c.passed)?0:1;
