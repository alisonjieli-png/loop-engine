# Ambiguous data

The skill's frontmatter gives `name` twice, with two different values. One
YAML reader keeps the last value, another refuses the file, so the same
package would install as a different skill, or as none, depending on the
harness.

Expected refusal codes: `frontmatter_ambiguous`.
