"""STEP 3 — Assess whether the decision is supported; prepare more if not.

CONTRACT   PractitionerState + Situation  ->  DecisionSupportPortfolio
REQUIRED   no (optional; kernel default = sufficient_no_expansion, never forces
           a model/research call)
WAYS       sufficient_no_expansion · retrieve reusable resources ·
           generate provisional resources · spawn a Practitioner Loop for research
EXTEND     provide an `assess_prepare` impl; register question/persona
           generators and research recipes.

Generated questions/perspectives are REASONING RESOURCES (provisional) — never
silently promoted to accepted evidence.
"""
from ...loop.kernel import DecisionSupportPortfolio, default_assess_prepare
from ...code_nodes.enrichment import (EnrichmentPolicy, coverage_probe, generate_enrichment)
from ...strings.question_engine import core_forms, multiply, QuestionForm
from ...strings.question_bank import QuestionBank, QuestionDefinition, QuestionPattern
from ...loop.spawned_practitioner import spawn_practitioner_loop

__all__ = ["DecisionSupportPortfolio", "default_assess_prepare",
           "EnrichmentPolicy", "coverage_probe", "generate_enrichment",
           "core_forms", "multiply", "QuestionForm", "QuestionBank",
           "QuestionDefinition", "QuestionPattern", "spawn_practitioner_loop"]
