"""The sign-up and recovery pages read the daily email limit the service answers with, alike for every address.

The page code under test is the slice of the served `service.js` that asks the
service for a sign-up or recovery link. It runs in a Node `vm` context with a
stand-in `fetch`, fed the exact refusal records the service builds with its
own functions, so the page is compared with the service and not with a second
copy of its answer. Each rule has a known-wrong page, changed in memory only,
that must fail it.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import unittest

from loop_engine.core.service_runtime.account_email import MAIL_BUSY, daily_budget_refusal
from loop_engine.core.service_runtime.http import RETRY_REFUSAL_VERSION, _error_record

ROOT = Path(__file__).resolve().parents[1]
SERVICE_SCRIPT = ROOT / "src/loop_engine/core/service_runtime/web_assets/service.js"
#: 21:00 on October 16, 2026 in Coordinated Universal Time, three hours before the limit resets.
LATE_EVENING = 1_792_184_400
ADDRESSES = ("known.person@example.com", "new.person@example.com")
GENERIC = "The request was not sent. Please try again later."
CHECK = r'''
const vm=require('node:vm');
const source=require('node:fs').readFileSync(0,'utf8'),{answers,addresses}=JSON.parse(process.argv[1]);
const start=source.indexOf('  const accountRequests = {'),end=source.indexOf('  const signupSent = ',start);
if(start<0||end<0)throw new Error('the account link code was not found in the page script');
const code=source.slice(start,end)+';globalThis.requestAccountLink=requestAccountLink;';
async function shown(answer,action,email){
  const sent=[];
  const context=vm.createContext({AbortController,setTimeout,clearTimeout,
    fetch:async(path,options)=>{sent.push({path,body:JSON.parse(options.body)});return {status:answer.status,json:async()=>answer.body};}});
  vm.runInContext(code,context);
  try{await context.requestAccountLink(action,email);return {message:'',sent};}
  catch(error){return {message:error.message,sent};}
}
(async()=>{
  const seen={};
  for(const [name,answer] of Object.entries(answers)){
    seen[name]=[];
    for(const action of ['signup','recovery'])for(const email of addresses){
      const row=await shown(answer,action,email);
      seen[name].push({action,email,message:row.message,sent:row.sent});
    }
  }
  console.log(JSON.stringify(seen));
})().catch(error=>{console.error(error);process.exitCode=1;});
'''


TILES = r'''
const vm=require('node:vm');
const source=require('node:fs').readFileSync(0,'utf8'),records=JSON.parse(process.argv[1]);
const start=source.indexOf('  const accountEmailTiles = mail => {'),end=source.indexOf('  async function loadStaff() {',start);
if(start<0||end<0)throw new Error('the account email tiles were not found in the page script');
const context=vm.createContext({});
vm.runInContext(source.slice(start,end)+';globalThis.accountEmailTiles=accountEmailTiles;',context);
console.log(JSON.stringify(Object.fromEntries(Object.entries(records).map(([name,record])=>[name,context.accountEmailTiles(record)]))));
'''


BRAND_SCRIPT = ROOT / "src/loop_engine/core/service_runtime/web_assets/agentfeeds/account.js"
#: The account forms of the AgentFeeds, AgentFoundry and AgentStudios sites, which share one script.
BRAND = r'''
const vm=require('node:vm');
const source=require('node:fs').readFileSync(0,'utf8'),{answers,addresses}=JSON.parse(process.argv[1]);
const start=source.indexOf('  async function json(response) {'),end=source.indexOf('  function keep(accessToken) {',start);
if(start<0||end<0)throw new Error('the brand request helper was not found in its script');
(async()=>{
  const seen={};
  for(const [name,answer] of Object.entries(answers)){
    seen[name]=[];
    for(const email of addresses){
      const context=vm.createContext({AbortController,setTimeout,clearTimeout,TextDecoder,
        fetch:async()=>new Response(JSON.stringify(answer.body),{status:answer.status})});
      vm.runInContext('let epoch=0,token="";const pending=new Set();'+source.slice(start,end)+';globalThis.request=request;',context);
      try{await context.request('/api/v1/account/signup',{record_type:'service_account_signup_request/v2',email},'',202);seen[name].push('');}
      catch(error){seen[name].push(error.message);}
    }
  }
  console.log(JSON.stringify(seen));
})().catch(error=>{console.error(error);process.exitCode=1;});
'''


def _brand_seen(source):
    result = subprocess.run(["node", "-e", BRAND, json.dumps({"answers": _answers(), "addresses": ADDRESSES})],
                            input=source, cwd=ROOT, text=True, capture_output=True, timeout=60)
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


def _brand_limit_holds(seen):
    """The brand forms show the service's own sentence and the reset, alike for every address."""
    said = _answers()["budget"]["body"]["error"]["message"]
    return (set(seen["budget"]) == {said + " Please try again after 00:00 UTC."}
            and not any(address in message for message in seen["budget"] for address in ADDRESSES)
            and set(seen["busy"]) == {_answers()["busy"]["body"]["error"]["message"]})


def _diagnostics_records(folder):
    """The account email part of the developer diagnostics, as the adapter builds it in four states."""
    from loop_engine.core.service_runtime import account_email_checks as checks
    counted = checks._counted(checks._Provider(), checks._counted_runtime(folder, "counted", checks._Clock(LATE_EVENING)), 95)
    for address in ADDRESSES:
        checks._answer_for(counted, checks._signup_request(address))
    capped = checks._counted(checks._Provider(mail_answers=[checks.DAILY_CAP_ANSWER]),
                             checks._counted_runtime(folder, "capped", checks._Clock(LATE_EVENING)), None)
    try:
        checks._answer_for(capped, checks._signup_request(ADDRESSES[0]))
    except Exception:  # noqa: BLE001 - the refusal is the state under test; the diagnostics record is what the page reads
        pass
    return {"counted": counted.message_budget(), "capped": capped.message_budget(),
            "not_counted": checks._adapter(checks._Provider()).message_budget(),
            "unreadable": {**counted.message_budget(), "readable": False, "code": "store_busy"}}


def _tiles(source, records):
    result = subprocess.run(["node", "-e", TILES, json.dumps(records)], input=source, cwd=ROOT, text=True,
                            capture_output=True, timeout=60)
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


def _refusal(code, status, details):
    return {"status": status, "body": _error_record(code, status, details, "ref_pagecheck0001")}


def _answers():
    """Each answer the page is shown, built by the service's own functions."""
    spent = daily_budget_refusal(LATE_EVENING)
    budget = _refusal(spent.code, spent.status, spent.details)
    unreadable = _refusal(spent.code, spent.status, {**spent.details, "resets_at": "not a time"})
    return {"budget": budget, "budget_without_a_time": unreadable,
            "busy": _refusal(MAIL_BUSY, 503, {"record_type": RETRY_REFUSAL_VERSION, "retry_after_seconds": 1}),
            "inherited_name": _refusal("toString", 503, None)}


def _seen(source):
    result = subprocess.run(["node", "-e", CHECK, json.dumps({"answers": _answers(), "addresses": ADDRESSES})],
                            input=source, cwd=ROOT, text=True, capture_output=True, timeout=60,
                            env={**os.environ, "TZ": "America/New_York"})
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


def _alike_without_an_address(rows):
    """One message for both actions and both addresses, naming no address."""
    messages = {row["message"] for row in rows}
    return len(rows) == 4 and len(messages) == 1 and not any(
        address in message or "@" in message for message in messages for address in ADDRESSES)


def _limit_rules_hold(seen):
    budget, untimed = seen["budget"][0]["message"], seen["budget_without_a_time"][0]["message"]
    return (_alike_without_an_address(seen["budget"]) and _alike_without_an_address(seen["budget_without_a_time"])
            and budget.startswith("Today's limit for sign-up and recovery email is reached, so nothing was sent. "
                                  "Please try again after 00:00 UTC (")
            and budget.endswith(" your time).") and "8:00" in budget
            and untimed == "Today's limit for sign-up and recovery email is reached, so nothing was sent. "
                           "Please try again after 00:00 UTC."
            and all(row["sent"][0]["body"] == {"record_type": ("service_account_signup_request/v2"
                                                              if row["action"] == "signup" else
                                                              "service_account_recovery_request/v1"),
                                               "email": row["email"]} for row in seen["budget"]))


def _mutant(find, replacement):
    source = SERVICE_SCRIPT.read_text(encoding="utf-8")
    if find not in source:
        raise AssertionError("the known-wrong page no longer matches the page script")
    return source.replace(find, replacement, 1)


class AccountLinkPageTests(unittest.TestCase):
    def setUp(self):
        self.seen = _seen(SERVICE_SCRIPT.read_text(encoding="utf-8"))

    def test_the_daily_limit_shows_its_plain_message_and_reset_alike_for_every_address(self):
        self.assertTrue(_limit_rules_hold(self.seen), json.dumps(self.seen["budget"], indent=1))

    def test_a_page_without_the_daily_limit_answer_is_detected(self):
        seen = _seen(_mutant("    account_email_daily_budget_reached:emailLimitAnswer,\n", ""))
        self.assertFalse(_limit_rules_hold(seen))
        self.assertEqual(seen["budget"][0]["message"], GENERIC)

    def test_a_page_that_names_the_address_is_detected(self):
        seen = _seen(_mutant('throw new Error((typeof answer === "function"',
                             'throw new Error(email + " " + (typeof answer === "function"'))
        self.assertFalse(_limit_rules_hold(seen))

    def test_the_provider_rate_asks_for_a_short_wait(self):
        self.assertTrue(_alike_without_an_address(self.seen["busy"]))
        self.assertEqual(self.seen["busy"][0]["message"],
                         "The email service is busy for a moment, so nothing was sent. Please try again in a few seconds.")

    def test_staff_read_todays_count_budget_and_remainder_and_no_address(self):
        import tempfile
        with tempfile.TemporaryDirectory(prefix="account-link-page-") as folder:
            records = _diagnostics_records(Path(folder))
        tiles = _tiles(SERVICE_SCRIPT.read_text(encoding="utf-8"), records)
        self.assertEqual(tiles["counted"], [["Account emails today", "2 of 95"],
                                            ["Account emails left until 00:00 UTC", "93"]])
        self.assertEqual(tiles["capped"], [["Account emails today", "0"],
                                           ["Account emails left until 00:00 UTC",
                                            "None, the mail provider refused at 21:00 UTC and is asked again at 21:15 UTC"]])
        self.assertEqual(tiles["not_counted"], [])
        self.assertEqual(tiles["unreadable"], [["Account emails today", "Not readable now"]])
        self.assertFalse(any(address in json.dumps(tiles) for address in ADDRESSES))
        # The overview hands the diagnostics to the tiles; a page that drops the call shows staff nothing.
        call = "...accountEmailTiles(overview.diagnostics?.account_email)"
        self.assertIn(call, SERVICE_SCRIPT.read_text(encoding="utf-8"))
        self.assertNotIn(call, _mutant(",\n      " + call, ""))

    def test_the_brand_sites_show_the_service_sentence_and_the_reset(self):
        source = BRAND_SCRIPT.read_text(encoding="utf-8")
        self.assertTrue(_brand_limit_holds(_brand_seen(source)))
        changed = source.replace("? ' Please try again after 00:00 UTC.' : ''", "? '' : ''", 1)
        self.assertNotEqual(changed, source)
        self.assertFalse(_brand_limit_holds(_brand_seen(changed)))
        # AgentFoundry and AgentStudios serve the same script with their own names.
        from loop_engine.core.service_runtime import agentfoundry_pages, agentstudios_pages
        for pages in (agentfoundry_pages, agentstudios_pages):
            served = pages.render(pages.ASSET_PREFIX + "account.js")[0].decode()
            self.assertIn("envelope.error?.code === 'account_email_daily_budget_reached'", served)

    def test_an_inherited_name_is_never_read_as_an_answer(self):
        self.assertEqual({row["message"] for row in self.seen["inherited_name"]}, {GENERIC})
        seen = _seen(_mutant('Object.hasOwn(accountAnswers, value?.error?.code ?? "") ? accountAnswers[value.error.code] : ""',
                             'accountAnswers[value?.error?.code]'))
        self.assertNotEqual({row["message"] for row in seen["inherited_name"]}, {GENERIC})


if __name__ == "__main__":
    unittest.main()
