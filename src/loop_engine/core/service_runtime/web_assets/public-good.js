"use strict";
(() => {
  const root = document.querySelector('[data-public-good-browser]');
  if (!root) return;
  const $ = id => document.getElementById('public-good-' + id);
  const form=$('filters'), query=$('query'), goal=$('goal'), mode=$('view'), media=$('media'), initiative=$('initiative');
  const status=$('status'), items=$('items'), previous=$('previous'), next=$('next');
  if (!mode || !media || !initiative) {status.textContent='This page changed. Reload it to browse the current files.';return;}
  const labels=Object.fromEntries([...goal.options].filter(option=>/^\d+$/.test(option.value)).map(option=>[option.value,option.textContent]));
  let page=1, requestNumber=0, controller;
  const element=(tag,text,className)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(className)node.className=className;return node;};
  const integer=value=>Number.isSafeInteger(value)&&value>=0;
  const text=value=>typeof value==='string';
  const digest=value=>text(value)&&/^[a-f0-9]{64}$/.test(value);
  const identity=value=>text(value)&&/^[a-zA-Z0-9_.:-]{1,256}$/.test(value);
  const goals=value=>Array.isArray(value)&&value.every(id=>Number.isInteger(id)&&id>=1&&id<=17);
  const path=value=>text(value)&&value.length>0&&value.length<=200&&value.split('/').length<=8
    &&value.split('/').every(part=>/^[A-Za-z0-9_.@+-]{1,100}$/.test(part)&&!['.','..','.git'].includes(part.toLowerCase()));
  const placement=row=>row&&identity(row.identity)&&digest(row.item_version)&&digest(row.body_digest)&&path(row.path)
    &&text(row.package_display_name)&&text(row.package_purpose)&&text(row.public_benefit)&&text(row.licence)&&text(row.media_type)
    &&text(row.placement_role)&&goals(row.sdg_goals)&&Array.isArray(row.initiatives)&&row.initiatives.every(text)
    &&row.requires_package_context===true&&typeof row.is_useful==='boolean'&&typeof row.matches_filters==='boolean';
  function validate(record,files) {
    if(!record||record.record_type!==(files?'public_good_file_collection/v1':'public_good_collection/v1')
      ||record.authentication_required!==true||record.subscription_required!==false||!integer(record.packages)||!integer(record.distinct_useful_files)
      ||!integer(record.matches)||!integer(record.page)||record.page<1||typeof record.has_next!=='boolean'
      ||!Array.isArray(record.items)||record.items.length>50||!Array.isArray(record.goals)||record.goals.length!==17
      ||new Set(record.goals.map(row=>row.id)).size!==17||!record.goals.every(row=>Number.isInteger(row.id)&&row.id>=1&&row.id<=17&&integer(row[files?'files':'packages'])))
      throw new Error('Invalid collection');
    if(files){
      if(!Array.isArray(record.media_types)||!Array.isArray(record.initiatives)||![...record.media_types,...record.initiatives].every(row=>text(row.id)&&integer(row.files))
        ||!record.items.every(row=>digest(row.file_sha256)&&integer(row.size_bytes)&&Array.isArray(row.media_types)&&row.media_types.every(text)
          &&Array.isArray(row.placements)&&row.placements.length>0&&row.placements.every(placement)&&row.placements.some(item=>item.is_useful&&item.matches_filters)))
        throw new Error('Invalid file collection');
    }else if(!record.items.every(row=>identity(row.identity)&&text(row.title)&&text(row.summary)&&text(row.public_benefit)&&text(row.component_form)&&text(row.licence)&&goals(row.sdg_goals)))
      throw new Error('Invalid package collection');
    return record;
  }
  const goalText=row=>row.sdg_goals.length?row.sdg_goals.map(id=>'SDG '+id).join(' · '):'Related public-benefit initiative';
  function packageCard(row) {
    const node=element('li',undefined,'pg-item');
    node.append(element('h2',row.title),element('p',row.summary),element('p',row.public_benefit),
      element('p',row.component_form+' · '+row.licence,'pg-meta'),element('p',goalText(row),'pg-meta'));
    const link=element('a','Sign in and open package');link.href='/app?component='+encodeURIComponent(row.identity)+'#browse-heading';node.append(link);
    return node;
  }
  function fileLink(file,row) {
    const link=element('a','Sign in and open this file');
    link.href='/app?'+new URLSearchParams({component:row.identity,file:row.path,body_digest:row.body_digest,file_digest:file.file_sha256})+'#browse-heading';
    return link;
  }
  function fileCard(file) {
    const first=file.placements.find(row=>row.is_useful&&row.matches_filters), node=element('li',undefined,'pg-item');
    node.append(element('h2',first.package_display_name),element('p',first.path,'pg-file-path'),
      element('p',first.package_purpose),element('p',first.public_benefit),
      element('p',file.media_types.join(' · '),'pg-meta'),element('p',goalText(first),'pg-meta'));
    const details=element('details',undefined,'pg-file-context');
    details.append(element('summary','Package context, licence and download options'));
    details.append(element('p','Keep the package’s licence, references and dependency instructions. A file is not automatically installed or run.'));
    const choices=element('ul');
    for(const row of file.placements){
      const item=element('li');
      item.append(element('p',row.package_display_name+' · '+row.licence),element('p',row.path,'pg-file-path'),
        element('p',(row.is_useful?'Useful file':'Supporting placement')+' · '+row.placement_role.replaceAll('_',' '),'pg-meta'),fileLink(file,row));
      choices.append(item);
    }
    details.append(choices);node.append(details);
    if(file.placements.length===1)node.append(fileLink(file,first));
    return node;
  }
  function options(select,rows,empty) {
    const chosen=select.value;select.replaceChildren(element('option',empty));select.options[0].value='';
    for(const row of rows){const label=select===media?row.id:row.id.replaceAll('-',' ');const option=element('option',label+' ('+row.files.toLocaleString('en-US')+')');option.value=row.id;select.append(option);}
    select.value=[...select.options].some(option=>option.value===chosen)?chosen:'';
  }
  async function load() {
    const mine=++requestNumber,files=mode.value==='files';
    controller?.abort();controller=new AbortController();previous.disabled=true;next.disabled=true;
    media.disabled=!files;initiative.disabled=!files;root.setAttribute('aria-busy','true');status.textContent='Loading the current collection…';
    const params=new URLSearchParams({page:String(page)});
    if(query.value.trim())params.set('query',query.value.trim());if(goal.value)params.set('goal',goal.value);
    if(files&&media.value)params.set('media_type',media.value);if(files&&initiative.value)params.set('initiative',initiative.value);
    try{
      const answer=await fetch((files?'/api/v1/public-good/files':'/api/v1/public-good')+'?'+params,{credentials:'omit',cache:'no-store',redirect:'error',signal:controller.signal});
      if(!answer.ok)throw new Error('Collection unavailable');
      const record=validate((await answer.json()).result,files);if(mine!==requestNumber)return;
      items.replaceChildren(...record.items.map(files?fileCard:packageCard));
      $('population').textContent=record.distinct_useful_files.toLocaleString('en-US')+' distinct useful '+(record.distinct_useful_files===1?'file':'files')+' in '+record.packages.toLocaleString('en-US')+(record.packages===1?' package':' packages');
      const unit=files?'file':'package';
      status.textContent=record.matches?record.matches.toLocaleString('en-US')+' matching '+unit+(record.matches===1?'':'s')+'. Account required for every download.'
        :'No published '+unit+'s match these filters. Try another goal or search.';
      $('page').textContent='Page '+record.page;previous.disabled=record.page<=1;next.disabled=!record.has_next;
      $('coverage').replaceChildren(...record.goals.map(row=>element('li',labels[row.id]+': '+row[files?'files':'packages'].toLocaleString('en-US')+' '+(files?'files':'packages'))));
      if(files){options(media,record.media_types,'Every file type');options(initiative,record.initiatives,'Every initiative');}
      if(text(record.limits_description))$('limits').textContent=record.limits_description;
    }catch(error){
      if(mine!==requestNumber||error.name==='AbortError')return;items.replaceChildren();$('population').textContent='';
      status.textContent='The collection could not be loaded. Please try again.';
    }finally{if(mine===requestNumber)root.removeAttribute('aria-busy');}
  }
  form.addEventListener('submit',event=>{event.preventDefault();page=1;load();});
  for(const control of [goal,media,initiative])control.addEventListener('change',()=>{page=1;load();});
  mode.addEventListener('change',()=>{page=1;media.value='';initiative.value='';load();});
  previous.addEventListener('click',()=>{if(page>1){page--;load();}});next.addEventListener('click',()=>{page++;load();});
  load();
})();
