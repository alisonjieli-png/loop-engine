/* The existing live account check's single-customer journal. No provider access here:
   its caller supplies the same mail/browser actions the full journey uses. */
import {closeSync, existsSync, fsyncSync, lstatSync, openSync, readFileSync, renameSync, unlinkSync, writeFileSync} from "node:fs";
import {randomUUID} from "node:crypto";
import {dirname, isAbsolute, resolve} from "node:path";

const version="fresh_account_journey/v1";
const stages=["prepared","mailbox_create_pending","mailbox_created","mailbox_ready","signup_pending","signup_sent",
  "confirmation_ready","confirmation_pending","confirmed","signin_pending","complete"];
const uncertain=new Set(["mailbox_create_pending","signup_pending","confirmation_pending"]);
export class FreshJourneyError extends Error {
  constructor(code,stage="unstarted"){super(code);this.name="FreshJourneyError";this.code=code;this.stage=stage;}
}
export const isConfirmationSender=address=>typeof address==="string"&&/^[^@\s]+@(?:auth\.|mail\.)?baltor\.ai$/i.test(address);
function requirePrivatePath(path){
  if(typeof path!=="string"||!isAbsolute(path)||resolve(path)!==path||typeof process.getuid!=="function")
    throw new FreshJourneyError("private_state_path_required");
  const parent=dirname(path),held=lstatSync(parent);
  if(!held.isDirectory()||held.isSymbolicLink()||held.uid!==process.getuid()||(held.mode&0o077)!==0)
    throw new FreshJourneyError("private_parent_permissions_required");
  for(let part=parent;;part=dirname(part)){
    if(lstatSync(part).isSymbolicLink())throw new FreshJourneyError("private_state_symlink_refused");
    if(dirname(part)===part)break;
  }
}
const safeAccount=value=>{
  if(value?.authentication_mode!=="browser_identity"||typeof value.tenant_id!=="string"||!value.tenant_id
      ||!["metadata","bodies"].includes(value.entitlement)||typeof value.access_source!=="string")
    throw new FreshJourneyError("authenticated_account_not_confirmed");
  return {authentication_mode:value.authentication_mode,tenant_id:value.tenant_id,
    entitlement:value.entitlement,access_source:value.access_source};
};
export function readFreshState(path,origin){
  requirePrivatePath(path);
  const stat=lstatSync(path);
  if(!stat.isFile()||stat.isSymbolicLink()||(stat.mode&0o777)!==0o600||stat.uid!==process.getuid())
    throw new FreshJourneyError("private_state_permissions_required");
  if(stat.size>65536)throw new FreshJourneyError("private_state_too_large");
  let state;try{state=JSON.parse(readFileSync(path,"utf8"));}catch{throw new FreshJourneyError("invalid_private_state");}
  if(state.record_type!==version||state.origin!==origin||!stages.includes(state.stage)||!Array.isArray(state.history)
      ||typeof state.run_id!=="string"||typeof state.fresh?.address!=="string"||!state.fresh.address.startsWith("baltor-check-")
      ||typeof state.fresh.password!=="string"||!state.fresh.password||state.mailbox?.address!==state.fresh.address
      ||typeof state.mailbox.password!=="string"||!state.mailbox.password)
    throw new FreshJourneyError("private_state_binding_refused");
  return state;
}
function save(path,state){
  const temporary=path+".write-"+randomUUID();let fd;
  try{
    fd=openSync(temporary,"wx",0o600);writeFileSync(fd,JSON.stringify(state));fsyncSync(fd);closeSync(fd);fd=null;
    renameSync(temporary,path);
    const directory=openSync(dirname(path),"r");try{fsyncSync(directory);}finally{closeSync(directory);}
  }finally{if(fd!==null&&fd!==undefined)closeSync(fd);if(existsSync(temporary))unlinkSync(temporary);}
}
export async function runFreshOnly({statePath,origin,resume=false,registrationOpen=true,actions,now=()=>new Date().toISOString()}){
  requirePrivatePath(statePath);
  let lock;
  try{lock=openSync(statePath+".lock","wx",0o600);}catch{throw new FreshJourneyError("journey_in_use_or_private_folder_missing");}
  let state;
  try{
    if(existsSync(statePath)){
      if(!resume)throw new FreshJourneyError("existing_state_requires_resume");
      state=readFreshState(statePath,origin);
    }else{
      if(!registrationOpen)throw new FreshJourneyError("registration_closed");
      if(resume)throw new FreshJourneyError("resume_state_missing");
      const prepared=await actions.prepare();
      state={record_type:version,run_id:randomUUID(),origin,stage:"prepared",history:[],fresh:prepared.fresh,mailbox:prepared.mailbox};
      save(statePath,state);state=readFreshState(statePath,origin);
    }
    const checkpoint=(stage,event=stage)=>{state.stage=stage;state.history.push({event,at:now()});save(statePath,state);};
    if(uncertain.has(state.stage))throw new FreshJourneyError("unknown_effect_requires_reconciliation",state.stage);
    if(state.stage==="prepared"){
      checkpoint("mailbox_create_pending");
      const created=await actions.createInbox(state.mailbox);
      if(typeof created?.id!=="string"||!created.id)throw new FreshJourneyError("mailbox_creation_not_confirmed",state.stage);
      state.mailbox.id=created.id;checkpoint("mailbox_created");
    }
    if(state.stage==="mailbox_created"){
      checkpoint("mailbox_created","mailbox_session_requested");
      const token=await actions.authorizeInbox(state.mailbox);
      if(typeof token!=="string"||!token)throw new FreshJourneyError("mailbox_session_not_confirmed",state.stage);
      state.mailbox.token=token;checkpoint("mailbox_ready");
    }
    if(state.stage==="mailbox_ready"){
      if(!registrationOpen)throw new FreshJourneyError("registration_closed",state.stage);
      checkpoint("signup_pending");await actions.signup(state.fresh.address);checkpoint("signup_sent");
    }
    if(state.stage==="signup_sent"){
      const link=await actions.waitForLink(state.mailbox);
      if(!link)throw new FreshJourneyError("confirmation_email_not_received",state.stage);
      const parsed=new URL(link);
      if(parsed.origin!==origin||parsed.pathname!=="/auth/confirm"||!parsed.search||parsed.username||parsed.password)
        throw new FreshJourneyError("confirmation_address_refused",state.stage);
      state.confirmation_link=link;checkpoint("confirmation_ready");
    }
    if(state.stage==="confirmation_ready"){
      const parsed=new URL(state.confirmation_link);
      if(parsed.origin!==origin||parsed.pathname!=="/auth/confirm"||!parsed.search||parsed.username||parsed.password)
        throw new FreshJourneyError("confirmation_address_refused",state.stage);
      checkpoint("confirmation_pending");
      state.account=safeAccount(await actions.confirm(state.confirmation_link,state.fresh.password));
      delete state.confirmation_link;checkpoint("confirmed");
    }
    if(state.stage==="confirmed"||state.stage==="signin_pending"){
      checkpoint("signin_pending");
      const account=safeAccount(await actions.signin(state.fresh.address,state.fresh.password));
      if(account.tenant_id!==state.account.tenant_id)throw new FreshJourneyError("fresh_signin_account_mismatch",state.stage);
      state.account=account;checkpoint("complete");
    }
    return {record_type:version,run_id:state.run_id,stage:state.stage,resumed:resume,account:safeAccount(state.account),
      completed_at:state.history.at(-1)?.at,stages:state.history.map(row=>row.event),
      test_account_marker:"baltor-check-",credentials_reported:false};
  }catch(error){
    if(error instanceof FreshJourneyError)throw error;
    throw new FreshJourneyError("fresh_step_failed",state?.stage||"unstarted");
  }finally{closeSync(lock);unlinkSync(statePath+".lock");}
}
