"""Bertrand-logit demand model and equilibrium solvers (CLAUDE.md §3).

The economy is the Calvano-Calzolari-Denicolo-Pastorello (2020) differentiated-
products logit model, the standard specification in the algorithmic-collusion
literature. ``n`` firms each post a price ``p_i`` for one product; there is an
outside good (good 0). Per-firm parameters are quality ``a_i`` and marginal cost
``c_i``; market-wide parameters are the outside-good index ``a0`` and the
horizontal-differentiation index ``mu`` (larger ``mu`` -> more differentiation /
market power).

Demand (logit choice probabilities, used as quantities with market size 1)::

    s_i = exp((a_i - p_i) / mu)
          / ( sum_j exp((a_j - p_j) / mu) + exp(a0 / mu) )

Profit: ``pi_i = (p_i - c_i) * s_i``.

Two price benchmarks are solved as fixed points of their markup equations:

* **Bertrand-Nash** (one-shot, each firm maximises own profit)::

      p_i - c_i = mu / (1 - s_i)

* **Joint-profit / monopoly** (a single agent sets all prices)::

      p_i - c_i = ( mu + sum_{j != i} (p_j - c_j) * s_j ) / (1 - s_i)

For the canonical ``n = 2`` parameters ``a_i = 2, a0 = 0, c_i = 1, mu = 0.25`` the
solvers reproduce the textbook values ``p^N ~= 1.4729`` and ``p^M ~= 1.9249``.

Both markup equations are contractions for interior logit instances, so plain
fixed-point iteration converges; this keeps the solvers dependency-light and fully
deterministic (CLAUDE.md §3 lists fixed-point iteration as the first option). A
``scipy.optimize.fsolve`` fallback can be added later if a generated instance ever
fails to converge.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]

__all__ = [
    "ConvergenceError",
    "logit_shares",
    "monopoly_prices",
    "nash_prices",
    "profits",
]


class ConvergenceError(RuntimeError):
    """Raised when a fixed-point price solver fails to converge within ``max_iter``."""


def _as_float_array(x: npt.ArrayLike) -> FloatArray:
    """Return ``x`` as a 1-D float64 array (a defensive copy of array-like input)."""
    arr: FloatArray = np.asarray(x, dtype=np.float64)
    return arr


def logit_shares(
    prices: npt.ArrayLike,
    a: npt.ArrayLike,
    a0: float,
    mu: float,
) -> FloatArray:
    """Compute logit choice probabilities (market shares) for each firm.

    Uses the standard max-subtraction trick for numerical stability so that large
    utilities do not overflow ``exp``.

    Args:
        prices: Posted prices ``p_i``, shape ``(n,)``.
        a: Per-firm quality indices ``a_i``, shape ``(n,)``.
        a0: Outside-good index ``a0``.
        mu: Horizontal-differentiation index ``mu`` (must be positive).

    Returns:
        Firm shares ``s_i``, shape ``(n,)``. Each lies strictly in ``(0, 1)`` and the
        firm shares sum to ``< 1`` because the outside good absorbs the remainder.

    Raises:
        ValueError: If ``mu <= 0`` or ``prices`` and ``a`` have mismatched shapes.
    """
    if mu <= 0.0:
        raise ValueError(f"mu must be positive, got {mu!r}")
    prices_arr = _as_float_array(prices)
    a_arr = _as_float_array(a)
    if prices_arr.shape != a_arr.shape:
        raise ValueError(
            f"prices and a must have the same shape, got {prices_arr.shape} and {a_arr.shape}"
        )

    util_firms = (a_arr - prices_arr) / mu
    util_outside = a0 / mu
    shift = max(float(util_firms.max(initial=util_outside)), util_outside)
    exp_firms = np.exp(util_firms - shift)
    exp_outside = float(np.exp(util_outside - shift))
    denom = float(exp_firms.sum()) + exp_outside
    shares: FloatArray = exp_firms / denom
    return shares


def profits(
    prices: npt.ArrayLike,
    shares: npt.ArrayLike,
    costs: npt.ArrayLike,
) -> FloatArray:
    """Compute per-firm profit ``pi_i = (p_i - c_i) * s_i``.

    Args:
        prices: Posted prices ``p_i``, shape ``(n,)``.
        shares: Market shares ``s_i``, shape ``(n,)`` (e.g. from :func:`logit_shares`).
        costs: Marginal costs ``c_i``, shape ``(n,)``.

    Returns:
        Per-firm profits, shape ``(n,)``.
    """
    prices_arr = _as_float_array(prices)
    shares_arr = _as_float_array(shares)
    costs_arr = _as_float_array(costs)
    result: FloatArray = (prices_arr - costs_arr) * shares_arr
    return result


def nash_prices(
    a: npt.ArrayLike,
    a0: float,
    c: npt.ArrayLike,
    mu: float,
    *,
    tol: float = 1e-12,
    max_iter: int = 10_000,
) -> FloatArray:
    """Solve the one-shot Bertrand-Nash prices ``p^N`` by fixed-point iteration.

    Iterates the markup equation ``p_i = c_i + mu / (1 - s_i(p))`` until the price
    update is below ``tol``.

    Args:
        a: Per-firm quality indices ``a_i``, shape ``(n,)``.
        a0: Outside-good index ``a0``.
        c: Per-firm marginal costs ``c_i``, shape ``(n,)``.
        mu: Horizontal-differentiation index ``mu`` (must be positive).
        tol: Convergence tolerance on the max absolute price change.
        max_iter: Maximum number of iterations before giving up.

    Returns:
        The Nash price vector ``p^N``, shape ``(n,)``.

    Raises:
        ValueError: If ``mu <= 0`` or ``a`` and ``c`` have mismatched shapes.
        ConvergenceError: If the iteration does not converge within ``max_iter``.
    """
    a_arr, c_arr = _validate_market(a, c, mu)
    prices = c_arr + mu
    for _ in range(max_iter):
        shares = logit_shares(prices, a_arr, a0, mu)
        prices_next = c_arr + mu / (1.0 - shares)
        if float(np.max(np.abs(prices_next - prices))) < tol:
            return prices_next
        prices = prices_next
    raise ConvergenceError(f"nash_prices did not converge within {max_iter} iterations")


def monopoly_prices(
    a: npt.ArrayLike,
    a0: float,
    c: npt.ArrayLike,
    mu: float,
    *,
    tol: float = 1e-12,
    max_iter: int = 10_000,
) -> FloatArray:
    """Solve the joint-profit (cartel/monopoly) prices ``p^M`` by fixed-point iteration.

    A single agent sets all prices to maximise total profit. Iterates the markup
    system ``p_i = c_i + (mu + sum_{j!=i} (p_j - c_j) s_j) / (1 - s_i)`` until the
    price update is below ``tol``. The solution satisfies ``p^M > p^N`` elementwise.

    Args:
        a: Per-firm quality indices ``a_i``, shape ``(n,)``.
        a0: Outside-good index ``a0``.
        c: Per-firm marginal costs ``c_i``, shape ``(n,)``.
        mu: Horizontal-differentiation index ``mu`` (must be positive).
        tol: Convergence tolerance on the max absolute price change.
        max_iter: Maximum number of iterations before giving up.

    Returns:
        The monopoly price vector ``p^M``, shape ``(n,)``.

    Raises:
        ValueError: If ``mu <= 0`` or ``a`` and ``c`` have mismatched shapes.
        ConvergenceError: If the iteration does not converge within ``max_iter``.
    """
    a_arr, c_arr = _validate_market(a, c, mu)
    prices = c_arr + mu
    for _ in range(max_iter):
        shares = logit_shares(prices, a_arr, a0, mu)
        margins = prices - c_arr
        total_margin_share = float(np.dot(margins, shares))  # sum_j (p_j - c_j) s_j
        # Per firm: sum over rivals only = total minus own term.
        rivals_term = total_margin_share - margins * shares
        prices_next = c_arr + (mu + rivals_term) / (1.0 - shares)
        if float(np.max(np.abs(prices_next - prices))) < tol:
            return prices_next
        prices = prices_next
    raise ConvergenceError(f"monopoly_prices did not converge within {max_iter} iterations")


def _validate_market(
    a: npt.ArrayLike,
    c: npt.ArrayLike,
    mu: float,
) -> tuple[FloatArray, FloatArray]:
    """Validate solver inputs and return ``(a, c)`` as float arrays.

    Raises:
        ValueError: If ``mu <= 0`` or ``a`` and ``c`` have mismatched shapes.
    """
    if mu <= 0.0:
        raise ValueError(f"mu must be positive, got {mu!r}")
    a_arr = _as_float_array(a)
    c_arr = _as_float_array(c)
    if a_arr.shape != c_arr.shape:
        raise ValueError(f"a and c must have the same shape, got {a_arr.shape} and {c_arr.shape}")
    return a_arr, c_arr
