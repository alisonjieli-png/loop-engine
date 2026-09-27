# Codex takes over the interrupted design deployment

The owner explicitly asked Codex to pick up Claude's interrupted UI/UX work and
complete a full deployment after Claude ran out of credits. This direction
supersedes the earlier division that reserved deployment for Claude.

Codex will preserve all design worktrees and their uncommitted changes, assemble
the design in a new detached release checkout, run the required checks, push the
reviewed main revision, deploy through the guarded Fly workflow and verify all
live hostnames. The source-library work remains preserved in its own checkout.

At takeover, local origin/main is `85a5217d`, the release 38 fix is `8850d37f`,
and the clean foundation merge is `7f56c01a`. Account, content, funnel and library
page commits exist; foundation, account, funnel, library, home and docs/states
worktrees also contain uncommitted changes. These will be saved before merging.
The preflight for `8850d37f` passed most checks but failed self-test; its failure
will be inspected rather than bypassed.

Please avoid starting another release or editing the Codex deployment checkout
while this takeover is active. Existing daily catalogue and model jobs remain
under their current ownership and are not being changed for this deployment.
