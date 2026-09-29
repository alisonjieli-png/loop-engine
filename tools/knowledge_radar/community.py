"""Community research drafts and reply leads, using the existing effect edge.

This module does not contact a platform, approve an effect or create a second
queue. Callers store drafts and outcomes through RecordOperationService and
dispatch exact effects through the existing approval and transport services.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from loop_engine.loop.effect_approval import ApprovalRequest, EffectClass, EffectSpec

REGISTRY = json.loads(Path(__file__).with_name("community-sources-v1.json").read_text())
if REGISTRY.get("record_type") != "community_research_registry/v1":
    raise ValueError("unsupported community registry")
SEED_COMMUNITIES = tuple(REGISTRY["communities"])
QUESTIONS = tuple(REGISTRY["questions"])


def _text(value, maximum):
    if type(value) is not str or not value.strip() or len(value) > maximum or "\x00" in value:
        raise ValueError("bounded nonempty text required")
    return value


def _url(value):
    parts = urlsplit(_text(value, 2048))
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise ValueError("public HTTPS source link required")
    return value


def draft(community, topic):
    """A disclosed, focused research question. No account or posting grant."""
    if community not in SEED_COMMUNITIES:
        raise ValueError("community needs a deliberate source-registry entry")
    topic = _text(topic, 180)
    body = (f"I'm researching {topic} for Baltor, a reusable component library for coding agents. "
            "I'd like to understand real workflows rather than collect showcase claims. "
            "Please share only material you are comfortable making public.\n\n" +
            "\n".join(f"{number}. {question}" for number, question in enumerate(QUESTIONS, 1)) +
            "\n\nA short answer to whichever questions matter is welcome. "
            "A reply does not grant permission to redistribute your code or assets. "
            "We would check that separately before including them in a library.")
    return {"record_type": "community_research_draft/v1", "target": _url(REGISTRY["communities"][community]),
            "title": f"Which {topic} workflows have you repeatedly used successfully?",
            "body": body, "state": "draft", "public_post_id": None, "grants_authority": False}


def approval_request(value, *, account_id, loop_id, rules_evidence, platform_access_evidence):
    """Bind an exact draft, account and rules evidence to the existing approval request.

    Evidence references are host-reviewed records, not self-approval by text.
    A sender still needs approval, effect consumption and outcome reconciliation.
    """
    if (type(value) is not dict or set(value) != {
            "record_type", "target", "title", "body", "state", "public_post_id", "grants_authority"}
            or value["record_type"] != "community_research_draft/v1" or value["state"] != "draft"
            or value["public_post_id"] is not None or value["grants_authority"] is not False):
        raise ValueError("unpublished draft required")
    targets = set(REGISTRY["communities"].values())
    if value["target"] not in targets:
        raise ValueError("target not in research registry")
    parameters = {"account_id": _text(account_id, 160), "title": _text(value["title"], 300),
                  "body": _text(value["body"], 12000), "rules_evidence": _text(rules_evidence, 512),
                  "platform_access_evidence": _text(platform_access_evidence, 512)}
    identity = hashlib.sha256(json.dumps({"target": value["target"], **parameters},
                                       sort_keys=True).encode()).hexdigest()
    parameters["operation_identity"] = identity
    effect = EffectSpec(EffectClass.EXTERNAL_MESSAGE, "publish_research_question", value["target"],
                        tuple(sorted(parameters.items())))
    return ApprovalRequest.create(loop_id, effect, "Review the exact account, community, text and posting rules.",
                                  requested_by="community_research")


def lead(*, source_url, observation_date, summary, primary_urls=()):
    """Original research notes and links, never copied replies or executable instructions."""
    from datetime import date
    date.fromisoformat(observation_date)
    source_url = _url(source_url)
    if len(primary_urls) > 20:
        raise ValueError("at most twenty primary source leads")
    return {"record_type": "community_research_lead/v1", "source_url": source_url,
            "observed_on": observation_date, "summary": _text(summary, 3000),
            "primary_urls": [_url(value) for value in primary_urls], "evidence_class": "creator_report",
            "consideration": "unreviewed", "reproduced": False, "reuse_rights": "not_established",
            "component_approved": False, "executable_authority": False}
