"""Split the Spaceship Titanic training file by travel group into a visible part and a held-out part.

Passengers who share the first four characters of PassengerId travel as one
group and are correlated, so whole groups are held out: 20 percent of the
groups, drawn with a fixed seed. The held-out labels go to the hidden folder,
which is never mounted in the harness sandbox. No competition data is copied
into the repository; only counts and digests are recorded.

Usage: python -I split_spaceship.py TRAIN.csv PROJECT_DATA_DIR HIDDEN_DIR SEED
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def split(train, seed):
    groups = train["PassengerId"].str.split("_").str[0]
    unique_groups = np.array(sorted(groups.unique()))
    rng = np.random.default_rng(seed)
    held = set(rng.choice(unique_groups, size=int(round(0.2 * len(unique_groups))), replace=False))
    mask = groups.isin(held)
    return train[~mask].reset_index(drop=True), train[mask].reset_index(drop=True), len(unique_groups), len(held)


def main():
    train_file, data_dir, hidden_dir, seed = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4])
    train = pd.read_csv(train_file, dtype=str, keep_default_na=False)
    visible, held, group_count, held_groups = split(train, seed)
    visible.to_csv(data_dir / "train.csv", index=False)
    held.drop(columns=["Transported"]).to_csv(data_dir / "test.csv", index=False)
    held[["PassengerId", "Transported"]].to_csv(hidden_dir / "holdout_labels.csv", index=False)
    summary = {
        "record_type": "comparison_pilot_spaceship_split/v1", "seed": seed, "method": "20 percent of travel groups",
        "rows_total": len(train), "rows_visible": len(visible), "rows_held_out": len(held),
        "groups_total": group_count, "groups_held_out": held_groups,
        "held_out_ids_sha256": hashlib.sha256("\n".join(sorted(held["PassengerId"])).encode()).hexdigest(),
        "visible_ids_sha256": hashlib.sha256("\n".join(sorted(visible["PassengerId"])).encode()).hexdigest(),
        "held_out_true_rate": round(float((held["Transported"] == "True").mean()), 4),
    }
    (hidden_dir / "split.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
