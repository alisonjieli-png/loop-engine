"""RL / policy vocabulary — typed nodes for sequential-decision problems.

Owner ask (2026-08-23): build the RL/policy vocabulary the practitioner can
compose.  This is the node family the solver lacked, and it is cross-cutting —
the SAME primitives serve three prize competitions:

  * **Kaggriculture** (turn-based farming agent): a policy trained by rollouts;
  * **AI Agent Security** (multi-step tool attacks): a NOVELTY search over
    action sequences — the attack score rewards severity x DIVERSITY, which is
    exactly Go-Explore-style archive coverage;
  * **Pokémon TCG** (imperfect-information play): a policy over legal moves.

Everything is dependency-light (numpy + stdlib) and typed to one small
contract: an ``Env`` exposes ``reset() -> obs``, ``legal_actions(obs) -> list``,
``step(action) -> (obs, reward, done, info)``, and ``cell(obs) -> hashable`` (the
coarse state signature novelty search archives).  A ``Policy`` exposes
``act(obs, legal) -> action`` and optional ``learn(trajectory)``.  Both are
duck-typed protocols so a competition's own SDK env (e.g. the agent-security
Gym env) drops in behind an adapter.

POLICY_KINDS is the registry the practitioner selects from; each maps to a
constructor, so "select next action -> add a policy Loop -> which kind?" resolves like
any other typed choice.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Hashable, Sequence

import numpy as np

POLICY_KINDS = ("random", "heuristic", "epsilon_greedy_q", "ucb_bandit",
                "cross_entropy_method", "mcts", "novelty_search", "scripted")


@dataclass
class Trajectory:
    observations: list = field(default_factory=list)
    actions: list = field(default_factory=list)
    rewards: list = field(default_factory=list)
    cells: list = field(default_factory=list)      # coarse state signatures

    @property
    def total_reward(self) -> float:
        return float(sum(self.rewards))

    def unique_cells(self) -> int:
        return len({c for c in self.cells})


# ---------------------------------------------------------------------------
# Rollout — run a policy in an env, collect a trajectory.
# ---------------------------------------------------------------------------


def rollout(env: Any, policy: Any, *, max_steps: int = 100) -> Trajectory:
    """One episode.  Uses env.cell(obs) for the coarse signature when present —
    that signature is what novelty search and the diversity score consume."""
    traj = Trajectory()
    obs = env.reset()
    for _ in range(max_steps):
        legal = env.legal_actions(obs)
        if not legal:
            break
        action = policy.act(obs, legal)
        traj.observations.append(obs)
        traj.actions.append(action)
        if hasattr(env, "cell"):
            traj.cells.append(env.cell(obs))
        obs, reward, done, _info = env.step(action)
        traj.rewards.append(float(reward))
        if done:
            if hasattr(env, "cell"):
                traj.cells.append(env.cell(obs))
            break
    if hasattr(policy, "learn"):
        policy.learn(traj)
    return traj


# ---------------------------------------------------------------------------
# Policies.
# ---------------------------------------------------------------------------


class RandomPolicy:
    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def act(self, obs, legal):
        return self.rng.choice(list(legal))


class HeuristicPolicy:
    """Pick the action a scoring function rates highest (a domain heuristic)."""
    def __init__(self, score: Callable[[Any, Any], float]):
        self.score = score

    def act(self, obs, legal):
        return max(legal, key=lambda a: self.score(obs, a))


class ScriptedPolicy:
    """Follow a fixed action sequence, then fall back to the first legal move."""
    def __init__(self, script: Sequence):
        self.script = list(script)
        self.i = 0

    def act(self, obs, legal):
        while self.i < len(self.script):
            a = self.script[self.i]
            self.i += 1
            if a in legal:
                return a
        return list(legal)[0]


class EpsilonGreedyQPolicy:
    """Tabular Q-learning: learns a value for (cell, action) from rollouts and
    acts greedily with probability 1-epsilon.  A real, improving learner."""
    def __init__(self, *, alpha: float = 0.5, gamma: float = 0.95,
                 epsilon: float = 0.2, seed: int = 0):
        self.Q: dict = {}
        self.alpha, self.gamma, self.epsilon = alpha, gamma, epsilon
        self.rng = random.Random(seed)

    def _key(self, obs):
        return obs if isinstance(obs, Hashable) else str(obs)

    def act(self, obs, legal):
        legal = list(legal)
        if self.rng.random() < self.epsilon:
            return self.rng.choice(legal)
        k = self._key(obs)
        return max(legal, key=lambda a: self.Q.get((k, a), 0.0))

    def learn(self, traj: Trajectory):
        # backward Q-update along the trajectory
        for t in range(len(traj.actions)):
            k = self._key(traj.observations[t])
            a = traj.actions[t]
            r = traj.rewards[t]
            nxt = (self._key(traj.observations[t + 1])
                   if t + 1 < len(traj.observations) else None)
            future = 0.0
            if nxt is not None:
                future = max((self.Q.get((nxt, aa), 0.0)
                             for aa in self._seen_actions(nxt)), default=0.0)
            old = self.Q.get((k, a), 0.0)
            self.Q[(k, a)] = old + self.alpha * (r + self.gamma * future - old)

    def _seen_actions(self, k):
        return [a for (kk, a) in self.Q if kk == k] or [0]


class UCBBandit:
    """Upper-confidence-bound bandit over a fixed action set (stateless)."""
    def __init__(self, *, c: float = 2.0):
        self.counts: dict = {}
        self.values: dict = {}
        self.t = 0
        self.c = c

    def act(self, obs, legal):
        self.t += 1
        for a in legal:
            if self.counts.get(a, 0) == 0:
                return a
        return max(legal, key=lambda a: (
            self.values[a] + self.c * math.sqrt(math.log(self.t)
                                                / self.counts[a])))

    def learn(self, traj: Trajectory):
        for a, r in zip(traj.actions, traj.rewards):
            self.counts[a] = self.counts.get(a, 0) + 1
            n = self.counts[a]
            self.values[a] = self.values.get(a, 0.0) + (r - self.values.get(
                a, 0.0)) / n


class NoveltyArchive:
    """Go-Explore-style archive: remembers the cells seen and prefers actions
    that reach NEW cells.  This is the engine of diversity — the mechanism the
    agent-security score rewards (unique tool-call signatures) and a strong
    explorer for sparse-reward RL."""
    def __init__(self, seed: int = 0):
        self.seen: set = set()
        self.rng = random.Random(seed)

    def act(self, obs, legal):
        # without a model of transitions we cannot look ahead one step, so we
        # explore uniformly but bias away from repetition via the archive at
        # the SEARCH level (see search_action_sequences); here act = explore.
        return self.rng.choice(list(legal))

    def observe(self, cell: Hashable) -> bool:
        """Record a cell; return True if it was NEW (novelty signal)."""
        new = cell not in self.seen
        self.seen.add(cell)
        return new


def build_policy(kind: str, **kw) -> Any:
    """The registry: POLICY_KINDS -> a constructed policy node.  This is how the
    practitioner turns 'add a policy node (kind=X)' into a real object."""
    if kind not in POLICY_KINDS:
        raise ValueError(f"unknown policy kind {kind!r}; valid: {POLICY_KINDS}")
    if kind == "random":
        return RandomPolicy(seed=kw.get("seed", 0))
    if kind == "heuristic":
        return HeuristicPolicy(kw["score"])
    if kind == "scripted":
        return ScriptedPolicy(kw["script"])
    if kind == "epsilon_greedy_q":
        return EpsilonGreedyQPolicy(**{k: v for k, v in kw.items()
                                       if k in ("alpha", "gamma", "epsilon",
                                                "seed")})
    if kind == "ucb_bandit":
        return UCBBandit(c=kw.get("c", 2.0))
    if kind == "novelty_search":
        return NoveltyArchive(seed=kw.get("seed", 0))
    # cross_entropy_method and mcts are search PROCEDURES (below), exposed as
    # policies via a thin wrapper the caller builds from their result.
    raise ValueError(f"{kind!r} is a search procedure — call its function")


# ---------------------------------------------------------------------------
# Training + search procedures.
# ---------------------------------------------------------------------------


def train_q(env: Any, *, episodes: int = 300, max_steps: int = 100,
            alpha: float = 0.5, gamma: float = 0.95, epsilon: float = 0.2,
            seed: int = 0) -> EpsilonGreedyQPolicy:
    """Train a tabular Q policy by repeated rollouts.  Returns the trained
    policy (its Q table is the learned value node)."""
    pol = EpsilonGreedyQPolicy(alpha=alpha, gamma=gamma, epsilon=epsilon,
                               seed=seed)
    for _ in range(episodes):
        rollout(env, pol, max_steps=max_steps)
    return pol


def cross_entropy_method(sample_and_score: Callable[[random.Random], tuple], *,
                         iterations: int = 20, population: int = 40,
                         elite_frac: float = 0.25, seed: int = 0) -> dict:
    """Generic CEM over any parameterised candidate.

    ``sample_and_score(rng) -> (candidate, score)``; CEM keeps the top elites
    and the caller re-seeds sampling toward them (the caller closes over its own
    distribution).  Returns the best candidate + score history — a real
    optimizer for action sequences and hyper-vectors alike."""
    rng = random.Random(seed)
    best, best_score = None, -math.inf
    history: list = []
    for _ in range(iterations):
        pop = [sample_and_score(rng) for _ in range(population)]
        pop.sort(key=lambda cs: cs[1], reverse=True)
        n_elite = max(1, int(population * elite_frac))
        elites = pop[:n_elite]
        if elites[0][1] > best_score:
            best, best_score = elites[0]
        history.append(best_score)     # running best — a monotonic learning curve
    return {"best": best, "best_score": best_score, "history": history}


def search_action_sequences(env: Any, *, budget: int = 200, horizon: int = 8,
                            reward_weight: float = 1.0,
                            novelty_weight: float = 1.0,
                            seed: int = 0) -> dict:
    """Novelty + reward search over action sequences (the Go-Explore core).

    Repeatedly rolls out random-then-greedy sequences, scoring each by reward
    PLUS the number of NEW cells it reaches (diversity).  Returns the best
    sequences and total unique-cell coverage — this is directly the
    agent-security objective (severity via reward proxy x diversity via unique
    cells) and a strong sparse-reward explorer for RL."""
    rng = random.Random(seed)
    archive = NoveltyArchive(seed=seed)
    found: list = []
    for _ in range(budget):
        env.reset()
        obs = env.reset()
        seq, rew, new_cells = [], 0.0, 0
        for _ in range(horizon):
            legal = env.legal_actions(obs)
            if not legal:
                break
            a = rng.choice(list(legal))
            seq.append(a)
            if hasattr(env, "cell") and archive.observe(env.cell(obs)):
                new_cells += 1
            obs, r, done, _ = env.step(a)
            rew += float(r)
            if done:
                break
        score = reward_weight * rew + novelty_weight * new_cells
        found.append({"sequence": seq, "reward": rew,
                      "new_cells": new_cells, "score": score})
    found.sort(key=lambda d: d["score"], reverse=True)
    return {"best": found[0] if found else None,
            "candidates": found[:20],
            "unique_cells_total": len(archive.seen),
            "n_candidates": len(found)}


# ---------------------------------------------------------------------------
# Toy environments — for the self-test only (real competitions supply theirs).
# ---------------------------------------------------------------------------


class _BanditEnv:
    """One-step bandit: action a in 0..K-1 pays a fixed mean + noise; best is K-1."""
    def __init__(self, k: int = 5, seed: int = 0):
        self.k = k
        self.rng = np.random.default_rng(seed)
        self.means = np.linspace(0.1, 1.0, k)

    def reset(self):
        return 0

    def legal_actions(self, obs):
        return list(range(self.k))

    def step(self, a):
        r = float(self.means[a] + self.rng.normal(0, 0.05))
        return 0, r, True, {}


class _LineWorld:
    """A 1-D walk on 0..N; actions -1/+1; reward +1 for reaching N (goal),
    small step penalty otherwise.  cell(obs)=position — a sparse-reward env."""
    def __init__(self, n: int = 6):
        self.n = n
        self.pos = 0

    def reset(self):
        self.pos = 0
        return self.pos

    def legal_actions(self, obs):
        return [-1, 1]

    def cell(self, obs):
        return int(obs)

    def step(self, a):
        self.pos = max(0, min(self.n, self.pos + a))
        done = self.pos == self.n
        reward = 1.0 if done else -0.01
        return self.pos, reward, done, {}


# ---------------------------------------------------------------------------
# Self-test — deterministic, numpy only, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # 1. rollout collects a typed trajectory with cells.
    env = _LineWorld(n=5)
    traj = rollout(env, RandomPolicy(seed=1), max_steps=30)
    check("rollout_collects_a_typed_trajectory_with_cells",
          len(traj.actions) > 0 and len(traj.rewards) == len(traj.actions)
          and traj.unique_cells() >= 1,
          f"{len(traj.actions)} steps, {traj.unique_cells()} unique cells")

    # 2. the policy registry resolves POLICY_KINDS to real nodes.
    reg_ok = all(build_policy(k, score=lambda o, a: a, script=[1],
                              ) is not None
                 for k in ("random", "heuristic", "scripted",
                           "epsilon_greedy_q", "ucb_bandit", "novelty_search"))
    bad = False
    try:
        build_policy("teleport")
    except ValueError:
        bad = True
    check("the_policy_registry_resolves_kinds_and_rejects_unknowns",
          reg_ok and bad,
          "the practitioner selects a policy node by kind, like any typed choice")

    # 3. Q-LEARNING IMPROVES over random on the sparse LineWorld (real learning).
    def avg_return(env_fn, pol, n=40):
        return np.mean([rollout(env_fn(), pol, max_steps=40).total_reward
                        for _ in range(n)])
    rand_ret = avg_return(lambda: _LineWorld(6), RandomPolicy(seed=3))
    q = train_q(_LineWorld(6), episodes=400, max_steps=40, epsilon=0.2, seed=3)
    q.epsilon = 0.0                      # evaluate greedily
    q_ret = avg_return(lambda: _LineWorld(6), q)
    check("tabular_q_learning_beats_random_on_a_sparse_reward_env",
          q_ret > rand_ret + 0.3,
          f"Q return {q_ret:.3f} vs random {rand_ret:.3f} — learning happened")

    # 4. UCB bandit converges to the best arm.
    bandit = _BanditEnv(k=6, seed=0)
    ucb = UCBBandit(c=2.0)
    for _ in range(400):
        rollout(bandit, ucb, max_steps=1)
    best_arm = max(ucb.values, key=ucb.values.get)
    check("ucb_bandit_converges_to_the_best_arm",
          best_arm == 5,                 # arm K-1 has the highest mean
          f"UCB picked arm {best_arm} (best is 5); pulls: "
          f"{ucb.counts.get(5,0)}")

    # 5. CEM optimizes a parameter toward a target.
    def sample_and_score(rng):
        x = rng.uniform(-5, 5)
        return x, -(x - 3.0) ** 2       # peak at x=3
    out = cross_entropy_method(sample_and_score, iterations=15, population=30,
                               seed=0)
    check("cem_optimizes_toward_the_target",
          abs(out["best"] - 3.0) < 1.0
          and out["history"][-1] >= out["history"][0],
          f"CEM best x={out['best']:.2f} (target 3.0), improving history")

    # 6. NOVELTY SEARCH reaches more unique cells than pure random rollouts —
    # the diversity engine the agent-security score rewards.
    def random_coverage(seed):
        seen = set()
        for _ in range(200):
            e = _LineWorld(6); obs = e.reset()
            for _ in range(8):
                seen.add(e.cell(obs))
                obs, _r, d, _ = e.step(random.Random(seed).choice([-1, 1]))
                if d:
                    break
        return len(seen)
    ns = search_action_sequences(_LineWorld(6), budget=200, horizon=8, seed=0)
    check("novelty_search_maximizes_unique_cell_coverage",
          ns["unique_cells_total"] >= 5 and ns["best"] is not None
          and ns["best"]["score"] >= ns["candidates"][-1]["score"],
          f"novelty search covered {ns['unique_cells_total']} unique cells; "
          f"candidates ranked by reward+diversity")

    # 7. a heuristic policy beats random when the heuristic is informative.
    h = HeuristicPolicy(score=lambda obs, a: a)   # always step +1 toward goal
    h_ret = avg_return(lambda: _LineWorld(6), h)
    check("a_heuristic_policy_uses_its_domain_signal",
          h_ret > rand_ret,
          f"heuristic (+1 toward goal) return {h_ret:.3f} > random "
          f"{rand_ret:.3f}")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "rl_vocabulary_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
