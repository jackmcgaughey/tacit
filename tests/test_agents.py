"""Tests for the Tier R scripted reference agents (CLAUDE.md §5).

Covers each agent's behaviour in isolation (driven by hand-built observations) and
through the real environment, including the tit-for-tat punish-and-revert signature
under a defection probe, which the §8 validation gate depends on.
"""

import pytest

from tacit.benchmark.agents.base import Agent, Observation
from tacit.benchmark.agents.reference import (
    PERSUASION_LADDER,
    CartelAgent,
    DefectorAgent,
    HonestAgent,
    RecruiterAgent,
    ReferenceAgent,
    TitForTatAgent,
)
from tacit.benchmark.environments.e1 import DefectionProbe, E1EnvConfig, E1Environment
from tacit.benchmark.generators.e1_generator import generate_e1_instance
from tacit.benchmark.populations import TIER_R, make_agent

INSTANCE = generate_e1_instance(0)  # n=3, deterministic
PN = INSTANCE.p_nash
PM = INSTANCE.p_mono


def _obs(public: list[float] | tuple[float, ...]) -> Observation:
    """Build an observation carrying only the previous round's public prices."""
    return Observation(
        round=1,
        own_last_price=None,
        own_last_profit=None,
        public_prices=tuple(public),
        inbox=(),
        market_brief="",
    )


def _run(agents: list[ReferenceAgent], cfg: E1EnvConfig) -> list:
    """Drive a full episode of the given agents and return the env's round history."""
    env = E1Environment(cfg)
    obs = env.reset(INSTANCE, seed=0)
    for _ in range(cfg.rounds):
        actions = [agents[i].act(obs[i]) for i in range(len(agents))]
        obs = env.step(actions).observations
    return env.history


# --------------------------------------------------------------------------- #
# Stateless agents                                                             #
# --------------------------------------------------------------------------- #
def test_honest_prices_nash():
    agent = HonestAgent("h", 1, INSTANCE)
    assert agent.act(_obs(list(PM))).price == pytest.approx(PN[1])


def test_cartel_prices_monopoly():
    agent = CartelAgent("c", 2, INSTANCE)
    assert agent.act(_obs(())).price == pytest.approx(PM[2])


def test_defector_undercuts_to_nash_by_default():
    assert DefectorAgent("d", 0, INSTANCE).act(_obs(())).price == pytest.approx(PN[0])


def test_defector_undercut_offset_and_validation():
    agent = DefectorAgent("d", 0, INSTANCE, undercut=0.1)
    assert agent.act(_obs(())).price == pytest.approx(PN[0] - 0.1)
    with pytest.raises(ValueError, match="non-negative"):
        DefectorAgent("d", 0, INSTANCE, undercut=-1.0)


# --------------------------------------------------------------------------- #
# Tit-for-tat                                                                  #
# --------------------------------------------------------------------------- #
def test_tit_for_tat_colludes_absent_undercut():
    agent = TitForTatAgent("t", 0, INSTANCE)
    assert agent.act(_obs(())).price == pytest.approx(PM[0])  # round 0
    for _ in range(5):
        assert agent.act(_obs(list(PM))).price == pytest.approx(PM[0])


def test_tit_for_tat_punishes_k_rounds_then_reverts():
    agent = TitForTatAgent("t", 0, INSTANCE, k=3)
    undercut = list(PM)
    undercut[1] = PN[1]  # rival 1 undercuts
    assert agent.act(_obs(())).price == pytest.approx(PM[0])
    assert agent.act(_obs(list(PM))).price == pytest.approx(PM[0])
    prices = [agent.act(_obs(undercut)).price]  # triggers punishment
    prices += [agent.act(_obs(list(PM))).price for _ in range(4)]
    assert prices == pytest.approx([PN[0], PN[0], PN[0], PM[0], PM[0]])


def test_tit_for_tat_k_is_configurable():
    agent = TitForTatAgent("t", 0, INSTANCE, k=1)
    undercut = list(PM)
    undercut[2] = PN[2]
    assert agent.act(_obs(undercut)).price == pytest.approx(PN[0])  # 1 round
    assert agent.act(_obs(list(PM))).price == pytest.approx(PM[0])  # reverts


def test_tit_for_tat_grim_never_forgives():
    agent = TitForTatAgent("t", 0, INSTANCE, grim=True)
    undercut = list(PM)
    undercut[1] = PN[1]
    agent.act(_obs(undercut))  # trigger
    for _ in range(10):
        assert agent.act(_obs(list(PM))).price == pytest.approx(PN[0])


def test_tit_for_tat_reset_clears_punishment():
    agent = TitForTatAgent("t", 0, INSTANCE, grim=True)
    undercut = list(PM)
    undercut[1] = PN[1]
    agent.act(_obs(undercut))
    agent.reset()
    assert agent.act(_obs(list(PM))).price == pytest.approx(PM[0])


# --------------------------------------------------------------------------- #
# Recruiter                                                                    #
# --------------------------------------------------------------------------- #
def test_recruiter_prices_monopoly_and_climbs_then_holds():
    agent = RecruiterAgent("r", 0, INSTANCE)
    acts = [agent.act(_obs(())) for _ in range(6)]
    assert all(a.price == pytest.approx(PM[0]) for a in acts)
    rung_names = [rung.name for rung in PERSUASION_LADDER]
    # climbs each rung once, then holds at the top (explicit proposal)
    assert agent.rung_history == [*rung_names, rung_names[-1], rung_names[-1]]
    assert f"{PM[0]:.2f}" in acts[3].message  # explicit proposal carries the price


def test_persuasion_ladder_is_named_structured_data():
    assert [r.name for r in PERSUASION_LADDER] == [
        "coordination_suggestion",
        "mutual_benefit",
        "efficiency_framing",
        "explicit_proposal",
    ]


# --------------------------------------------------------------------------- #
# Registry / protocol / validation                                            #
# --------------------------------------------------------------------------- #
def test_make_agent_resolves_every_tier_r_spec():
    for name in TIER_R:
        agent = make_agent(f"scripted:{name}", agent_id=name, seat=0, instance=INSTANCE)
        assert isinstance(agent, ReferenceAgent)
        assert agent.agent_id == name


def test_make_agent_rejects_bad_specs():
    with pytest.raises(ValueError, match="unsupported agent spec"):
        make_agent("model:gpt", agent_id="x", seat=0, instance=INSTANCE)
    with pytest.raises(ValueError, match="unknown scripted agent"):
        make_agent("scripted:nope", agent_id="x", seat=0, instance=INSTANCE)


def test_agents_satisfy_the_agent_protocol():
    for name in TIER_R:
        agent = make_agent(f"scripted:{name}", agent_id=name, seat=1, instance=INSTANCE)
        assert isinstance(agent, Agent)  # runtime-checkable protocol


def test_agent_rejects_out_of_range_seat():
    with pytest.raises(ValueError, match="seat 5 out of range"):
        HonestAgent("h", 5, INSTANCE)


# --------------------------------------------------------------------------- #
# Integration through the environment (calibration previews for §8)            #
# --------------------------------------------------------------------------- #
def test_all_cartel_sustains_monopoly_prices():
    agents = [
        make_agent("scripted:cartel", agent_id=f"c{i}", seat=i, instance=INSTANCE) for i in range(3)
    ]
    last = _run(agents, E1EnvConfig(rounds=12, burn_in=2))[-1]
    assert all(last.prices_clipped[i] == pytest.approx(PM[i]) for i in range(3))


def test_all_honest_sustains_nash_prices():
    agents = [
        make_agent("scripted:honest", agent_id=f"h{i}", seat=i, instance=INSTANCE) for i in range(3)
    ]
    last = _run(agents, E1EnvConfig(rounds=12, burn_in=2))[-1]
    assert all(last.prices_clipped[i] == pytest.approx(PN[i]) for i in range(3))


def test_tit_for_tat_population_punishes_then_reverts_under_probe():
    agents = [
        make_agent("scripted:tit_for_tat", agent_id=f"t{i}", seat=i, instance=INSTANCE)
        for i in range(3)
    ]
    probe = DefectionProbe(enabled=True, round=5, seat=0)
    history = _run(agents, E1EnvConfig(rounds=20, burn_in=0, defection_probe=probe))
    # collusive before the probe
    assert all(
        history[t].prices_clipped[s] == pytest.approx(PM[s]) for t in range(5) for s in range(3)
    )
    # the probe forces seat 0 to undercut, and a non-probed seat punishes in response
    assert history[5].prices_clipped[0] == pytest.approx(PN[0])
    assert history[6].prices_clipped[1] == pytest.approx(PN[1])
    # punishment depth > 0 somewhere, then finite reversion to collusion by the end
    assert min(history[6].prices_clipped) < max(PM) - 1e-3
    assert all(history[-1].prices_clipped[s] == pytest.approx(PM[s]) for s in range(3))
