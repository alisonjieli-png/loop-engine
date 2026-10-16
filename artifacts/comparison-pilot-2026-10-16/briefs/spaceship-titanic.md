# AgentBriefs demonstration brief: Spaceship Titanic baseline

Kind: demonstration brief for the AgentBriefs proposal, written by engineering
on October 16, 2026 from dated public sources and this pilot's own records. It
is not output of a qualified AgentBriefs service. Every benefit below is a
hypothesis to test. No experiment has run, so this brief reports no realized
benefit. The machine-readable form is
[spaceship-titanic.json](spaceship-titanic.json).

## Project as observed

The project is pilot task c: a model for the Kaggle Getting Started
competition [Spaceship Titanic](https://www.kaggle.com/competitions/spaceship-titanic).
It trains on 6,970 passengers and is scored on 1,723 passengers from held-out
travel groups. The environment pins Python 3.14.4, pandas 3.0.6, numpy 2.5.4
and scikit-learn 1.9.1, with no network for package installation.

- All four pilot runs of this task, two in each arm, wrote
  `RandomForestClassifier(n_estimators=100, random_state=42)` on
  label-encoded columns. They scored 0.8120, 0.7992, 0.8108 and 0.7847 on the
  held-out groups; three met the 0.790 acceptance floor
  ([pilot report](../../../docs/verification/COMPARISON-PILOT-2026-10-16.md)).
  The frozen gradient boosting reference scored 0.8131, plain logistic
  regression 0.7841 and the CryoSleep rule 0.7226.
- Each run also reported its own accuracy on a random 20 percent split of the
  visible rows: 0.8106, 0.8056, 0.8121 and 0.7991. Those figures were between
  0.0014 below and 0.0144 above the held-out results.
- The most-voted public notebook for the competition uses TensorFlow Decision
  Forests (gusthema/spaceship-titanic-with-tfdf, 8,050 votes on October 16,
  2026, read through the Kaggle notebook listing).

## Opportunities worth one bounded experiment

### ST-1. A tabular in-context model against the boosting reference

- **Evidence.** [TabICL](https://pypi.org/project/tabicl/) 2.2.0 was uploaded
  on September 2, 2026 under the BSD-3-Clause licence, and its classifier
  weights on the Hugging Face Hub (jingang/TabICL-clf) carry the same
  licence. [TabPFN](https://pypi.org/project/tabpfn/) 9.2.0 was uploaded on
  October 12, 2026. Its package is Apache-2.0, but its weights use their own
  licences: `priorlabs-1-1` for TabPFN-v2-clf, and a gated
  `tabpfn-2.5-license-v1.1` for TabPFN 2.5. Baltor's
  [model directory](https://baltor.ai/models) listed none of these models: no
  row of its 2,146 matched a tabular search on October 16.
- **Estimated benefit, a hypothesis.** An in-context tabular model could add
  0.5 to 1.5 accuracy points over 0.8131 on this split, without feature
  engineering. The cost is a package and weights download and more CPU time.
- **Experiment.** Install TabICL in a copy of the environment and fit it on
  the visible rows with the reference preprocessing. Predict the 1,723
  held-out passengers and compare with the reference by McNemar's test.
  Accept if p is below 0.05 in favour of TabICL and CPU training plus
  prediction takes under 10 minutes. Try TabPFN only after the owner reviews
  its weight licences, because using TabPFN 2.5 requires accepting gated
  terms.

### ST-2. Boosting libraries with native categorical handling

- **Evidence.** [CatBoost](https://pypi.org/project/catboost/) 1.2.10
  (February 18, 2026), [LightGBM](https://pypi.org/project/lightgbm/) 4.7.0
  (July 18, 2026) and [XGBoost](https://pypi.org/project/xgboost/) 3.4.1
  (August 15, 2026) are current. The most-voted public notebook's title
  names TensorFlow Decision Forests. Every pilot run label-encoded the
  categories and used a random forest.
- **Estimated benefit, a hypothesis.** Native categorical splits and group
  features, such as travel-group size, may add 0.3 to 1.0 points over the
  pilot runs and reach or pass the 0.8131 reference.
- **Experiment.** Same split and McNemar comparison as ST-1, one library at a
  time with default parameters, then one bounded search of at most 30
  settings validated by travel group. Report each library's result,
  including any that lose.

### ST-3. Validate by travel group and use Baltor's split checks

- **Evidence.** The held-out split keeps whole travel groups apart. A
  post-hoc search of Baltor with the pilot's customer key returned two
  Verified skills, `audit_data_splits_for_errors_and_leakage` and
  `read_the_train_validation_gap`. No Baltor-arm run searched Baltor, so
  neither was used.
- **Estimated benefit, a hypothesis.** Grouped validation estimates the
  held-out accuracy at least as well as a random row split, and so picks
  models more reliably. Three of the four runs' own estimates were already
  within 0.7 points, so the gain may be small for this model; the fourth was
  1.4 points high.
- **Experiment.** For the reference model and one run's model, compare
  five-fold random-row validation, five-fold grouped validation and the
  frozen holdout over five seeds. Accept grouped validation as the default if
  its absolute error against the holdout is lower in at least four of five
  seeds.

## Considered and not recommended

- **Withheld: fine-tune a hosted language model on the training rows.** The
  competition rules, section 7.B, forbid making the data available to anyone
  not in the competition. A hosted fine-tuning service would hold a copy. No
  source read for this brief shows such a model beating tree ensembles on a
  7,000-row tabular task. The brief raises no alert for it.
- **Not current: AutoGluon.** autogluon.tabular 1.6.3 (September 18, 2026)
  declares `requires-python <3.14,>=3.10`, so it cannot be installed in this
  project's Python 3.14 environment.
- **Advisories: none listed.** [OSV](https://osv.dev) returned no advisory
  for scikit-learn 1.9.1, pandas 3.0.6 or numpy 2.5.4 on October 16, 2026. An
  empty answer is not a security certificate, so the brief raises nothing.
- **Tooling, not an experiment yet.** Baltor's MCP directory lists two Kaggle
  servers: io.github.Seif-Sameh/Kaggle-mcp (MIT, updated June 11, 2026) and a
  safety-first server that gates submissions (io.github.parkseokjune/kaggle-mcp,
  updated June 16, 2026). Either would need a credential review before an
  agent may hold a Kaggle token. This pilot read competition metadata with the
  Kaggle command line instead.

## Sources read on October 16, 2026

| Source | What it supplied |
| --- | --- |
| Kaggle command line: competition list, rules page, notebook list | Rules, file list, most-voted notebooks |
| PyPI JSON for tabicl, tabpfn, catboost, lightgbm, xgboost, autogluon.tabular | Versions, upload dates, licences, Python limits |
| Hugging Face Hub model metadata | Weight licences for TabPFN and TabICL |
| OSV queries for scikit-learn, pandas and numpy | No advisory listed |
| Baltor model directory search index | No tabular model rows |
| Baltor MCP directory data | Kaggle servers |
| Baltor search, after the trials | Split and validation skills |
| This pilot's trial records | Methods and accuracies of the runs |
