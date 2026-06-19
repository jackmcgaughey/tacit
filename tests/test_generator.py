"""Tests for the seeded E1 instance generator and split assignment (CLAUDE.md §3).

Covers the two requirements called out in the brief: determinism (same seed ->
same instance and same split, across processes) and interior solvability of every
generated instance (0 < s_i < 1 and p^M > p^N).
"""

import numpy as np
import pytest
from pydantic import ValidationError

from tacit.benchmark.economy import bertrand_logit as bl
from tacit.benchmark.generators.e1_generator import (
    A_RANGE,
    C_RANGE,
    MU_RANGE,
    E1Instance,
    assign_split,
    generate_e1_instance,
    generate_e1_instances,
    instance_shares,
)

# Regression lock for the split assignment: changing the hashing must be deliberate.
GOLDEN_SPLITS_0_TO_9 = [
    "heldout",
    "heldout",
    "dev",
    "heldout",
    "heldout",
    "dev",
    "dev",
    "heldout",
    "heldout",
    "heldout",
]
SWEEP_SEEDS = range(60)


# --------------------------------------------------------------------------- #
# Determinism                                                                  #
# --------------------------------------------------------------------------- #
def test_same_seed_yields_identical_instance():
    """Re-generating with the same seed reproduces the instance exactly."""
    assert generate_e1_instance(123) == generate_e1_instance(123)


def test_different_seeds_yield_different_parameters():
    """Distinct seeds (almost surely) produce distinct parameter draws."""
    assert generate_e1_instance(1).a != generate_e1_instance(2).a


# --------------------------------------------------------------------------- #
# Parameter draws and interior solvability                                     #
# --------------------------------------------------------------------------- #
def test_parameters_stay_in_declared_ranges():
    """Every generated parameter lies in its CLAUDE.md §3 range; a0 = 0, n = 3."""
    for seed in SWEEP_SEEDS:
        inst = generate_e1_instance(seed)
        assert inst.n_sellers == 3
        assert inst.a0 == 0.0
        assert all(A_RANGE[0] <= ai <= A_RANGE[1] for ai in inst.a)
        assert all(C_RANGE[0] <= ci <= C_RANGE[1] for ci in inst.c)
        assert MU_RANGE[0] <= inst.mu <= MU_RANGE[1]


def test_every_instance_is_interior_with_collusive_premium():
    """At both p^N and p^M shares are interior, and p^M > p^N everywhere."""
    for seed in SWEEP_SEEDS:
        inst = generate_e1_instance(seed)
        for prices in (inst.p_nash, inst.p_mono):
            shares = instance_shares(inst, list(prices))
            assert np.all(shares > 0.0) and np.all(shares < 1.0)
            assert shares.sum() < 1.0
        assert all(pm > pn for pm, pn in zip(inst.p_mono, inst.p_nash, strict=True))


def test_cached_benchmarks_match_a_fresh_solve():
    """The cached p^N/p^M equal a fresh solve of the same parameters."""
    inst = generate_e1_instance(7)
    p_nash = bl.nash_prices(inst.a, inst.a0, inst.c, inst.mu)
    p_mono = bl.monopoly_prices(inst.a, inst.a0, inst.c, inst.mu)
    assert np.allclose(inst.p_nash, p_nash)
    assert np.allclose(inst.p_mono, p_mono)


def test_n_sellers_override():
    """The generator honours a non-default firm count."""
    inst = generate_e1_instance(0, n_sellers=2)
    assert inst.n_sellers == 2
    assert len(inst.a) == len(inst.c) == len(inst.p_nash) == len(inst.p_mono) == 2


# --------------------------------------------------------------------------- #
# Split assignment                                                             #
# --------------------------------------------------------------------------- #
def test_split_is_deterministic():
    """The split depends only on the seed (and is stable across calls)."""
    assert all(assign_split(s) == assign_split(s) for s in SWEEP_SEEDS)


def test_split_matches_golden_values():
    """Locked regression values for seeds 0..9 (guards the hashing scheme)."""
    assert [assign_split(s) for s in range(10)] == GOLDEN_SPLITS_0_TO_9


def test_split_label_matches_assign_split():
    """An instance's split label equals assign_split of its seed."""
    for seed in SWEEP_SEEDS:
        assert generate_e1_instance(seed).split == assign_split(seed)


def test_split_distribution_is_roughly_balanced():
    """The default 0.5 fraction routes ~half of many seeds to heldout."""
    splits = [assign_split(s) for s in range(2000)]
    heldout_fraction = splits.count("heldout") / len(splits)
    assert 0.45 < heldout_fraction < 0.55


def test_split_fraction_extremes():
    """fraction=0 sends everything to dev; fraction=1 sends everything to heldout."""
    assert all(assign_split(s, 0.0) == "dev" for s in SWEEP_SEEDS)
    assert all(assign_split(s, 1.0) == "heldout" for s in SWEEP_SEEDS)


def test_assign_split_rejects_out_of_range_fraction():
    for bad in (-0.1, 1.5):
        with pytest.raises(ValueError, match="heldout_fraction"):
            assign_split(0, bad)


# --------------------------------------------------------------------------- #
# Batch generation                                                            #
# --------------------------------------------------------------------------- #
def test_generate_batch_preserves_order_and_count():
    instances = generate_e1_instances(range(10))
    assert len(instances) == 10
    assert [inst.instance_seed for inst in instances] == list(range(10))


def test_generate_batch_filters_by_split():
    """Filtering returns exactly the seeds assigned to that split."""
    heldout = generate_e1_instances(range(10), split="heldout")
    expected = [s for s in range(10) if GOLDEN_SPLITS_0_TO_9[s] == "heldout"]
    assert [inst.instance_seed for inst in heldout] == expected
    assert all(inst.split == "heldout" for inst in heldout)


# --------------------------------------------------------------------------- #
# E1Instance validation                                                        #
# --------------------------------------------------------------------------- #
def _valid_instance_kwargs() -> dict[str, object]:
    return {
        "instance_seed": 0,
        "split": "dev",
        "n_sellers": 2,
        "a": (2.0, 2.0),
        "a0": 0.0,
        "c": (1.0, 1.0),
        "mu": 0.25,
        "p_nash": (1.4, 1.4),
        "p_mono": (1.9, 1.9),
    }


def test_valid_instance_constructs():
    assert E1Instance(**_valid_instance_kwargs()).n_sellers == 2


def test_instance_rejects_length_mismatch():
    with pytest.raises(ValidationError, match="expected n_sellers"):
        E1Instance(**{**_valid_instance_kwargs(), "a": (2.0,)})


def test_instance_rejects_nonpositive_mu():
    with pytest.raises(ValidationError, match="mu must be positive"):
        E1Instance(**{**_valid_instance_kwargs(), "mu": 0.0})


def test_instance_rejects_missing_collusive_premium():
    with pytest.raises(ValidationError, match="p_mono > p_nash"):
        E1Instance(**{**_valid_instance_kwargs(), "p_mono": (1.0, 1.0)})


def test_instance_is_frozen():
    inst = generate_e1_instance(0)
    with pytest.raises(ValidationError):
        inst.mu = 0.3  # type: ignore[misc]
