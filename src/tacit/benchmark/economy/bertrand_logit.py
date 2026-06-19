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

Two price benchmarks are the interior roots of their markup equations:

* **Bertrand-Nash** (one-shot, each firm maximises own profit)::

      p_i - c_i = mu / (1 - s_i)

* **Joint-profit / monopoly** (a single agent sets all prices)::

      p_i - c_i = ( mu + sum_{j != i} (p_j - c_j) * s_j ) / (1 - s_i)

For the canonical ``n = 2`` parameters ``a_i = 2, a0 = 0, c_i = 1, mu = 0.25`` the
solvers reproduce the textbook values ``p^N ~= 1.4729`` and ``p^M ~= 1.9249``.

**Solver method.** Each benchmark is the unique interior root of its markup system,
found with ``scipy.optimize.fsolve`` (MINPACK ``hybrd``, a robust trust-region
Newton). CLAUDE.md §3 lists fixed-point iteration *or* ``fsolve``; we use ``fsolve``
because naive simultaneous (Jacobi) markup iteration limit-cycles on asymmetric
instances with a dominant firm (e.g. high quality / low cost), which the procedural
generator readily produces. ``fsolve`` is deterministic, so seeded reproducibility
is preserved. Each solution is validated (small residual, interior shares) and a
``ConvergenceError`` is raised otherwise.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import numpy.typing as npt
from scipy.optimize import fsolve

FloatArray = npt.NDArray[np.float64]

__all__ = [
    "ConvergenceError",
    "logit_shares",
    "monopoly_prices",
    "nash_prices",
    "profits",
]

# Default acceptance gate on the max absolute markup-equation residual at the
# returned solution. A converged fsolve leaves a residual of ~1e-9 or smaller for
# these smooth systems, whereas a failed solve (e.g. a limit cycle) leaves a
# residual of order 1; this loose bound cleanly separates success from failure
# while still implying price accuracy far tighter than anything the benchmark needs.
_RESIDUAL_TOL = 1e-6


class ConvergenceError(RuntimeError):
    """Raised when a price solver fails to find a valid interior root."""


def _as_float_array(x: npt.ArrayLike) -> FloatArray:
    """Return ``x`` as a float64 array (a defensive copy of array-like input)."""
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


def _nash_residual(
    prices: FloatArray, a: FloatArray, a0: float, c: FloatArray, mu: float
) -> FloatArray:
    """Residual of the Bertrand-Nash markup equation ``p_i - c_i - mu/(1 - s_i)``."""
    shares = logit_shares(prices, a, a0, mu)
    residual: FloatArray = (prices - c) - mu / (1.0 - shares)
    return residual


def _monopoly_residual(
    prices: FloatArray, a: FloatArray, a0: float, c: FloatArray, mu: float
) -> FloatArray:
    """Residual of the joint-profit markup system.

    ``p_i - c_i - (mu + sum_{j != i} (p_j - c_j) s_j) / (1 - s_i)``.
    """
    shares = logit_shares(prices, a, a0, mu)
    margins = prices - c
    rivals_term = float(np.dot(margins, shares)) - margins * shares
    residual: FloatArray = margins - (mu + rivals_term) / (1.0 - shares)
    return residual


def nash_prices(
    a: npt.ArrayLike,
    a0: float,
    c: npt.ArrayLike,
    mu: float,
    *,
    residual_tol: float = _RESIDUAL_TOL,
) -> FloatArray:
    """Solve the one-shot Bertrand-Nash prices ``p^N``.

    Args:
        a: Per-firm quality indices ``a_i``, shape ``(n,)``.
        a0: Outside-good index ``a0``.
        c: Per-firm marginal costs ``c_i``, shape ``(n,)``.
        mu: Horizontal-differentiation index ``mu`` (must be positive).
        residual_tol: Maximum tolerated markup-equation residual at the solution.

    Returns:
        The Nash price vector ``p^N``, shape ``(n,)``.

    Raises:
        ValueError: If ``mu <= 0`` or ``a`` and ``c`` have mismatched shapes.
        ConvergenceError: If no valid interior root is found.
    """
    a_arr, c_arr = _validate_market(a, c, mu)
    guess = c_arr + mu
    return _solve_markup(_nash_residual, guess, a_arr, a0, c_arr, mu, residual_tol, "nash_prices")


def monopoly_prices(
    a: npt.ArrayLike,
    a0: float,
    c: npt.ArrayLike,
    mu: float,
    *,
    residual_tol: float = _RESIDUAL_TOL,
) -> FloatArray:
    """Solve the joint-profit (cartel/monopoly) prices ``p^M``.

    A single agent sets all prices to maximise total profit. The solution satisfies
    ``p^M > p^N`` elementwise.

    Args:
        a: Per-firm quality indices ``a_i``, shape ``(n,)``.
        a0: Outside-good index ``a0``.
        c: Per-firm marginal costs ``c_i``, shape ``(n,)``.
        mu: Horizontal-differentiation index ``mu`` (must be positive).
        residual_tol: Maximum tolerated markup-equation residual at the solution.

    Returns:
        The monopoly price vector ``p^M``, shape ``(n,)``.

    Raises:
        ValueError: If ``mu <= 0`` or ``a`` and ``c`` have mismatched shapes.
        ConvergenceError: If no valid interior root is found.
    """
    a_arr, c_arr = _validate_market(a, c, mu)
    # Warm-start above marginal cost; monopoly prices sit above the Nash markup.
    guess = c_arr + 2.0 * mu
    return _solve_markup(
        _monopoly_residual, guess, a_arr, a0, c_arr, mu, residual_tol, "monopoly_prices"
    )


def _solve_markup(
    residual_fn: Callable[[FloatArray, FloatArray, float, FloatArray, float], FloatArray],
    guess: FloatArray,
    a: FloatArray,
    a0: float,
    c: FloatArray,
    mu: float,
    residual_tol: float,
    label: str,
) -> FloatArray:
    """Root-find a markup system with fsolve and validate the solution.

    Raises:
        ConvergenceError: If the residual exceeds ``residual_tol`` or the implied
            shares are not strictly interior.
    """
    raw = fsolve(residual_fn, guess, args=(a, a0, c, mu), full_output=False)
    prices: FloatArray = np.asarray(raw, dtype=np.float64)
    max_residual = float(np.max(np.abs(residual_fn(prices, a, a0, c, mu))))
    if not np.isfinite(max_residual) or max_residual > residual_tol:
        raise ConvergenceError(
            f"{label}: residual {max_residual:.2e} exceeds tolerance {residual_tol:.2e}"
        )
    shares = logit_shares(prices, a, a0, mu)
    if not (bool(np.all(shares > 0.0)) and bool(np.all(shares < 1.0))):
        raise ConvergenceError(f"{label}: solution has non-interior shares {shares!r}")
    return prices


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
