# Tools for Multi-source table merge with provenance and conflicts

## O*NET data

O*NET 31.0 lists software per occupation. For the 63 occupations whose tasks link to this kit's activities, the most frequently listed software examples are:

| Software example | Occupations listing it | Hot technology | Listed as in demand |
| --- | --- | --- | --- |
| Microsoft Excel | 62 | yes | 45 |
| Microsoft Office software | 62 | yes | 48 |
| Microsoft Word | 61 | yes | 18 |
| Microsoft PowerPoint | 60 | yes | 24 |
| Microsoft Outlook | 56 | yes | 29 |
| Microsoft Access | 52 | yes | 0 |
| Web browser software | 43 | no | 0 |
| Database software | 26 | no | 0 |
| Adobe Acrobat | 25 | yes | 0 |
| Microsoft Windows | 23 | yes | 0 |
| SAP software | 23 | yes | 2 |
| Email software | 20 | no | 0 |
| Microsoft Project | 20 | yes | 0 |
| Microsoft SharePoint | 20 | yes | 2 |
| Structured query language SQL | 17 | yes | 2 |

Software classes (O*NET commodity titles) listed for the most of these occupations:

| Class | Occupations |
| --- | --- |
| Office suite software | 62 |
| Spreadsheet software | 62 |
| Data base user interface and query software | 62 |
| Word processing software | 61 |
| Presentation software | 61 |
| Electronic mail software | 60 |
| Internet browser software | 46 |
| Document management software | 36 |

These are tools the occupations use. O*NET does not say which tool serves this activity.

## Inference: what serves each step

This table is Baltor's inference, not O*NET data. Free means free to use under an open source or no-cost licence; paid means a commercial licence or subscription is usual.

| Step | Baltor components | Free tools | Paid tools |
| --- | --- | --- | --- |
| Profile sources | column_profile kit | OpenRefine | Microsoft Excel |
| Merge with provenance | this kit's helper | Python standard library, SQLite | ETL software (Informatica, Microsoft SQL Server Integration Services) |
| Resolve near-duplicate keys | duplicate_record_finder kit | OpenRefine | master data management software |
