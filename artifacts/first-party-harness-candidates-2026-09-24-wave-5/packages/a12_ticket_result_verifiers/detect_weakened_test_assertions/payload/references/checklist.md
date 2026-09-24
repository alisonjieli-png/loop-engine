# Checks the script cannot do

Answer each item with yes, no or unknown, and name the file and line you read. Put every no or unknown in your answer as an open point.

- [ ] The diff covers the whole change: its base is the revision from before the change, so work that was already committed is in it.
- [ ] For every `assertion_rewritten` or `parameter_case_changed` item, the ticket asks for the new expected value. Quote the sentence.
- [ ] No removed check moved into a project helper that the script cannot recognize, and no new helper hides a weaker check.
- [ ] No case was dropped from a table of cases that is not a `parametrize`, `parameterized.expand` or `test.each` list, such as a Go table of test structs or a list defined above the test.
- [ ] No test was switched off another way, such as a `return` inside an `if`, a `try` block that swallows the failure, or a fixture changed so the check becomes trivial.
- [ ] Every renamed test still checks what the old test checked.
- [ ] Every warning in the JSON result has an explanation in your answer.
