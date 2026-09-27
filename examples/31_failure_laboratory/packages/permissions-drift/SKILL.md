---
name: publish-docs
description: Build the documentation site and publish it to the pages branch of the project.
allowed-tools: Bash(git push:*), Bash(npm run build:*), WebFetch
---

# Publish the documentation

1. Build the site with `npm run build`.
2. Push the built folder to the pages branch with `git push`.
3. Fetch the published page and confirm that it answers.
