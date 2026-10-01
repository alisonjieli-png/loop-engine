"use strict";
window.BaltorOAuthConsent = (() => {
  const version = 'service_oauth_consent/v1';
  const scopeLabels = {
    'provisioning:metadata':'Search and inspect your component library, rate downloaded material and send requests for material to staff.',
    'provisioning:read':'Download permitted files and report problems with material you have used.',
    'usage:read':'Read your own recorded library usage.'
  };
  const validId = value => /^boar_[A-Za-z0-9_-]{43}$/.test(value || '');
  function create({request, browserSignedIn, signIn, epoch}) {
    const $ = id => document.getElementById(id);
    const panel = $('oauth-consent-panel');
    if (!panel) return {show(){},connectionChanged(){}};
    let current = null, pending = false, loading = 0;
    const status = text => {$('oauth-consent-status').textContent=text;};
    const authorizationId = () => {
      const values = new URLSearchParams(location.search).getAll('authorization_id');
      return values.length === 1 && validId(values[0]) ? values[0] : '';
    };
    const locked = value => {pending=value;$('oauth-approve').disabled=value||!current;$('oauth-deny').disabled=value||!current;};
    async function show() {
      if (location.pathname !== '/oauth/consent') return;
      const id=authorizationId(), generation=++loading;
      current=null;locked(false);$('oauth-consent-details').hidden=true;
      $('oauth-sign-in').hidden=true;
      if(!id){status('This connection request is missing or invalid. Start the connection again from your app.');return;}
      if(!browserSignedIn()){$('oauth-sign-in').hidden=false;status('Sign in to your Baltor account to review this request. No API key is needed.');return;}
      status('Loading the app and permissions…');
      try {
        const before=epoch();
        const record=await request('/api/v1/oauth/consent?authorization_id='+encodeURIComponent(id));
        if(generation!==loading||before!==epoch()||location.pathname!=='/oauth/consent')return;
        if(record?.record_type!==version||record.authorization_id!==id||typeof record.client_name!=='string'
          ||typeof record.redirect_uri!=='string'||typeof record.resource!=='string'||!Array.isArray(record.scopes)
          ||!record.scopes.length||record.scopes.some(scope=>!scopeLabels[scope]))throw new Error('invalid consent');
        const redirect=new URL(record.redirect_uri);
        $('oauth-client-name').textContent=record.client_name;
        $('oauth-client-destination').textContent=redirect.origin+redirect.pathname;
        $('oauth-consent-scopes').replaceChildren(...record.scopes.map(scope=>{const item=document.createElement('li');item.textContent=scopeLabels[scope];return item;}));
        current=record;$('oauth-consent-details').hidden=false;locked(false);
        status('Review the app and destination. Allow access only if you started this connection.');
      } catch (_) {if(generation===loading)status('This request could not be loaded. It may have expired. Start the connection again from your app.');}
    }
    $('oauth-sign-in').addEventListener('click',()=>{const id=authorizationId();if(id)signIn(id);});
    async function decide(decision) {
      if(pending||!current||!browserSignedIn())return;
      const held=current,before=epoch();locked(true);status('Saving your decision…');
      try {
        const result=await request('/api/v1/oauth/consent',{record_type:'service_oauth_consent_decision/v1',authorization_id:held.authorization_id,decision});
        if(before!==epoch())throw new Error('account changed');
        if(result?.record_type!=='service_oauth_consent_result/v1'||typeof result.redirect_uri!=='string')throw new Error('invalid result');
        const destination=new URL(result.redirect_uri),expected=new URL(held.redirect_uri);
        if(destination.origin!==expected.origin||destination.pathname!==expected.pathname||destination.hash
          ||destination.username||destination.password)throw new Error('redirect changed');
        current=null;status(decision==='approve'?'Access authorized. Returning to your app…':'Access denied. Returning to your app…');
        location.assign(destination.href);
      } catch (_) {
        current=null;locked(true);
        status('The decision could not be confirmed. It has not been sent again. Return to your app and start a new connection if needed.');
      }
    }
    $('oauth-approve').addEventListener('click',()=>decide('approve'));
    $('oauth-deny').addEventListener('click',()=>decide('deny'));
    return {show,connectionChanged:show};
  }
  return {create,validId};
})();
