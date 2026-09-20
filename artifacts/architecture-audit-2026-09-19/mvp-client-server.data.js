/* Project-owned, illustrative architecture. No credentials or live records. */
window.LOOP_ARCHITECTURE = {
  version:"2026-09-19", library:{name:"ELK.js",version:"0.12.0"},
  facts:{
    deployment:"proposed",remoteHttpImplemented:false,remoteOauthImplemented:false,
    localProtocol:"2025-11-25",runHistoryOwner:"Loop Engine",
    currentRetrieval:{lexical:"SQLite FTS5",vector:"hash vectors",optional:["model2vec","LanceDB"]},
    proposedStorage:{metadata:"Supabase Postgres + pgvector",bodies:"Supabase private bucket"},
    providers:{Vercel:"proposed",Supabase:"proposed",Stripe:"proposed"}
  },
  views:{
    overview:{
      eyebrow:"01 / Overview",title:"Three boundaries. Different responsibilities.",
      description:"The customer runs the task. Loop Engine supplies permitted intelligence. External services support the proposed hosted product.",
      caption:"Boxes show software boundaries, not executable Loop vertices. Hosted connections are proposed. Optional model calls go directly from the customer's harness to a separately authorized provider.",
      nodes:[
        {id:"customer",zone:"customer",owner:"Customer-controlled",title:"Your environment",copy:"Your task, files and execution authority.",status:"customer",state:"Stays with the customer",
         items:[{name:"Browser",detail:"Account setup and catalogue browsing",status:"proposed"},{name:"Installed harness",detail:"Runs work using your permissions",status:"customer"}],
         detail:"An ordinary Model Context Protocol client can retrieve material for an installed harness. Full Loop Engine graph governance is a separate local runtime path.",
         limit:"Connecting does not upload your full task folder, prompts, credentials or Run History."},
        {id:"engine",zone:"engine",owner:"Loop Engine",title:"The intelligence service",copy:"Reviewed material, exact access rules.",status:"mixed",state:"Local domain; hosting proposed",
         items:[{name:"Website + dashboard",detail:"Vercel is a proposed host",status:"proposed"},{name:"Python serving domain",detail:"Tenant grants, disclosure and integrity",status:"existing"}],
         detail:"The local Python domain separates authentication, disclosure, qualification, body integrity and metering acknowledgment. The website and remote transport still need integration.",
         limit:"Remote provisioning HTTP and OAuth are not implemented. A trusted host callback does not prove independent qualification across every intelligence layer."},
        {id:"providers",zone:"vendor",owner:"External services",title:"Managed services",copy:"Outside the Loop Engine runtime.",status:"proposed",state:"Vendor choices are proposals",
         items:[{name:"Supabase",detail:"Identity, metadata and private storage",status:"proposed"},{name:"Stripe",detail:"Hosted checkout and subscription events",status:"proposed"},{name:"Remote models",detail:"Customer-selected and authorized",status:"external"}],
         detail:"Supabase and Stripe are proposed integrations. Remote model providers remain external services, reached by the customer's execution environment when separately authorized.",
         limit:"A subscription does not grant model-call authority, permission to execute code, or implicit access to customer files."}
      ],
      edges:[{id:"o1",from:"customer",to:"engine",label:"Find + retrieve"},{id:"o2",from:"engine",to:"providers",label:"Account + data"},{id:"o3",from:"customer",to:"providers",label:"Optional model calls",optional:true,mobileTextOnly:true}],
      notes:[{title:"What the service supplies",text:"Context Intelligence, Code Intelligence, Runtime History and Solution Intelligence, and User Feedback Intelligence. Harness Intelligence is a provisioning view over those layers."},{title:"What remains local",text:"Harness execution and task files. With the Loop Engine runtime installed, the customer also gets governed task graphs, independent acceptance and Loop Engine Run History."}]
    },
    "sign-in":{
      eyebrow:"02 / Sign-in & access",title:"A payment return page does not grant access.",
      description:"The planned flow separates sign-in, checkout and durable entitlement. Loop Engine must verify the payment event before changing access.",
      caption:"This is a proposed workflow, not a network trace. Arrows show the next step; select a box to see the responsible service.",
      nodes:[
        {id:"sign",zone:"customer",owner:"Customer",title:"Sign in",copy:"Open the website and authenticate.",status:"proposed",state:"Supabase Auth proposal",detail:"The browser opens the proposed website. Supabase Auth is the proposed identity provider. A dashboard session and scoped client authorization are separate flows.",limit:"Hosted login and Model Context Protocol OAuth are not integrated."},
        {id:"checkout",zone:"vendor",owner:"External / Stripe",title:"Complete checkout",copy:"Pay through the proposed hosted checkout.",status:"proposed",state:"Stripe proposal",detail:"After the customer chooses an approved plan, the application creates a checkout session for that identity. The payment provider handles payment entry.",limit:"No payment details belong in a harness configuration or client URL."},
        {id:"event",zone:"engine",owner:"Loop Engine",title:"Verify the event",copy:"Check signature, identity and event order.",status:"proposed",state:"Billing work required",detail:"The application must verify signed subscription events and handle duplicates, delayed events, failed payment, cancellation and reactivation.",limit:"Returning from checkout is not evidence that subscription access is active."},
        {id:"rights",zone:"vendor",owner:"External / Supabase",title:"Save current access",copy:"Store one durable entitlement state.",status:"proposed",state:"Postgres proposal",detail:"Loop Engine would update its entitlement record in Supabase Postgres using idempotent writes. The domain owns the access rules; the hosted database stores them.",limit:"Durable billing reconciliation and recovery require implementation."},
        {id:"connect",zone:"customer",owner:"Customer",title:"Connect the client",copy:"Follow the supported setup flow.",status:"proposed",state:"Remote setup not built",detail:"The website and protocol service must read the same current entitlement. The customer then approves appropriately scoped client access.",limit:"Current tests cover local host-bound credentials, not an end-user remote OAuth flow."}
      ],
      edges:[{id:"s1",from:"sign",to:"checkout",label:"Choose plan"},{id:"s2",from:"checkout",to:"event",label:"Signed event"},{id:"s3",from:"event",to:"rights",label:"Verified update"},{id:"s4",from:"rights",to:"connect",label:"Current rights"}],
      notes:[{title:"One access record",text:"Dashboard and client access must agree. A delayed or duplicated payment event must not accidentally restore revoked access."},{title:"No live billing in this diagram",text:"Vercel, Supabase and Stripe are proposed. No account, checkout session, payment or subscription is created by this page."}]
    },
    retrieval:{
      eyebrow:"03 / Retrieve material",title:"Find references first. Fetch only what you select.",
      description:"Each request crosses an access check. Payment does not qualify a candidate, and a retrieved body is not permission to execute it.",
      caption:"Existing local domain behavior is separate from proposed hosted storage. Remote HTTP and OAuth remain open integration work.",
      nodes:[
        {id:"query",zone:"customer",owner:"Customer client",title:"Ask for references",copy:"Send the scope needed for this assignment.",status:"existing",state:"Local protocol tested",detail:"A plain Model Context Protocol client can discover operations, list permitted references and request an exact manifest.",limit:"The current profile is 2025-11-25 over local JSON-RPC streams."},
        {id:"permit",zone:"engine",owner:"Loop Engine",title:"Check disclosure",copy:"Check tenant, grant and exact qualification.",status:"existing",state:"Local domain",detail:"Unknown, unapproved and ungranted items are withheld before metadata disclosure, including discovery counts. Qualification binds exact identity and digest.",limit:"Authoritative qualification adapters across all four layers are not fully wired. Host attestation is labeled as such."},
        {id:"select",zone:"customer",owner:"Customer client",title:"Select exact material",copy:"Choose a reference, version and digest.",status:"existing",state:"Reference selection",detail:"The client inspects the manifest before requesting its body. Retrieval is separate from loading, use and independent verification.",limit:"Selecting a reference does not establish that a native harness loaded its instructions."},
        {id:"serve",zone:"engine",owner:"Loop Engine",title:"Verify and serve",copy:"Recheck access, bytes and required usage acknowledgment.",status:"existing",state:"Local domain",detail:"The domain rechecks authority, verifies body integrity and requires an exact committed acknowledgment when the grant requires metering.",limit:"The reference meter is volatile. A lost response does not prove that a charge failed; recovery keeps the same request identity."},
        {id:"check",zone:"customer",owner:"Customer client",title:"Check the manifest",copy:"Confirm exact material before local use.",status:"customer",state:"Client responsibility",detail:"The execution environment checks identity and manifest, then separately decides whether and how it may use the material.",limit:"Full authenticated typed template, graph and package delivery is not complete."}
      ],
      edges:[{id:"r1",from:"query",to:"permit",label:"Scoped query"},{id:"r2",from:"permit",to:"select",label:"Metadata only"},{id:"r3",from:"select",to:"serve",label:"Exact request"},{id:"r4",from:"serve",to:"check",label:"Body + manifest"}],
      notes:[{tag:"Proposed hosted storage",title:"Metadata and access in Postgres",text:"Supabase Postgres would hold catalogue metadata, rights, qualification references and usage. pgvector is a proposed vector-search option, not the current default."},{tag:"Proposed hosted storage",title:"Body bytes in a private bucket",text:"Supabase Storage would hold selected artifact bodies. The Python service must check access before releasing bytes; a bucket path is not a disclosure grant."},{tag:"Current implementation",title:"Local search today",text:"SQLite FTS5 is the default lexical backend. Hash vectors are the default vector backend. model2vec and LanceDB are optional adapters."},{title:"Keep material states distinct",text:"Offered, fetched, loaded, used and independently verified are different observations. Retrieval and payment never promote a candidate."}]
    },
    execution:{
      eyebrow:"04 / Run locally",title:"Graph governance needs the local Loop Engine runtime.",
      description:"A plain Model Context Protocol client retrieves material. The full local runtime owns decomposition, scoped assignments, verification and Run History.",
      caption:"Every executable graph vertex is a Loop. These boxes summarize workflow steps and an external service, not additional runtime types. Model calls remain separately authorized.",
      nodes:[
        {id:"decompose",zone:"customer",owner:"Local Loop Engine",title:"Build the task graph",copy:"Graphs, subgraphs and atomic assignments.",status:"existing",state:"Local runtime",detail:"A Starting Practitioner decomposes work into governed assignments. Relationships, typed contracts, conditions, budgets and permissions stay explicit.",limit:"A displayed task graph is not proof that every path executed or passed independent verification."},
        {id:"prepare",zone:"customer",owner:"Local Loop Engine",title:"Prepare each assignment",copy:"Bind scope, resources and exact settings.",status:"existing",state:"Local runtime",detail:"The runtime binds an assignment to its chosen configuration and permitted references. It initializes the declared harness path in a scoped environment.",limit:"Materializing an instruction file is not observed native loading. Native profiles require their own checks."},
        {id:"run",zone:"customer",owner:"Customer harness",title:"Run the work",copy:"Use an installed harness within its authority.",status:"existing",state:"Local execution",detail:"The customer controls execution. File, network, model and spending permissions remain separate from intelligence subscription access.",limit:"The first-release hosted intelligence product is not a hosted task-execution service."},
        {id:"verify",zone:"customer",owner:"Local Loop Engine",title:"Verify the result",copy:"Accept, continue or repair from evidence.",status:"existing",state:"Local runtime",detail:"The owning Loop separates harness completion from independent task acceptance. Failed or unverified results stay visible and can trigger authorized continuation.",limit:"Local contract checks do not establish general model quality or qualification of every native harness."},
        {id:"history",zone:"customer",owner:"Local Loop Engine",title:"Record Run History",copy:"Keep exact outcomes and accounting.",status:"existing",state:"Owned by Loop Engine",detail:"Loop Engine owns Run History: output identity, observed attempts, unknown usage and verification. Runtime Memory is temporary and run-scoped.",limit:"Run History is not automatically uploaded or owned by a model provider."},
        {id:"model",zone:"vendor",owner:"External provider",title:"Optional remote model",copy:"A separate authorized service call.",status:"external",state:"Customer-selected",detail:"An installed harness may call a remote model under a separately authorized route. Harness execution and Run History do not move to the model vendor.",limit:"The intelligence subscription does not grant a model allowance."}
      ],
      edges:[{id:"l1",from:"decompose",to:"prepare",label:"Scoped work"},{id:"l2",from:"prepare",to:"run",label:"Bound assignment"},{id:"l3",from:"run",to:"verify",label:"Observed output"},{id:"l4",from:"verify",to:"history",label:"Exact outcome"},{id:"l5",from:"run",to:"model",label:"Optional model call",optional:true,mobileTextOnly:true}],
      notes:[{title:"Plain Model Context Protocol client",text:"Retrieve permitted material and use it with your own harness. Connecting alone does not enforce Loop Engine graphs, continuation rules or independent acceptance."},{title:"Full local Loop Engine",text:"Use the canonical Loop runtime for decomposition, scoped execution and verification. Runtime Memory stays run-scoped. Run History belongs to Loop Engine on the execution side."}]
    }
  }
};
