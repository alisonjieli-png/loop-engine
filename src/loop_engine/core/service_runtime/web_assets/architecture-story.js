/* Public architecture illustration. This data grants no runtime authority. */
"use strict";
(() => {
  const get = id => document.getElementById(id);
  const vocabulary = get("runtime-vocabulary-template");
  document.querySelectorAll("[data-runtime-vocabulary]").forEach(target => target.append(vocabulary.content.cloneNode(true)));
  const deployment = get("deployment-boundary-template");
  document.querySelectorAll("[data-deployment-boundary]").forEach(target => target.append(deployment.content.cloneNode(true)));
  const layer = {
    context:"Expert guidance", code:"Reusable code",
    history:"Previous findings", feedback:"Your preferences",
    assignment:"Step instructions", input:"Task files"
  };
  const assignments = {
    inspect: {
      title:"Understand the inputs before changing anything.", kind:"Understand",
      objective:"Read a sample, identify the columns and flag missing or unclear values. Keep the original file unchanged.",
      engine:"A research session", delivery:"A short brief, the selected sample and read-only tools.",
      materials:[
        ["task.json","assignment","What to inspect, what to report and what must stay unchanged."],
        ["field-definitions.md","context","Definitions for the columns in this file."],
        ["customer-sample.csv","input","Only the sample you have allowed this step to read."],
        ["previous-import-findings.json","history","Relevant past mistakes, such as losing leading zeroes in customer numbers."]
      ],
      tools:"Read the selected files and check their contents. This step cannot change the input or browse unrelated files.",
      withheld:["The rest of the customer archive","Permission to change the original file","Billing and model-provider keys"],
      output:"A report of the columns, unclear values and questions that affect the import.",
      condition:"Keep checking while an important question remains and the time limit allows it.",
      exit:"Return the report, including anything that could not be established.",
      budget:"Example limit: five minutes and up to three approved model requests. No changes to external services."
    },
    decide: {
      title:"Choose an approach that fits the data.", kind:"Choose",
      objective:"Compare the available import methods with the report and your requirements. Ask for missing information when it affects the choice.",
      engine:"A focused decision request", delivery:"A small comparison may need one model request rather than a full development session.",
      materials:[
        ["schema-report.json","input","The first step's findings, including unanswered questions."],
        ["eligible-capabilities.json","code","Descriptions of reusable tools and the inputs they can handle."],
        ["keep-uncertain-matches.json","feedback","Your instruction to keep unclear matches for review."],
        ["comparison-results.json","history","Relevant results from previous attempts."]
      ],
      tools:"Compare the options using a model you have configured or another approved method. This step does not install or host a model.",
      withheld:["Customer rows that do not affect the choice","The full code of every search result","The research session's entire conversation"],
      output:"A suggested approach, its reasons and any questions to resolve before building.",
      condition:"Ask for more information if the available evidence does not support a choice.",
      exit:"Return a supported choice or explain what prevents one.",
      budget:"Example limit: two minutes and up to two approved model requests. No file or payment changes."
    },
    build: {
      title:"Reuse what fits. Build what is missing.", kind:"Build",
      objective:"Prepare the import in a new output file. Keep unclear rows for review and leave the original untouched.",
      engine:"A focused development session", delivery:"Its own instructions, selected code, permitted inputs and a place for new files.",
      materials:[
        ["AGENTS.md","assignment","Instructions for this step, without the entire planning conversation."],
        ["selected-normalizer.py","code","The reviewed version of a reusable data-cleaning function."],
        ["import-output-contract.json","context","The required columns and checks for the finished import."],
        ["preserve-original-input.json","feedback","Your rule against changing the original file."],
        ["authorized-input.csv","input","The input you have allowed this step to use."]
      ],
      tools:"Read the chosen inputs, write new files and run approved tests in an isolated workspace.",
      withheld:["Permission to change the original input","Unrelated tools and instructions","The reviewer's private test cases"],
      output:"The proposed import, any new code and a record of the changes. A separate review still needs to check them.",
      condition:"Repair failed checks while safe work remains within the agreed limits.",
      exit:"Send the proposed result and its test results for separate review.",
      budget:"Example limit: fifteen minutes, five approved model requests and writes only to the output folder."
    },
    verify: {
      title:"Check the result against your requirements.", kind:"Check",
      objective:"Use separate tests to find mistakes. Check that customer numbers, unclear rows and the original file are preserved.",
      engine:"A separate review", delivery:"The proposed result and review tests, without permission to rewrite the work being checked.",
      materials:[
        ["candidate-import.json","input","The exact proposed import to review."],
        ["acceptance-contract.md","context","What a correct result must include and what it must not change."],
        ["import-verifier.py","code","Tests that can detect known mistakes."],
        ["expected-results.json","input","Expected answers kept separate from the building step."]
      ],
      tools:"Read the result and run the review tests. This example uses existing checks, so it needs no model request.",
      withheld:["Permission to change the candidate","The builder's own success claim as proof","Permission to approve its own tests for wider reuse"],
      output:"A pass, a list of problems to repair, or an explanation of what could not be checked.",
      condition:"Complete each required check within the agreed limits.",
      exit:"Return the findings. Unfinished checks do not count as a pass.",
      budget:"Example limit: five minutes, no model requests and no changes to the proposed result."
    }
  };
  const tabs = [...document.querySelectorAll("[data-assignment]")];
  const text = (tag, value, className) => { const item = document.createElement(tag); item.textContent = value; if (className) item.className = className; return item; };
  function select(id, announce = true) {
    const value = assignments[id];
    if (!value) return;
    for (const tab of tabs) { const active = tab.dataset.assignment === id; tab.setAttribute("aria-selected", String(active)); tab.tabIndex = active ? 0 : -1; }
    get("assignment-panel").setAttribute("aria-labelledby", "assignment-" + id);
    for (const [target, property] of [["assignment-kind","kind"],["assignment-title","title"],["assignment-objective","objective"],["assignment-engine","engine"],["assignment-runtime","delivery"],["assignment-tools","tools"],["assignment-output","output"]]) get(target).textContent = value[property];
    get("assignment-materials").replaceChildren();
    for (const [file, source, reason] of value.materials) { const row = text("li", ""); row.append(text("span", layer[source], "material-source"), text("strong", file), text("p", reason)); get("assignment-materials").append(row); }
    get("assignment-withheld").replaceChildren(...value.withheld.map(item => text("li", item)));
    get("assignment-contract").replaceChildren();
    for (const [name, item] of [["Continue when",value.condition],["Finish when",value.exit],["Example limits",value.budget]]) get("assignment-contract").append(text("dt", name), text("dd", item));
    if (announce) get("assignment-announcement").textContent = value.title;
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => select(tab.dataset.assignment));
    tab.addEventListener("keydown", event => {
      let next;
      if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
      else if (event.key === "ArrowLeft") next = (index + tabs.length - 1) % tabs.length;
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = tabs.length - 1;
      else return;
      event.preventDefault(); tabs[next].focus(); select(tabs[next].dataset.assignment);
    });
  });
  select("inspect", false);
})();
