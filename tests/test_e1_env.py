"""Tests for the E1 repeated price-competition environment (CLAUDE.md §3).

Covers the round mechanics, the public-price observation, per-firm price clipping,
the three communication regimes, the defection probe, episode termination, input
and config validation, and determinism.
"""

import numpy as np
import pytest
from pydantic import ValidationError

from tacit.benchmark.agents.base import Action
from tacit.benchmark.economy.bertrand_logit import logit_shares, profits
from tacit.benchmark.environments.e1 import (
    CommsRegime,
    DefectionProbe,
    E1EnvConfig,
    E1Environment,
)
from tacit.benchmark.generators.e1_generator import generate_e1_instance

INSTANCE = generate_e1_instance(0)  # n=3, deterministic


def _cfg(**kwargs) -> E1EnvConfig:
    """Build a config with burn_in=0 (the production default 10 needs T>10)."""
    kwargs.setdefault("burn_in", 0)
    return E1EnvConfig(**kwargs)


def _prices_at(level: str) -> list[float]:
    """Helper: all sellers price at their Nash or monopoly benchmark."""
    return list(INSTANCE.p_nash if level == "nash" else INSTANCE.p_mono)


def _step_all(env: E1Environment, prices: list[float], messages: list[str | None] | None = None):
    msgs = messages if messages is not None else [None] * len(prices)
    return env.step([Action(price=p, message=m) for p, m in zip(prices, msgs, strict=True)])


# --------------------------------------------------------------------------- #
# Reset / observation plumbing                                                 #
# --------------------------------------------------------------------------- #
def test_reset_returns_one_blank_observation_per_seat():
    env = E1Environment(_cfg(rounds=5))
    obs = env.reset(INSTANCE, seed=0)
    assert len(obs) == INSTANCE.n_sellers
    for seat, o in enumerate(obs):
        assert o.round == 0
        assert o.own_last_price is None and o.own_last_profit is None
        assert o.public_prices == ()
        assert o.inbox == ()
        assert f"seat_{seat}" in o.market_brief


def test_step_exposes_previous_round_prices_and_private_profit():
    env = E1Environment(_cfg(rounds=5))
    env.reset(INSTANCE, seed=0)
    result = _step_all(env, _prices_at("monopoly"))
    record = result.info["record"]
    for seat, o in enumerate(result.observations):
        assert o.round == 1
        assert o.own_last_price == pytest.approx(record.prices_clipped[seat])
        assert o.own_last_profit == pytest.approx(record.profits[seat])
        # All firms' prices are public, in seat order.
        assert o.public_prices == record.prices_clipped


def test_shares_and_profits_match_the_economy_module():
    env = E1Environment(_cfg(rounds=3))
    env.reset(INSTANCE, seed=0)
    record = _step_all(env, _prices_at("monopoly")).info["record"]
    clipped = np.asarray(record.prices_clipped)
    exp_shares = logit_shares(clipped, INSTANCE.a, INSTANCE.a0, INSTANCE.mu)
    exp_profits = profits(clipped, exp_shares, INSTANCE.c)
    assert np.allclose(record.shares, exp_shares)
    assert np.allclose(record.profits, exp_profits)


# --------------------------------------------------------------------------- #
# Price clipping                                                               #
# --------------------------------------------------------------------------- #
def test_prices_are_clipped_per_firm_and_raw_is_preserved():
    env = E1Environment(_cfg(rounds=3, clip_low_factor=0.8, clip_high_factor=1.3))
    env.reset(INSTANCE, seed=0)
    low = 0.8 * np.asarray(INSTANCE.p_nash)
    high = 1.3 * np.asarray(INSTANCE.p_mono)
    submitted = [0.0, 100.0, float(INSTANCE.p_mono[2])]  # below band, above band, in band
    record = _step_all(env, submitted).info["record"]
    assert record.prices_raw == tuple(submitted)
    assert record.prices_clipped[0] == pytest.approx(low[0])
    assert record.prices_clipped[1] == pytest.approx(high[1])
    assert low[2] <= record.prices_clipped[2] <= high[2]


# --------------------------------------------------------------------------- #
# Communication regimes                                                        #
# --------------------------------------------------------------------------- #
def test_comms_none_drops_all_messages():
    env = E1Environment(_cfg(rounds=3, comms_regime=CommsRegime.NONE))
    env.reset(INSTANCE, seed=0)
    result = _step_all(env, _prices_at("nash"), messages=["hello", "hi", "yo"])
    assert result.info["record"].messages == ()
    assert all(o.inbox == () for o in result.observations)


def test_comms_public_broadcasts_to_every_other_seat():
    env = E1Environment(_cfg(rounds=3, comms_regime=CommsRegime.PUBLIC))
    env.reset(INSTANCE, seed=0)
    result = _step_all(env, _prices_at("nash"), messages=["let's hold price", None, None])
    sent = result.info["record"].messages
    assert len(sent) == 1
    assert sent[0].sender == "seat_0" and sent[0].to is None
    # Delivered next round to seats 1 and 2, but not back to the sender.
    assert result.observations[0].inbox == ()
    assert len(result.observations[1].inbox) == 1
    assert len(result.observations[2].inbox) == 1
    assert result.observations[1].inbox[0].text == "let's hold price"


def test_comms_private_keeps_the_third_seat_out_of_view():
    env = E1Environment(_cfg(rounds=3, comms_regime=CommsRegime.PRIVATE, private_channel=(0, 1)))
    env.reset(INSTANCE, seed=0)
    # seat 0 (in channel) speaks; seat 2 (out of channel) also tries to speak.
    result = _step_all(env, _prices_at("nash"), messages=["coordinate?", None, "let me in"])
    sent = result.info["record"].messages
    assert len(sent) == 1  # only the in-channel message survives
    assert sent[0].sender == "seat_0" and sent[0].to == "seat_1"
    assert len(result.observations[1].inbox) == 1  # the partner receives it
    assert result.observations[0].inbox == ()  # sender does not
    assert result.observations[2].inbox == ()  # the excluded third seat does not


# --------------------------------------------------------------------------- #
# Defection probe                                                              #
# --------------------------------------------------------------------------- #
def test_defection_probe_forces_undercut_only_on_its_round():
    probe = DefectionProbe(enabled=True, round=2, seat=1)
    env = E1Environment(_cfg(rounds=5, defection_probe=probe))
    env.reset(INSTANCE, seed=0)
    for t in range(5):
        record = _step_all(env, _prices_at("monopoly")).info["record"]
        if t == 2:
            assert record.probe_applied and record.probe_seat == 1
            assert record.prices_clipped[1] == pytest.approx(INSTANCE.p_nash[1])
            # the agent's raw submission is still logged faithfully
            assert record.prices_raw[1] == pytest.approx(INSTANCE.p_mono[1])
        else:
            assert not record.probe_applied and record.probe_seat is None
            assert record.prices_clipped[1] == pytest.approx(INSTANCE.p_mono[1])


# --------------------------------------------------------------------------- #
# Termination, validation, determinism                                         #
# --------------------------------------------------------------------------- #
def test_done_is_set_only_on_the_final_round():
    env = E1Environment(_cfg(rounds=3))
    env.reset(INSTANCE, seed=0)
    dones = [_step_all(env, _prices_at("nash")).done for _ in range(3)]
    assert dones == [False, False, True]
    assert len(env.history) == 3


def test_reset_rejects_probe_seat_out_of_range():
    # seat is only checkable against n at reset time (n comes from the instance).
    env = E1Environment(
        _cfg(rounds=5, defection_probe=DefectionProbe(enabled=True, round=2, seat=5))
    )
    with pytest.raises(ValueError, match=r"defection_probe\.seat"):
        env.reset(INSTANCE, seed=0)


def test_step_rejects_wrong_action_count():
    env = E1Environment(_cfg(rounds=3))
    env.reset(INSTANCE, seed=0)
    with pytest.raises(ValueError, match="expected 3 actions"):
        env.step([Action(price=1.5)])


def test_use_before_reset_raises():
    env = E1Environment(_cfg(rounds=3))
    with pytest.raises(RuntimeError, match="reset"):
        env.step([Action(price=1.5)])
    with pytest.raises(RuntimeError, match="reset"):
        _ = env.history


@pytest.mark.parametrize(
    "kwargs",
    [
        {"rounds": 0},
        {"rounds": 5, "burn_in": 5},
        {"rounds": 5, "burn_in": 0, "clip_low_factor": 1.5, "clip_high_factor": 1.0},
        {"rounds": 5, "burn_in": 0, "defection_probe": DefectionProbe(enabled=True, round=9)},
    ],
)
def test_config_validation_rejects_bad_settings(kwargs):
    with pytest.raises(ValidationError):
        E1EnvConfig(**kwargs)


def test_episode_is_deterministic_given_config_seed_and_actions():
    cfg = _cfg(
        rounds=6,
        comms_regime=CommsRegime.PUBLIC,
        defection_probe=DefectionProbe(enabled=True, round=3, seat=0),
    )
    prices = _prices_at("monopoly")

    def run() -> list:
        env = E1Environment(cfg)
        env.reset(INSTANCE, seed=7)
        return [_step_all(env, prices, messages=["x", None, None]) for _ in range(6)]

    run_a, run_b = run(), run()
    assert [r.model_dump() for r in run_a] == [r.model_dump() for r in run_b]
