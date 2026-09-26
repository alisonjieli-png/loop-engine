# Served catalogue rescans

Kind: dated records of the nightly rescan of the served library.

Each file is one run of `tools/rescan_served_catalogue.py`, record
`served_catalogue_rescan/v1`: the release rescanned, how many item versions
were served, which failed a rule now and with which findings, whether the run
was asked to withdraw, and what it withdrew. Failed runs and runs that withdrew
nothing are kept beside the others. The guide is
[catalogue feedback and withdrawal](../../docs/guides/catalogue-feedback-and-withdrawal.md).
