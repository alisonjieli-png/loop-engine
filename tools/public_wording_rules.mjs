/* The public wording rules of the Baltor website, in one place.

   Every browser check imports its wording rules from this file, so a rule can no longer drift between copies (on
   September 23, 2026 two copies of the retired-word rule disagreed, and a page offering "early access" passed locally and
   was caught only after a deployment). To change what a customer page may say, change the rule here: every check follows.
   tools/check_service_workspace.mjs holds one check that both page checks import this file and define no copy of their own.

   Each rule names the owner's decision it carries out. Marketing copy may be energetic and evaluative; these rules keep
   out words that are wrong for a customer page, not words that are merely enthusiastic (the owner, September 21, 2026:
   marketing language is not a claim; a number, a comparison, a guarantee or an invented customer is). */

/* Runtime vocabulary stays in the documentation and the repository, never on a customer page (AGENTS.md, Public writing). */
export const internalTerms=/\bLoop(?:s|[ -]node| Engine)?\b|runtime classification|role profile/i;
/* The same rule with the role names, for text a customer reads in the workspace. */
export const publicVocabulary=/\bLoop(?:s|[ -]node| Engine)?\b|runtime classification|role profiles?|\bPractitioner\b/i;
/* Words that describe the product as a trial, retired when registration opened (September 23 and 24, 2026). */
export const retiredAccessWords=/\bpilots?\b|\bbetas?\b|early access/i;
/* The words of an invitation-only service and of unfinished work, retired on September 23, 2026: "remove all mentions of
   invitation only, this should be consistent as if it is fully working" and "We also need to get rid of 'search is free'".
   A capability that is not released yet is described with "built to", never with a status word. */
export const invitationWords=/\binvit(?:e|es|ed|ing|ations?)\b|small groups|waiting list|\bsearch(?:ing)? is free\b|being built|being prepared|\bplanned\b/i;
/* A statement that the terms are unpublished; the owner approved the terms on September 23, 2026. */
export const unpublishedTerms=/terms of service:?\s+not yet published|terms(?: of service)? (?:are|is) (?:still )?(?:a draft|not (?:yet )?published)/i;
/* Status tags on cards and badges, retired on September 23, 2026 ("no status tags or fluff"). */
export const cardStatusWords=/available now|being built|\bplanned\b|coming soon|packages coming/i;
/* Phrases the owner called meaningless on September 24, 2026, and the few of the same kind removed with them: words that
   describe Baltor's own checks or repeat the navigation instead of telling a visitor something. They are read in the
   rendered words of every page; keep the list short so it never pins other copy. */
export const retiredPhrases=["creates your account.","connects your harness.","Bytes match the digest","Recorded from this release's library",
  "digest checked","typed in by hand","from saved evidence","Seen in the run"];

/* The same rules as data, for a page an owner reads and adjusts. */
export const RULES=[
  {id:"runtime-words",rule:String(internalTerms),decided:"AGENTS.md, Public writing",applies_to:"every customer page"},
  {id:"trial-words",rule:String(retiredAccessWords),decided:"2026-09-23",applies_to:"every customer page"},
  {id:"invitation-and-status-words",rule:String(invitationWords),decided:"2026-09-23",applies_to:"every customer page and served file"},
  {id:"unpublished-terms",rule:String(unpublishedTerms),decided:"2026-09-23",applies_to:"every customer page"},
  {id:"status-tags",rule:String(cardStatusWords),decided:"2026-09-23",applies_to:"cards and badges"},
  {id:"retired-phrases",rule:JSON.stringify(retiredPhrases),decided:"2026-09-24",applies_to:"the rendered words of every page"}];
