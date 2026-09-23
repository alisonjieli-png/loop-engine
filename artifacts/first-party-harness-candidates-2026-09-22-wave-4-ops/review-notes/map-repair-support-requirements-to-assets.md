# Candidate review: map-repair-support-requirements-to-assets

Status: candidate only. No independent approval, native-use result or measured customer benefit.

- Source basis and rights: Original method prompted by O*NET® 31.0 task ID `8944`, occupation `13-1081.00` (Logisticians), in the [pinned database inventory](../../occupation-grid-research-2026-09-22/README.md). O*NET® database material is from the U.S. Department of Labor, Employment and Training Administration under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html); ZIP SHA-256 `55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd`. Method text is newly written; no agency endorsement or test.
- Applicability: repair support planner with an approved procedure, item revisions and controlled assets. It is not repair guidance. Model performance is unmeasured.
- Conceptual typed input: `RepairProcedure`, `ProductRevision`, `AssetInventory`, `QualificationEvidence`, `RepairWindow`.
- Conceptual typed output: `RepairReadinessMap` with requirement links and first blocking dependency.
- Effect class: read-only readiness analysis; no equipment operation, substitution, repair or purchase.
- Good case: Compatible parts are in stock, but the only required tester has expired calibration; readiness remains blocked until qualified test capability exists.
- Known-wrong case: Mark repair ready because the parts count is positive while ignoring required calibrated test equipment and acceptance steps.
- Nearest starter item: `supply_the_files_and_facts_an_assignment_needs.md` gathers inputs; this method maps versioned procedural prerequisites to qualified physical assets and time windows.
- Nearest earlier candidate: `bound-obsolete-stock-by-support-horizon` evaluates future spare-part usability; this method evaluates a particular approved repair's whole asset chain.
- Limits: The supplied procedure owns safety and substitution rules. The skill must not teach a model to perform hazardous work.
- Customer search phrasings: "Do we have every tool and test fixture needed for this repair?"; "Parts are stocked, but can the service team finish the approved procedure?"
