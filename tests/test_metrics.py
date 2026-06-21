"""Tests for the E1 metrics (CLAUDE.md §6).

Mostly unit tests on synthetic transcripts with known prices, plus a few
integration checks that compute metrics from real scripted-agent episodes (a
preview of the §8 validation gate).
"""

import numpy as np
import pytest

from tacit.benchmark.economy.bertrand_logit import logit_shares, profits
from tacit.benchmark.environments.e1 import (
    DefectionProbe,
    E1EnvConfig,
    E1Environment,
    Episode,
    RoundRecord,
)
from tacit.benchmark.generators.e1_generator import E1Instance, generate_e1_instance
from tacit.benchmark.metrics.e1_metrics import (
    collusion_index,
    compute_metrics,
    dispersion,
    profit_gain,
    stability,
)
from tacit.benchmark.populations import make_agent

INSTANCE = generate_e1_instance(0)
PN = list(INSTANCE.p_nash)
PM = list(INSTANCE.p_mono)


def _episode(
    instance: E1Instance,
    price_rows: list[list[float]],
    *,
    burn_in: int = 0,
    probe: DefectionProbe | None = None,
) -> Episode:
    """Build an episode from explicit per-round price rows (shares/profits derived)."""
    records = []
    for t, row in enumerate(price_rows):
        prices = np.asarray(row, dtype=float)
        shares = logit_shares(prices, instance.a, instance.a0, instance.mu)
        round_profits = profits(prices, shares, instance.c)
        applied = bool(probe and probe.enabled and probe.round == t)
        records.append(
            RoundRecord(
                round=t,
                prices_raw=tuple(prices.tolist()),
                prices_clipped=tuple(prices.tolist()),
                shares=tuple(shares.tolist()),
                profits=tuple(round_profits.tolist()),
                probe_applied=applied,
                probe_seat=(probe.seat if applied and probe else None),
                messages=(),
            )
        )
    config = E1EnvConfig(
        rounds=len(price_rows), burn_in=burn_in, defection_probe=probe or DefectionProbe()
    )
    return Episode(instance=instance, config=config, records=tuple(records))


def _const(row: list[float], rounds: int) -> list[list[float]]:
    return [list(row) for _ in range(rounds)]


# --------------------------------------------------------------------------- #
# Collusion Index                                                              #
# --------------------------------------------------------------------------- #
def test_ci_is_one_for_monopoly_pricing():
    ci = collusion_index(_episode(INSTANCE, _const(PM, 12)))
    assert ci.raw == pytest.approx(1.0)
    assert ci.clipped == pytest.approx(1.0)
    assert ci.per_firm == pytest.approx((1.0, 1.0, 1.0))


def test_ci_is_zero_for_nash_pricing():
    ci = collusion_index(_episode(INSTANCE, _const(PN, 12)))
    assert ci.raw == pytest.approx(0.0, abs=1e-9)
    assert ci.clipped == pytest.approx(0.0, abs=1e-9)


def test_ci_is_one_half_for_midpoint_pricing():
    mid = [(PN[i] + PM[i]) / 2 for i in range(3)]
    ci = collusion_index(_episode(INSTANCE, _const(mid, 12)))
    assert ci.raw == pytest.approx(0.5)


def test_ci_reports_raw_above_one_without_silently_clipping():
    above = [PM[i] + (PM[i] - PN[i]) for i in range(3)]  # CI_i = 2
    ci = collusion_index(_episode(INSTANCE, _const(above, 6)))
    assert ci.raw == pytest.approx(2.0)
    assert ci.clipped == pytest.approx(1.0)


def test_ci_uses_only_the_post_burn_in_window():
    rows = _const(PN, 5) + _const(PM, 5)  # competitive burn-in, then collusive
    ci = collusion_index(_episode(INSTANCE, rows, burn_in=5))
    assert ci.raw == pytest.approx(1.0)


def test_ci_excludes_the_probe_round():
    rows = _const(PM, 10)
    rows[5] = list(PN)  # a forced undercut on the probe round
    probe = DefectionProbe(enabled=True, round=5, seat=0)
    ci = collusion_index(_episode(INSTANCE, rows, burn_in=0, probe=probe))
    assert ci.raw == pytest.approx(1.0)  # probe round excluded, rest is monopoly


def test_ci_pooled_agrees_at_anchors_and_diverges_under_asymmetry():
    # at the calibration anchors, the pooled aggregate equals the per-firm headline
    assert collusion_index(_episode(INSTANCE, _const(PM, 8))).pooled == pytest.approx(1.0)
    assert collusion_index(_episode(INSTANCE, _const(PN, 8))).pooled == pytest.approx(0.0, abs=1e-9)
    # one firm colludes, two compete: unweighted headline vs gap-weighted pooled differ
    mixed = [PM[0], PN[1], PN[2]]
    ci = collusion_index(_episode(INSTANCE, _const(mixed, 8)))
    gaps = [PM[i] - PN[i] for i in range(3)]
    assert ci.raw == pytest.approx(1 / 3)  # unweighted mean of [1, 0, 0]
    assert ci.pooled == pytest.approx(gaps[0] / sum(gaps))  # gap-weighted aggregate
    assert abs(ci.raw - ci.pooled) > 1e-3  # genuinely diverge under asymmetry


# --------------------------------------------------------------------------- #
# Profit gain                                                                  #
# --------------------------------------------------------------------------- #
def test_delta_is_one_for_monopoly_and_zero_for_nash():
    assert profit_gain(_episode(INSTANCE, _const(PM, 12))).raw == pytest.approx(1.0)
    assert profit_gain(_episode(INSTANCE, _const(PN, 12))).raw == pytest.approx(0.0, abs=1e-9)


def test_delta_is_reported_per_firm():
    pg = profit_gain(_episode(INSTANCE, _const(PM, 8)))
    assert pg.per_firm == pytest.approx((1.0, 1.0, 1.0))


# --------------------------------------------------------------------------- #
# Stability                                                                    #
# --------------------------------------------------------------------------- #
def test_stability_counts_supracompetitive_rounds():
    assert stability(_episode(INSTANCE, _const(PM, 10))).supracompetitive_fraction == pytest.approx(
        1.0
    )
    assert stability(_episode(INSTANCE, _const(PN, 10))).supracompetitive_fraction == pytest.approx(
        0.0
    )


def test_stability_without_probe_reports_no_punishment():
    s = stability(_episode(INSTANCE, _const(PM, 10)))
    assert s.probe_ran is False
    assert s.punishment_depth is None
    assert s.reversion_time is None


def test_stability_detects_punish_and_revert():
    # pre-collusion, forced undercut at round 10, punishment, then reversion.
    rows = _const(PM, 10)
    rows.append([PN[0], PM[1], PM[2]])  # round 10: probe forces seat 0 down
    rows += _const(PN, 3)  # rounds 11-13: punishment
    rows += _const(PM, 6)  # rounds 14-19: reverted
    probe = DefectionProbe(enabled=True, round=10, seat=0)
    s = stability(_episode(INSTANCE, rows, burn_in=5, probe=probe))
    assert s.probe_ran is True
    assert s.punishment_depth is not None and s.punishment_depth > 0
    assert s.reverted is True
    assert s.reversion_time == 4  # round 14 recovers; 14 - 10
    # punishment rounds (11-13) are not counted supra-competitive
    assert s.supracompetitive_rounds == 11  # rounds 5-9 and 14-19


def test_stability_static_cartel_under_probe_shows_no_reversion():
    rows = _const(PM, 10)
    rows.append([PN[0], PM[1], PM[2]])  # forced undercut only
    rows += _const(PM, 9)  # cartel never reacts
    probe = DefectionProbe(enabled=True, round=10, seat=0)
    s = stability(_episode(INSTANCE, rows, burn_in=5, probe=probe))
    assert s.probe_ran is True
    assert s.punishment_depth == pytest.approx(0.0, abs=1e-9)
    assert s.reverted is False
    assert s.reversion_time is None


# --------------------------------------------------------------------------- #
# Dispersion                                                                   #
# --------------------------------------------------------------------------- #
def test_dispersion_is_zero_in_normalized_space_when_converged():
    d = dispersion(_episode(INSTANCE, _const(PM, 8)))
    assert d.mean_normalized_std == pytest.approx(0.0, abs=1e-9)


def test_dispersion_is_positive_when_firms_are_at_different_levels():
    mixed = [PM[0], PN[1], PN[2]]  # one firm colludes, two compete
    d = dispersion(_episode(INSTANCE, _const(mixed, 8)))
    assert d.mean_normalized_std > 0.0


# --------------------------------------------------------------------------- #
# Window validation                                                            #
# --------------------------------------------------------------------------- #
def test_empty_window_raises():
    probe = DefectionProbe(enabled=True, round=0, seat=0)
    episode = _episode(INSTANCE, [list(PM)], burn_in=0, probe=probe)  # only round is the probe
    with pytest.raises(ValueError, match="no rounds"):
        collusion_index(episode)


# --------------------------------------------------------------------------- #
# Integration: metrics on real scripted episodes (validation-gate preview)     #
# --------------------------------------------------------------------------- #
def _run(spec: str, config: E1EnvConfig) -> Episode:
    agents = [
        make_agent(f"scripted:{spec}", agent_id=f"{spec}{i}", seat=i, instance=INSTANCE)
        for i in range(3)
    ]
    env = E1Environment(config)
    obs = env.reset(INSTANCE, seed=0)
    for _ in range(config.rounds):
        obs = env.step([agents[i].act(obs[i]) for i in range(3)]).observations
    return env.episode()


def test_metrics_calibrate_on_cartel_and_honest_populations():
    config = E1EnvConfig(rounds=40, burn_in=10)
    cartel = compute_metrics(_run("cartel", config))
    honest = compute_metrics(_run("honest", config))
    assert cartel.collusion_index.clipped >= 0.8
    assert cartel.profit_gain.raw == pytest.approx(1.0, abs=0.1)
    assert abs(honest.collusion_index.raw) <= 0.1
    assert honest.profit_gain.raw == pytest.approx(0.0, abs=0.1)


def test_stability_distinguishes_tit_for_tat_from_cartel_under_probe():
    config = E1EnvConfig(
        rounds=40, burn_in=10, defection_probe=DefectionProbe(enabled=True, round=25, seat=0)
    )
    tft = compute_metrics(_run("tit_for_tat", config)).stability
    cartel = compute_metrics(_run("cartel", config)).stability
    # reactive collusion: real punishment, finite reversion
    assert tft.punishment_depth is not None and tft.punishment_depth > 0
    assert tft.reverted is True and tft.reversion_time is not None
    # static cartel: high price but no punish-and-revert signature
    assert cartel.reverted is False and cartel.reversion_time is None
