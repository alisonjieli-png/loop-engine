// One factual edit shared by three render treatments and two compositions.
export const DURATION = 30;
export const FPS = 24;
export const SHOTS = Object.freeze([
  {id:'intro',start:0,end:5,label:'For the agent you already use',title:"Don't be a\nmeat proxy.",copy:'Give your agent the sources. Keep the judgment.',note:'An AgentFeeds campaign · Operated by Baltor.AI',url:'dontbeameatproxy.si',accent:'#ef6043'},
  {id:'feeds',start:5,end:12,label:'01 / AgentFeeds',title:'Let your agent\nread the sources.',copy:'Choose a collection. Download a reading profile.',note:'Curated references. Your agent reads the originals.',url:'agentfeeds.si',accent:'#68d5b7'},
  {id:'foundry',start:12,end:19,label:'02 / AgentFoundry',title:'Start with\nworking material.',copy:'Explore component examples, reusable files and setup guides.',note:'Inspect the source, licence and requirements before use.',url:'getagentfoundry.si',accent:'#f5bc69'},
  {id:'afk',start:19,end:26,label:'03 / AgentAFK · Local Preview',title:'Prepare the work.\nKeep control.',copy:'Arrange ready task files. Export your task list.',note:'Bring your worker and model access. No hosted execution.',url:'agentafk.si',accent:'#b9a2ed'},
  {id:'close',start:26,end:30,label:'Explore the live sites',title:'A useful next step\nfor your agent.',copy:'Sources to read. Files to use. Work you authorize.',note:'AgentAFK is a free local Preview, not a hosted worker.',url:'baltor.ai',accent:'#68d5b7'}
]);
export function shotAt(seconds){
  if(!Number.isFinite(seconds)||seconds<0||seconds>DURATION)throw Error('Time must be within the30-second edit');
  return SHOTS.find(shot=>seconds>=shot.start&&seconds<shot.end)||SHOTS.at(-1);
}
export const clamp=(n,low=0,high=1)=>Math.min(high,Math.max(low,n));
export const ease=n=>1-(1-clamp(n))**3;
export function inspectTimeline(shots=SHOTS){
  const errors=[];let cursor=0;
  for(const shot of shots){if(shot.start!==cursor||shot.end<=shot.start)errors.push('non-contiguous timing');cursor=shot.end;if(!shot.title||!shot.note||!shot.url)errors.push('missing visible claim context');}
  if(cursor!==DURATION)errors.push('wrong duration');
  if(!shots.some(s=>s.id==='afk'&&s.label.includes('Local Preview')&&s.note.includes('No hosted execution')))errors.push('missing AFK limit');
  return errors;
}
