/* The owner's September 29 direction: three equal entry points, one product.
   Rules inspect meaning and destinations, not a verbatim marketing headline. */
export const audienceDestinations={engineers:"/for/coding-agents",designers:"/for/designers","ai-agents":"/for/protocol-and-client"};
export const keepsThePerStepOptionOut=copy=>!/fresh harness|harness (?:for|per) (?:each|every) step|one harness per step/i.test(copy.text);
export const heroProblems=copy=>[
  ...([/\bengineers\b/i,/\bdesigners\b/i,/\bAI agents\b/i].every(rule=>rule.test(copy.headline))?[]:["the hero must name all three audiences"]),
  ...(/\blibrary\b/i.test(copy.subhead)&&/\bcode\b/i.test(copy.subhead)&&/\btools\b/i.test(copy.subhead)?[]:["the hero must explain the shared product"]),
  ...(/\bby hand\b|\brewriting\b/i.test(copy.subhead)?[]:["the hero must explain the repeated work it removes"]),
  ...(keepsThePerStepOptionOut(copy)?[]:["the hero promises a fresh harness for each step"])];
export function heroCheckRejectsItsKnownWrongCases(copy){
  return ["engineers","designers","AI agents"].every(word=>heroProblems({...copy,headline:copy.headline.replace(new RegExp(word,"i"),"")}).length>0)
    &&heroProblems({...copy,subhead:""}).length>0
    &&heroProblems({...copy,text:copy.text+" Each step runs in a fresh harness."}).length>0;
}
export function audienceProblems(cards){
  const problems=[];
  if(JSON.stringify(cards.map(card=>card.id))!==JSON.stringify(Object.keys(audienceDestinations)))problems.push("missing or repeated audience");
  for(const card of cards){
    if(!card.title||card.href!==audienceDestinations[card.id])problems.push("missing heading or wrong destination");
    if(card.id==="designers"&&!/in development/i.test(card.text))problems.push("creative availability is not disclosed");
  }
  return problems;
}
export async function checkAudiences(page,check){
  const cards=await page.locator("[data-audience]").evaluateAll(items=>items.map(item=>({id:item.dataset.audience,title:item.querySelector("h2")?.textContent,
    href:item.querySelector("[data-audience-target]")?.getAttribute("href"),text:item.textContent})));
  check("three_audience_paths_are_distinct_and_disclose_availability",audienceProblems(cards).length===0);
  check("audience_check_detects_missing_path_wrong_target_and_hidden_availability",audienceProblems(cards.slice(0,2)).length>0
    &&audienceProblems(cards.map(card=>({...card,href:"/"}))).length>0
    &&audienceProblems(cards.map(card=>({...card,text:""}))).length>0);
}
