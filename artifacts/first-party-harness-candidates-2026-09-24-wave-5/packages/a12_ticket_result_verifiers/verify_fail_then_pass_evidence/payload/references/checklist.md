# Checks the script cannot do

Answer each item with yes, no or unknown, and name the file or line you read. Put every no or unknown in your answer as an open point.

- [ ] BEFORE came from the base revision plus the new test, with the fix absent.
- [ ] In BEFORE, the new test fails for the reported defect. Its failure text matches the ticket and is not an import error, a typo or a broken fixture.
- [ ] The new test checks the behavior the ticket asks for, not only that the code runs without an error.
- [ ] BEFORE and AFTER come from the same command, the same folder and the same environment.
- [ ] The new test did not change between the two runs.
- [ ] The fix works for the general case and does not look for the exact input of the new test.
- [ ] Every warning in the JSON result has an explanation in your answer.
