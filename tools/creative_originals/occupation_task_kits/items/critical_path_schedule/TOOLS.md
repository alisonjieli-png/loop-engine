# Tools for Critical path schedule from tasks and dependencies

## O*NET data

O*NET 31.0 lists software per occupation. For the 49 occupations whose tasks link to this kit's activities, the most frequently listed software examples are:

| Software example | Occupations listing it | Hot technology | Listed as in demand |
| --- | --- | --- | --- |
| Microsoft Excel | 48 | yes | 38 |
| Microsoft Office software | 48 | yes | 39 |
| Microsoft PowerPoint | 45 | yes | 26 |
| Microsoft Word | 45 | yes | 11 |
| Microsoft Outlook | 38 | yes | 18 |
| Microsoft Access | 37 | yes | 1 |
| Microsoft Project | 31 | yes | 1 |
| Autodesk AutoCAD | 30 | yes | 14 |
| SAP software | 29 | yes | 4 |
| The MathWorks MATLAB | 25 | yes | 4 |
| C++ | 23 | yes | 3 |
| Python | 23 | yes | 12 |
| Web browser software | 22 | no | 0 |
| Linux | 21 | yes | 3 |
| Microsoft Visio | 21 | yes | 1 |

Software classes (O*NET commodity titles) listed for the most of these occupations:

| Class | Occupations |
| --- | --- |
| Office suite software | 48 |
| Spreadsheet software | 48 |
| Word processing software | 47 |
| Presentation software | 46 |
| Data base user interface and query software | 45 |
| Electronic mail software | 42 |
| Analytical or scientific software | 39 |
| Computer aided design CAD software | 35 |

These are tools the occupations use. O*NET does not say which tool serves this activity.

## Inference: what serves each step

This table is Baltor's inference, not O*NET data. Free means free to use under an open source or no-cost licence; paid means a commercial licence or subscription is usual.

| Step | Baltor components | Free tools | Paid tools |
| --- | --- | --- | --- |
| Collect tasks and durations | procedure step list; record_entry_validator for a task table | spreadsheet (LibreOffice Calc) | Microsoft Excel, Smartsheet |
| Compute dates, float, critical path | this kit's helper | Python standard library; GanttProject | Microsoft Project, Oracle Primavera |
| Track progress against the plan | milestone_status_report, earned_value_status kits | spreadsheet | Microsoft Project, Atlassian JIRA |
| Show the plan | svg_chart_builder kit for a bar view | GanttProject | Microsoft Project |
