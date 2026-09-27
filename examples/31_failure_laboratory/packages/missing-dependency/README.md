# Missing dependency

A plugin manifest names a reviewer subagent and a hook script that the
package does not ship. Claude Code would load the plugin, then fail to find
the subagent, and the hook would fail on every write. This is the most common
activation fault in imported material: a file that names another file from
its source repository without carrying it.

Expected refusal codes: `manifest_part_missing` and `hook_script_missing`.
