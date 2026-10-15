"""Evidence-based hosted checker rules, including actual Chromium observations."""

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE = (ROOT / "tools/check_hosted_website.mjs").as_uri()
PLAYWRIGHT = (ROOT / "showcase/node_modules/playwright-core/index.mjs").as_uri()


class HostedWebsiteCheckerRulesTests(unittest.TestCase):
    def run_node(self, source):
        header = (
            "import assert from 'node:assert/strict';\n"
            f"import * as check from {MODULE!r};\n"
        )
        result = subprocess.run(
            ["node", "--input-type=module", "-e", header + source],
            cwd=ROOT, text=True, capture_output=True, timeout=40,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_exact_endpoint_and_media_failure_negative_controls(self):
        self.run_node(r'''
const endpoint="https://brand.example/mcp";
const problems=text=>check.connectionTextProblems({text},endpoint);
assert.deepEqual(problems(endpoint),[]);
assert.deepEqual(problems(JSON.stringify({url:endpoint})),[]);
for(const wrong of [endpoint+"-evil",endpoint+"/other",endpoint+"?extra=1",endpoint+"#fragment",
  "https://brand.example.evil/mcp","https://other.example/mcp","http://brand.example/mcp",
  "https://user@brand.example/mcp","https://brand.example/not-mcp"])
  assert.ok(problems(wrong).length,wrong);
assert.ok(check.connectionTextProblems({text:endpoint},endpoint,{requireBearer:true}).length);
assert.deepEqual(check.connectionTextProblems({text:endpoint+' Authorization: Bearer <reference>'},endpoint,{requireBearer:true}),[]);
assert.ok(check.connectionTextProblems({text:endpoint},endpoint+"?extra=1").length);
const event={url:"https://brand.example/a.mp4",method:"GET",resourceType:"media",error:"net::ERR_ABORTED",status:206};
const accepted=value=>check.isVerifiedMediaAbort(value,"https://brand.example");
assert.equal(accepted(event),true);
assert.equal(accepted({...event,status:200}),true);
assert.equal(accepted({...event,resourceType:"other"}),true);
for(const status of [null,0,204,301,404,429,500,503])assert.equal(accepted({...event,status}),false);
for(const resourceType of ["script","stylesheet","fetch","xhr","document","font"])
  assert.equal(accepted({...event,resourceType}),false);
for(const error of ["net::ERR_NAME_NOT_RESOLVED","net::ERR_CERT_AUTHORITY_INVALID","net::ERR_BLOCKED_BY_CORS","net::ERR_FAILED"])
  assert.equal(accepted({...event,error}),false);
assert.equal(accepted({...event,url:"https://other.example/a.mp4"}),false);
assert.equal(accepted({...event,method:"POST"}),false);
assert.equal(accepted({...event,resourceType:"other",url:"https://brand.example/prefetch"}),false);
''')

    def test_readonly_values_require_actual_browser_visibility(self):
        self.run_node(f"import {{chromium}} from {PLAYWRIGHT!r};\n" + r'''
const browser=await chromium.launch({executablePath:process.env.CHROME_BINARY||"/opt/google/chrome/chrome",headless:true,args:["--no-sandbox"]});
try{
  const page=await browser.newPage();
  const endpoint="https://brand.example/mcp";
  await page.setContent(`<p>Connect your harness</p><input readonly value="${endpoint}"><textarea readonly>Authorization: Bearer &lt;reference&gt;</textarea>`);
  assert.equal((await page.locator("body").innerText()).includes(endpoint),false);
  const good=await page.evaluate(check.visibleConnectionText);
  assert.deepEqual(check.connectionTextProblems(good,endpoint,{requireBearer:true}),[]);
  for(const wrapper of [
    '<div hidden>CONTENT</div>', '<div style="display:none">CONTENT</div>',
    '<div style="visibility:hidden">CONTENT</div>', '<div style="opacity:0">CONTENT</div>',
    '<div style="content-visibility:hidden">CONTENT</div>',
    '<details><summary>Closed</summary>CONTENT</details>'
  ]){
    await page.setContent(wrapper.replace("CONTENT",`<input readonly value="${endpoint}">`));
    assert.ok(check.connectionTextProblems(await page.evaluate(check.visibleConnectionText),endpoint).length,wrapper);
  }
  for(const markup of [
    `<input value="${endpoint}">`, `<textarea>${endpoint}</textarea>`, `<input readonly type="hidden" value="${endpoint}">`,
    `<input readonly type="password" value="${endpoint}">`, `<input readonly type="checkbox" value="${endpoint}">`,
    `<input readonly style="width:0;height:0;padding:0;border:0" value="${endpoint}">`,
    `<span style="opacity:0">${endpoint}</span>`, `<input readonly value="${endpoint}-evil">`
  ]){
    await page.setContent(markup);
    assert.ok(check.connectionTextProblems(await page.evaluate(check.visibleConnectionText),endpoint).length,markup);
  }
  await page.setContent(`<textarea readonly>${endpoint}</textarea>`);
  await page.locator("textarea").evaluate(node=>{node.value="https://other.example/mcp";});
  assert.ok(check.connectionTextProblems(await page.evaluate(check.visibleConnectionText),endpoint).length);
  await page.setContent(`<p>${endpoint}</p>`);
  assert.deepEqual(check.connectionTextProblems(await page.evaluate(check.visibleConnectionText),endpoint),[]);
}finally{await browser.close();}
''')

    def test_request_identity_status_and_browser_failures(self):
        self.run_node(f"import {{chromium}} from {PLAYWRIGHT!r};\n" + r'''
import http from "node:http";
import {EventEmitter,once} from "node:events";
const mock=new EventEmitter(),accounting=check.createRequestAccounting("https://brand.example");
accounting.attach(mock);
const request=(status=null,error="net::ERR_ABORTED")=>({url:()=>"https://brand.example/a.mp4",method:()=>"GET",resourceType:()=>"media",failure:()=>({errorText:error}),response:async()=>status===null?null:{status:()=>status}});
const earlier=request(404),later=request(200),unknown=request();
mock.emit("response",{request:()=>earlier,status:()=>404});
mock.emit("response",{request:()=>later,status:()=>200});
mock.emit("requestfailed",earlier);mock.emit("requestfailed",later);mock.emit("requestfailed",unknown);
const result=await accounting.settle();
assert.equal(result.httpErrors.length,1);
assert.equal(result.requestFailures.length,3);
assert.equal(result.failedRequests.length,2);
assert.equal(result.abortedMediaPreviews.length,1);
assert.equal(result.failedRequests[0].status,404);
assert.equal(result.failedRequests[1].status,null);

const sockets=new Set();
const server=http.createServer((req,res)=>{
  if(req.url==="/missing"){res.writeHead(404);res.end("missing");return;}
  res.writeHead(200,{"Content-Type":"text/html"});res.end("<!doctype html><title>Local checker fixture</title>");
});
server.on("connection",socket=>{sockets.add(socket);socket.on("close",()=>sockets.delete(socket));});
server.listen(0,"127.0.0.1");await once(server,"listening");
const origin=`http://127.0.0.1:${server.address().port}`;
const browser=await chromium.launch({executablePath:process.env.CHROME_BINARY||"/opt/google/chrome/chrome",headless:true,args:["--no-sandbox"]});
try{
  const page=await browser.newPage(),live=check.createRequestAccounting(origin);live.attach(page);
  await page.goto(origin);
  await page.route("**/abort.mp4",route=>route.abort("aborted"));
  const failure=page.waitForEvent("requestfailed",{predicate:r=>r.url()===origin+"/abort.mp4",timeout:5000});
  await page.evaluate(()=>{const video=document.createElement("video");video.src="/abort.mp4";video.preload="auto";document.body.append(video);video.load();});
  await failure;
  await page.evaluate(()=>fetch("/missing"));
  await page.close();
  const observed=await live.settle();
  assert.equal(observed.abortedMediaPreviews.length,0,JSON.stringify(observed));
  assert.equal(observed.requestFailures.length,1);
  assert.equal(observed.failedRequests.length,1);
  assert.equal(observed.failedRequests[0].status,null);
  assert.equal(observed.failedRequests[0].error,"net::ERR_ABORTED");
  assert.equal(observed.httpErrors.length,1);
  assert.equal(observed.httpErrors[0].status,404);
}finally{await browser.close();for(const socket of sockets)socket.destroy();await new Promise(resolve=>server.close(resolve));}
''')


if __name__ == "__main__":
    unittest.main()
