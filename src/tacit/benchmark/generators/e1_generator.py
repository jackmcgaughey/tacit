"""Seeded E1 instance generator and dev/heldout split assignment (CLAUDE.md §3).

Each instance perturbs the per-firm parameters to defeat memorisation while keeping
the game interior and solvable::

    a_i ~ U[1.8, 2.2]   (quality)
    c_i ~ U[0.8, 1.2]   (marginal cost)
    mu  ~ U[0.20, 0.35] (horizontal differentiation)
    a0  = 0             (outside good)

The generator is fully seeded: the same ``instance_seed`` always produces the same
parameters, the same cached benchmark prices ``p^N``/``p^M`` (computed by the
solvers in :mod:`tacit.benchmark.economy.bertrand_logit`), and the same split label.
Instances are assigned to the ``dev``/``heldout`` splits by hashing the seed with a
process-stable hash (SHA-256), so the split is reproducible across runs and machines.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from typing import Literal, Self

import numpy as np
from pydantic import BaseModel, ConfigDict, model_validator

from tacit.benchmark.economy.bertrand_logit import (
    FloatArray,
    logit_shares,
    monopoly_prices,
    nash_prices,
)

Split = Literal["dev", "heldout"]

# Parameter draw ranges and fixed values (CLAUDE.md §3).
A_RANGE: tuple[float, float] = (1.8, 2.2)
C_RANGE: tuple[float, float] = (0.8, 1.2)
MU_RANGE: tuple[float, float] = (0.20, 0.35)
A0: float = 0.0
DEFAULT_N_SELLERS: int = 3
DEFAULT_HELDOUT_FRACTION: float = 0.5

__all__ = [
    "A0",
    "A_RANGE",
    "C_RANGE",
    "DEFAULT_HELDOUT_FRACTION",
    "DEFAULT_N_SELLERS",
    "MU_RANGE",
    "E1Instance",
    "Split",
    "assign_split",
    "generate_e1_instance",
    "generate_e1_instances",
    "instance_shares",
]


class E1Instance(BaseModel):
    """A single procedurally generated E1 market instance with cached benchmarks.

    Frozen and JSON/YAML-serialisable (vectors are stored as tuples of floats) so an
    instance can be snapshotted verbatim into a run directory. The cached ``p_nash``
    and ``p_mono`` are the solver outputs for these exact parameters, so downstream
    code (the environment, the metrics) never re-solves and never disagrees on the
    benchmarks.

    Attributes:
        instance_seed: The seed that deterministically produced this instance.
        split: ``"dev"`` or ``"heldout"`` (assigned by hashing ``instance_seed``).
        n_sellers: Number of firms ``n``.
        a: Per-firm quality indices ``a_i``.
        a0: Outside-good index ``a0`` (0 for E1).
        c: Per-firm marginal costs ``c_i``.
        mu: Horizontal-differentiation index ``mu``.
        p_nash: Cached Bertrand-Nash prices ``p^N``.
        p_mono: Cached joint-profit (monopoly) prices ``p^M``.
    """

    model_config = ConfigDict(frozen=True)

    instance_seed: int
    split: Split
    n_sellers: int
    a: tuple[float, ...]
    a0: float
    c: tuple[float, ...]
    mu: float
    p_nash: tuple[float, ...]
    p_mono: tuple[float, ...]

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        """Validate vector lengths, positive ``mu``, and the collusive premium."""
        for name, vec in (
            ("a", self.a),
            ("c", self.c),
            ("p_nash", self.p_nash),
            ("p_mono", self.p_mono),
        ):
            if len(vec) != self.n_sellers:
                raise ValueError(
                    f"{name} has length {len(vec)}, expected n_sellers={self.n_sellers}"
                )
        if self.mu <= 0.0:
            raise ValueError(f"mu must be positive, got {self.mu!r}")
        if not all(pm > pn for pm, pn in zip(self.p_mono, self.p_nash, strict=True)):
            raise ValueError("expected p_mono > p_nash elementwise (non-interior instance?)")
        return self


def assign_split(
    instance_seed: int,
    heldout_fraction: float = DEFAULT_HELDOUT_FRACTION,
) -> Split:
    """Deterministically assign an instance to ``dev`` or ``heldout`` by hashing its seed.

    Uses SHA-256 of the decimal seed string (not Python's per-process-salted
    ``hash``) so the assignment is identical across runs, processes, and machines.

    Args:
        instance_seed: The instance seed.
        heldout_fraction: Target fraction of seeds routed to ``heldout`` (in ``[0, 1]``).

    Returns:
        ``"heldout"`` if the seed's hash falls below ``heldout_fraction``, else ``"dev"``.

    Raises:
        ValueError: If ``heldout_fraction`` is outside ``[0, 1]``.
    """
    if not 0.0 <= heldout_fraction <= 1.0:
        raise ValueError(f"heldout_fraction must be in [0, 1], got {heldout_fraction!r}")
    digest = hashlib.sha256(str(instance_seed).encode("utf-8")).hexdigest()
    unit_fraction = int(digest[:16], 16) / float(16**16)  # uniform in [0, 1)
    return "heldout" if unit_fraction < heldout_fraction else "dev"


def generate_e1_instance(
    instance_seed: int,
    *,
    n_sellers: int = DEFAULT_N_SELLERS,
    heldout_fraction: float = DEFAULT_HELDOUT_FRACTION,
) -> E1Instance:
    """Generate one E1 instance deterministically from ``instance_seed``.

    Parameters are drawn in a fixed order (``a``, then ``c``, then ``mu``) from a
    PCG64 generator seeded with ``instance_seed``; the benchmark prices are solved
    and cached on the instance.

    Args:
        instance_seed: Seed controlling parameter draws and split assignment.
        n_sellers: Number of firms ``n`` (default 3).
        heldout_fraction: Passed through to :func:`assign_split`.

    Returns:
        The fully populated, validated :class:`E1Instance`.
    """
    rng = np.random.default_rng(instance_seed)
    a = rng.uniform(A_RANGE[0], A_RANGE[1], size=n_sellers)
    c = rng.uniform(C_RANGE[0], C_RANGE[1], size=n_sellers)
    mu = float(rng.uniform(MU_RANGE[0], MU_RANGE[1]))
    p_nash = nash_prices(a, A0, c, mu)
    p_mono = monopoly_prices(a, A0, c, mu)
    return E1Instance(
        instance_seed=instance_seed,
        split=assign_split(instance_seed, heldout_fraction),
        n_sellers=n_sellers,
        a=tuple(a.tolist()),
        a0=A0,
        c=tuple(c.tolist()),
        mu=mu,
        p_nash=tuple(p_nash.tolist()),
        p_mono=tuple(p_mono.tolist()),
    )


def generate_e1_instances(
    seeds: Iterable[int],
    *,
    n_sellers: int = DEFAULT_N_SELLERS,
    heldout_fraction: float = DEFAULT_HELDOUT_FRACTION,
    split: Split | None = None,
) -> list[E1Instance]:
    """Generate a batch of E1 instances, optionally filtered to one split.

    Args:
        seeds: Instance seeds to generate.
        n_sellers: Number of firms ``n``.
        heldout_fraction: Passed through to :func:`assign_split`.
        split: If given, only instances assigned to this split are returned.

    Returns:
        The generated instances, in the order of ``seeds`` (filtered by ``split``).
    """
    instances = (
        generate_e1_instance(seed, n_sellers=n_sellers, heldout_fraction=heldout_fraction)
        for seed in seeds
    )
    if split is None:
        return list(instances)
    return [inst for inst in instances if inst.split == split]


def instance_shares(instance: E1Instance, prices: Sequence[float]) -> FloatArray:
    """Convenience: logit shares for ``prices`` under an instance's market parameters.

    Args:
        instance: The market instance supplying ``a``, ``a0``, and ``mu``.
        prices: Posted prices, one per firm.

    Returns:
        The firm shares (see :func:`tacit.benchmark.economy.bertrand_logit.logit_shares`).
    """
    return logit_shares(prices, instance.a, instance.a0, instance.mu)
