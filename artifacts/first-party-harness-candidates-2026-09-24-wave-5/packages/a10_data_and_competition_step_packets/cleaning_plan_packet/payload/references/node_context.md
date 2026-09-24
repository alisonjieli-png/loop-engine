# Cleaning plan step packet: context

## Objective

Hand over a cleaning plan for one table: for each column, the rules that would fix it, each with counted evidence and a reason, plus the questions a person must answer. The table stays unchanged.

## Relevant context

- A later step applies approved rules to a copy of the table. A wrong rule there damages good values, so judge each rule by what the column means.
- Common traps: `NA` can be a country code, `none` can be a real category, and `03/04/2025` reads as two different dates.
- When a date column's only non-ISO values read two ways, the draft still suggests `parse_date`. That rule holds those values, and a question asks which order the column uses.
- `01234` in a postal code or an account number is a code, and a number rule would drop its leading 0. The draft then asks a question instead of suggesting `parse_number`. Add that rule yourself only for a quantity.
- In the profile, `dates.formats` gives `only_this_format` for each format. Remove a format only when it shows 0 there while another format shows more than 0, and say so in the reason. Otherwise keep both formats and ask.

## Current state

The table is raw and has no plan yet. The draft command writes `table_profile.json` and a draft `cleaning_plan.json` with suggested rules.

## Contracts and input

The five operations and their `parameters`:

- `trim_whitespace`: `{}`. Removes spaces, tabs and line breaks at both ends and turns each inner run of them into one space, so a note written on two lines becomes one line.
- `missing_tokens_to_empty`: `tokens`, compared without letter case.
- `map_values`: `mapping` from spelling to value, and `unmapped` set to `keep` or `hold`. A target differs from its spelling only in letter case. On a tie, the draft picks mixed case such as `Paris`.
- `parse_number`: `decimal_separator` and `thousands_separator`. The output has a dot and no grouping.
- `parse_date`: `formats` built from `%Y`, `%m`, `%d`, `%b` and `%B`. The output is `YYYY-MM-DD`. A value that two formats read as different dates is held.

Per column the order is trim, missing tokens, map, then one parse rule. A cell that a rule holds keeps its source value, so the evidence counts no change for it from the rules before that rule. A rule you add needs `rule_id`, `column`, `operation`, `parameters`, `status`, `reason` and `"evidence": {}`; the check fills the evidence. The rendered input values follow `.baltor/step/contracts/input.schema.json`.

## Acceptance

- The check passes, and no evidence number was typed by hand.
- Every suggested rule is still present, as `proposed` or `dropped`, with a reason.
- No rule is `approved` or `rejected`. That decision belongs to the reviewer.
