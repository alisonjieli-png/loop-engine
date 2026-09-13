"""Offline documentation example for candidate enumeration through Loop.

These labels describe proposed configurations, not installed resources or
execution authority. This example does not run the proposed task workflows,
call a provider, write candidates, or implement a general optimizer.
"""
from __future__ import annotations

from math import prod

from loop_engine.generation.model.campaign import GenerationCampaign
from loop_engine.generation.model.dimensions import ConditionalRule, VariationDimension
from loop_engine.generation.operators import generate_candidates


def example_campaign() -> GenerationCampaign:
    """Declare a small grid and one illustrative policy, without implicit limits."""
    return GenerationCampaign(
        campaign_id='documentation.flexible_configuration_grid',
        version='1.0.0',
        target_artifact_kind='config_patch',
        search_strategy='exact_enumeration',
        dimensions=(
            VariationDimension('planned_step_count', 'ordinal', values=(3, 7, 12)),
            VariationDimension('prompt_bundle', 'categorical',
                               values=('instructions_only', 'instructions_with_examples')),
            VariationDimension('intelligence_bundle', 'categorical',
                               values=('selected_context', 'selected_context_and_code')),
        ),
        conditional_rules=(
            ConditionalRule(
                'documentation.twelve_step_candidate_uses_examples',
                when={'planned_step_count': 12},
                require={'prompt_bundle': ('instructions_with_examples',)},
            ),
        ),
    )


def run_example() -> dict:
    """Return the actual enumeration result, not task-quality evidence."""
    campaign = example_campaign()
    raw_combinations = prod(len(dimension.expand()) for dimension in campaign.dimensions)
    result = generate_candidates(campaign)
    candidates = result['value']['candidates']
    return {
        'raw_combinations': raw_combinations,
        'returned_candidates': len(candidates),
        'excluded_by_example_rule': raw_combinations - len(candidates),
        'model_calls': result['model_calls'],
        'loop_id': result['loop_id'],
        'candidates': candidates,
        'task_configurations_executed': 0,
        'task_quality_claimed': False,
    }


def main() -> None:
    report = run_example()
    print(f"Raw combinations: {report['raw_combinations']}")
    print(f"Excluded by the example rule: {report['excluded_by_example_rule']}")
    print(f"Proposed configurations: {report['returned_candidates']}")
    print(f"Physical model calls: {report['model_calls']}")
    print('The proposed task configurations were not executed or promoted.')


if __name__ == '__main__':
    main()
