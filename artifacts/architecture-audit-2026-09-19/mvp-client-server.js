/* ELK.js owns layout and orthogonal routing. This file owns presentation only. */
(() => {
  "use strict";
  const data = window.LOOP_ARCHITECTURE;
  const diagram = document.getElementById("diagram");
  const message = document.getElementById("layout-message");
  const detail = document.getElementById("component-detail");
  const buttons = [...document.querySelectorAll("[data-view]")];
  const statusNames = {proposed:"Proposed",existing:"Existing local",external:"External",customer:"Customer-controlled",mixed:"Mixed maturity"};
  let sequence = 0, selected = null, activeView = "overview", lastWidth = 0;
  let layoutState = null;
  const elk = typeof window.ELK === "function" ? new window.ELK({algorithms:["layered"]}) : null;
  const element = (tag, className, text) => {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (text !== undefined) item.textContent = text;
    return item;
  };
  const svgElement = (tag, attrs = {}) => {
    const item = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.entries(attrs).forEach(([name,value]) => item.setAttribute(name,String(value)));
    return item;
  };

  function validateData(value) {
    const errors = [];
    const f = value && value.facts;
    if (!f || f.deployment !== "proposed" || f.remoteHttpImplemented !== false || f.remoteOauthImplemented !== false)
      errors.push("Hosted implementation state is not the reviewed proposal.");
    if (f?.runHistoryOwner !== "Loop Engine") errors.push("Run History ownership changed.");
    if (f?.currentRetrieval?.lexical !== "SQLite FTS5" || f?.currentRetrieval?.vector !== "hash vectors")
      errors.push("Current retrieval defaults changed.");
    if (JSON.stringify(f?.currentRetrieval?.optional) !== JSON.stringify(["model2vec","LanceDB"]))
      errors.push("Optional retrieval adapters changed.");
    if (f?.proposedStorage?.metadata !== "Supabase Postgres + pgvector" || f?.proposedStorage?.bodies !== "Supabase private bucket")
      errors.push("The proposed metadata/body split changed.");
    for (const name of ["Vercel","Supabase","Stripe"])
      if (f?.providers?.[name] !== "proposed") errors.push(name + " must remain proposed.");
    if (f?.localProtocol !== "2025-11-25") errors.push("Local protocol evidence changed.");
    if (!value?.views || Object.keys(value.views).join(",") !== "overview,sign-in,retrieval,execution")
      errors.push("The four reviewed views are required.");
    for (const [name,view] of Object.entries(value?.views || {})) {
      if (!Array.isArray(view.nodes) || !view.nodes.length) { errors.push(name + ": missing content."); continue; }
      const ids = new Set(view.nodes.map(n => n.id));
      if (ids.size !== view.nodes.length) errors.push(name + ": duplicate identities.");
      for (const node of view.nodes) {
        if (!["customer","engine","vendor"].includes(node.zone) || !statusNames[node.status])
          errors.push(name + ": unknown trust boundary or status.");
        if (![node.title,node.copy,node.detail,node.limit].every(t => typeof t === "string" && t.trim()))
          errors.push(name + ": incomplete component explanation.");
      }
      for (const edge of view.edges || [])
        if (!ids.has(edge.from) || !ids.has(edge.to)) errors.push(name + ": dangling connection.");
    }
    const providers = value?.views?.overview?.nodes.find(n => n.id === "providers");
    for (const name of ["Supabase","Stripe"])
      if (providers?.items?.find(n => n.name === name)?.status !== "proposed") errors.push(name + ": label must remain proposed.");
    const local = value?.views?.execution?.nodes || [];
    if (local.find(n => n.id === "history")?.zone !== "customer") errors.push("Run History must stay on the execution side.");
    if (local.find(n => n.id === "model")?.zone !== "vendor") errors.push("Remote models must stay external.");
    return errors;
  }

  function closeDetails(returnFocus = false) {
    const previous = selected;
    selected = null;
    diagram.querySelectorAll(".map-card").forEach(card => card.setAttribute("aria-expanded","false"));
    detail.hidden = true;
    if (returnFocus && previous) diagram.querySelector('[data-card="' + previous + '"]')?.focus();
  }
  function showDetails(node, button) {
    if (selected === node.id) { closeDetails(); return; }
    selected = node.id;
    diagram.querySelectorAll(".map-card").forEach(card => card.setAttribute("aria-expanded",String(card === button)));
    document.getElementById("detail-owner").textContent = node.owner;
    document.getElementById("detail-title").textContent = node.title;
    document.getElementById("detail-copy").textContent = node.detail;
    document.getElementById("detail-state").textContent = node.limit;
    detail.hidden = false;
    detail.scrollIntoView({block:"nearest",behavior:"auto"});
  }
  function makeCard(node, width) {
    const card = element("button","map-card");
    card.type = "button";
    card.dataset.card = node.id;
    card.dataset.zone = node.zone;
    card.dataset.status = node.status;
    card.style.width = width + "px";
    card.style.visibility = "hidden";
    card.setAttribute("aria-expanded","false");
    card.setAttribute("aria-controls","component-detail");
    card.append(element("span","card-owner",node.owner),element("span","card-title",node.title),element("span","card-copy",node.copy));
    if (node.items) {
      const list = element("span","card-items");
      node.items.forEach(item => {
        const row = element("span","card-item");
        row.append(element("span","card-item-name",item.name),element("span","card-item-detail",item.detail));
        const state = element("span","card-item-state",statusNames[item.status]);
        state.dataset.status = item.status;
        row.append(state); list.append(row);
      });
      card.append(list);
    }
    card.append(element("span","status " + node.status,node.state));
    card.addEventListener("click",() => showDetails(node,card));
    return card;
  }
  function renderNotes(view) {
    const notes = document.getElementById("view-notes");
    notes.replaceChildren();
    view.notes.forEach(note => {
      const section = element("section","view-note");
      if (note.tag) section.append(element("span","note-tag",note.tag));
      section.append(element("h3","",note.title),element("p","",note.text));
      notes.append(section);
    });
    const list = document.getElementById("connection-list");
    list.replaceChildren();
    view.edges.forEach(edge => {
      const source = view.nodes.find(n => n.id === edge.from);
      const target = view.nodes.find(n => n.id === edge.to);
      const item = element("li");
      item.append(element("strong","",source.title + " → " + target.title),document.createTextNode(": " + edge.label + "."));
      list.append(item);
    });
  }
  async function calculate(view, width, horizontal) {
    const count = activeView === "overview" ? 3 : 5;
    const cardWidth = horizontal
      ? Math.max(activeView === "overview" ? 190 : 172,Math.min(activeView === "overview" ? 282 : 216,
          (width - (activeView === "overview" ? 440 : 48 * (count - 1) + 32)) / count))
      : Math.min(420,width - 32);
    diagram.replaceChildren();
    const cards = new Map(view.nodes.map(node => {
      const card = makeCard(node,cardWidth);
      diagram.append(card); return [node.id,card];
    }));
    const heights = [...cards.values()].map(card => Math.ceil(card.getBoundingClientRect().height));
    const maximum = Math.max(...heights);
    const children = view.nodes.map((node,index) => ({
      id:node.id, width:cardWidth,
      height:horizontal ? maximum : heights[index]
    }));
    children.forEach(node => cards.get(node.id).style.height = node.height + "px");
    children.forEach(node => {
      node.layoutOptions = {"elk.portConstraints":"FIXED_POS"};
      node.ports = horizontal
        ? [{id:node.id+"-in",x:0,y:node.height/2,width:0,height:0,layoutOptions:{"elk.port.side":"WEST"}},
           {id:node.id+"-out",x:node.width,y:node.height/2,width:0,height:0,layoutOptions:{"elk.port.side":"EAST"}}]
        : [{id:node.id+"-in",x:node.width/2,y:0,width:0,height:0,layoutOptions:{"elk.port.side":"NORTH"}},
           {id:node.id+"-out",x:node.width/2,y:node.height,width:0,height:0,layoutOptions:{"elk.port.side":"SOUTH"}}];
    });
    const visibleEdges = view.edges.filter(edge => horizontal || !edge.mobileTextOnly);
    const edges = visibleEdges.map(edge => ({
      id:edge.id,sources:[edge.from+"-out"],targets:[edge.to+"-in"],
      ...(horizontal && activeView === "overview" ? {labels:[{text:edge.label,width:edge.label.length * 6.3 + 4,height:18}]} : {})
    }));
    if (!horizontal) {
      for (let i = 1; i < children.length; i++)
        if (!edges.some(edge => edge.sources[0] === children[i - 1].id+"-out" && edge.targets[0] === children[i].id+"-in"))
          edges.push({id:"ordering-" + i,sources:[children[i - 1].id+"-out"],targets:[children[i].id+"-in"]});
    }
    if (!elk) return {cards,unavailable:true};
    const graph = await elk.layout({
      id:"architecture",children,edges,
      layoutOptions:{
        "elk.algorithm":"layered","elk.direction":horizontal ? "RIGHT" : "DOWN",
        "elk.edgeRouting":"ORTHOGONAL","elk.padding":"[top=22,left=16,bottom=22,right=16]",
        "elk.spacing.nodeNode":"36","elk.layered.spacing.nodeNodeBetweenLayers":horizontal ? "48" : "46",
        "elk.layered.considerModelOrder.strategy":"NODES_AND_EDGES",
        "elk.layered.crossingMinimization.forceNodeModelOrder":"true",
        "elk.layered.nodePlacement.bk.fixedAlignment":"BALANCED"
      }
    });
    return {graph,cards,visibleEdges,horizontal};
  }
  function draw(result, width, view) {
    const {graph,cards,visibleEdges,horizontal} = result;
    const offset = Math.max(0,(width - graph.width) / 2);
    const svg = svgElement("svg",{width,height:graph.height,viewBox:"0 0 " + width + " " + graph.height,"aria-hidden":"true"});
    const definitions = svgElement("defs");
    const marker = svgElement("marker",{id:"diagram-arrow",viewBox:"0 0 8 8",refX:7,refY:4,markerWidth:6,markerHeight:6,orient:"auto"});
    marker.append(svgElement("path",{d:"M 1 1 L 7 4 L 1 7 Z",class:"edge-arrow"})); definitions.append(marker); svg.append(definitions);
    const group = svgElement("g",{transform:"translate(" + offset + " 0)"});
    const routed = [];
    for (const edge of graph.edges) {
      const content = visibleEdges.find(item => item.id === edge.id);
      if (!content) continue;
      for (const section of edge.sections || []) {
        const points = [section.startPoint,...(section.bendPoints || []),section.endPoint];
        const path = svgElement("path",{d:points.map((point,index) => (index ? "L " : "M ") + point.x + " " + point.y).join(" "),class:"edge-path" + (content.optional ? " optional" : ""),"marker-end":"url(#diagram-arrow)"});
        group.append(path);
        routed.push({id:edge.id,from:content.from,to:content.to,points:points.map(p => ({x:p.x+offset,y:p.y}))});
      }
      for (const label of edge.labels || []) {
        const text = svgElement("text",{x:label.x+label.width/2,y:label.y+13,"text-anchor":"middle",class:"edge-label"});
        text.textContent = label.text; group.append(text);
      }
    }
    svg.append(group); diagram.prepend(svg);
    for (const node of graph.children) {
      const card = cards.get(node.id);
      card.style.left = (node.x + offset) + "px"; card.style.top = node.y + "px"; card.style.visibility = "visible";
    }
    diagram.style.height = graph.height + "px";
    diagram.classList.remove("layout-fallback");
    diagram.dataset.layoutEngine = "ELK.js@0.12.0";
    diagram.dataset.direction = horizontal ? "horizontal" : "vertical";
    layoutState = {view:activeView,width,height:graph.height,routes:routed,nodes:graph.children.map(n => ({...n,x:n.x+offset}))};
    document.getElementById("connections").open = !horizontal;
    document.getElementById("diagram-caption").textContent = view.caption;
  }
  async function render(id = activeView) {
    clearTimeout(resizeToken);
    const current = ++sequence;
    const problems = validateData(data);
    if (problems.length) {
      diagram.replaceChildren(); diagram.style.height = "auto"; diagram.setAttribute("aria-busy","false");
      message.hidden = false; message.textContent = "Architecture data failed validation. Read the architecture note for the reviewed version.";
      diagram.dataset.layoutEngine = "refused";
      return;
    }
    activeView = data.views[id] ? id : "overview";
    const view = data.views[activeView];
    document.body.dataset.activeView = activeView;
    buttons.forEach(button => button.setAttribute("aria-pressed",String(button.dataset.view === activeView)));
    document.getElementById("view-eyebrow").textContent = view.eyebrow;
    document.getElementById("view-title").textContent = view.title;
    document.getElementById("view-description").textContent = view.description;
    closeDetails(); renderNotes(view);
    diagram.setAttribute("aria-busy","true");
    message.hidden = true;
    const width = diagram.clientWidth;
    lastWidth = width;
    try {
      let horizontal = width >= (activeView === "overview" ? 880 : 1050);
      let result = await calculate(view,width,horizontal);
      if (current !== sequence) return;
      if (!result.unavailable && result.graph.width > width + 1 && horizontal) {
        horizontal = false; result = await calculate(view,width,false);
        if (current !== sequence) return;
      }
      if (result.unavailable) throw new Error("layout package unavailable");
      draw(result,width,view);
    } catch (_) {
      if (current !== sequence) return;
      diagram.classList.add("layout-fallback"); diagram.dataset.layoutEngine = "unavailable";
      diagram.querySelectorAll(".map-card").forEach(card => {card.style.visibility="visible";card.style.height="auto";});
      diagram.style.height="auto";
      message.hidden=false; message.textContent="Automatic layout is unavailable. The same architecture is shown as readable boxes and connections.";
      document.getElementById("connections").open=true;
      document.getElementById("diagram-caption").textContent=view.caption;
    }
    diagram.setAttribute("aria-busy","false");
    document.getElementById("view-announcement").textContent = view.eyebrow + ". " + view.nodes.length + " boxes. " + view.title;
  }
  function layoutErrors() {
    const errors = [];
    const frame = diagram.getBoundingClientRect();
    const cards = [...diagram.querySelectorAll(".map-card")].map(el => ({el,rect:el.getBoundingClientRect()}));
    if (document.documentElement.scrollWidth > innerWidth + 1) errors.push("Page overflows horizontally.");
    for (const {el,rect} of cards) {
      if (rect.left < frame.left - 1 || rect.right > frame.right + 1 || rect.bottom > frame.bottom + 1) errors.push("Card outside diagram: " + el.dataset.card);
      if (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1) errors.push("Clipped card: " + el.dataset.card);
    }
    for (let a = 0; a < cards.length; a++) for (let b = a + 1; b < cards.length; b++) {
      const x = Math.min(cards[a].rect.right,cards[b].rect.right)-Math.max(cards[a].rect.left,cards[b].rect.left);
      const y = Math.min(cards[a].rect.bottom,cards[b].rect.bottom)-Math.max(cards[a].rect.top,cards[b].rect.top);
      if (x > 1 && y > 1) errors.push("Overlapping cards: " + cards[a].el.dataset.card + "/" + cards[b].el.dataset.card);
    }
    return errors;
  }
  buttons.forEach(button => button.addEventListener("click",() => {
    history.replaceState(null,"","#" + button.dataset.view); render(button.dataset.view);
  }));
  document.getElementById("close-detail").addEventListener("click",() => closeDetails(true));
  document.addEventListener("keydown",event => {if(event.key === "Escape") closeDetails(true);});
  document.getElementById("appearance").addEventListener("change",event => {
    if (event.target.value === "system") delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = event.target.value;
  });
  window.addEventListener("hashchange",() => render(location.hash.slice(1)));
  let resizeToken;
  new ResizeObserver(() => {
    if (Math.abs(diagram.clientWidth-lastWidth)<2) return;
    clearTimeout(resizeToken); resizeToken=setTimeout(() => render(),80);
  }).observe(diagram);
  window.LoopArchitectureDiagram = {render,validateData,layoutErrors,data,getState:() => layoutState};
  render(location.hash.slice(1) || "overview");
})();
