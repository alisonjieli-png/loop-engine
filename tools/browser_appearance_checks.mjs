/* Read the site's actual supported appearance, not the browser's OS preference.
   This samples body text and the visible headline; the full text contrast audit
   remains in check_website_layout.mjs. No account, provider or analytics data. */
export async function setRequestedAppearance(context, origin, choice){
  if(!["light","dark"].includes(choice))throw new Error("Unsupported test appearance");
  await context.addInitScript(({origin,choice})=>{
    if(location.origin===origin)localStorage.setItem("baltor.appearance",choice);
  },{origin,choice});
}

export async function readRequestedAppearance(page){
  return page.evaluate(()=>{
    const canvas=document.createElement("canvas");canvas.width=canvas.height=1;
    const brush=canvas.getContext("2d",{willReadFrequently:true});
    const colour=text=>{brush.clearRect(0,0,1,1);brush.fillStyle=text;brush.fillRect(0,0,1,1);return [...brush.getImageData(0,0,1,1).data];};
    const blend=(front,back)=>front.slice(0,3).map((v,i)=>v*front[3]/255+back[i]*(1-front[3]/255));
    const light=rgb=>{const channels=rgb.slice(0,3).map(value=>{const n=value/255;return n<=.04045?n/12.92:((n+.055)/1.055)**2.4;});return .2126*channels[0]+.7152*channels[1]+.0722*channels[2];};
    const background=node=>{
      const parents=[];for(let current=node;current;current=current.parentElement)parents.unshift(current);
      let result=[255,255,255];
      for(const parent of parents){const style=getComputedStyle(parent);if(style.backgroundImage!=="none")return null;result=blend(colour(style.backgroundColor),result);}
      return result;
    };
    const sample=node=>{
      if(!node)return null;
      const ground=background(node);if(!ground)return {contrast:null,reason:"background_image"};
      const ink=blend(colour(getComputedStyle(node).color),ground),levels=[light(ink),light(ground)].sort((a,b)=>b-a);
      return {contrast:(levels[0]+.05)/(levels[1]+.05),ground_luminance:light(ground)};
    };
    const heading=[...document.querySelectorAll("h1")].find(node=>node.getClientRects().length>0&&!node.closest("[hidden]"));
    return {theme:document.documentElement.dataset.theme||"system",control:document.getElementById("theme")?.textContent.trim()||"",
      body:sample(document.body),heading:sample(heading),contrast_scope:"body_and_visible_headline"};
  });
}

export function appearanceProblems(value,expected){
  const errors=[];
  if(value.theme!==expected||value.control!=="Appearance: "+expected)errors.push("the supported appearance choice did not apply");
  if(!Number.isFinite(value.body?.ground_luminance)||(expected==="dark"?value.body.ground_luminance>=.5:value.body.ground_luminance<=.5))errors.push("the rendered ground contradicts the appearance label");
  if([value.body,value.heading].some(sample=>!Number.isFinite(sample?.contrast)||sample.contrast<4.5))errors.push("sampled text contrast is below 4.5 or unavailable");
  return errors;
}

export function appearanceKnownWrongControls(value,expected){
  return appearanceProblems(value,expected).length===0
    &&appearanceProblems({...value,theme:expected==="dark"?"light":"dark"},expected).length>0
    &&appearanceProblems({...value,body:{contrast:1,ground_luminance:value.body.ground_luminance}},expected).length>0
    &&appearanceProblems({...value,body:{...value.body,ground_luminance:expected==="dark"?1:0}},expected).length>0;
}
