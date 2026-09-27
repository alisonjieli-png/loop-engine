# Interrupted installation

The download stopped halfway. The skill file arrived, the script it runs did
not, and a partial copy of the script is left beside it. A harness would load
the skill and then fail when the model runs the script. An installer writes
to a partial file and renames it only when the digest matches, so a leftover
partial file is proof of an installation that did not finish.

Expected refusal codes: `file_missing` and `partial_file_present`.
