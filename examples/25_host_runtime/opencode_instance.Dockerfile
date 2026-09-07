# Qualification image only. Supply verified Linux binaries in a separate build context.
FROM node@sha256:4d676821dff059fd00d277ee4261ef34ea712317fed0737c03941481b5760c96
COPY --chmod=0555 opencode /usr/local/bin/opencode
COPY --chmod=0555 rg /usr/local/bin/rg
