"""Bounded readiness decisions and the full-route check's owning call sites."""
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE = (ROOT / "tools/live_site_readiness.mjs").as_uri()


class LiveSiteReadinessTests(unittest.TestCase):
    def run_node(self, body):
        source = f"import assert from 'node:assert/strict'; import * as check from {MODULE!r};\n" + body
        result = subprocess.run(["node", "--input-type=module", "-e", source], cwd=ROOT,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_heading_and_content_are_independent_final_assertions(self):
        self.run_node("""
const ready={heading:'A real title',documentation:'page',content_state:'ready',content_present:true};
assert.deepEqual(check.readinessProblems(ready),[]);
assert.deepEqual(check.readinessProblems({...ready,heading:''}),['shows no main heading']);
for(const state of ['loading','error','missing','unavailable'])
  assert.ok(check.readinessProblems({...ready,content_state:state}).some(value=>value.includes('content is not ready')));
assert.ok(check.readinessProblems({...ready,content_present:false}).length);
assert.deepEqual(check.readinessProblems({...ready,documentation:null}),[]);
""")

    def test_phone_light_failure_keeps_a_screenshot(self):
        self.run_node("""
for(const size of ['phone','desktop'])for(const scheme of ['light','dark'])
  assert.equal(check.shouldCaptureView({size,scheme,failed:true}),true);
assert.equal(check.shouldCaptureView({size:'phone',scheme:'light',failed:false}),false);
assert.equal(check.shouldCaptureView({size:'phone',scheme:'dark',failed:false}),true);
assert.equal(check.shouldCaptureView({size:'desktop',scheme:'light',failed:false}),true);
""")

    def test_wait_uses_the_same_predicate_and_preserves_initial_failure(self):
        self.run_node("""
const pending={heading:'',ready:false,terminal_failure:false,content_state:'loading',content_present:false};
const ready={...pending,heading:'Real title',ready:true,content_state:'ready',content_present:true};
let value=pending,initialObserved=false,waited=false;
const page={waitForTimeout:async ms=>assert.equal(ms,1500),
  evaluate:async fn=>fn===check.visiblePageState?value:[],
  waitForFunction:async(fn,arg,options)=>{
    assert.equal(fn,check.visiblePageState);assert.equal(arg.documentation,'page');assert.equal(arg.waitForReady,true);
    assert.ok(options.timeout>0&&options.timeout<=10000);assert.ok(initialObserved);waited=true;value=ready;
  }};
const result=await check.observePageReadiness(page,{documentation:'page',onInitialNotReady:async()=>{initialObserved=true;}});
assert.ok(waited);assert.equal(result.readiness.initial.ready,false);assert.equal(result.readiness.final.ready,true);
assert.equal(result.readiness.late,true);assert.equal(result.readiness.timed_out,false);
assert.equal(result.readiness.initial_delay_ms,1500);assert.equal(result.readiness.timeout_after_initial_ms,10000);
""")

    def test_timeout_is_recorded_and_does_not_erase_pending_state(self):
        self.run_node("""
const pending={heading:'Loading',ready:false,terminal_failure:false,documentation:'page',content_state:'loading',content_present:false};
const page={waitForTimeout:async()=>{},evaluate:async fn=>fn===check.visiblePageState?pending:[],
  waitForFunction:async()=>{const error=new Error('deadline');error.name='TimeoutError';throw error;}};
const result=await check.observePageReadiness(page,{documentation:'page',initialDelayMs:0,timeoutMs:20});
assert.equal(result.readiness.timed_out,true);assert.equal(result.seen.ready,false);
assert.equal(result.readiness.errors.length,1);assert.ok(check.readinessProblems(result.seen).length);
""")

    def test_refused_content_is_terminal_but_not_success(self):
        self.run_node("""
const refused={heading:'Documentation',ready:false,terminal_failure:true,documentation:'page',content_state:'error',content_present:false};
const page={waitForTimeout:async()=>{},evaluate:async fn=>fn===check.visiblePageState?refused:[],
  waitForFunction:async()=>{throw new Error('must not retry a terminal refusal');}};
const result=await check.observePageReadiness(page,{documentation:'page',initialDelayMs:0});
assert.equal(result.readiness.timed_out,false);assert.equal(result.readiness.errors.length,0);
assert.equal(result.seen.ready,false);assert.ok(check.readinessProblems(result.seen).length);
""")

    def test_unbounded_or_invalid_waits_are_refused(self):
        self.run_node("""
for(const options of [{timeoutMs:0},{timeoutMs:10001},{timeoutMs:Infinity},{initialDelayMs:-1},{initialDelayMs:1501}])
  await assert.rejects(check.observePageReadiness({},options),/declared bounds/);
""")

    def test_squeezed_text_is_refused_and_ordinary_wrapping_is_not(self):
        self.run_node("""
const {isSqueezed,squeezedTextProblems,SQUEEZED_TEXT}=check;
assert.deepEqual(SQUEEZED_TEXT,{minimumCharacters:24,minimumLines:5,charactersPerLineBelow:6});
// The steps of /case-studies/sign-up-protection on October 16, 2026: 57 characters in 20 lines of two or three letters.
const known={text:'Get started asks for your email address and nothing else.',characters:57,lines:20};
assert.equal(isSqueezed(known),true);
assert.deepEqual(squeezedTextProblems([known]),['squeezes "Get started asks for your email address and nothing else." into 20 lines of about 3 characters']);
for(const ordinary of [{characters:57,lines:2},{characters:400,lines:9},{characters:30,lines:5},{characters:23,lines:23},{characters:60,lines:4}])
  assert.equal(isSqueezed(ordinary),false,JSON.stringify(ordinary));
assert.deepEqual(squeezedTextProblems([{text:'a',characters:57,lines:2}]),[]);
""")

    def test_checkers_use_the_shared_controls_and_final_assertions(self):
        live = (ROOT / "tools/check_live_site_for_people.mjs").read_text()
        self.assertIn('from "./live_site_readiness.mjs"', live)
        self.assertIn("for(const problem of readinessProblems(seen))note(where,problem)", live)
        self.assertIn("if(readiness.timed_out)note(where", live)
        self.assertIn("shouldCaptureView({size:sizeName,scheme,failed:problems.length>firstProblem})", live)
        self.assertIn('documentation:view==="docs"?(address==="/docs"?"index":"page"):null', live)
        self.assertIn("page.evaluate(squeezedTextCandidates,SQUEEZED_TEXT)", live)
        self.assertIn("for(const problem of squeezedTextProblems(squeezed))note(where,problem)", live)
        for name in ("check_documentation_browser.mjs", "check_service_workspace.mjs"):
            source = (ROOT / "tools" / name).read_text()
            self.assertIn('from "./documentation_readiness_checks.mjs"', source)
            self.assertIn("await runDocumentationReadinessChecks({browser,base", source)


if __name__ == "__main__":
    unittest.main()
