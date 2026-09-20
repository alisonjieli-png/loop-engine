/* Browser-only checks for the owned local diagram, never a production page. */
import {chromium} from "../../showcase/node_modules/playwright-core/index.mjs";
import {fileURLToPath} from "node:url";
import {readFileSync} from "node:fs";
import {createHash} from "node:crypto";

const directory = new URL(".",import.meta.url);
const source = new URL("mvp-client-server.html",directory);
const browser = await chromium.launch({executablePath:"/opt/google/chrome/chrome",headless:true,args:["--no-sandbox"]});
const checks = [], matrix = [], screenshots = [], pageErrors = [], requests = [];
const check = (name,passed,detail={}) => checks.push({name,passed:passed===true,detail});
const page = await browser.newPage({viewport:{width:1440,height:1200},colorScheme:"light"});
page.on("pageerror",error => pageErrors.push(error.message));
page.on("request",request => requests.push({url:request.url(),type:request.resourceType()}));
const settled = async () => page.waitForFunction(() =>
  document.getElementById("diagram").getAttribute("aria-busy")==="false");

try {
  await page.goto(source.href);
  await settled();
  for (const theme of ["light","dark"]) {
    await page.emulateMedia({colorScheme:theme,reducedMotion:"reduce"});
    for (const width of [1440,1280,1024,736,360,320]) {
      await page.setViewportSize({width,height:1000});
      for (const view of ["overview","sign-in","retrieval","execution"]) {
        await page.evaluate(async id => {await window.LoopArchitectureDiagram.render(id);},view);
        await settled();
        const observed = await page.evaluate(() => {
          const cards=[...document.querySelectorAll(".map-card")];
          const svgLabels=[...document.querySelectorAll(".edge-label")];
          const cross = (a,b) => Math.min(a.right,b.right)-Math.max(a.left,b.left)>1 &&
            Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1;
          const collisions=[];
          for(const text of svgLabels) for(const card of cards)
            if(cross(text.getBoundingClientRect(),card.getBoundingClientRect())) collisions.push("edge label/card");
          const state=window.LoopArchitectureDiagram.getState();
          const channel=c=>c<=0.04045?c/12.92:((c+0.055)/1.055)**2.4;
          const rgb=value=>(value.match(/[\d.]+/g)||[]).slice(0,3).map(n=>Number(n)/255);
          const luminance=value=>{const c=rgb(value).map(channel);return .2126*c[0]+.7152*c[1]+.0722*c[2];};
          const contrasts=[...document.querySelectorAll(".card-title,.card-copy,.card-owner,.card-item-detail,.status")].map(el=>{
            const style=getComputedStyle(el);let target=el,bg="rgba(0, 0, 0, 0)";
            while(target){bg=getComputedStyle(target).backgroundColor;if(bg!=="rgba(0, 0, 0, 0)"&&bg!=="transparent")break;target=target.parentElement;}
            const a=luminance(style.color),b=luminance(bg);
            return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
          });
          for(const edge of state?.routes||[]) for(const card of state.nodes){
            if(card.id===edge.from || card.id===edge.to)continue;
            for(let i=1;i<edge.points.length;i++){
              const a=edge.points[i-1],b=edge.points[i];
              if(a.x===b.x && a.x>card.x+1 && a.x<card.x+card.width-1 &&
                Math.max(a.y,b.y)>card.y+1 && Math.min(a.y,b.y)<card.y+card.height-1) collisions.push("edge/card");
              if(a.y===b.y && a.y>card.y+1 && a.y<card.y+card.height-1 &&
                Math.max(a.x,b.x)>card.x+1 && Math.min(a.x,b.x)<card.x+card.width-1) collisions.push("edge/card");
            }
          }
          return {
            engine:document.getElementById("diagram").dataset.layoutEngine,
            direction:document.getElementById("diagram").dataset.direction,
            active:document.body.dataset.activeView,
            errors:[...window.LoopArchitectureDiagram.layoutErrors(),...collisions],
            cards:cards.length,
            selected:[...document.querySelectorAll('[data-view][aria-pressed="true"]')].map(el=>el.dataset.view),
            minimumCardText:Math.min(...[...document.querySelectorAll(".map-card span")].map(el=>parseFloat(getComputedStyle(el).fontSize))),
            minimumTextContrast:Math.min(...contrasts),
            background:getComputedStyle(document.body).backgroundColor
          };
        });
        const pass=observed.engine==="ELK.js@0.12.0" && observed.active===view &&
          observed.errors.length===0 && observed.selected.length===1 && observed.selected[0]===view &&
          observed.minimumCardText>=11 && observed.minimumTextContrast>=4.5;
        matrix.push({theme,width,view,passed:pass,...observed});
        if(width===1440 || width===360){
          const name="mvp-client-server-"+view+"-"+width+"-"+theme+".png";
          await page.screenshot({path:fileURLToPath(new URL(name,directory)),fullPage:true});
          screenshots.push(name);
        }
      }
    }
  }
  check("forty_eight_viewport_theme_view_combinations_are_legible",matrix.every(row=>row.passed),
    {passed:matrix.filter(row=>row.passed).length,total:matrix.length,failed:matrix.filter(row=>!row.passed)});

  await page.setViewportSize({width:1024,height:1000});
  await page.locator('[data-view="retrieval"]').focus();
  await page.keyboard.press("Enter"); await settled();
  check("keyboard_selects_view",await page.evaluate(()=>document.body.dataset.activeView==="retrieval"));
  await page.locator(".map-card").first().focus(); await page.keyboard.press("Enter");
  check("keyboard_opens_component_detail",await page.locator("#component-detail").isVisible());
  check("opened_detail_is_inside_the_viewport",await page.evaluate(()=>{
    const r=document.getElementById("component-detail").getBoundingClientRect();
    return r.top>=0 && r.bottom<=innerHeight+1;
  }));
  await page.keyboard.press("Escape");
  check("escape_closes_detail_and_returns_focus",await page.evaluate(() =>
    document.getElementById("component-detail").hidden && document.activeElement.classList.contains("map-card")));
  await page.keyboard.press("Tab");
  check("native_tab_order_reaches_the_next_component",await page.evaluate(()=>document.activeElement.dataset.card==="permit"));
  await page.selectOption("#appearance","light");
  const light=await page.evaluate(()=>getComputedStyle(document.body).backgroundColor);
  await page.selectOption("#appearance","dark");
  const dark=await page.evaluate(()=>getComputedStyle(document.body).backgroundColor);
  check("appearance_control_changes_actual_surfaces",light!==dark,{light,dark});
  await page.selectOption("#appearance","system");

  const badData = await page.evaluate(() => {
    const api=window.LoopArchitectureDiagram;
    const edits=[
      ["provider_claimed_implemented",d=>{d.facts.providers.Supabase="existing";}],
      ["postgres_used_as_body_store",d=>{d.facts.proposedStorage.bodies="Postgres";}],
      ["pgvector_claimed_current_default",d=>{d.facts.currentRetrieval.vector="pgvector";}],
      ["history_assigned_to_model_provider",d=>{d.facts.runHistoryOwner="model provider";}],
      ["remote_authorization_claimed_implemented",d=>{d.facts.remoteOauthImplemented=true;}],
      ["visible_vendor_status_changed",d=>{d.views.overview.nodes[2].items[0].status="existing";}],
      ["model_moved_inside_product",d=>{d.views.execution.nodes.find(n=>n.id==="model").zone="engine";}],
      ["dangling_connection",d=>{d.views.retrieval.edges[0].to="missing";}]
    ];
    return edits.map(([name,edit])=>{const d=structuredClone(api.data);edit(d);return{name,errors:api.validateData(d)};});
  });
  check("eight_false_or_broken_content_variants_are_rejected",badData.every(row=>row.errors.length),badData);

  await page.setViewportSize({width:360,height:1000});
  const adversarial=await page.evaluate(async()=>{
    const api=window.LoopArchitectureDiagram, node=api.data.views.retrieval.nodes[0], old=node.title;
    node.title="ExtremelyLongUnbrokenAssignmentIdentifier".repeat(5)+" <img src=x onerror='window.unexpectedExecution=true'>";
    await api.render("retrieval");
    document.querySelector(".map-card").click();
    const result={errors:api.layoutErrors(),injectedElement:!!document.querySelector(".map-card img"),
      executed:window.unexpectedExecution===true,textVisible:document.querySelector(".card-title").textContent.includes("<img")};
    node.title=old; await api.render("retrieval"); return result;
  });
  check("long_and_markup_shaped_labels_wrap_without_execution",adversarial.errors.length===0 &&
    !adversarial.injectedElement && !adversarial.executed && adversarial.textVisible,adversarial);
  const geometryMutants=await page.evaluate(async()=>{
    const api=window.LoopArchitectureDiagram;
    await api.render("overview");
    const cards=document.querySelectorAll(".map-card");
    cards[1].style.left=cards[0].style.left;cards[1].style.top=cards[0].style.top;
    const overlap=api.layoutErrors();
    await api.render("overview");
    document.querySelector(".map-card").style.height="10px";
    const clipping=api.layoutErrors();
    await api.render("overview");
    return{overlap,clipping};
  });
  check("overlap_and_clipping_mutants_are_detected",geometryMutants.overlap.some(x=>x.startsWith("Overlapping")) &&
    geometryMutants.clipping.some(x=>x.startsWith("Clipped")),geometryMutants);
  const rapid=await page.evaluate(async()=>{
    const api=window.LoopArchitectureDiagram;
    await Promise.all([api.render("overview"),api.render("sign-in"),api.render("execution")]);
    return{active:document.body.dataset.activeView,state:api.getState().view,errors:api.layoutErrors()};
  });
  check("rapid_view_changes_cannot_publish_stale_layout",rapid.active==="execution" && rapid.state==="execution" && !rapid.errors.length,rapid);

  const fallback=await browser.newPage({viewport:{width:360,height:1000}});
  await fallback.route("https://cdn.jsdelivr.net/**",route=>route.abort());
  await fallback.goto(source.href);
  await fallback.waitForFunction(()=>document.getElementById("diagram").getAttribute("aria-busy")==="false");
  const fallbackState=await fallback.evaluate(()=>({engine:document.getElementById("diagram").dataset.layoutEngine,
    text:document.getElementById("layout-message").textContent,cards:document.querySelectorAll(".map-card").length,
    errors:window.LoopArchitectureDiagram.layoutErrors(),connections:document.getElementById("connections").open}));
  check("blocked_layout_dependency_has_honest_readable_fallback",fallbackState.engine==="unavailable" &&
    fallbackState.cards===3 && fallbackState.connections && !fallbackState.errors.length,fallbackState);
  await fallback.close();
  check("no_runtime_javascript_errors",pageErrors.length===0,pageErrors);
  const allowed=requests.every(r=>
    (r.url.startsWith(directory.href) && ["document","stylesheet","script"].includes(r.type)) ||
    (r.url==="https://cdn.jsdelivr.net/npm/elkjs@0.12.0/lib/elk.bundled.js" && r.type==="script"));
  check("only_owned_files_and_one_pinned_static_package_are_requested",allowed,requests);
} finally { await browser.close(); }

const files=["mvp-client-server.html","mvp-client-server.css","mvp-client-server.data.js","mvp-client-server.js"];
const hashes=Object.fromEntries(files.map(name=>[name,createHash("sha256").update(readFileSync(new URL(name,directory))).digest("hex")]));
const result={record_type:"client_server_diagram_browser_checks/v1",browser:"/opt/google/chrome/chrome",
  library:"ELK.js 0.12.0",checks,matrix,screenshots,source_sha256:hashes,
  passed:checks.every(row=>row.passed),network_scope:"Static package only; no fetch, API, account or payment call."};
console.log(JSON.stringify(result,null,2));
process.exitCode=result.passed?0:1;
