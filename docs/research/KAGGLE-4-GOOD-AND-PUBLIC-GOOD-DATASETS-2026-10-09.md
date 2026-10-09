# Kaggle 4 Good and the public-good datasets of the owner's Kaggle download

October 9, 2026. The owner asked why so little of "Kaggle 4 Good hackathon"
material reaches the library as SDG files, components, skills and feeds. This
record says what that program is, what its data and licences allow, and what
the first run of the `kaggle_public_good` supply line made of the owner's
October 6, 2026 Kaggle download. Kaggle was read only through the existing
metadata intake: no competition was joined, no rule accepted, no notebook run
and nothing downloaded.

## What "Kaggle 4 Good" is

The owner's own DueCare datasets call it the "Kaggle / Gemma 4 Good
Hackathon". The intake observed it on October 8, 2026 and again in one
search read on October 9 (15 of the managed state's 20 reads are now used):

| Fact | Value |
|---|---|
| Competition | [The Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon), identifier 134561 |
| Category and size | Featured, 1,605 teams |
| Deadline | May 18, 2026, 23:59 UTC (closed) |
| Licence label the API reports | Subject to Competition Rules |
| Published pages | Description, Submission Requirements, rules, foundational rules, abstract, tracks and awards, Evaluation, Timeline, judges, and an 84-byte data description; the intake keeps names and passive links, not page text |

It is a hackathon judged on writeups, not a data competition, and its only
data label is the competition rules, which no allowlisted licence covers.
Nothing of the competition itself can be packaged. The ten most-voted public
notebooks recorded on October 8 carry no licence field in the API, so they
stay private leads.

What the hackathon produced that can be packaged is the owner's own entry,
DueCare. Its writeup was submitted under CC BY 4.0 (see
[OWNER-PUBLICATIONS-AND-REPOSITORY-SHOWCASE-2026-09-24.md](OWNER-PUBLICATIONS-AND-REPOSITORY-SHOWCASE-2026-09-24.md)),
and five DueCare datasets remain on Kaggle:

| Dataset | Licence in its own files | Line outcome |
|---|---|---|
| DueCare Harness Benchmark Grades | CC BY 4.0 (LICENSE) | packaged |
| DueCare Measured Response Training Corpus | CC BY 4.0 (LICENSE, Croissant, citation file agree) | packaged |
| DueCare Measured Response Review Curriculum 200K | CC BY 4.0 (LICENSE, Croissant, citation file agree) | packaged |
| DueCare Gemma 4 Adapter Learning Study | mixed terms: adapters Apache-2.0 with Gemma's use policy, everything else CC BY 4.0; the download holds no adapter, so a declared decision applies CC BY 4.0 | packaged |
| DueCare Multiperspective Fine-Tuning Corpus | CC BY-SA 4.0 | held, not on the allowlist |

The same search for "for good" listed 20 competitions. Every social-good
program among them is labelled "Subject to Competition Rules": Data Science
for Good: CareerVillage.org and City of Los Angeles (2019), Coleridge
Initiative - Show US the Data (2021), The Purdue Using Data Analytics &
Science for Good (2022) and AI for Social Good - ARIES IITD x Kaizen '24. One
community competition, DataC'EPT, reports CC BY 4.0 and another, Cup-ybara,
CC BY-NC 4.0. A reported label is a lead, not a verified grant, and the intake
has no operation that reads a competition's data files.

## The owner's download

The download holds 243 dataset folders of the owner's Kaggle account (14,896
files, 88.6 GB), most of them deleted from Kaggle the day they were
downloaded. The line profiled every file locally: 267 delimited text files
(67.8 GB), 172 JSON lines files (5.0 GB), 164 JSON documents, spreadsheets,
geospatial layers, models and 10,745 images, each with its SHA-256.

| Outcome | Datasets |
|---|---|
| packaged | 4 |
| licence unknown: the dataset's own files name no licence | 234 |
| licence off the allowlist (ODbL, CC BY-SA 4.0) | 2 |
| permission or terms of use required | 2 |
| licensable but holds no table (MIT source code) | 1 |

Most of the 234 are copies of city, state and federal open data the account
re-published. The Kaggle copy carries no evidence of the publisher's licence,
and a re-publisher's label could not license someone else's data in any case.
Many of those publishers do license openly, so the route is the line that owns
each publisher: `data_tables` for byte copies of GitHub files (22 of the
download's files are such copies, named after their raw GitHub or gist address),
`publisher_tables` for official series, and a new collection for city portals
that reads each portal dataset's own licence field.

The SDG rules propose goals for 175 of the 243 datasets, covering 16 of the 17
goals; goal 4 has none, because the download holds no education data:

| Goal | Datasets | Goal | Datasets |
|---|---:|---|---:|
| 1 | 13 | 10 | 15 |
| 2 | 3 | 11 | 55 |
| 3 | 15 | 12 | 2 |
| 4 | 0 | 13 | 37 |
| 5 | 14 | 14 | 1 |
| 6 | 3 | 15 | 2 |
| 7 | 19 | 16 | 44 |
| 8 | 33 | 17 | 2 |
| 9 | 6 | | |

The four packages propose goals 5, 8 and 16 (targets 5.2, 8.7 and 16.2), from
the trafficking rule: the DueCare datasets grade and train model answers to
labour-exploitation and trafficking prompts.

## What was built

- The `kaggle_public_good` supply line ([README](../../tools/supply_lines/README.md#kaggle-public-good-datasets-kaggle_public_good)):
  the local profiler, the licence decisions, the SDG rules and one dataset
  contract per licensable dataset (card, JSON Schema of every table, typed
  standard-library reader, tests with synthetic fixtures and known-wrong
  controls).
- The `public_good_analysis` family of `tools/creative_originals`: ten atomic
  functions, six built for the DueCare tables (paired arm lift, judge
  agreement, labelled score summaries, split leakage, redistribution rights,
  shard manifests) and four for shapes the held datasets show (rates per
  100,000, service request resolution times, migration deaths and missing,
  building energy use intensity), each with known-answer tests.

## Limits

- The Kaggle record of a dataset was not read; licences come from the files
  the download holds.
- The intake's 20-read ceiling and its lack of a dataset operation bound what
  can be learned about other programs' data from Kaggle itself.
- The SDG rules are keyword rules; 30 datasets were reviewed by hand and agree
  with the rules after two corrections, and every other proposal is unreviewed.
