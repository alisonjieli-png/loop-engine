"""Run the five local deterministic campaign cases and print the summary."""

import json
import tempfile

from loop_engine.code_nodes.campaign_runner import (
    CampaignRunOptions,
    CampaignRunner,
    default_campaign_spec,
)


def main():
    spec = default_campaign_spec(
        modes=("deterministic",),
        providers=(),
        campaign_id="example-five-utility-problems",
    )
    with tempfile.TemporaryDirectory(
            prefix="loop-engine-five-problems-") as runs_dir:
        options = CampaignRunOptions(runs_dir=runs_dir, watch=True)
        result = CampaignRunner(spec, options).run()
        print(json.dumps(result.to_dict(), indent=1))


if __name__ == "__main__":
    main()
