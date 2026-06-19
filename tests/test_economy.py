"""Tests for the Bertrand-logit economy and equilibrium solvers (CLAUDE.md §3).

The hard correctness anchor is the canonical n=2 instance
(a_i = 2, a0 = 0, c_i = 1, mu = 0.25), whose textbook benchmarks are
p^N ~= 1.4729 and p^M ~= 1.9249. Per CLAUDE.md §3 the build does not proceed past
Milestone 2 until these match to 1e-3.
"""

import numpy as np
import pytest

from tacit.benchmark.economy import bertrand_logit as bl

# Canonical n=2 instance and its textbook benchmark prices.
CANON_A = [2.0, 2.0]
CANON_A0 = 0.0
CANON_C = [1.0, 1.0]
CANON_MU = 0.25
CANON_PN = 1.4729
CANON_PM = 1.9249


# --------------------------------------------------------------------------- #
# logit_shares                                                                 #
# --------------------------------------------------------------------------- #
def test_logit_shares_matches_hand_computation():
    """Shares for a simple symmetric case match the closed-form value."""
    shares = bl.logit_shares([1.5, 1.5], [2.0, 2.0], 0.0, 0.25)
    # util = (2 - 1.5)/0.25 = 2 each; outside util 0.
    # s = exp(2) / (2 exp(2) + exp(0)) = 1 / (2 + exp(-2)).
    expected = 1.0 / (2.0 + np.exp(-2.0))
    assert np.allclose(shares, expected, atol=1e-12)


def test_logit_shares_are_interior_and_leave_room_for_outside_good():
    """Every share is in (0, 1) and firm shares sum to < 1 (outside good)."""
    shares = bl.logit_shares([1.4, 1.6, 1.5], [1.9, 2.0, 2.1], 0.0, 0.3)
    assert np.all(shares > 0.0)
    assert np.all(shares < 1.0)
    assert shares.sum() < 1.0


def test_logit_shares_stable_for_large_utilities():
    """Max-subtraction keeps shares finite even when raw exponents would overflow."""
    # (a - p)/mu ~ 2000 here; a naive exp() would overflow to inf.
    shares = bl.logit_shares([0.0, 0.0], [1.0, 1.0], 0.0, 1e-3)
    assert np.all(np.isfinite(shares))
    assert np.allclose(shares, 0.5, atol=1e-6)  # outside good is negligible


def test_logit_shares_rejects_nonpositive_mu():
    with pytest.raises(ValueError, match="mu must be positive"):
        bl.logit_shares([1.5, 1.5], [2.0, 2.0], 0.0, 0.0)


def test_logit_shares_rejects_shape_mismatch():
    with pytest.raises(ValueError, match="same shape"):
        bl.logit_shares([1.5, 1.5, 1.5], [2.0, 2.0], 0.0, 0.25)


# --------------------------------------------------------------------------- #
# profits                                                                      #
# --------------------------------------------------------------------------- #
def test_profits_formula():
    """pi_i = (p_i - c_i) * s_i, elementwise."""
    result = bl.profits([1.5, 2.0], [0.4, 0.25], [1.0, 1.2])
    assert np.allclose(result, [(1.5 - 1.0) * 0.4, (2.0 - 1.2) * 0.25])


# --------------------------------------------------------------------------- #
# Canonical n=2 anchor — the Milestone 2 gate                                  #
# --------------------------------------------------------------------------- #
def test_nash_canonical_n2():
    """p^N reproduces the textbook 1.4729 (CLAUDE.md §3)."""
    p_nash = bl.nash_prices(CANON_A, CANON_A0, CANON_C, CANON_MU)
    assert np.allclose(p_nash, CANON_PN, atol=1e-3)


def test_monopoly_canonical_n2():
    """p^M reproduces the textbook 1.9249 (CLAUDE.md §3)."""
    p_mono = bl.monopoly_prices(CANON_A, CANON_A0, CANON_C, CANON_MU)
    assert np.allclose(p_mono, CANON_PM, atol=1e-3)


def test_monopoly_strictly_above_nash_n2():
    """Collusive prices exceed competitive prices elementwise."""
    p_nash = bl.nash_prices(CANON_A, CANON_A0, CANON_C, CANON_MU)
    p_mono = bl.monopoly_prices(CANON_A, CANON_A0, CANON_C, CANON_MU)
    assert np.all(p_mono > p_nash)


# --------------------------------------------------------------------------- #
# First-order conditions — internal consistency of the solvers                #
# --------------------------------------------------------------------------- #
def test_nash_satisfies_its_markup_foc():
    """At p^N, the residual of p_i - c_i = mu/(1 - s_i) is ~0."""
    a = np.array([1.9, 2.0, 2.1])
    c = np.array([0.9, 1.0, 1.1])
    mu, a0 = 0.30, 0.0
    p_nash = bl.nash_prices(a, a0, c, mu)
    shares = bl.logit_shares(p_nash, a, a0, mu)
    residual = (p_nash - c) - mu / (1.0 - shares)
    assert np.allclose(residual, 0.0, atol=1e-9)


def test_monopoly_satisfies_its_markup_foc():
    """At p^M, the residual of the joint-profit markup system is ~0."""
    a = np.array([1.9, 2.0, 2.1])
    c = np.array([0.9, 1.0, 1.1])
    mu, a0 = 0.30, 0.0
    p_mono = bl.monopoly_prices(a, a0, c, mu)
    shares = bl.logit_shares(p_mono, a, a0, mu)
    margins = p_mono - c
    rivals_term = float(np.dot(margins, shares)) - margins * shares
    residual = margins - (mu + rivals_term) / (1.0 - shares)
    assert np.allclose(residual, 0.0, atol=1e-9)


# --------------------------------------------------------------------------- #
# Interior solutions and economic sanity for asymmetric n=3                    #
# --------------------------------------------------------------------------- #
def test_asymmetric_n3_is_interior_with_collusive_premium():
    """Asymmetric n=3 yields interior shares and p^M > p^N everywhere."""
    a = np.array([1.85, 2.05, 2.2])
    c = np.array([0.85, 1.0, 1.15])
    mu, a0 = 0.22, 0.0
    p_nash = bl.nash_prices(a, a0, c, mu)
    p_mono = bl.monopoly_prices(a, a0, c, mu)
    for prices in (p_nash, p_mono):
        shares = bl.logit_shares(prices, a, a0, mu)
        assert np.all(shares > 0.0) and np.all(shares < 1.0)
        assert shares.sum() < 1.0
    assert np.all(p_mono > p_nash)


def test_monopoly_earns_at_least_nash_joint_profit():
    """Joint-profit prices weakly dominate Nash on total profit (they maximise it)."""
    a = np.array([1.9, 2.0, 2.1])
    c = np.array([0.9, 1.0, 1.1])
    mu, a0 = 0.30, 0.0
    p_nash = bl.nash_prices(a, a0, c, mu)
    p_mono = bl.monopoly_prices(a, a0, c, mu)
    joint_nash = bl.profits(p_nash, bl.logit_shares(p_nash, a, a0, mu), c).sum()
    joint_mono = bl.profits(p_mono, bl.logit_shares(p_mono, a, a0, mu), c).sum()
    assert joint_mono > joint_nash


# --------------------------------------------------------------------------- #
# Determinism                                                                  #
# --------------------------------------------------------------------------- #
def test_solvers_are_deterministic():
    """Identical inputs yield bit-for-bit identical solver outputs."""
    p1 = bl.nash_prices(CANON_A, CANON_A0, CANON_C, CANON_MU)
    p2 = bl.nash_prices(CANON_A, CANON_A0, CANON_C, CANON_MU)
    assert np.array_equal(p1, p2)
    m1 = bl.monopoly_prices(CANON_A, CANON_A0, CANON_C, CANON_MU)
    m2 = bl.monopoly_prices(CANON_A, CANON_A0, CANON_C, CANON_MU)
    assert np.array_equal(m1, m2)
