# Candidate review: design a bounded product experiment

Status: candidate only. No independent approval, native-load test, or task
evaluation has occurred.

- Original source basis: first-party product experiment specification based
  on an explicit proposed change and ordinary measurement design. It does
  not import a third-party playbook or claim an experiment was run.
- Job, company, and project facets: product manager, growth analyst, or
  researcher; target company supplies consent, rollout, and risk rules;
  discovery or limited-rollout stage.
- Search phrasings: "Plan a test of this onboarding change before anyone is
  enrolled."; "How should we assign accounts and pause the experiment if
  errors rise?"
- Typed input/output concept: `ChangeProposal`, `EligiblePopulation`,
  `CurrentExperience`, `Baseline?`, and `Constraint[]` to `ExperimentSpec`
  containing assignment, exposure, primary outcome, denominator,
  minimum sample or precision target, guardrails, and stop rule.
- Effects: write a read-only specification. No enrollment, feature-flag
  change, message, telemetry deployment, or spending.
- Good fixture: forty eligible accounts can be assigned once per account;
  seven-day task completion is the primary outcome; a minimum analyzable
  sample is justified against the supplied decision threshold; an error-rate
  guardrail has a pause threshold; missing exposure events block launch.
- Known-wrong fixture: the specification assigns variants once per account,
  but the implementation reassigns on every page load, so one account sees
  both variants. Completion appears to rise while errors exceed the declared
  guardrail pause threshold. Reporting a winner from those data fails both
  the assignment and guardrail rules, even if the primary metric improved.
- Overlap search: starter `freeze_the_success_metric_before_measuring`
  freezes a metric. This candidate specifies the full product intervention,
  assignment, exposure, guardrail, and launch prerequisites.
- Limits: this skill calls for a justified sample or precision rule but does
  not certify a power calculation, legal compliance, or privacy compliance.
  Those require supplied context and qualified review.
