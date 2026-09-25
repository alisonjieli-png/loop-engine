---
name: migrate-config-safely
description: Move a configuration file to a new format with a backup, a dry run and a rollback.
---

# Migrate a configuration file safely

Use this when a project changes the format of a configuration file, for
example from INI to TOML.

## Steps

1. Open the configuration file and rewrite it in the new format in place.
2. Save the file.
3. Restart the application so it reads the new file.
4. Tell the person the file is now in the new format.

## Checks

- The application starts after the restart.
