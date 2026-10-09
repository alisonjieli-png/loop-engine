# Tools for Record entry validator with normalization rules

## O*NET data

O*NET 31.0 lists software per occupation. For the 52 occupations whose tasks link to this kit's activities, the most frequently listed software examples are:

| Software example | Occupations listing it | Hot technology | Listed as in demand |
| --- | --- | --- | --- |
| Microsoft Office software | 52 | yes | 42 |
| Microsoft Excel | 51 | yes | 37 |
| Microsoft Word | 51 | yes | 10 |
| Microsoft PowerPoint | 49 | yes | 19 |
| Microsoft Outlook | 48 | yes | 25 |
| Microsoft Access | 39 | yes | 3 |
| Web browser software | 29 | no | 0 |
| SAP software | 24 | yes | 6 |
| Microsoft Windows | 22 | yes | 0 |
| Microsoft SharePoint | 21 | yes | 2 |
| Microsoft Visio | 19 | yes | 0 |
| Adobe Acrobat | 17 | yes | 0 |
| Database software | 17 | no | 0 |
| Structured query language SQL | 17 | yes | 7 |
| Microsoft Dynamics | 15 | no | 0 |

Software classes (O*NET commodity titles) listed for the most of these occupations:

| Class | Occupations |
| --- | --- |
| Office suite software | 52 |
| Word processing software | 51 |
| Spreadsheet software | 51 |
| Electronic mail software | 50 |
| Presentation software | 50 |
| Data base user interface and query software | 49 |
| Enterprise resource planning ERP software | 37 |
| Document management software | 34 |

These are tools the occupations use. O*NET does not say which tool serves this activity.

## Inference: what serves each step

This table is Baltor's inference, not O*NET data. Free means free to use under an open source or no-cost licence; paid means a commercial licence or subscription is usual.

| Step | Baltor components | Free tools | Paid tools |
| --- | --- | --- | --- |
| Inspect the file | column_profile kit | OpenRefine, LibreOffice Calc | Microsoft Excel |
| Validate and normalize | this kit's helper | Python standard library | data quality software |
| Find duplicates | duplicate_record_finder kit | OpenRefine | master data management software |
| Load | schema documentation of the target system | PostgreSQL, SQLite | Microsoft SQL Server |
