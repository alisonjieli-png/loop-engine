# Facet tag precision, September 26, 2026

This record measures the `facet_rules` engine behind the
`library_facet_tagging` slot (roadmap S-6.209). The engine tags each library
item with the job titles, industries, experience levels, natural languages and
geographies its own words name. Four hand checks of 100 tags each were made on
the same day. After each of the first three, the rules changed where the
sample showed a clear pattern, and each change has a known-wrong check in
`src/loop_engine/core/library_ingestion/facet_tag_checks.py` with a `removed_`
control that fails when the change is taken back. No served release carries
facet tags yet, so the rules were run directly on candidate and reviewed
material.

## How it was measured

- Unit: one tag, that is one item, one facet and one value. The first check
  drew evidence rows instead (a tag with two phrases could be drawn twice).
  The `english` default of the language facet is never drawn, because nearly
  every item carries it.
- Verdicts: correct, wrong or arguable. Strict precision counts only correct
  tags; lenient precision counts arguable tags too. The first check used
  right and wrong only.
- Judge: the engineering session that built the tagger, reading each item's
  title, purpose, the head of its entry text and the evidence phrase. This is
  one judge, not the owner and not an independent reviewer.
- Seeds: `random.Random(20260926)` for the first three samples and
  `random.Random(20260927)` for the fourth, which also leaves out every tag
  the third check judged.
- Populations: the first two checks used the 6,877 candidate items of the
  10,000-idea batch (a scratch copy of the candidate snapshot, outside the
  repository). The last two used the 1,586 approved items of
  `/home/username/baltor-library/reviewed-2026-09-26-10/imported`, the same
  population as the step function measurement, with the material built as
  `tools/write_reviewed_catalogue.py` builds it. Package files were read in
  place and never copied into this repository; the records keep at most ten
  words of any title or purpose.

## Results

| Check | Rules | Population | Tags judged | Correct | Wrong | Arguable | Strict | Lenient |
|---|---|---|---|---|---|---|---|---|
| First | before any repair | candidates | 100 evidence rows | 47 | 53 | not used | 0.47 | 0.47 |
| Second | after the first repair | candidates | 100 | 56 | 24 | 20 | 0.56 | 0.76 |
| Third | after the second repair | reviewed | 100 | 47 | 31 | 22 | 0.47 | 0.69 |
| Fourth | final rules | reviewed | 100 | 66 | 19 | 15 | 0.66 | 0.81 |

The fourth check is the number for the rules in this change: 66 of 100 tags
correct and 81 of 100 correct or arguable, on tags that no earlier check had
judged.

The third check scored lower than the second on a different population: the
reviewed imported packages have long bodies, and one word said twice in a
body was enough to tag a value under the rules of that time.

## First check and first repair

Before any repair, the rules tagged 137 of the 6,877 candidates with a job
title, 1,936 with an industry, 209 with a level and 20 with a geography.
"auditor" was behind 119 of the 137 job title tags and "expert" behind 126
of 131 senior tags. In the hand check, 47 of 100 evidence rows were right.
Most wrong industry tags came from words with a software meaning: claim,
dashboard, engagement, environment, resume, lesson, interview, flight,
inventory, dispatch and escalation.

The first repair removed those words and kept only their longer forms, such
as insurance claim and job interview. It also took compliance out of the
industries and expert, principal, supervisor and director out of the
levels, keeping longer forms such as legal compliance, principal engineer
and managing director. Checks:
`words_with_a_software_meaning_name_no_industry_title_or_level` and
`removed_software_word_exclusion_tags_a_security_auditor_as_an_accountant`.

## Second check and second repair

After the first repair, 20 candidates had a job title, 1,449 an industry, 82
a level and 20 a geography, and 64 language tags named a language other than
English. The sample of 100 tags from the 2,018 tags that are not the English
default held 56 correct, 24 wrong and 20 arguable.

The wrong tags pointed at bare words with a common software or figurative
sense: `analytics` (four wrong, none correct), `media` (three wrong),
`animation` (two wrong, one arguable), and one wrong tag each from
`streaming`, `agency`, `regulations`, `nuclear`, `ecosystems`, `plumbing`,
`construction` and `factory`. `project manager` gave one wrong and one
arguable `lead` tag; a project manager is a job title, not a level.

The second repair removed those words and kept their industry forms (data
analytics, media company, streaming service, animation studio, government
agency, nuclear power, construction site, factory floor), and took project
and product managers and scrum masters out of the levels. Checks:
`words_with_a_software_or_figurative_sense_name_no_industry_or_level` and
`removed_second_software_word_exclusion_tags_a_render_step_as_analytics_manufacturing_and_media`.

Re-tagged under the second repair, the same 100 tags kept 77. The repair
removed 18 wrong and 5 arguable tags and no correct one, so the kept tags
were 0.73 strict and 0.92 lenient. The final rules keep 76 of them (0.74
strict, 0.92 lenient).

## Third check and the final repair

On the reviewed folder, the rules after the second repair tagged 13 of the
1,586 approved items with a job title, 605 with an industry, 61 with a level
and 7 with a geography, and 68 language tags named a language other than
English (chinese 45, russian 13, korean 5, japanese 3, spanish 1, portuguese
1). The sample held 47 correct, 31 wrong and 22 arguable tags.

Two patterns stood out.

1. Body words alone. 49 of the 100 tags came from the body only, with no
   word in the name or purpose. They were correct 14 times, wrong 19 times
   and arguable 16 times (0.29 strict). Most wrong ones were one word said
   twice in a long body: `vehicle` in a planning framework, `invoice` in a
   letter-writing voice, `doctor` as a command name, `physics` in a video
   model. Tags with a word in the name or purpose were correct 30 of 48
   times (0.62 strict). The final rules tag a value from the body alone only
   when the body names it by two distinct phrases, a singular and its
   plural counting once. 11 of the 14 correct body-only tags met that bar.
   Checks: `a_value_named_by_the_body_alone_needs_two_distinct_phrases` and
   `removed_body_phrase_minimum_tags_one_word_said_twice_in_the_body`. The
   earlier score threshold (one mention in the name or purpose or two in the
   body) is replaced by this rule, which it would only repeat.
2. Tooling words. `scaffolding`, `utility`, `utilities`, `advisory`,
   `doctor` and `dataset` each drove at least two wrong tags and at most one
   correct tag: code scaffolding, test utilities, security advisories and a
   doctor command. `recipes` and `battery` each drove one wrong tag in their
   usual software sense (build recipes, phone battery) and were removed on
   that judgement. The vocabulary keeps electric utility, utility company,
   advisory firm, doctors, energy storage and cooking recipe. Checks:
   `tooling_words_name_no_industry_but_their_industry_forms_do` and
   `removed_third_word_exclusion_tags_a_scaffolding_step_as_construction_and_healthcare`.

Re-tagged under the final rules, the same 100 tags kept 61. The rules
removed 23 wrong, 13 arguable and 3 correct tags (two trading tags and one
dataset tag, each named by one word in a body), so the kept tags were 0.72
strict and 0.87 lenient.

## Fourth check: the final rules

Under the final rules, 5 of the 1,586 approved items carry a job title, 413
(26 percent) an industry, 35 a level and 2 a geography; the language tags
do not change. The rules tag far fewer items than before, which is the
price of the higher precision.

The fourth sample drew 100 tags with seed 20260927 from the 593 tags that
are not the English default and that the third check had not judged. It
held 66 correct, 19 wrong and 15 arguable tags (0.66 strict, 0.81 lenient).

| Facet | Tags | Correct | Wrong | Arguable | Strict | Lenient |
|---|---|---|---|---|---|---|
| industries | 78 | 48 | 19 | 11 | 0.62 | 0.76 |
| languages | 14 | 14 | 0 | 0 | 1.00 | 1.00 |
| levels | 5 | 2 | 0 | 3 | 0.40 | 1.00 |
| job titles | 2 | 1 | 0 | 1 | 0.50 | 1.00 |
| geographies | 1 | 1 | 0 | 0 | 1.00 | 1.00 |

By evidence source, the 27 body-only tags were 0.56 strict and 0.85
lenient, and the 59 tags with a word in the name or purpose were 0.63 strict
and 0.75 lenient. Most remaining wrong tags now come from one word in a
purpose: `brand` alone (four wrong: reverse image search, subdomain
enumeration, image outpainting and leak hunting), `supply chain` in its
software sense (two wrong), and one wrong tag each from `shipping`,
`startup`, `listings`, `car` (the CAR file format), `grading`, `insurance`,
`onboarding`, `campaigns` and `seo`, plus `news` and `publishing` in an
advertising agent and `bank`, `investment` and `payment` in a skill about
forming a company. These are the candidates for the next repair. They are
not changed here, so the fourth check stays a measurement on tags that no
repair was fitted to.

## Limits

- One judge, the session that wrote the rules, judged every sample and chose
  the repairs. The second and third samples were then re-tagged under the
  later rules, which measures the repair on the data that suggested it and
  flatters it. The fourth check, on tags no earlier check judged, is the
  fairer number. A second, independent judge on the same samples is not done.
- Removing a word can let another value into a facet's bound of four
  industries, six job titles, three levels or six geographies. Such a tag
  is new, and only the fourth check can have drawn it.
- The vocabulary is English. Items in Chinese, Russian, Korean, Japanese,
  Spanish and Portuguese get a language tag and seldom any other facet.
  A Vietnamese text written without its diacritics is called English.
- Only the samples were judged; the distributions count rule output, not
  correctness.

## Browser check of the signed-in table

A real browser (Chromium through Playwright) loaded the browse section of
`index.html` with the page's own stylesheets and the exact
`catalogue-browser.js` of this change. Only the service was a stub: it
answered the list and the item requests from five fixture rows, one with
every facet, one with two industries, one in Spanish, one with only the
language, and one with no attributes at all. 13 of 13 checks passed:

- before loading, the five facet selects are disabled and offer only their
  empty choice; after loading, each offers exactly the values the rows carry,
  sorted;
- the industry `legal` keeps the two rows that carry it; adding the job
  title `Lawyers` keeps one row and the count reads "1 of 5 items";
  clearing both shows all five; the language `spanish` keeps the Spanish
  row; typing `healthcare` in the search box finds the row tagged with it;
- the detail of the tagged row lists each facet's values, and the detail of
  the row without attributes says "Not tagged" for all five; the report
  control of the feedback work still shows beside them;
- the section fits widths of 1440, 820, 390 and 320 pixels at normal and
  doubled text size without sideways scrolling, and the page raised no
  error;
- the control run loads the module with the facet rule replaced by `true`,
  and choosing `legal` then shows all five rows, so the comparison fails.

The screenshots at 1440 and 390 pixels were reviewed by eye and are not
kept here, because the repository ignores images under `artifacts/`. At
1440 pixels the filters wrap into three rows; at 390 pixels they stack. The
narrow Label column of the table wraps its badge text over several lines at
both widths; the table's columns and styles are not changed by this work.

## Files

- `README.md`: this record.
- `browser-check-2026-09-26.mjs` and `browser-check-2026-09-26.json`: the
  browser check as it was run (with the shared checkout's Playwright and the
  local Chromium) and its report.
- `distribution-before-2026-09-26.json`,
  `distribution-after-first-repair-2026-09-26.json`,
  `distribution-after-second-repair-2026-09-26.json` and
  `distribution-final-2026-09-26.json`: items with a value per facet, the
  top values and the top evidence phrases for each set of rules.
- `hand-check-before-2026-09-26.json`,
  `hand-check-after-first-repair-2026-09-26.json`,
  `hand-check-after-second-repair-2026-09-26.json` and
  `hand-check-final-2026-09-26.json`: each sampled tag with its evidence,
  its verdict and, for the second and third checks, whether the later rules
  keep it.

## Current and planned behaviour

Current: `tools/write_reviewed_catalogue.py` writes these tags for every
approved item of the next reviewed folder, and the signed-in library table
and search results show them. No served release carries them yet, so
nothing live changed with this record, and the browser check above used
fixture rows, not a served catalogue.

Planned, not done here: a second judge on the same samples; a text model
engine behind the same facet edge, which the slot declaration allows; a
vocabulary for items in other languages; and a measurement on served lines
after the first release that carries the tags.
