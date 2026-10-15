"""Evidence-based hosted checker rules, including actual Chromium observations."""

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE = (ROOT / "tools/check_hosted_website.mjs").as_uri()
PLAYWRIGHT = (ROOT / "showcase/node_modules/playwright-core/index.mjs").as_uri()
BROWSER_CANDIDATES = ([os.environ["CHROME_BINARY"]] if os.environ.get("CHROME_BINARY") else [
    os.environ.get("LOOP_SHOWCASE_BROWSER"), "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable", "/opt/google/chrome/chrome",
    "/usr/bin/chromium", "/snap/bin/chromium",
])
BROWSER_EXECUTABLE = next((path for path in BROWSER_CANDIDATES
                           if path and Path(path).is_file() and os.access(path, os.X_OK)), None)
BROWSER_AVAILABLE = (ROOT / "showcase/node_modules/playwright-core/index.mjs").is_file() and bool(BROWSER_EXECUTABLE)
BROWSER_REQUIREMENT = "Browser qualification requires showcase npm dependencies and Chrome; pure rules still run."


class HostedWebsiteCheckerRulesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get("BALTOR_REQUIRE_BROWSER_CHECKER_TESTS") == "1" and not BROWSER_AVAILABLE:
            raise RuntimeError("Required browser qualification cannot run: install showcase npm dependencies and Chrome.")

    def run_node(self, source):
        header = (
            "import assert from 'node:assert/strict';\n"
            f"import * as check from {MODULE!r};\n"
        )
        # Chrome fails to launch under a deeply nested shard TMPDIR on Linux.
        # Give only this child a fresh short temp root, not an existing browser
        # profile. The pre-push credential-free environment is otherwise intact.
        # Use the existing home-based fixture pattern rather than quota-bound /tmp.
        with tempfile.TemporaryDirectory(prefix=".hc-", dir=Path.home()) as temporary:
            result = subprocess.run(
                ["node", "--input-type=module", "-e", header + source],
                cwd=ROOT, text=True, capture_output=True, timeout=40,
                env={**os.environ, "TMPDIR": temporary,
                     **({"CHROME_BINARY": BROWSER_EXECUTABLE} if BROWSER_EXECUTABLE else {})},
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_child_temp_directory_is_short_private_and_removed_after_success_or_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder) / ("long-browser-parent-" * 6)
            parent.mkdir()
            for fail in (False, True):
                with self.subTest(fail=fail), mock.patch.dict(os.environ, {"TMPDIR": str(parent)}):
                    selected = []
                    def inspect_child(command, **options):
                        temporary = Path(options["env"]["TMPDIR"])
                        selected.append(temporary)
                        self.assertEqual(temporary.parent, Path.home())
                        self.assertLess(len(os.fsencode(temporary)), len(os.fsencode(parent)))
                        self.assertEqual(temporary.stat().st_mode & 0o777, 0o700)
                        expected = {**os.environ, "TMPDIR": str(temporary),
                                    **({"CHROME_BINARY": BROWSER_EXECUTABLE} if BROWSER_EXECUTABLE else {})}
                        self.assertEqual(options["env"], expected)
                        if fail:
                            raise subprocess.TimeoutExpired(command, options["timeout"])
                        return subprocess.CompletedProcess(command, 0, "", "")
                    with mock.patch.object(subprocess, "run", side_effect=inspect_child):
                        if fail:
                            with self.assertRaises(subprocess.TimeoutExpired):
                                self.run_node("// controlled timeout")
                        else:
                            self.run_node("// controlled success")
                    self.assertEqual(os.environ["TMPDIR"], str(parent))
                    self.assertEqual(len(selected), 1)
                    self.assertFalse(selected[0].exists())

    def test_required_browser_mode_cannot_silently_skip(self):
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "tools.test_hosted_website_checker_rules.HostedWebsiteCheckerRulesTests.test_readonly_values_require_actual_browser_visibility"],
            cwd=ROOT, text=True, capture_output=True, timeout=15,
            env={**os.environ, "BALTOR_REQUIRE_BROWSER_CHECKER_TESTS": "1",
                 "CHROME_BINARY": str(ROOT / "intentionally-missing-browser-negative-control")},
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Required browser qualification cannot run", result.stdout + result.stderr)

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

    @unittest.skipUnless(BROWSER_AVAILABLE, BROWSER_REQUIREMENT)
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

    def test_request_status_is_scoped_to_one_request(self):
        self.run_node(r'''
import {EventEmitter} from "node:events";
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
''')

    @unittest.skipUnless(BROWSER_AVAILABLE, BROWSER_REQUIREMENT)
    def test_real_browser_aborts_and_http_errors_remain_failures(self):
        self.run_node(f"import {{chromium}} from {PLAYWRIGHT!r};\n" + r'''
import http from "node:http";
import {once} from "node:events";
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
