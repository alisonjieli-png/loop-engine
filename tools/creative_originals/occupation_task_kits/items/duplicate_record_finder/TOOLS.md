# Tools for Duplicate record finder with blocking and weighted similarity

## O*NET data

O*NET 31.0 lists software per occupation. For the 31 occupations whose tasks link to this kit's activities, the most frequently listed software examples are:

| Software example | Occupations listing it | Hot technology | Listed as in demand |
| --- | --- | --- | --- |
| Microsoft Excel | 30 | yes | 20 |
| Microsoft Office software | 30 | yes | 22 |
| Microsoft Word | 30 | yes | 4 |
| Microsoft PowerPoint | 26 | yes | 13 |
| Microsoft Outlook | 24 | yes | 13 |
| Web browser software | 21 | no | 0 |
| Microsoft Access | 19 | yes | 0 |
| Microsoft Windows | 12 | yes | 0 |
| Adobe Acrobat | 11 | yes | 0 |
| Email software | 10 | no | 0 |
| Microsoft Publisher | 10 | no | 0 |
| Intuit QuickBooks | 9 | yes | 1 |
| Microsoft Project | 9 | yes | 0 |
| Adobe InDesign | 8 | yes | 1 |
| Database software | 8 | no | 0 |

Software classes (O*NET commodity titles) listed for the most of these occupations:

| Class | Occupations |
| --- | --- |
| Office suite software | 30 |
| Word processing software | 30 |
| Spreadsheet software | 30 |
| Electronic mail software | 28 |
| Presentation software | 27 |
| Data base user interface and query software | 26 |
| Internet browser software | 24 |
| Operating system software | 17 |

These are tools the occupations use. O*NET does not say which tool serves this activity.

## Inference: what serves each step

This table is Baltor's inference, not O*NET data. Free means free to use under an open source or no-cost licence; paid means a commercial licence or subscription is usual.

| Step | Baltor components | Free tools | Paid tools |
| --- | --- | --- | --- |
| Normalize records | record_entry_validator kit | OpenRefine | data quality software |
| Score and cluster pairs | this kit's helper | Python standard library, Splink | master data management software |
| Compile the surviving table | multi_source_table_merge kit | Python standard library | ETL software |
