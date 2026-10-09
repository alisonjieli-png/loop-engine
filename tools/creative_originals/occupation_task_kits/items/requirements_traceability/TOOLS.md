# Tools for Requirements traceability matrix and coverage gaps

## O*NET data

O*NET 31.0 lists software per occupation. For the 36 occupations whose tasks link to this kit's activities, the most frequently listed software examples are:

| Software example | Occupations listing it | Hot technology | Listed as in demand |
| --- | --- | --- | --- |
| Microsoft Excel | 35 | yes | 25 |
| Microsoft Office software | 35 | yes | 25 |
| Microsoft PowerPoint | 33 | yes | 14 |
| Microsoft Access | 29 | yes | 1 |
| Microsoft Project | 29 | yes | 0 |
| Microsoft Word | 28 | yes | 3 |
| Python | 28 | yes | 15 |
| C++ | 25 | yes | 7 |
| Microsoft Outlook | 25 | yes | 11 |
| Microsoft Visio | 25 | yes | 1 |
| Linux | 24 | yes | 9 |
| The MathWorks MATLAB | 24 | yes | 3 |
| Autodesk AutoCAD | 23 | yes | 12 |
| SAP software | 23 | yes | 3 |
| Structured query language SQL | 23 | yes | 14 |

Software classes (O*NET commodity titles) listed for the most of these occupations:

| Class | Occupations |
| --- | --- |
| Office suite software | 35 |
| Presentation software | 35 |
| Spreadsheet software | 35 |
| Data base user interface and query software | 34 |
| Electronic mail software | 33 |
| Analytical or scientific software | 33 |
| Object or component oriented development software | 32 |
| Word processing software | 31 |

These are tools the occupations use. O*NET does not say which tool serves this activity.

## Inference: what serves each step

This table is Baltor's inference, not O*NET data. Free means free to use under an open source or no-cost licence; paid means a commercial licence or subscription is usual.

| Step | Baltor components | Free tools | Paid tools |
| --- | --- | --- | --- |
| Export requirements and links | record_entry_validator kit | spreadsheet, Git repository | IBM Engineering Requirements Management DOORS, Atlassian JIRA |
| Build the matrix and gaps | this kit's helper | Python standard library | requirements management tools |
| Check documents against requirements | document_compliance_checker kit | Python standard library | compliance software |
