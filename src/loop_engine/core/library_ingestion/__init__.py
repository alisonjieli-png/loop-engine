"""Library ingestion: outside harness material with provenance, as candidates.

This component reads outside material (skills, instruction files and
protocol server registry entries) through source engines behind one fixed
edge, keeps every fetched byte in quarantine, records a versioned provenance
record for each item, and prepares candidates for the existing candidate
staging contract. It approves, serves and publishes nothing. See README.md
beside this file for the edges, the engines and the rules.
"""
