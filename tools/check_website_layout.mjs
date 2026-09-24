/* Measure the website in a real browser against its site map and the layout standard of
   docs/guides/website-design-standards.md.

   Use one of:
     node tools/check_website_layout.mjs --local NEW_REPORT.json
     node tools/check_website_layout.mjs --url ORIGIN NEW_REPORT.json, where ORIGIN is an https origin with no path

   --local starts a service on a loopback address, as tools/check_service_workspace.mjs does, over a temporary
   database with local fixture keys, and also signs in with those keys to read the signed-in and the operator
   header. --url reads a deployed origin and changes nothing there: it opens pages, scrolls, presses the menu
   button and follows links inside a page. It submits no form and sends no credential. Requests to any other
   origin are blocked and listed, except the hostnames the site map names, which it opens only to read the page
   each one shows.

   The site map and the layout standard are read once, through their typed reader in
   src/loop_engine/core/service_runtime/web_site_map.py, so this check never reads them another way.

   For every page of the site map it measures, at the widths the layout standard names: the address answers with
   the page and its view; the title and the canonical address; one visible h1; at most one primary action in the
   view; the header and footer entries against the site map; no sideways scrolling on a phone; no empty stretch
   longer than the limit on a desktop; section padding from the allowed values only; the Geist typefaces only;
   the text contrast; touch targets on a phone; dark bands; line length; the shared left edge; what the first
   screen shows; the scroll budget and the contents list of a long documentation page; the header on one row at
   the desktop widths and folded into its menu at the narrow ones; a header that stays in view; the header
   height on a phone held sideways; and a jump to a part of a page that lands below the header. It writes a
   report that refuses to overwrite an existing file and exits 1 unless every check passed. */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {spawn,spawnSync} from "node:child_process";
import {createInterface} from "node:readline";
import {existsSync,readFileSync,writeFileSync} from "node:fs";
import {createHash} from "node:crypto";
import {resolve} from "node:path";

const root=resolve(new URL("..",import.meta.url).pathname);
const usage="Use: node tools/check_website_layout.mjs --local NEW_REPORT.json, or --url ORIGIN NEW_REPORT.json with an https origin.";
const argv=process.argv.slice(2),mode=argv[0]==="--local"?"local":argv[0]==="--url"?"url":"";
const given=mode==="url"?argv[1]:null,output=resolve((mode==="url"?argv[2]:argv[1])||"");
if(!mode||(mode==="url"&&(!given||!given.startsWith("https://")||new URL(given).origin!==given))||!output.endsWith(".json")||existsSync(output))
  throw new Error(usage+" The origin has no path, and the report path must be new.");
/* PYTHON names a qualified environment when the checkout has no .venv of its own, as a separate worktree may not. */
const python=process.env.PYTHON||(existsSync(resolve(root,".venv/bin/python"))?resolve(root,".venv/bin/python"):"python3");
const env={...process.env,PYTHONPATH:resolve(root,"src")};
const READER=`import json
from loop_engine.core.service_runtime.web_site_map import as_plain_record, load_layout_standard, load_site_map
print(json.dumps({"site_map": as_plain_record(load_site_map()), "layout": as_plain_record(load_layout_standard())}))`;
const read=spawnSync(python,["-c",READER],{cwd:root,env,encoding:"utf8"});
if(read.status!==0)throw new Error("The typed reader refused the website records:\n"+read.stderr);
const {site_map:siteMap,layout}=JSON.parse(read.stdout);
const recordDigest=name=>createHash("sha256").update(readFileSync(resolve(root,"src/loop_engine/core/service_runtime",name))).digest("hex");
const SERVICE=`from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
import json, sys
from loop_engine.core.service_runtime.access_checks import prepared
from loop_engine.core.service_runtime.http import ServiceHttpApplication
from loop_engine.core.service_runtime.http_test_fixtures import running_http
with ExitStack() as stack:
    folder = Path(stack.enter_context(TemporaryDirectory(prefix="website-layout-")))
    (folder / "intelligence").mkdir()
    held = prepared(folder / "intelligence")
    factory = lambda config: ServiceHttpApplication(held.runtime, held.provisioning, config, access_administration=held.administration)
    base, _ = stack.enter_context(running_http(held, application_factory=factory, display_name=sys.argv[1]))
    print(json.dumps({"base": base, "signed_in": held.keys["alpha"].key, "operator": held.admin_key.key}), flush=True)
    sys.stdin.readline()
`;
const browserPath=[process.env.LOOP_WEBSITE_BROWSER,"/opt/google/chrome/chrome","/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(path=>path&&existsSync(path));
if(!browserPath)throw new Error("No Chrome or Chromium was found. Set LOOP_WEBSITE_BROWSER to its absolute path.");

const checks=[],skipped=[],pages=[],surfaces=[],external=new Set(),errors=[];
const check=(name,passed,where={},detail={})=>checks.push({name,...where,passed:passed===true,...(Object.keys(detail).length?{detail}:{})});
const skip=(name,where,reason)=>skipped.push({name,...where,reason});
const vp=layout.viewports,desktop=vp.desktop,phone=vp.phone;
const edgeTolerance=layout.shared_edge_tolerance_px;

/* Decisions, kept apart from the measurements so the known-wrong controls below can prove each one refuses. */
const key=entry=>entry.href??("button:"+entry.label);
const compareEntries=(expected,actual)=>{
  const wanted=expected.map(key),found=actual.map(key),problems=[];
  const missing=wanted.filter(item=>!found.includes(item)),extra=found.filter(item=>!wanted.includes(item));
  if(missing.length)problems.push("missing "+JSON.stringify(missing));
  if(extra.length)problems.push("extra "+JSON.stringify(extra));
  const shared=wanted.filter(item=>found.includes(item)),order=found.filter(item=>wanted.includes(item));
  if(JSON.stringify(shared)!==JSON.stringify(order))problems.push("out of order: the site map has "+JSON.stringify(shared)+" and the page has "+JSON.stringify(order));
  for(const entry of expected){const shown=actual.find(item=>key(item)===key(entry));
    if(shown&&(shown.label!==entry.label||shown.role!==entry.role))problems.push(`${key(entry)} is a ${shown.role} labelled ${JSON.stringify(shown.label)}, and the site map has a ${entry.role} labelled ${JSON.stringify(entry.label)}`);}
  return problems;
};
const paddingAllowed=(value,allowed)=>allowed.some(item=>Math.abs(item-value)<=0.5);
const luminance=([r,g,b])=>{const f=v=>{v/=255;return v<=0.04045?v/12.92:((v+0.055)/1.055)**2.4;};return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b);};
const contrast=(a,b)=>{const [x,y]=[luminance(a),luminance(b)].sort((p,q)=>q-p);return (x+0.05)/(y+0.05);};
const heightBudget=(page,viewport)=>{
  if(page.scroll_budget==="documentation")return null;
  const desktopMax=layout.page_height_max_px[page.scroll_budget];
  return viewport.width===desktop.width?desktopMax:Math.round(layout.phone_screens_factor*desktopMax/desktop.height*viewport.height);
};
const oneRow=(boxes,bar)=>boxes.length>0&&Math.max(...boxes.map(item=>item.top))<Math.min(...boxes.map(item=>item.bottom))
  &&boxes.every(item=>item.left>=bar.left-0.5&&item.right<=bar.right+0.5&&item.top>=bar.top-0.5&&item.bottom<=bar.bottom+0.5);
const inFirstScreen=(box,height)=>Boolean(box)&&box.top>=0&&box.bottom<=height+0.5;
const tapSized=box=>box.width>=layout.tap_target_min_px-0.5&&box.height>=layout.tap_target_min_px-0.5;
const knownWrong=[
  ["padding_rule_refuses_112_pixels_on_a_desktop",!paddingAllowed(112,layout.section_padding_px.desktop)&&paddingAllowed(64,layout.section_padding_px.desktop)],
  ["padding_rule_refuses_87_84_pixels_on_a_desktop",!paddingAllowed(87.84,layout.section_padding_px.desktop)],
  ["entry_rule_refuses_a_missing_an_extra_and_a_reordered_link",
    compareEntries([{role:"link",label:"A",href:"/a"},{role:"link",label:"B",href:"/b"}],[{role:"link",label:"B",href:"/b"},{role:"link",label:"C",href:"/c"}]).length===3
    &&compareEntries([{role:"link",label:"A",href:"/a"},{role:"link",label:"B",href:"/b"}],[{role:"link",label:"B",href:"/b"},{role:"link",label:"A",href:"/a"}]).length===1],
  ["contrast_rule_refuses_grey_8a8a8a_on_white",contrast([138,138,138],[255,255,255])<layout.text_contrast_min&&contrast([85,96,112],[255,255,255])>=layout.text_contrast_min],
  ["scroll_budget_refuses_a_homepage_of_7046_pixels",heightBudget({scroll_budget:"long"},desktop)<7046],
  ["touch_rule_refuses_a_40_pixel_target",!tapSized({width:120,height:40})&&tapSized({width:44,height:44})],
  ["one_row_rule_refuses_a_header_that_wraps",!oneRow([{left:0,right:50,top:10,bottom:40},{left:60,right:90,top:50,bottom:80}],{left:0,right:100,top:0,bottom:90})],
  ["first_screen_rule_refuses_a_price_at_5001_pixels",!inFirstScreen({top:5001,bottom:5030},desktop.height)&&inFirstScreen({top:600,bottom:640},desktop.height)]];
for(const [name,passed] of knownWrong)check("known_wrong_control_"+name,passed);

/* Measurements, run inside the page. Only numbers and short samples come back. */
function measure({base,price,lineMax,menu}){
  scrollTo(0,0);
  const vw=innerWidth,vh=innerHeight,cache=new Map();
  const shown=el=>{if(!el||!el.isConnected)return false;if(cache.has(el))return cache.get(el);
    const box=el.getBoundingClientRect();
    const value=el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true,opacityProperty:true,visibilityProperty:true})&&box.width>1&&box.height>1;
    cache.set(el,value);return value;};
  const box=el=>{const r=el.getBoundingClientRect();return {left:r.left+scrollX,top:r.top+scrollY,right:r.right+scrollX,bottom:r.bottom+scrollY,width:r.width,height:r.height};};
  const words=el=>(el.innerText??el.textContent??"").replace(/\s+/g," ").replace(/\s*[↗→]$/,"").trim();
  const name=el=>el.tagName.toLowerCase()+(el.id?"#"+el.id:"")+[...el.classList].slice(0,2).map(item=>"."+item).join("")
    +(el.dataset?.band?`[data-band="${el.dataset.band}"]`:"")+(el.dataset?.view?`[data-view="${el.dataset.view}"]`:"");
  const sample=text=>(text||"").replace(/\s+/g," ").trim().slice(0,70);
  const header=document.querySelector("header"),footer=document.querySelector("footer"),main=document.querySelector("main");
  const view=[...document.querySelectorAll("[data-view]")].find(shown)||null,scope=view||main||document.body;
  const role=el=>el.classList.contains("brand")?"brand":el.classList.contains("primary")?"primary":el.tagName==="BUTTON"?"button":"link";
  const entries=header?[...header.querySelectorAll("a[href], button")].filter(shown).map(el=>({role:role(el),label:words(el),href:el.tagName==="A"?el.getAttribute("href"):null,box:box(el)})):null;
  const menuControl=header?[...header.querySelectorAll("label[for], button[aria-controls]")].find(el=>el.tagName==="LABEL"||el.getAttribute("aria-controls")):null;
  const result={view:view?.dataset.view??null,title:document.title,canonical:document.querySelector('link[rel="canonical"]')?.getAttribute("href")??null,
    height:document.documentElement.scrollHeight,overflow:Math.round(document.documentElement.scrollWidth-vw),header:header?{box:box(header),
    position:getComputedStyle(header).position,entries,menu_control_shown:shown(menuControl),menu_control_box:menuControl&&shown(menuControl)?box(menuControl):null}:null};
  if(result.overflow>1)result.wide=[...document.body.querySelectorAll("*")].filter(el=>el.getBoundingClientRect().right>vw+1&&shown(el)).slice(0,6)
    .map(el=>({element:name(el),right:Math.round(el.getBoundingClientRect().right)}));
  if(footer){
    const groups=[...footer.querySelectorAll("nav")].filter(shown).map(nav=>({name:nav.getAttribute("aria-label")||"",
      links:[...nav.querySelectorAll("a[href]")].filter(shown).map(a=>({role:"link",label:words(a),href:a.getAttribute("href")}))}));
    const outside=[...footer.querySelectorAll("a[href]")].filter(a=>shown(a)&&!a.closest("nav"));
    const rows=[...footer.querySelectorAll("*")].filter(el=>!el.closest("nav")&&shown(el)&&el.textContent.includes(base.operator)&&el.textContent.includes(base.operator_line))
      .sort((a,b)=>a.querySelectorAll("*").length-b.querySelectorAll("*").length);
    result.footer={groups,brand:outside.filter(a=>a.classList.contains("brand")).map(a=>a.getAttribute("href")),
      extra:outside.filter(a=>!a.classList.contains("brand")).map(a=>a.getAttribute("href")),
      base:rows[0]?{text:sample(rows[0].textContent),mark:[...rows[0].querySelectorAll("img")].some(img=>img.getAttribute("src")===base.mark),
        year:/\b20[0-9]{2}\b/.test(rows[0].textContent)}:null};
  }else result.footer=null;
  /* Sections: the page frame, the footer, and every block inside the main column that spans the window or paints a band that does. */
  const sections=new Set([main,footer].filter(Boolean));
  if(main)for(const el of main.querySelectorAll("*")){if(!shown(el))continue;const style=getComputedStyle(el);
    if(style.display.startsWith("inline")||style.position==="absolute"||style.position==="fixed")continue;
    if(el.getBoundingClientRect().width>=vw-1||style.borderImageSource!=="none")sections.add(el);}
  result.sections=[...sections].filter(shown).map(el=>{const style=getComputedStyle(el),r=box(el);
    return {element:name(el),top:Math.round(r.top),height:Math.round(r.height),padding_top:+parseFloat(style.paddingTop).toFixed(2),
      padding_bottom:+parseFloat(style.paddingBottom).toFixed(2),background:style.backgroundColor};});
  /* Ink: text, pictures, controls, and cards narrower than the window that draw an edge or a ground of their own. */
  const intervals=[],push=r=>{if(r.width>0&&r.height>0&&r.bottom+scrollY>0)intervals.push([r.top+scrollY,r.bottom+scrollY]);};
  const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
  for(let node=walker.nextNode();node;node=walker.nextNode()){if(!node.textContent.trim()||!shown(node.parentElement))continue;
    const range=document.createRange();range.selectNodeContents(node);for(const r of range.getClientRects())push(r);}
  const clear=color=>color==="rgba(0, 0, 0, 0)"||color==="transparent";
  for(const el of document.body.querySelectorAll("*")){if(!shown(el))continue;
    if(/^(IMG|SVG|VIDEO|CANVAS|IFRAME|INPUT|SELECT|TEXTAREA|BUTTON|HR)$/i.test(el.tagName)){push(el.getBoundingClientRect());continue;}
    const r=el.getBoundingClientRect();if(r.width>=vw*0.9)continue;const style=getComputedStyle(el);
    const edged=["Top","Right","Bottom","Left"].some(side=>parseFloat(style["border"+side+"Width"])>0&&!clear(style["border"+side+"Color"]));
    const grounded=!clear(style.backgroundColor)&&el.parentElement&&style.backgroundColor!==getComputedStyle(el.parentElement).backgroundColor;
    if(edged||grounded)push(r);}
  intervals.sort((a,b)=>a[0]-b[0]);
  let cursor=header?box(header).bottom:0;const runs=[];
  for(const [top,bottom] of intervals){if(bottom<=cursor)continue;if(top>cursor)runs.push({from:Math.round(cursor),to:Math.round(top),length:Math.round(top-cursor)});cursor=Math.max(cursor,bottom);}
  result.empty_runs=runs.sort((a,b)=>b.length-a.length).slice(0,5);
  /* Typefaces, contrast and touch targets, over every visible element that holds text of its own. */
  const parse=color=>{const found=color.match(/rgba?\(([^)]+)\)/);if(!found)return null;const [r,g,b,a=1]=found[1].split(/[\s,/]+/).filter(Boolean).map(Number);return [r,g,b,a];};
  const blend=(top,bottom)=>[0,1,2].map(index=>top[index]*top[3]+bottom[index]*(1-top[3])).concat(1);
  const ground=el=>{const layers=[];for(let node=el;node;node=node.parentElement){const color=parse(getComputedStyle(node).backgroundColor);
    if(color&&color[3]>0){layers.push(color);if(color[3]>=1)break;}}return layers.reverse().reduce((under,layer)=>blend(layer,under),[255,255,255,1]);};
  const lum=([r,g,b])=>{const f=v=>{v/=255;return v<=0.04045?v/12.92:((v+0.055)/1.055)**2.4;};return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b);};
  const ratio=(a,b)=>{const [x,y]=[lum(a),lum(b)].sort((p,q)=>q-p);return (x+0.05)/(y+0.05);};
  const families={},lowContrast={};
  for(const el of document.body.querySelectorAll("*")){
    if(![...el.childNodes].some(node=>node.nodeType===3&&node.textContent.trim())||!shown(el))continue;
    const style=getComputedStyle(el),family=style.fontFamily.split(",")[0].trim().replace(/^["']|["']$/g,"");
    (families[family]??=[]).length<4&&families[family].push(name(el)+" "+JSON.stringify(sample(el.textContent).slice(0,32)));
    if(el.closest(":disabled, [aria-disabled='true'], [inert]"))continue;
    let opacity=1;for(let node=el;node;node=node.parentElement)opacity*=parseFloat(getComputedStyle(node).opacity);
    const color=parse(style.color);if(!color)continue;const back=ground(el),front=blend([color[0],color[1],color[2],color[3]*opacity],back);
    const value=ratio(front,back),pair=style.color+" on "+back.slice(0,3).map(Math.round).join(",");
    if(value<4.5&&!lowContrast[pair])lowContrast[pair]={ratio:+value.toFixed(2),element:name(el),text:sample(el.textContent).slice(0,40),size:style.fontSize};
  }
  result.families=families;result.low_contrast=Object.values(lowContrast);
  result.fonts_loaded=[...document.fonts].filter(face=>face.status==="loaded").map(face=>face.family.replace(/["']/g,""));
  const inline=el=>{if(getComputedStyle(el).display!=="inline")return false;const block=el.parentElement?.closest("p, li, dd, td, figcaption, dt");
    return Boolean(block)&&block.textContent.replace(/\s+/g," ").trim().length>words(el).length+8;};
  result.small_targets=[...document.querySelectorAll("a[href], button, input:not([type=hidden]), select, textarea, summary, [role=tab], label[for]")].filter(el=>{
    if(!shown(el)||el.closest("header nav")&&!menu)return false;const r=el.getBoundingClientRect();if(r.width<=2||r.height<=2||r.bottom+scrollY<0)return false;
    if(el.tagName==="LABEL"){const control=document.getElementById(el.htmlFor);if(!control||!["checkbox","radio"].includes(control.type))return false;}
    if(el.tagName==="INPUT"&&["checkbox","radio"].includes(el.type)&&el.labels?.length)return false;
    return !inline(el)&&(r.width<43.5||r.height<43.5);}).slice(0,40).map(el=>({element:name(el),label:sample(words(el)).slice(0,40),
      width:Math.round(el.getBoundingClientRect().width),height:Math.round(el.getBoundingClientRect().height)}));
  /* Dark bands: blocks as wide as the window, at least 120 pixels tall, on a dark ground; a band inside a band counts once. */
  const dark=[];for(const el of [main,footer,...(main?main.querySelectorAll("*"):[])].filter(Boolean)){if(!shown(el))continue;const r=el.getBoundingClientRect();
    if(r.width<vw-1||r.height<120)continue;const color=parse(getComputedStyle(el).backgroundColor);
    if(color&&color[3]>=0.5&&lum(color)<0.2&&!dark.some(item=>item.el.contains(el)))dark.push({el,element:name(el),height:Math.round(r.height)});}
  result.dark_bands=dark.map(({element,height})=>({element,height}));
  /* Line length: how many characters of its own text a full line of each paragraph holds. */
  const pen=document.createElement("canvas").getContext("2d");result.long_lines=[];
  for(const el of scope.querySelectorAll("p, li, dd, blockquote")){if(!shown(el))continue;const text=el.textContent.replace(/\s+/g," ").trim();if(text.length<120)continue;
    const style=getComputedStyle(el);pen.font=`${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
    const each=pen.measureText(text).width/text.length,room=el.clientWidth-parseFloat(style.paddingLeft)-parseFloat(style.paddingRight);
    const holds=each>0?room/each:0;if(holds>lineMax&&text.length>holds)result.long_lines.push({element:name(el),characters:Math.round(holds),text:sample(text).slice(0,40)});}
  result.long_lines=result.long_lines.slice(0,12);
  /* The first screen, the shared left edge and the price. */
  const h1s=[...document.querySelectorAll("h1")].filter(shown),h1=h1s[0]||null;
  const lead=h1?[...scope.querySelectorAll("p")].find(p=>shown(p)&&!h1.contains(p)&&(h1.compareDocumentPosition(p)&Node.DOCUMENT_POSITION_FOLLOWING)&&p.textContent.trim().length>=12):null;
  const primaries=[...scope.querySelectorAll("a.primary, button.primary, input.primary")].filter(el=>shown(el)&&!el.closest("header, footer"));
  const actions=new Map();for(const el of primaries){const action=words(el)+" -> "+(el.getAttribute("href")||(el.form?"form "+(el.form.id||""):"button"));if(!actions.has(action))actions.set(action,el);}
  const headerPrimary=header?[...header.querySelectorAll(".primary")].find(shown)||null:null;
  const screen=el=>{if(!el)return null;const r=el.getBoundingClientRect();return {top:Math.round(r.top),bottom:Math.round(r.bottom)};};
  result.h1={count:h1s.length,text:h1?sample(h1.textContent):null,screen:screen(h1),left:h1?Math.round(h1.getBoundingClientRect().left):null};
  result.lead=lead?{text:sample(lead.textContent),screen:screen(lead)}:null;
  result.primary_actions=[...actions.keys()];
  result.page_primary=primaries[0]?{action:[...actions.keys()][0],screen:screen(primaries[0])}:headerPrimary?{action:words(headerPrimary)+" (header)",screen:screen(headerPrimary)}:null;
  result.any_primary_in_first_screen=[headerPrimary,...primaries].filter(Boolean).some(el=>{const r=el.getBoundingClientRect();return r.top>=0&&r.bottom<=vh+0.5;});
  const brand=header?.querySelector("a.brand"),footerBrand=footer?.querySelector("a.brand");
  result.edges={brand:brand&&shown(brand)?Math.round(brand.getBoundingClientRect().left*10)/10:null,h1:h1?Math.round(h1.getBoundingClientRect().left*10)/10:null,
    footer_brand:footerBrand&&shown(footerBrand)?Math.round(footerBrand.getBoundingClientRect().left*10)/10:null};
  result.price=null;const texts=document.createTreeWalker(scope,NodeFilter.SHOW_TEXT);
  for(let node=texts.nextNode();node;node=texts.nextNode()){const at=node.textContent.indexOf(price.marker);if(at<0||!shown(node.parentElement))continue;
    const range=document.createRange();range.setStart(node,at);range.setEnd(node,at+price.marker.length);const r=range.getBoundingClientRect();
    result.price={top:Math.round(r.top+scrollY),bottom:Math.round(r.bottom+scrollY),text:sample(node.parentElement.textContent).slice(0,40)};break;}
  const ids=new Set([...document.querySelectorAll("[id]")].map(el=>el.id));
  const lists=[...scope.querySelectorAll("nav")].filter(shown).map(nav=>({nav,count:[...nav.querySelectorAll("a[href*='#']")].filter(a=>{
    const url=new URL(a.getAttribute("href"),location.href);return url.pathname===location.pathname&&ids.has(decodeURIComponent(url.hash.slice(1)));}).length}))
    .filter(item=>item.count>=2);
  result.contents_list=lists[0]?{top:Math.round(box(lists[0].nav).top),links:lists[0].count}:null;
  result.in_page_links=[...document.querySelectorAll("a[href*='#']")].filter(a=>{if(!shown(a))return false;const url=new URL(a.getAttribute("href"),location.href);
    return url.pathname===location.pathname&&url.hash.length>1&&ids.has(decodeURIComponent(url.hash.slice(1)));}).slice(0,2).map(a=>a.getAttribute("href"));
  return result;
}

async function stickiness(page){
  return page.evaluate(async ()=>{
    const header=document.querySelector("header");if(!header)return {present:false};
    const frame=()=>new Promise(done=>requestAnimationFrame(()=>requestAnimationFrame(done)));
    const seen=()=>{const r=header.getBoundingClientRect();return r.height>0&&r.bottom>1&&r.top>-1&&r.top<2;};
    const tall=document.documentElement.scrollHeight>innerHeight*1.5,position=getComputedStyle(header).position;
    if(!tall){scrollTo(0,0);return {present:true,tall,position,height:Math.round(header.getBoundingClientRect().height)};}
    scrollTo(0,Math.round(innerHeight*1.5));await frame();await new Promise(done=>setTimeout(done,250));const down=seen();
    scrollTo(0,scrollY-Math.round(innerHeight*0.25));await frame();await new Promise(done=>setTimeout(done,400));const up=seen();
    scrollTo(0,0);await frame();
    return {present:true,tall,position,shown_after_scrolling_down:down,shown_after_scrolling_up:up,height:Math.round(header.getBoundingClientRect().height)};
  });
}

let child=null,lines=null,origin=given,keys=null,browser=null;
try{
  if(mode==="local"){
    child=spawn(python,["-u","-c",SERVICE,siteMap.display_name],{cwd:root,env,stdio:["pipe","pipe","pipe"]});
    lines=createInterface({input:child.stdout});
    const started=await new Promise((done,fail)=>{const timer=setTimeout(()=>fail(new Error("The local service did not start in time")),30000);
      lines.once("line",line=>{clearTimeout(timer);done(JSON.parse(line));});child.once("exit",code=>{clearTimeout(timer);fail(new Error("The local service stopped: "+code));});});
    origin=started.base;keys={signed_in:started.signed_in,operator:started.operator};
  }
  const allowed=new Set([origin,...(mode==="url"?siteMap.hostnames.map(surface=>"https://"+surface.hostname):[])]);
  browser=await chromium.launch({executablePath:browserPath,headless:true,args:["--no-sandbox"]});
  const open=async viewport=>{
    const context=await browser.newContext({viewport:{width:viewport.width,height:viewport.height},reducedMotion:"reduce",serviceWorkers:"block"});
    await context.route("**/*",route=>{const target=new URL(route.request().url()).origin;if(allowed.has(target))route.continue();else{external.add(target);route.abort();}});
    const page=await context.newPage();page.on("pageerror",error=>errors.push(String(error.message||error).slice(0,200)));return {context,page};
  };
  const load=async (page,address)=>{
    const response=await page.goto(origin+address,{waitUntil:"load",timeout:45000});
    await page.waitForLoadState("networkidle",{timeout:8000}).catch(()=>{});
    await page.evaluate(()=>document.fonts.ready.then(()=>true));
    return response;
  };
  const arguments_=menu=>({base:siteMap.footer.base_row,price:layout.price,lineMax:layout.line_characters_max,menu});
  const byWidth={};
  for(const [label,viewport] of Object.entries(vp))byWidth[label]=await open(viewport);
  for(const page of siteMap.pages){
    const where={address:page.address},record={address:page.address,view_expected:page.view,title_expected:page.title};
    pages.push(record);
    /* Desktop: the page itself, then everything measured at 1440 by 900. */
    const {page:tab}=byWidth.desktop;let response=null;
    try{response=await load(tab,page.address);}catch(error){check("address_is_served_as_a_page",false,where,{error:String(error).slice(0,200)});continue;}
    record.status=response?.status()??null;record.media_type=(response?.headers()["content-type"]||"").split(";")[0];
    const served=record.status===200&&record.media_type==="text/html";
    check("address_is_served_as_a_page",served,where,{status:record.status,media_type:record.media_type});
    if(!served){skip("every_other_check",where,"the address is not served as a page, so there is no page to measure");continue;}
    const d=await tab.evaluate(measure,arguments_(false));
    Object.assign(record,{view_shown:d.view,title:d.title,height:{desktop:d.height},h1:d.h1.text,price:d.price,first_section:d.sections.find(item=>item.element.startsWith("div")||item.element.includes("band"))||null});
    const w={...where,width:desktop.width};
    check("address_shows_its_view",d.view===page.view,w,{expected:page.view,shown:d.view});
    check("page_title_matches_the_site_map",d.title===siteMap.display_name+" | "+page.title,w,{expected:siteMap.display_name+" | "+page.title,shown:d.title});
    const canonical="https://"+siteMap.canonical_hostname+page.address;
    check("page_names_its_canonical_address",d.canonical===canonical,w,{expected:canonical,shown:d.canonical});
    const measured={desktop:d};
    const phoneTab=byWidth.phone.page;await load(phoneTab,page.address);measured.phone=await phoneTab.evaluate(measure,arguments_(false));record.height.phone=measured.phone.height;
    for(const [label,m] of Object.entries(measured)){
      const viewport=vp[label],at={...where,width:viewport.width};
      check("page_shows_exactly_one_h1",m.h1.count===1,at,{count:m.h1.count,text:m.h1.text});
      check("view_shows_at_most_one_primary_action",m.primary_actions.length<=layout.primary_actions_per_view_max,at,{actions:m.primary_actions});
      check("footer_groups_and_links_match_the_site_map",Boolean(m.footer)&&(()=>{const problems=[];
        problems.push(...compareEntries(siteMap.footer.groups.map(group=>({role:"group",label:group.name,href:group.name})),m.footer.groups.map(group=>({role:"group",label:group.name,href:group.name}))));
        for(const group of siteMap.footer.groups){const shown=m.footer.groups.find(item=>item.name===group.name);if(shown)problems.push(...compareEntries(group.links,shown.links).map(problem=>group.name+": "+problem));}
        if(JSON.stringify(m.footer.brand)!==JSON.stringify([siteMap.footer.brand_href]))problems.push("the footer brand links to "+JSON.stringify(m.footer.brand));
        if(m.footer.extra.length)problems.push("links outside the groups "+JSON.stringify(m.footer.extra));
        if(!m.footer.base||!m.footer.base.mark||!m.footer.base.year)problems.push("base row "+JSON.stringify(m.footer.base));
        at.problems=problems;return problems.length===0;})(),{...at},{problems:at.problems});
      delete at.problems;
      const allowedPadding=label==="desktop"?layout.section_padding_px.desktop:layout.section_padding_px.phone;
      const offPadding=m.sections.filter(item=>!paddingAllowed(item.padding_top,allowedPadding)||!paddingAllowed(item.padding_bottom,allowedPadding));
      check("section_padding_uses_only_allowed_values",offPadding.length===0,at,{allowed:allowedPadding,refused:offPadding.map(({element,padding_top,padding_bottom})=>({element,padding_top,padding_bottom}))});
      check("sampled_text_meets_the_contrast_minimum",m.low_contrast.length===0,at,{minimum:layout.text_contrast_min,refused:m.low_contrast});
      const edge=m.edges,edgeProblems=[];
      if(edge.brand===null||edge.h1===null)edgeProblems.push("no brand or no h1 to measure");
      else{if(Math.abs(edge.h1-edge.brand)>edgeTolerance)edgeProblems.push(`the h1 starts at ${edge.h1} and the brand at ${edge.brand}`);
        if(edge.footer_brand!==null&&Math.abs(edge.footer_brand-edge.brand)>edgeTolerance)edgeProblems.push(`the footer brand starts at ${edge.footer_brand} and the header brand at ${edge.brand}`);}
      check("page_content_starts_on_the_shared_left_edge",edgeProblems.length===0,at,{edges:edge,problems:edgeProblems});
      const budget=heightBudget(page,viewport);
      if(budget===null)skip("page_height_stays_within_its_scroll_budget",at,"a documentation page has no height budget; it opens with a contents list instead");
      else check("page_height_stays_within_its_scroll_budget",m.height<=budget,at,{height:m.height,budget,scroll_budget:page.scroll_budget});
      check("first_screen_shows_a_primary_action",m.any_primary_in_first_screen,at,{page_primary:m.page_primary});
    }
    const p=measured.phone,pw={...where,width:phone.width};
    check("page_does_not_scroll_sideways",p.overflow<=1,pw,{overflow:p.overflow,wide:p.wide||[]});
    check("touch_targets_meet_the_minimum_on_a_phone",p.small_targets.length===0,pw,{minimum:layout.tap_target_min_px,refused:p.small_targets});
    check("first_screen_on_a_phone_shows_the_heading_and_primary_action",inFirstScreen(p.h1.screen,phone.height)&&inFirstScreen(p.page_primary?.screen,phone.height),pw,
      {h1:p.h1.screen,primary:p.page_primary});
    check("page_does_not_scroll_sideways",d.overflow<=1,w,{overflow:d.overflow,wide:d.wide||[]});
    const longest=d.empty_runs[0]||null;
    check("no_empty_vertical_run_is_longer_than_the_limit",!longest||longest.length<=layout.empty_vertical_run_max_px,w,
      {limit:layout.empty_vertical_run_max_px,longest:d.empty_runs.filter(run=>run.length>layout.empty_vertical_run_max_px).map(run=>({...run,
        within:d.sections.filter(item=>item.top<=run.from&&item.top+item.height>=run.from).map(item=>item.element).slice(-1)[0]||null}))});
    const foreign=Object.keys(d.families).filter(family=>!layout.font_families.includes(family));
    check("text_uses_only_the_standard_typefaces",foreign.length===0&&layout.font_families.every(family=>d.fonts_loaded.includes(family)),w,
      {refused:Object.fromEntries(foreign.map(family=>[family,d.families[family]])),loaded:[...new Set(d.fonts_loaded)]});
    check("dark_bands_stay_within_the_limit",d.dark_bands.length<=layout.dark_bands_per_view_max,w,{limit:layout.dark_bands_per_view_max,bands:d.dark_bands});
    check("running_text_stays_within_the_line_length",d.long_lines.length===0,w,{limit:layout.line_characters_max,refused:d.long_lines});
    check("first_screen_shows_the_heading_lead_and_primary_action",inFirstScreen(d.h1.screen,desktop.height)&&inFirstScreen(d.lead?.screen,desktop.height)
      &&inFirstScreen(d.page_primary?.screen,desktop.height),w,{h1:d.h1.screen,lead:d.lead,primary:d.page_primary});
    if(page.price_in_first_screen)check("first_screen_shows_the_price",Boolean(d.price)&&d.price.bottom<=desktop.height,w,{price:d.price,marker:layout.price.marker});
    if(page.scroll_budget==="documentation"){
      if(d.height>layout.contents_list_after_px)check("long_documentation_page_opens_with_a_contents_list",Boolean(d.contents_list)&&d.contents_list.top<desktop.height,w,
        {height:d.height,after:layout.contents_list_after_px,contents_list:d.contents_list});
      else skip("long_documentation_page_opens_with_a_contents_list",w,`the page is ${d.height} pixels tall, within ${layout.contents_list_after_px}`);
    }
    /* The header: one row at the desktop widths, folded into its menu at the narrow ones, the signed-out entries of the site map. */
    const expectedOut=siteMap.header.signed_out;
    for(const width of layout.header_one_row_widths){
      const label=Object.keys(vp).find(name=>vp[name].width===width),tabAt=byWidth[label].page;
      const m=width===desktop.width?d:(await load(tabAt,page.address),await tabAt.evaluate(measure,arguments_(false)));
      const at={...where,width},header=m.header;
      check("header_entries_match_the_site_map",Boolean(header)&&compareEntries(expectedOut,header.entries).length===0,at,{problems:header?compareEntries(expectedOut,header.entries):["no header"]});
      check("header_sits_on_one_row",Boolean(header)&&!header.menu_control_shown&&oneRow(header.entries.map(entry=>entry.box),header.box),at,
        {menu_control_shown:header?.menu_control_shown,bar:header?.box,entries:header?.entries.map(entry=>({label:entry.label,top:Math.round(entry.box.top),bottom:Math.round(entry.box.bottom),right:Math.round(entry.box.right)}))});
    }
    for(const width of layout.header_menu_widths){
      const label=Object.keys(vp).find(name=>vp[name].width===width),tabAt=byWidth[label].page;await load(tabAt,page.address);
      const closed=await tabAt.evaluate(measure,arguments_(false)),at={...where,width},problems=[];
      if(!closed.header){check("header_folds_into_the_menu",false,at,{problems:["no header"]});continue;}
      if(!closed.header.menu_control_shown)problems.push("the menu button is not shown");
      else if(!tapSized(closed.header.menu_control_box))problems.push("the menu button is smaller than the touch minimum");
      const hiddenLinks=expectedOut.filter(entry=>entry.role==="link"||entry.role==="button").filter(entry=>closed.header.entries.some(item=>key(item)===key(entry)));
      if(hiddenLinks.length)problems.push("links stand in the bar before the menu opens: "+JSON.stringify(hiddenLinks.map(key)));
      let opened=null;
      if(closed.header.menu_control_shown){
        await tabAt.locator("header label[for], header button[aria-controls]").first().click();await tabAt.waitForTimeout(150);
        opened=await tabAt.evaluate(measure,arguments_(true));
        const bar=opened.header.box;
        problems.push(...compareEntries(expectedOut,opened.header.entries).map(problem=>"with the menu open: "+problem));
        const outside=opened.header.entries.filter(entry=>(entry.role==="link"||entry.role==="button")&&entry.box.top<bar.bottom-1);
        if(outside.length)problems.push("links outside the menu panel: "+JSON.stringify(outside.map(entry=>entry.label)));
        const small=opened.header.entries.filter(entry=>entry.role!=="brand"&&!tapSized(entry.box));
        if(small.length)problems.push("menu entries under the touch minimum: "+JSON.stringify(small.map(entry=>`${entry.label} ${Math.round(entry.box.width)}x${Math.round(entry.box.height)}`)));
      }
      check("header_folds_into_the_menu",problems.length===0,at,{problems});
    }
    /* The header stays in view, the bar of a phone held sideways stays low or steps aside, and every size shows a primary action. */
    for(const [label,viewport] of Object.entries(vp)){
      const tabAt=byWidth[label].page;await load(tabAt,page.address);
      const at={...where,width:viewport.width,height:viewport.height},sticky=await stickiness(tabAt);
      if(!sticky.present){check("header_stays_in_view",false,at,{problems:["no header"]});continue;}
      if(!sticky.tall){if(["sticky","fixed"].includes(sticky.position))check("header_stays_in_view",true,at,{position:sticky.position});
        else skip("header_stays_in_view",at,"the page is shorter than one and a half screens, and the header is not sticky or fixed");}
      else check("header_stays_in_view",sticky.shown_after_scrolling_down||sticky.shown_after_scrolling_up,at,sticky);
      if(label==="landscape"){
        check("header_is_low_on_a_phone_held_sideways",sticky.height<=layout.header_landscape_max_px||(sticky.tall&&!sticky.shown_after_scrolling_down&&sticky.shown_after_scrolling_up),at,
          {height:sticky.height,limit:layout.header_landscape_max_px,position:sticky.position});
        const m=await tabAt.evaluate(measure,arguments_(false));
        check("first_screen_shows_a_primary_action",m.any_primary_in_first_screen,at,{page_primary:m.page_primary});
      }else if(label==="laptop"||label==="menu"){
        const m=await tabAt.evaluate(measure,arguments_(false));
        check("first_screen_shows_a_primary_action",m.any_primary_in_first_screen,at,{page_primary:m.page_primary});
      }
    }
    /* A jump to a part of the page lands below the header. */
    await load(tab,page.address);
    for(const href of d.in_page_links){
      const at={...where,width:desktop.width,link:href};
      try{
        await tab.locator(`a[href="${href}"]`).filter({visible:true}).first().click();await tab.waitForTimeout(400);
        const landing=await tab.evaluate(target=>{const id=decodeURIComponent(new URL(target,location.href).hash.slice(1)),element=document.getElementById(id),header=document.querySelector("header");
          if(!element)return null;const r=element.getBoundingClientRect(),bar=header?header.getBoundingClientRect():null;
          return {target_top:Math.round(r.top),header_bottom:bar?Math.round(bar.bottom):null};},href);
        check("jump_to_a_part_of_the_page_lands_below_the_header",Boolean(landing)&&(landing.header_bottom===null||landing.header_bottom<=0||landing.target_top>=landing.header_bottom-1),at,landing||{});
        await load(tab,page.address);
      }catch(error){check("jump_to_a_part_of_the_page_lands_below_the_header",false,at,{error:String(error).slice(0,160)});}
    }
  }
  /* The signed-in and the operator header, read after signing in with a local fixture key. The deployed service is never signed in to. */
  for(const state of ["signed_in","operator"]){
    const where={state};
    if(mode!=="local"){skip("signed_in_header_matches_the_site_map",where,"a deployed origin is read without credentials");continue;}
    const {context,page:tab}=await open(desktop);
    try{
      await load(tab,"/login");await tab.fill("#access-token",keys[state]);await tab.click("#connect-button");
      await tab.waitForFunction(()=>document.querySelector("header [data-signed-in]:not([hidden])"),null,{timeout:15000});
      if(state==="operator")await tab.waitForFunction(()=>[...document.querySelectorAll("header a[href]")].some(a=>a.getAttribute("href")==="/admin"&&a.checkVisibility()),null,{timeout:15000}).catch(()=>{});
      const m=await tab.evaluate(measure,arguments_(false));
      check("signed_in_header_matches_the_site_map",compareEntries(siteMap.header[state],m.header.entries).length===0,{...where,width:desktop.width},{problems:compareEntries(siteMap.header[state],m.header.entries)});
      await tab.setViewportSize({width:phone.width,height:phone.height});await tab.waitForTimeout(150);
      await tab.locator("header label[for], header button[aria-controls]").first().click();await tab.waitForTimeout(150);
      const narrow=await tab.evaluate(measure,arguments_(true));
      check("signed_in_header_matches_the_site_map",compareEntries(siteMap.header[state],narrow.header.entries).length===0,{...where,width:phone.width},{problems:compareEntries(siteMap.header[state],narrow.header.entries)});
    }catch(error){check("signed_in_header_matches_the_site_map",false,where,{error:String(error).slice(0,200)});}
    await context.close();
  }
  /* Each hostname opens its page. Only a deployed origin has hostnames to open. */
  for(const surface of siteMap.hostnames){
    const where={hostname:surface.hostname,address:surface.address+(surface.anchor?"#"+surface.anchor:"")};
    if(mode!=="url"){skip("hostname_opens_its_page",where,"a local service answers on one loopback address");continue;}
    const expected=siteMap.pages.find(item=>item.address===surface.address);
    const {context,page:tab}=await open(desktop);
    try{
      const response=await tab.goto("https://"+surface.hostname+"/",{waitUntil:"load",timeout:45000});await tab.waitForLoadState("networkidle",{timeout:8000}).catch(()=>{});
      const shown=await tab.evaluate(anchor=>{const view=[...document.querySelectorAll("[data-view]")].find(item=>item.checkVisibility());const target=anchor?document.getElementById(anchor):null;
        const r=target?.getBoundingClientRect();return {view:view?.dataset.view??null,path:location.pathname,anchor_top:r?Math.round(r.top):null,anchor_bottom:r?Math.round(r.bottom):null};},surface.anchor);
      const opened=response?.status()===200&&shown.view===expected.view&&(!surface.anchor||(shown.anchor_top!==null&&shown.anchor_top>=0&&shown.anchor_top<desktop.height));
      surfaces.push({...where,status:response?.status(),...shown,expected_view:expected.view});
      check("hostname_opens_its_page",opened,where,{status:response?.status(),expected_view:expected.view,...shown});
    }catch(error){check("hostname_opens_its_page",false,where,{error:String(error).slice(0,200)});}
    await context.close();
  }
  for(const {context} of Object.values(byWidth))await context.close();
}catch(error){check("layout_measurement_completed",false,{},{error:String(error.stack||error).slice(0,600)});}
finally{
  if(browser)await browser.close();
  if(child){child.stdin.end("\n");await new Promise(done=>{if(child.exitCode!==null)return done();const timer=setTimeout(()=>{child.kill("SIGTERM");done();},5000);child.once("exit",()=>{clearTimeout(timer);done();});});lines?.close();}
}
const rules={};for(const row of checks){const rule=rules[row.name]??={passed:0,failed:0};rule[row.passed?"passed":"failed"]+=1;}
const revision=spawnSync("git",["rev-parse","HEAD"],{cwd:root,encoding:"utf8"}).stdout.trim()||null;
const result={record_type:"website_layout_check/v1",mode,origin:mode==="url"?origin:"a loopback service started from this checkout",observed_at:new Date().toISOString(),
  checkout_revision:revision,site_map_sha256:recordDigest("web_site_map.json"),layout_standard_sha256:recordDigest("web_layout_standard.json"),browser:browser?.version?.()??null,
  viewports:vp,rules,checks,skipped,pages,hostnames:surfaces,passed:checks.filter(row=>row.passed).length,total:checks.length,all_passed:checks.every(row=>row.passed),
  failed_pages:[...new Set(checks.filter(row=>!row.passed&&row.address).map(row=>row.address))],errors:[...new Set(errors)].slice(0,40),external_requests_blocked:[...external],
  credentials_used:mode==="local"?"local fixture keys of a temporary loopback service only":false,forms_submitted:mode==="local"?["the sign-in form of the loopback service"]:[],
  external_mutations:false,
  limitations:["One headless Chrome on the development workstation; not field data from real devices.",
    "Contrast is sampled on the element that holds the text, against the nearest painted ground color; text over a picture or over a band painted with a border image is measured against the ground behind it.",
    "Line length is the number of characters of a paragraph's own text that a full line holds, from the width of that text in its own typeface.",
    "An empty run is vertical space with no text, picture, control, or card edge or ground inside it; a rule across the whole window does not end a run.",
    "The jump to a part of a page is measured for at most two links on each page, at 1440 pixels."]};
writeFileSync(output,JSON.stringify(result,null,2)+"\n",{flag:"wx"});
console.log(JSON.stringify({passed:result.passed,total:result.total,all_passed:result.all_passed,rules,skipped:skipped.length,output}));
process.exitCode=result.all_passed?0:1;
