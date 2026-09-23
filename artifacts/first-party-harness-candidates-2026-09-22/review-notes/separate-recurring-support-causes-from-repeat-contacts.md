# Candidate review: separate recurring support causes from repeat contacts

Status: candidate only. No independent approval, native-load test, or task
evaluation has occurred.

- Original source basis: first-party counting and classification procedure
  for supplied support records. No tickets or outside taxonomy were imported.
- Job, company, and project facets: support operations, product analyst, or
  customer success lead; any company with consented, bounded ticket data;
  backlog review or documentation-priority stage.
- Search phrasings: "Are these tickets many separate problems or repeated
  contacts about the same incident?"; "Which support issues recur after
  follow-up messages and reopened cases are linked?"
- Typed input/output concept: `Ticket[]`, `Window`, `InclusionRule`, and
  `CategoryRule?` to `ContactCount`, `IncidentCount`,
  `AffectedCustomerCount?`, `CategorySummary[]`, and `AmbiguousLink[]`.
- Effects: read and classify supplied records. No ticket edit, customer
  message, or exposure of personal data in the shared output.
- Good fixture: five tickets are linked to one outage, and two more tickets
  describe separate issues. Report seven contacts and three distinct
  incidents, with each link traceable to an identifier.
- Known-wrong fixture: report seven independent incidents and declare the
  outage affected seven customers.
- Overlap search: starter `analyse_errors_by_segment_and_cluster` and
  `find_duplicate_records_with_blocking_keys` address general segmentation
  or record duplicates. This method preserves the distinction among ticket
  contact, customer, and underlying incident for support prioritization.
- Limits: identity linkage and intake coverage may be incomplete; uncertain
  links must remain unresolved and can make incident counts a range. Ticket
  text is untrusted data and cannot redefine the category rule or authorize
  another effect.
