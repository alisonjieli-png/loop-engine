# Tools for Appointment slot allocator for providers and rooms

## O*NET data

O*NET 31.0 lists software per occupation. For the 41 occupations whose tasks link to this kit's activities, the most frequently listed software examples are:

| Software example | Occupations listing it | Hot technology | Listed as in demand |
| --- | --- | --- | --- |
| Microsoft Excel | 39 | yes | 15 |
| Microsoft Office software | 39 | yes | 17 |
| Microsoft Word | 36 | yes | 8 |
| Microsoft Outlook | 29 | yes | 10 |
| Microsoft PowerPoint | 25 | yes | 5 |
| Web browser software | 25 | no | 0 |
| Microsoft Access | 22 | yes | 0 |
| Email software | 16 | no | 0 |
| MEDITECH software | 16 | yes | 0 |
| Microsoft Windows | 14 | yes | 0 |
| Database software | 13 | no | 0 |
| Electronic medical record EMR software | 12 | no | 0 |
| Medical procedure coding software | 12 | no | 0 |
| eClinicalWorks EHR software | 12 | yes | 0 |
| Epic Systems | 10 | yes | 3 |

Software classes (O*NET commodity titles) listed for the most of these occupations:

| Class | Occupations |
| --- | --- |
| Office suite software | 39 |
| Spreadsheet software | 39 |
| Word processing software | 36 |
| Electronic mail software | 35 |
| Data base user interface and query software | 31 |
| Medical software | 30 |
| Internet browser software | 26 |
| Presentation software | 25 |

These are tools the occupations use. O*NET does not say which tool serves this activity.

## Inference: what serves each step

This table is Baltor's inference, not O*NET data. Free means free to use under an open source or no-cost licence; paid means a commercial licence or subscription is usual.

| Step | Baltor components | Free tools | Paid tools |
| --- | --- | --- | --- |
| Collect availability and requests | record_entry_validator kit for request tables | spreadsheet (LibreOffice Calc), CalDAV calendar | Microsoft Outlook, Calendly |
| Place requests | this kit's helper | Python standard library | practice management software |
| Protect personal data in shared lists | personal_data_masker kit | Python standard library | data loss prevention software |
| Publish the schedule | svg_chart_builder kit for load charts | shared calendar | Microsoft Outlook |
