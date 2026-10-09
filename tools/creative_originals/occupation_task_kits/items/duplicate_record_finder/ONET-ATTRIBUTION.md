# O*NET attribution for Duplicate record finder with blocking and weighted similarity

This includes information from the O*NET 31.0 Database by the U.S. Department of Labor, Employment and Training Administration (USDOL/ETA). Used under the CC BY 4.0 license. O*NET is a trademark of USDOL/ETA. The contents were modified (selected, joined and summarized). USDOL/ETA has not approved, endorsed, or tested these modifications.

Source: O*NET 31.0 Database, https://www.onetcenter.org/database.html, archive db_31_0_csv.zip, SHA-256 55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd. Licence: https://www.onetcenter.org/license_db.html (CC BY 4.0).

Tables used: Occupation Data, Task Statements, Task Ratings, Tasks to DWAs, DWA Reference (GWAs to IWAs to DWAs), Software Skills. Quoted O*NET text keeps its words; dashes are normalized to hyphens.

What is O*NET data here: DWA, IWA and GWA identifiers and titles, task identifiers and statements, occupation codes and titles, task importance ratings and software lists. What is inference: the choice of activities for this kit, the computer information work flag and rank, the procedure, the tool notes and the helper's method.

## Detailed work activities

| DWA | Title | IWA | GWA | Rank | Computer information work (inference) |
| --- | --- | --- | --- | --- | --- |
| `4.A.2.a.2.a.1` | Verify accuracy of records. | `4.A.2.a.2.a` Evaluate the quality or accuracy of data. | `4.A.2.a.2` Processing Information | 115 | yes |
| `4.A.3.b.6.h.9` | Maintain records, documents, or other files. | `4.A.3.b.6.h` Maintain operational records. | `4.A.3.b.6` Documenting/Recording Information | 71 | yes |
| `4.A.3.b.6.h.15` | Maintain records of customer accounts. | `4.A.3.b.6.h` Maintain operational records. | `4.A.3.b.6` Documenting/Recording Information | 749 | yes |

## Occupations (31)

| Code | Title |
| --- | --- |
| `11-3012.00` | Administrative Services Managers |
| `11-9179.01` | Fitness and Wellness Coordinators |
| `11-9199.02` | Compliance Managers |
| `13-1031.00` | Claims Adjusters, Examiners, and Investigators |
| `13-1041.00` | Compliance Officers |
| `13-1071.00` | Human Resources Specialists |
| `13-1121.00` | Meeting, Convention, and Event Planners |
| `13-1199.07` | Security Management Specialists |
| `13-2011.00` | Accountants and Auditors |
| `13-2023.00` | Appraisers and Assessors of Real Estate |
| `13-2053.00` | Insurance Underwriters |
| `13-2072.00` | Loan Officers |
| `13-2081.00` | Tax Examiners and Collectors, and Revenue Agents |
| `13-2082.00` | Tax Preparers |
| `15-1299.06` | Digital Forensics Analysts |
| `19-3034.00` | School Psychologists |
| `27-1013.00` | Fine Artists, Including Painters, Sculptors, and Illustrators |
| `27-1023.00` | Floral Designers |
| `27-1024.00` | Graphic Designers |
| `27-1026.00` | Merchandise Displayers and Window Trimmers |
| `27-2012.04` | Talent Directors |
| `27-2022.00` | Coaches and Scouts |
| `27-2091.00` | Disc Jockeys, Except Radio |
| `27-3042.00` | Technical Writers |
| `27-3092.00` | Court Reporters and Simultaneous Captioners |
| `27-4011.00` | Audio and Video Technicians |
| `27-4021.00` | Photographers |
| `39-4012.00` | Crematory Operators |
| `41-3091.00` | Sales Representatives of Services, Except Advertising, Insurance, Financial Services, and Travel |
| `41-4011.00` | Sales Representatives, Wholesale and Manufacturing, Technical and Scientific Products |
| `41-9041.00` | Telemarketers |

## Task statements linked to these activities (39)

| Task | Occupation |
| --- | --- |
| `1212` | `13-1121.00` |
| `1265` | `13-2053.00` |
| `1726` | `27-1023.00` |
| `3967` | `27-3042.00` |
| `3990` | `27-4011.00` |
| `4004` | `27-4011.00` |
| `4621` | `41-9041.00` |
| `4622` | `41-9041.00` |
| `4627` | `41-9041.00` |
| `5302` | `13-2081.00` |
| `5455` | `19-3034.00` |
| `7366` | `13-2082.00` |
| `8662` | `27-3092.00` |
| `9354` | `27-4021.00` |
| `10993` | `27-1013.00` |
| `11019` | `27-2012.04` |
| `11241` | `41-4011.00` |
| `15228` | `27-1024.00` |
| `15544` | `11-9179.01` |
| `18863` | `13-1071.00` |
| `20114` | `27-2022.00` |
| `20619` | `41-4011.00` |
| `20756` | `27-1026.00` |
| `21089` | `11-9199.02` |
| `21266` | `11-3012.00` |
| `21428` | `13-1031.00` |
| `21438` | `13-1031.00` |
| `21461` | `13-1041.00` |
| `21502` | `13-1199.07` |
| `21512` | `13-2011.00` |
| `21518` | `13-2011.00` |
| `21558` | `13-2023.00` |
| `21567` | `13-2023.00` |
| `21647` | `13-2072.00` |
| `21799` | `15-1299.06` |
| `22621` | `27-2091.00` |
| `23181` | `39-4012.00` |
| `23233` | `41-3091.00` |
| `24028` | `27-3092.00` |

DWA ranking rule (inference): see dwa-ranking.json in the build outputs; in short, breadth across occupations and SOC minor groups, importance-weighted tasks, the O*NET importance of Working with Computers, and software coverage, with activities not flagged as computer information work scaled down.
