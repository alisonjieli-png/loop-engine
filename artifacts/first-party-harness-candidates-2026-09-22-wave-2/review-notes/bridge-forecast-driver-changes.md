# Candidate review: bridge-forecast-driver-changes

Status: candidate only. No admission, licence, native-use result, or benefit claim is attached to these bytes.

- Original source basis: Written in original words for this batch from general forecast-reconciliation reasoning after inspecting the 123 starter bodies and first 24 packages. The [Agent Skills specification](https://agentskills.io/specification) informed layout only. No forecast model or protected source text was copied.
- Job, company archetype, and project facets: planning analyst or operations lead; a company forecasting demand or workload; monthly reforecast or scenario review.
- Model applicability: general text-capable harnesses; no accuracy or cost benefit has been measured.
- Conceptual typed input: `BaselineForecast`, `RevisedForecast`, `DriverVersions`, `AttributionRule`, `ForecastScope`.
- Conceptual typed output: `ForecastChangeBridge` with comparable definitions, named contributions, interactions, residual, and assumptions.
- Effect intent: read-only analysis of supplied forecasts. It does not authorize changing a planning system or making purchasing decisions.
- Positive fixture: A baseline of 100 units becomes 112 units for the same horizon and population. Under a supplied additive attribution, volume contributes plus 15 and attrition contributes minus three. The residual is zero.
- Known-wrong fixture: The revised forecast is 112 and documented driver changes add only eight, but the report calls all 12 units explained. The four-unit residual must remain visible.
- Nearest overlap: Starter `forecast_an_action_then_compare.md` calibrates a prediction about a planned action against its later outcome. First-batch `design-a-bounded-product-experiment` defines causal measurement before an intervention. This candidate explains the arithmetic movement between two versions of a business forecast and does not claim that its drivers are causal.
- Limitations: Nonlinear interactions and sequential replacement order can change attribution. A reviewer should test mismatched forecast horizons and a missing model version.
- Customer search phrasings: "What changed between last month's demand forecast and this one?"; "Which assumptions explain the increase, and how much is still unexplained?"
