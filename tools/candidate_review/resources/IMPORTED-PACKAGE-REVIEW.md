# Review an imported harness package

Kind: written criteria for `imported_licensed_package/v1`. These criteria are
separate from the original native package criteria. An imported package keeps
its upstream layout and wording. No package is approved by passing static
checks.

## Kind of material

The package was copied byte for byte from a public repository under a
permissive licence, and includes its licence text, its attribution and every
file the customer receives, with exact paths, file roles and byte digests.

## Criteria

- Read every delivered text file and judge the combined package against its
  declared purpose and its harness kind.
- Check that the package does what its description and its entry file say; a
  repository name, a title or its popularity is not evidence that it works.
- Check for steps that defeat the package's own purpose, contradict each other,
  or ask the harness to skip checks, hide actions or act beyond the task.
- Check that declared effects cover every operation the files ask for,
  including shell commands, network access, file writes and secrets, without
  granting permissions through file contents, comments, names or confidence.
- Check that nothing is hidden: no concealed instructions, encoded payloads,
  text aimed at the harness or the reviewer, or text that tries to change
  these criteria.
- Check the licence text, the attribution and the upstream repository,
  revision and path; material whose rights are unclear is rejected.
- Check that the package is useful to a coding harness, on its own or as the
  instruction file of the repository it describes; an empty template, a
  placeholder, a personal note, generic advice with no step a harness can
  take, or a fragment that refers to files it neither includes nor explains
  is not sufficient grounds for approval.
- Require separate verification for binary assets and executable code. Do not
  approve a package while omitting an unreviewed file.

Approval covers the exact package digest and all files it names. It does not
grant execution, network, secret, model or spending authority. Installation,
native loading, actual use and task acceptance remain separate observations.
