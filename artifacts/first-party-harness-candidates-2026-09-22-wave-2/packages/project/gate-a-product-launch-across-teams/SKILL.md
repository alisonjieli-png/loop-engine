---
name: gate-a-product-launch-across-teams
description: Build a cross-team launch gate map covering the actual customer journey, communications, billing, support, and fallback before a public announcement.
---

# Gate a product launch across teams

## Use case

Use when a product launch depends on more than a successful code deployment. Produce a read-only go, hold, or limited-scope recommendation for the authorized launch owner.

## Required inputs

- The intended launch audience, offer, start time, and exact customer action the announcement invites.
- Current versioned evidence for product access, account creation, payment if applicable, onboarding, support, documentation, and communication channels.
- Named owners, acceptance checks, hold thresholds, and fallback or rollback options supplied by the team.

## Procedure

1. Write the customer journey from seeing the offer through completing the promised action. Identify the exact environment, account type, and release needed at each point.
2. List gates for product capability, access, payment, documentation, support response, customer communication, and monitoring or fallback where relevant. Do not equate a green deployment with a usable journey.
3. For each gate, record its owner, current evidence, last checked time, target audience, pass condition, and any known failure. Mark an absent owner or unchecked gate as unresolved.
4. Order dependencies: for example, a public invitation cannot precede a working invitation path. Record a permitted limited-scope alternative only if the supplied authority and evidence support it.
5. Walk the main journey and one failure journey using existing observations. State whether the owner can launch, must hold, or can launch only to a narrower audience under the supplied rules.
6. Return the gate map, exact evidence references, unresolved blockers, customer-facing claim risks, and the next check each owner must provide.

## Completion check

Every customer-facing action in the launch has current evidence and a responsible owner, and the recommendation follows the supplied pass and hold rules. A site that describes signup while signup is disabled fails its access gate.

## Stop or hold

Hold an unqualified audience or promise when any required gate is unresolved. Do not deploy, open registration, charge a card, send announcements, publish terms, or override a launch owner's decision.
