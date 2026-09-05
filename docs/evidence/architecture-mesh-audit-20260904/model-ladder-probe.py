"""Offline counterexample to the model ladder's sample-sufficiency wording."""
import json
from types import SimpleNamespace

from loop_engine.core.model_demand import ladder_from_observations

rows = [SimpleNamespace(model_route="cheap", helped=True)]
rows.extend(SimpleNamespace(model_route="strong", helped=None) for _ in range(11))
ladder = ladder_from_observations(rows, cost_order=("cheap", "strong"))
print(json.dumps({
    "provider_calls": 0,
    "observations": len(rows),
    "known_outcomes": 1,
    "proven_property": ladder.proven,
    "ladder": ladder.to_dict(),
    "scope": "Bootstrap evidence sufficiency only; no live model, routing or quality claim.",
}, indent=2))
