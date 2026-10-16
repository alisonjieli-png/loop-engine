/* AgentFeeds view adapter for the existing identity and service account contracts.
   No account/tenant selection is accepted from the page; the service owns access. */
"use strict";
(() => {
  const note = document.querySelector('[data-account-status]');
  if (!note) return;
  const forms = [...document.querySelectorAll('[data-account-form]')];
  const key = 'agentfeeds.identity-session', pending = new Set();
  let client = null, settings = null, token = '', epoch = 0, busy = false, expiryTimer, confirmation = null, passwordSet = false;
  const query = new URLSearchParams(location.search);
  if (location.pathname === '/auth/confirm') {
    const hashes = query.getAll('token_hash'), types = query.getAll('type');
    if (hashes.length === 1 && /^[A-Za-z0-9_-]{1,256}$/.test(hashes[0]) && types.length === 1 && ['signup','recovery'].includes(types[0]))
      confirmation = {hash:hashes[0],type:types[0],session:null,email:''};
    history.replaceState({}, '', '/auth/confirm');
  } else if (location.pathname === '/auth/callback') {
    history.replaceState({}, '', '/login');
  }
  const oauthIds = query.getAll('oauth_authorization_id');
  const oauthId = oauthIds.length === 1 && window.BaltorOAuthConsent?.validId(oauthIds[0]) ? oauthIds[0] : '';
  function say(text, error = false) {
    note.textContent = text; note.dataset.state = error ? 'error' : 'status';
    if (error) { note.tabIndex = -1; note.focus(); }
  }
  function clear() {
    epoch++; token = ''; clearTimeout(expiryTimer);
    for (const controller of pending) controller.abort(); pending.clear();
    try { sessionStorage.removeItem(key); } catch (_) {}
    const details = document.querySelector('[data-account-details]'); if (details) details.hidden = true;
    const login = document.querySelector('[data-account-login]'); if (login) login.hidden = false;
  }
  async function json(response) {
    if (!response.body) throw Error('The service returned an empty response.');
    const reader = response.body.getReader(), chunks = []; let bytes = 0;
    try { for (;;) { const part = await reader.read(); if (part.done) break; bytes += part.value.length; if (bytes > 131072) throw Error('The response was too large.'); chunks.push(part.value); } }
    catch (error) { await reader.cancel(); throw error; }
    const body = new Uint8Array(bytes); let offset = 0; for (const part of chunks) { body.set(part,offset); offset += part.length; }
    return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(body));
  }
  const stale = () => Object.assign(Error('The account changed. Start this action again.'),{stale:true});
  async function request(path, payload = null, credential = token, expectedStatus = 200) {
    const before = epoch, controller = new AbortController(); pending.add(controller);
    const timeout = setTimeout(() => controller.abort(), payload ? 35000 : 15000);
    try {
      const response = await fetch(path, {method:payload ? 'POST' : 'GET',credentials:'omit',redirect:'error',cache:'no-store',signal:controller.signal,
        headers:{...(payload ? {'Content-Type':'application/json'} : {}),...(credential ? {Authorization:'Bearer '+credential} : {})},...(payload ? {body:JSON.stringify(payload)} : {})});
      const envelope = await json(response);
      if (before !== epoch) throw stale();
      if (!response.ok || response.status !== expectedStatus) {
        // The day's sign-up and recovery email is spent: the service's own sentence, the same for every address, and when it resets.
        const resets = envelope.error?.code === 'account_email_daily_budget_reached' ? ' Please try again after 00:00 UTC.' : '';
        const error = Error((envelope.error?.message || 'The service could not finish this request.') + resets); error.code = envelope.error?.code; throw error;
      }
      if (!envelope.result || typeof envelope.result !== 'object') throw Error('The service response was not recognized.');
      return envelope.result;
    } catch (error) {
      if (before !== epoch) throw stale();
      if (error.name === 'AbortError') throw Error('The service did not answer in time. A requested change or email may still complete. Check its state before trying again.');
      throw error;
    } finally { clearTimeout(timeout); pending.delete(controller); }
  }
  function keep(accessToken) {
    let expires; try { expires = JSON.parse(atob(accessToken.split('.')[1].replace(/-/g,'+').replace(/_/g,'/'))).exp; } catch (_) {}
    if (!Number.isFinite(expires) || expires * 1000 <= Date.now()) return;
    try { sessionStorage.setItem(key,JSON.stringify({access_token:accessToken,expires_at:expires})); } catch (_) {}
    clearTimeout(expiryTimer); expiryTimer = setTimeout(() => { clear(); say('Your session expired. Sign in again to continue.'); },Math.min(2147483647,expires*1000-Date.now()));
  }
  const consent = window.BaltorOAuthConsent?.create({request,browserSignedIn:()=>Boolean(token),epoch:()=>epoch,displayName:'AgentFeeds',
    signIn:id=>location.assign('/login?oauth_authorization_id='+encodeURIComponent(id))});
  async function open(accessToken, activate = false) {
    clear(); token = accessToken;
    const flow = epoch;
    try {
      if (activate) { const result = await request('/api/v1/account/activate',{record_type:'service_account_activation_request/v1'}); if (result.record_type !== 'service_account_activation/v1' || typeof result.tenant_id !== 'string') throw Error('Account activation was not confirmed.'); }
      const session = await request('/api/v1/session');
      if (session.record_type !== 'service_session/v1' || session.authentication_mode !== 'browser_identity' || typeof session.principal?.tenant_id !== 'string') throw Error('Account access could not be verified.');
      keep(accessToken);
      const facts = document.querySelector('[data-account-facts]');
      if (facts) {
        facts.replaceChildren(); for (const [name,value] of [['Account reference',session.principal.tenant_id],['Connection','Signed in']]) { const term = document.createElement('dt'), detail = document.createElement('dd'); term.textContent = name; detail.textContent = value; facts.append(term,detail); }
        document.querySelector('[data-account-details]').hidden = false; document.querySelector('[data-account-login]').hidden = true;
      }
      say('Signed in. Your reading profiles remain in the files you save.'); consent?.connectionChanged();
    } catch (error) { if (flow === epoch) clear(); else error.stale = true; throw error; }
  }
  function passwordProblem(password, again, email) {
    const minimum = Number.isInteger(settings?.minimum_password_length) && settings.minimum_password_length >= 8 && settings.minimum_password_length <= 72 ? settings.minimum_password_length : 12;
    if ([...password].length < minimum) return 'Use at least '+minimum+' characters.';
    if (new TextEncoder().encode(password).length > 72 || /[\u0000-\u001f\u007f]/.test(password)) return 'Use no more than 72 bytes, without control characters.';
    if (password !== again) return 'The passwords do not match.';
    if (email && password.trim().toLowerCase() === email.trim().toLowerCase()) return 'Choose a password different from your email address.';
    return '';
  }
  function available(action) {
    if (!client) return false;
    if (action === 'signup') return settings.signup_available === true && settings.email_signup_enabled === true;
    if (action === 'recovery') return settings.recovery_available === true;
    if (action === 'confirm') return Boolean(confirmation) && !passwordSet;
    return true;
  }
  async function submit(form) {
    const action = form.dataset.accountForm, fields = new FormData(form), before = epoch;
    const current = () => before === epoch;
    if (action === 'signup' || action === 'recovery') {
      const signup = action === 'signup';
      if (signup ? !(settings?.signup_available && settings?.email_signup_enabled) : !settings?.recovery_available) throw Error('This account action is not available right now.');
      const result = await request('/api/v1/account/'+action,{record_type:signup?'service_account_signup_request/v2':'service_account_recovery_request/v1',email:String(fields.get('email')).trim()},'',202);
      if (result.record_type !== (signup?'service_account_signup_result/v1':'service_account_recovery_result/v1') || result.status !== (signup?'confirmation_sent':'recovery_sent')) throw Error('The email request could not be confirmed. It has not been sent again.');
      say('Check your email. The message explains how to continue for this address. Nothing here starts a subscription.');
    } else if (action === 'login') {
      const result = await client.auth.signInWithPassword({email:String(fields.get('email')).trim(),password:String(fields.get('password'))});
      if (!current()) return;
      if (result.error || !result.data?.session?.access_token) throw Error('Sign-in was not accepted. Check your email and password, or request a recovery link.');
      await open(result.data.session.access_token,settings.registration_enabled === true);
      form.reset(); location.assign(oauthId?'/oauth/consent?authorization_id='+encodeURIComponent(oauthId):'/account');
    } else if (action === 'confirm') {
      if (passwordSet) throw Error('Your password was already set. Sign in to continue.');
      if (!confirmation) throw Error('This link is missing, expired or invalid. Request a new link from the sign-in page.');
      const password = String(fields.get('password')), again = String(fields.get('again'));
      let problem = passwordProblem(password,again,confirmation.email); if (problem) throw Error(problem);
      if (!confirmation.session) {
        const hash = confirmation.hash; confirmation.hash = '';
        const result = await client.auth.verifyOtp({token_hash:hash,type:confirmation.type});
        if (!current()) return;
        if (result.error || !result.data?.session) { confirmation = null; throw Error('This link cannot be used. Request a new link from the sign-in page.'); }
        confirmation.session = result.data.session; confirmation.email = result.data.user?.email || '';
      }
      problem = passwordProblem(password,again,confirmation.email); if (problem) throw Error(problem);
      const updated = await client.auth.updateUser({password}); if (!current()) return;
      if (updated.error) throw Error('The password was not accepted. Choose another password and try again.');
      passwordSet = true; const accessToken = confirmation.session.access_token; confirmation = null; form.reset();
      say('Password set. Opening your account…');
      try { await open(accessToken,settings.registration_enabled === true); location.assign('/account'); }
      catch (_) { say('Your password is set, but account access could not be confirmed. Sign in to continue.',true); }
    }
  }
  for (const form of forms) form.addEventListener('submit', async event => {
    event.preventDefault(); if (busy || !client) return;
    busy = true; const button = form.querySelector('button'); button.disabled = true; say('Working…');
    try { await submit(form); } catch (error) { if (!error.stale) say(error.message,true); }
    finally { busy = false; button.disabled = !available(form.dataset.accountForm); }
  });
  document.querySelector('[data-signout]')?.addEventListener('click', async () => {
    const previous = token; clear(); say('Signed out on this page. Confirming remote sign-out…');
    let service = false, provider = false;
    try { const result = await request('/api/v1/account/logout',{record_type:'service_browser_logout_request/v1'},previous); service = result.committed === true && result.revoked === true; } catch (_) {}
    try { provider = !(await client.auth.signOut({scope:'local'})).error; } catch (_) {}
    say(service && provider ? 'Signed out.' : 'This page is cleared. Remote sign-out was not fully confirmed; a session may remain valid until expiry.',!service || !provider);
  });
  addEventListener('pagehide', () => { epoch++; for (const controller of pending) controller.abort(); pending.clear(); confirmation = null; clearTimeout(expiryTimer); });
  (async () => {
    try {
      settings = await request('/api/v1/account/identity',null,'');
      if (settings.record_type !== 'browser_identity_public_configuration/v1' || settings.provider_profile !== 'supabase_user/v1' || !settings.publishable_key?.startsWith('sb_publishable_') || !window.BaltorIdentitySdk) throw Error('Account sign-in is unavailable right now.');
      const provider = new URL(settings.project_url); if (provider.protocol !== 'https:' || provider.username || provider.password) throw Error('Account configuration was not recognized.');
      client = window.BaltorIdentitySdk.createClient(settings.project_url,settings.publishable_key,{auth:{persistSession:false,autoRefreshToken:false,detectSessionInUrl:false}});
      for (const form of forms) {
        const action = form.dataset.accountForm;
        form.querySelector('button').disabled = !available(action);
      }
      const rule = document.querySelector('[data-password-rule]'); if (rule) rule.textContent = 'Use at least '+settings.minimum_password_length+' characters and a password you do not use elsewhere.';
      let kept; try { kept = JSON.parse(sessionStorage.getItem(key)||'null'); } catch (_) {}
      if (location.pathname !== '/auth/confirm' && kept && typeof kept.access_token === 'string' && kept.access_token.length < 16384 && Number.isFinite(kept.expires_at) && kept.expires_at*1000 > Date.now()) await open(kept.access_token);
      else if (location.pathname === '/auth/confirm') say(confirmation?'Choose your password to continue.':'This confirmation link is missing or invalid. Request a new link from the sign-in page.',!confirmation);
      else say('Account controls are ready. Public feeds do not require sign-in.');
      consent?.show();
    } catch (error) { if (!error.stale) { clear(); say(error.message,true); } }
  })();
})();
