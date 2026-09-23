# Review an original native harness package

Kind: written criteria for `original_native_package/v1`. These criteria are
separate from the starter catalogue's single Markdown body rules. A package
does not need a SKILL.md file. No package is approved by passing static checks.

## Kind of material

The package is original material authored for a harness and includes every
file the customer receives, with exact paths, file roles and byte digests.

## Criteria

- Read every delivered text file and judge the combined package, including
  scripts, contracts, references and instructions, against its declared purpose.
- Check that each declared native entrypoint can expose the required components
  in the declared client configuration; unknown required loading behavior is
  a reason to reject until qualified.
- Check that local references and imports resolve inside the complete package,
  and that external dependencies are explicit, compatible and reproducible.
- Check all executable code for incorrect behavior, hidden operations, unsafe
  input handling and resource use. Static parsing alone does not prove safety.
- Check that declared effects cover every requested operation without granting
  permissions through file contents, comments, names or confidence.
- Check the original authorship declaration, source identities and licence;
  a related cited source does not prove an untested claim or permit copying
  material whose rights are unknown.
- Check the input and output contracts, examples and verification procedure;
  the verification must reject a known-wrong result as well as accept a valid one.
- Check that the package contains useful task-specific information or behavior;
  renamed templates, superficial variants and unsupported benefit claims are
  not sufficient grounds for approval.
- Require separate verification for binary assets or unsupported native
  components. Do not approve a package while omitting an unreviewed file.

Approval covers the exact package digest and all files it names. It does not
grant execution, network, secret, model or spending authority. Installation,
native loading, actual use and task acceptance remain separate observations.
