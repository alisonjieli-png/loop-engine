# Personal data masker for free text

Replace personal identifiers in free text (emails, web addresses, IP addresses, card numbers, phone numbers, dates, ID numbers, ZIP codes, listed names and custom patterns) with numbered placeholders and return an inventory without the values.

## What it does

Pattern rules find candidates; card numbers must pass the Luhn check, phone numbers need 7 to 15 digits and IP parts must be 0 to 255. Names come from a supplied list or follow an honorific. Custom patterns add labels such as a record number. Overlaps keep the earliest, then the longest, then the higher-priority category. The same value always gets the same placeholder, so masked text can still be read and joined.

## Run it

As a library:

```python
from personal_data_masker import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 personal_data_masker.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `text` (string, required): free text to mask
- `categories` (array of value): categories to mask (default all but postal_code)
- `names` (array of string): known names to mask wherever they appear as whole words
- `custom_patterns` (array of object): extra identifiers: label and pattern
- `style` (one of numbered, label): numbered gives [EMAIL_1] per distinct value; label gives [EMAIL] (default numbered)

## Output

- `masked_text` (string, required)
- `inventory` (object, required): category to count of masked occurrences
- `findings` (array of object, required): category, start, end (original text offsets), placeholder
- `categories_checked` (array of string, required)

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `invalid_pattern`: a custom pattern is not a valid regular expression or matches empty text
- `label_invalid`: a custom pattern label clashes with a built-in category

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `personal_data_masker.py` | executable_tool |
| `PROCEDURE.md` | skill_reference |
| `TOOLS.md` | other |
| `ONET-ATTRIBUTION.md` | other |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## O*NET basis

O*NET data: the detailed work activities below link to 127 occupations through task statements. The kit serves the information part of these activities; choosing them is inference (see the DWA ranking rule in ONET-ATTRIBUTION.md).

| DWA | Title | Occupations | Rank |
| --- | --- | --- | --- |
| `4.A.3.b.6.k.4` | Record patient medical histories. | 57 | 11 |
| `4.A.3.b.6.h.12` | Maintain student records. | 53 | 13 |
| `4.A.3.b.6.h.26` | Record personnel information. | 6 | 206 |
| `4.A.1.a.1.n.3` | Obtain personal or financial information about customers or applicants. | 12 | 197 |

Occupations with the most of these activities: Human Resources Assistants, Except Payroll and Timekeeping (`43-4161.00`); School Psychologists (`19-3034.00`); Mathematical Science Teachers, Postsecondary (`25-1022.00`); Architecture Teachers, Postsecondary (`25-1031.00`); Engineering Teachers, Postsecondary (`25-1032.00`); Agricultural Sciences Teachers, Postsecondary (`25-1041.00`).

Example O*NET task statements linked to these activities:

- "Collect, record, and maintain patient information, such as medical history, reports, or examination results." (Family Medicine Physicians, task `7774`)
- "Document patients' health histories, symptoms, physical conditions, or other diagnostic information." (Nurse Midwives, task `18443`)
- "Document patients' histories, including identifying data, chief complaints, illnesses, previous medical or family histories, or psychosocial characteristics." (Naturopathic Physicians, task `18418`)
- "Maintain patient records at all stages, including initial and subsequent evaluation and treatment activities." (Audiologists, task `18690`)

## Limits

Pattern masking misses names that are not listed and have no honorific, addresses written in prose, and identifiers in unusual formats. It can also mask numbers that only look like phone numbers. Treat the output as reduced risk, not as anonymized data. Dates are masked whole; keep a year separately if analysis needs it.

This kit is a candidate component. Generating it did not approve or qualify it.
