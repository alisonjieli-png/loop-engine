# O*NET attribution for Earned value status with performance indices and forecasts

This includes information from the O*NET 31.0 Database by the U.S. Department of Labor, Employment and Training Administration (USDOL/ETA). Used under the CC BY 4.0 license. O*NET is a trademark of USDOL/ETA. The contents were modified (selected, joined and summarized). USDOL/ETA has not approved, endorsed, or tested these modifications.

Source: O*NET 31.0 Database, https://www.onetcenter.org/database.html, archive db_31_0_csv.zip, SHA-256 55033fc68b4c13ec23e7f74dc6378660f6e854e75d55d6e333ae0a761d3987cd. Licence: https://www.onetcenter.org/license_db.html (CC BY 4.0).

Tables used: Occupation Data, Task Statements, Task Ratings, Tasks to DWAs, DWA Reference (GWAs to IWAs to DWAs), Software Skills. Quoted O*NET text keeps its words; dashes are normalized to hyphens.

What is O*NET data here: DWA, IWA and GWA identifiers and titles, task identifiers and statements, occupation codes and titles, task importance ratings and software lists. What is inference: the choice of activities for this kit, the computer information work flag and rank, the procedure, the tool notes and the helper's method.

## Detailed work activities

| DWA | Title | IWA | GWA | Rank | Computer information work (inference) |
| --- | --- | --- | --- | --- | --- |
| `4.A.4.b.4.j.12` | Manage operations, research, or logistics projects. | `4.A.4.b.4.j` Direct organizational operations, activities, or procedures. | `4.A.4.b.4` Guiding, Directing, and Motivating Subordinates | 147 | yes |
| `4.A.4.b.4.e.7` | Manage information technology projects or system activities. | `4.A.4.b.4.e` Direct scientific or technical activities. | `4.A.4.b.4` Guiding, Directing, and Motivating Subordinates | 120 | yes |
| `4.A.4.b.4.h.5` | Manage organizational or project budgets. | `4.A.4.b.4.h` Manage budgets or finances. | `4.A.4.b.4` Guiding, Directing, and Motivating Subordinates | 282 | yes |

## Occupations (27)

| Code | Title |
| --- | --- |
| `11-2011.00` | Advertising and Promotions Managers |
| `11-2032.00` | Public Relations Managers |
| `11-2033.00` | Fundraising Managers |
| `11-3021.00` | Computer and Information Systems Managers |
| `11-3071.04` | Supply Chain Managers |
| `11-9031.00` | Education and Childcare Administrators, Preschool and Daycare |
| `11-9033.00` | Education Administrators, Postsecondary |
| `11-9041.00` | Architectural and Engineering Managers |
| `11-9051.00` | Food Service Managers |
| `11-9081.00` | Lodging Managers |
| `11-9111.00` | Medical and Health Services Managers |
| `11-9121.00` | Natural Sciences Managers |
| `11-9121.01` | Clinical Research Coordinators |
| `11-9199.10` | Wind Energy Development Managers |
| `13-1081.00` | Logisticians |
| `13-1082.00` | Project Management Specialists |
| `15-1211.00` | Computer Systems Analysts |
| `15-1221.00` | Computer and Information Research Scientists |
| `15-1251.00` | Computer Programmers |
| `15-1252.00` | Software Developers |
| `15-1255.01` | Video Game Designers |
| `15-1299.05` | Information Security Engineers |
| `15-1299.08` | Computer Systems Engineers/Architects |
| `15-1299.09` | Information Technology Project Managers |
| `19-1023.00` | Zoologists and Wildlife Biologists |
| `23-1011.00` | Lawyers |
| `41-3021.00` | Insurance Sales Agents |

## Task statements linked to these activities (39)

| Task | Occupation |
| --- | --- |
| `56` | `11-9111.00` |
| `735` | `41-3021.00` |
| `974` | `11-3021.00` |
| `978` | `11-3021.00` |
| `1081` | `11-9051.00` |
| `1108` | `11-9081.00` |
| `1279` | `15-1251.00` |
| `1498` | `19-1023.00` |
| `3239` | `11-2011.00` |
| `3244` | `11-2011.00` |
| `3481` | `15-1211.00` |
| `3790` | `23-1011.00` |
| `5197` | `11-9031.00` |
| `5254` | `11-9033.00` |
| `7205` | `11-9121.00` |
| `14637` | `15-1221.00` |
| `14676` | `15-1299.08` |
| `15586` | `11-9121.01` |
| `15605` | `11-9121.01` |
| `15698` | `11-3071.04` |
| `15834` | `11-9199.10` |
| `16156` | `15-1299.09` |
| `16163` | `15-1299.09` |
| `16169` | `15-1299.09` |
| `16171` | `15-1299.09` |
| `16212` | `15-1255.01` |
| `18597` | `11-9033.00` |
| `20171` | `11-9041.00` |
| `20847` | `13-1081.00` |
| `20944` | `11-3071.04` |
| `21239` | `11-2032.00` |
| `21258` | `11-2033.00` |
| `21470` | `13-1082.00` |
| `21480` | `13-1082.00` |
| `21669` | `15-1252.00` |
| `21769` | `15-1299.05` |
| `21770` | `15-1299.05` |
| `21777` | `15-1299.05` |
| `21778` | `15-1299.05` |

DWA ranking rule (inference): see dwa-ranking.json in the build outputs; in short, breadth across occupations and SOC minor groups, importance-weighted tasks, the O*NET importance of Working with Computers, and software coverage, with activities not flagged as computer information work scaled down.
