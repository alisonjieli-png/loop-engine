/* Browser regression scenarios shared by the full service suite and the focused replay.
   Identity and email are the existing loopback stand-in; no provider call occurs. */
import {randomBytes} from "node:crypto";
const changes={omit_invalidation:['confirmation = null; $("confirm-password").value = ""; $("confirm-password-again").value = ""; showConfirmation();',""],omit_async_guards:["if (!current()) return;", ""]};

export async function runSignupSessionBoundaries(browser,fixture,check,mutation="") {
 const blocked=[];let mutationApplied=false;const context=await browser.newContext();
 try {
await context.route("**/*",route=>[fixture.base,fixture.confirm_base,fixture.confirm_identity_origin].includes(new URL(route.request().url()).origin)?route.continue():(blocked.push(new URL(route.request().url()).origin),route.abort()));
 if(mutation){if(!changes[mutation])throw new Error("unknown mutation");await context.route(url=>url.origin===fixture.confirm_base&&url.pathname==="/assets/service.js",async route=>{const response=await route.fetch(),body=await response.text(),[old,replacement]=changes[mutation],changed=body.split(old).join(replacement);mutationApplied=changed!==body;await route.fulfill({response,body:changed});});}
 const page=await context.newPage(),service=fixture.confirm_base,provider=fixture.confirm_identity_origin;
 const identity=randomBytes(5).toString("hex"),emailA=identity+"-pending-a@example.invalid",emailB=identity+"-other-b@example.invalid",originalB="Fixture_B_password_19",replacement="Fixture_replacement_password_29";
 const message=async email=>{const r=await page.request.get(provider+"/stand-in/outbox?to="+encodeURIComponent(email));return r.json();};
 const signup=async email=>{const r=await page.request.post(service+"/api/v1/account/signup",{data:{record_type:"service_account_signup_request/v2",email}});if(r.status()!==202)throw new Error("signup fixture refused");const m=await message(email);return m.messages.at(-1).text.split(/\s+/).find(x=>x.includes("/auth/confirm?"));};
 const linkA=await signup(emailA),linkB=await signup(emailB),queryB=new URL(linkB).searchParams;
 const beforeVerify=(await message(emailA)).calls.verify||0;
 const verifiedB=await page.request.post(provider+"/auth/v1/verify",{data:{token_hash:queryB.get("token_hash"),type:queryB.get("type")}});const sessionB=await verifiedB.json();
 const setB=await page.request.put(provider+"/auth/v1/user",{headers:{Authorization:"Bearer "+sessionB.access_token},data:{password:originalB}});if(setB.status()!==200)throw new Error("second account setup failed");
 await page.goto(linkA);await page.waitForFunction(()=>document.getElementById("confirm-form")?.getClientRects().length&&document.getElementById("email-login")?.hidden===false);
 await page.fill('#confirm-password',emailA);await page.fill('#confirm-password-again',emailA);await page.click('#confirm-button');
 await page.waitForFunction(()=>document.getElementById('confirm-message')?.classList.contains('error'));
 check("a_verified_pending_confirmation_can_be_held_without_activating",(await message(emailA)).calls.verify===beforeVerify+2&&await page.locator('#connection-state').innerText()==="Not connected");
 await page.evaluate(()=>{history.pushState({},"","/login");dispatchEvent(new PopStateEvent('popstate'));});
 await page.fill('#login-email',emailB);await page.fill('#login-password',originalB);await page.click('#email-login-button');await page.waitForFunction(()=>document.getElementById('connection-state').textContent==="Connected");
 const before=(await message(emailA)).calls.set_password;
 await page.evaluate(()=>{history.pushState({},"","/auth/confirm");dispatchEvent(new PopStateEvent('popstate'));});
 const formVisible=await page.locator('#confirm-form').isVisible();
 if(formVisible){await page.fill('#confirm-password',replacement);await page.fill('#confirm-password-again',replacement);await page.click('#confirm-button');await page.waitForFunction(()=>!document.getElementById('confirm-button').disabled);}
 const after=(await message(emailA)).calls.set_password;
 const attempt=async password=>(await page.request.post(provider+"/auth/v1/token?grant_type=password",{data:{email:emailB,password}})).status();
 const oldStatus=await attempt(originalB),newStatus=await attempt(replacement);
 check("a_stale_confirmation_never_changes_the_new_sessions_password",after===before&&oldStatus===200&&newStatus===400,{password_writes_before:before,password_writes_after:after,original_password_status:oldStatus,replacement_password_status:newStatus});
 for(const stage of ["verify","password"]){
  const email=identity+"-pending-"+stage+"@example.invalid",link=await signup(email);
  await page.goto(link);await page.waitForFunction(()=>document.getElementById("confirm-form")?.getClientRects().length&&document.getElementById("email-login")?.hidden===false);
  let release,started;const gate=new Promise(resolve=>release=resolve),held=new Promise(resolve=>started=resolve),path=stage==="verify"?"/auth/v1/verify":"/auth/v1/user";
  const before=(await message(email)).calls.set_password||0;let activations=0;
  const track=request=>{if(new URL(request.url()).pathname==="/api/v1/account/activate")activations++;};page.on('request',track);
  await page.route(provider+path,async route=>{if(route.request().method()!==(stage==="verify"?"POST":"PUT"))return route.continue();const response=await route.fetch();started();await gate;await route.fulfill({response});});
  await page.fill('#confirm-password',replacement);await page.fill('#confirm-password-again',replacement);await page.click('#confirm-button');
  let deadline;try{await Promise.race([held,new Promise((_,reject)=>{deadline=setTimeout(()=>reject(new Error("held confirmation stage deadline")),10000);})]);}finally{clearTimeout(deadline);}
  // Exercise the existing disconnect action directly because confirmation has not yet exposed signed-in navigation.
  await page.evaluate(()=>document.getElementById('disconnect').click());release();
  await page.waitForFunction(()=>document.getElementById('confirm-button').disabled===false);
  const after=(await message(email)).calls.set_password||0;
  check(`disconnect_during_${stage}_never_reactivates_the_page`,activations===0&&await page.locator('#connection-state').innerText()==="Not connected"&&after-before===(stage==="password"?1:0),{activations,password_writes:after-before});
  await page.unroute(provider+path);page.off('request',track);
 }
 await page.goto(fixture.base+"/get-started");await page.waitForFunction(()=>document.getElementById('service-status').textContent==="Service available");
 check("closed_registration_without_waitlist_offers_no_missing_form",await page.locator('#funnel-invite').getAttribute('href')==="/login"&&await page.locator('#funnel-invite').innerText()==="Sign in"&&await page.locator('#funnel-signup-form').isHidden()&&await page.locator('#funnel-signin').isHidden());
 check("no_external_requests",blocked.length===0,{blocked});
 }catch(error){check("session_boundary_probe_completed",false,{error:String(error).replace(/https?:\/\/\S+/g,"[address]")});}
 finally{await context.close();}
 return {mutationApplied};
}
