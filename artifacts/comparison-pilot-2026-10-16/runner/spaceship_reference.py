"""Reference solution and control predictions for the Spaceship Titanic pilot task.

Without arguments it behaves like the solution.py the task asks for: it reads
data/train.csv and data/test.csv and writes predictions.csv. With --mode it
writes one of the declared control predictions instead. It never reads the
held-out labels. Only pandas, numpy and scikit-learn are used.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SEED = 20261016
SPEND = ["RoomService", "FoodCourt", "ShoppingMall", "Spa", "VRDeck"]
BOOLEAN = {True: 1, False: 0, "True": 1, "False": 0}


def engineered(frame):
    out = pd.DataFrame(index=frame.index)
    for column in SPEND:
        out[column] = frame[column].fillna(0.0)
    out["TotalSpend"] = out[SPEND].sum(axis=1)
    out["Age"] = frame["Age"].fillna(frame["Age"].median())
    out["CryoSleep"] = frame["CryoSleep"].map(BOOLEAN).fillna(-1)
    out["VIP"] = frame["VIP"].map(BOOLEAN).fillna(-1)
    cabin = frame["Cabin"].fillna("U/-1/U").str.split("/", expand=True)
    out["Deck"] = cabin[0].astype("category").cat.codes
    out["CabinNum"] = pd.to_numeric(cabin[1], errors="coerce").fillna(-1)
    out["Side"] = (cabin[2] == "S").astype(int)
    out["HomePlanet"] = frame["HomePlanet"].fillna("U").astype("category").cat.codes
    out["Destination"] = frame["Destination"].fillna("U").astype("category").cat.codes
    group = frame["PassengerId"].str.split("_").str[0]
    out["GroupSize"] = group.map(group.value_counts())
    return out


def plain(frame):
    out = pd.DataFrame(index=frame.index)
    for column in ["Age"] + SPEND:
        out[column] = frame[column].fillna(0.0)
    out["CryoSleep"] = frame["CryoSleep"].map(BOOLEAN).fillna(0)
    return out


def reference(train, test):
    both = pd.concat([train.drop(columns=["Transported"]), test], ignore_index=True)
    features = engineered(both)
    model = HistGradientBoostingClassifier(random_state=SEED, max_iter=300, learning_rate=0.05)
    model.fit(features.iloc[: len(train)], train["Transported"].astype(bool))
    return model.predict(features.iloc[len(train):]).astype(bool)


def write(path, ids, values, words=("True", "False")):
    pd.DataFrame({"PassengerId": ids, "Transported": [words[0] if value else words[1] for value in values]}) \
        .to_csv(path, index=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="reference",
                        choices=["reference", "all_true", "cryosleep", "logistic", "shuffled", "missing_rows",
                                 "yes_no"])
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path, default=Path("predictions.csv"))
    args = parser.parse_args()
    train = pd.read_csv(args.data / "train.csv")
    test = pd.read_csv(args.data / "test.csv")
    ids = test["PassengerId"]
    if args.mode == "all_true":
        write(args.output, ids, [True] * len(test))
    elif args.mode == "cryosleep":
        write(args.output, ids, test["CryoSleep"].map(BOOLEAN).fillna(0).astype(bool))
    elif args.mode == "logistic":
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
        model.fit(plain(train), train["Transported"].astype(bool))
        write(args.output, ids, model.predict(plain(test)))
    else:
        values = reference(train, test)
        if args.mode == "shuffled":
            values = np.random.default_rng(SEED).permutation(values)
        if args.mode == "missing_rows":
            ids, values = ids.iloc[10:], values[10:]
        write(args.output, ids, values, words=("yes", "no") if args.mode == "yes_no" else ("True", "False"))


if __name__ == "__main__":
    main()
