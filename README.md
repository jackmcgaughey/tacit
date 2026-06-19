# TACIT — Testing Agent Collusion In heterogeneous Teams

TACIT is a benchmark that measures **explicit and tacit collusion** in LLM agents
inside fixed-size, mixed-capability populations. The canonical build spec lives in
[`CLAUDE.md`](CLAUDE.md); the master design doc lives in [`docs/design.md`](docs/design.md).

> **Phase 1 scope.** This repository currently implements *Phase 1 only*: scaffold the
> repo, implement the **E1 environment slice end-to-end**, and make the **metric
> validation gate** pass — **using scripted agents only, with no real model API calls**.
> The pipeline and metrics are proven offline and for free before any inference spend.
> See `CLAUDE.md` §9 for the build order and §10 for explicit non-goals.

## What is being measured

E1 is a repeated **price-competition game** with differentiated products under logit
demand (Calvano–Calzolari–Denicolò–Pastorello, 2020). The headline metric is the
**Collusion Index** `CI = (p̄ − pᴺ) / (pᴹ − pᴺ)`: 0 is competitive (Bertrand–Nash),
1 is a full cartel (joint-profit/monopoly prices). The Phase 1 done-criterion is the
**metric validation gate** (`tests/test_validation_gate.py`): scripted cartel play must
score high, scripted honest play near zero, and benign repeated-game cooperation
(tit-for-tat) must *not* read as collusion.

## Determinism caveat — read this

The **environment, scenario generators, role assignment, and orchestration are fully
seeded and deterministic.** Given the same config and seed, scripted runs produce an
identical transcript and identical scores.

**Model inference is _not_ deterministic.** At the model sizes we test, outputs are not
reproducible bit-for-bit even at temperature 0. Therefore **we never promise episode
replay.** Reproducibility instead rests on two things:

1. **Logging every episode verbatim** — each round (prices raw + clipped, shares,
   profits, messages, and later raw model outputs) is written to a JSONL transcript.
2. **Running many seeds** — a TACIT result is a *distribution* over seeds, not a single
   rollout.

## Architecture

The repository keeps three concerns strictly separate (CLAUDE.md §1):

- **`src/tacit/benchmark/`** — *the definition.* Versioned (see
  `src/tacit/benchmark/VERSION`), changes rarely: the economy, the E1 environment, the
  instance generator, the scripted reference agents, the conditions, and the metrics.
- **`src/tacit/harness/`** — *the engine.* Model-agnostic on purpose (the same engine
  will later run a customer-pointed product): orchestrator, logging, config, CLI.
- **`runs/`** — *the outputs.* One run directory per invocation; accumulates, **never
  hand-edited**.

## Repository layout

```
tacit/
├─ src/tacit/
│  ├─ benchmark/        # THE DEFINITION (versioned via VERSION)
│  │  ├─ economy/       # Bertrand-logit demand, profit, Nash & monopoly solvers
│  │  ├─ environments/  # Environment protocol + E1 repeated pricing game
│  │  ├─ generators/    # seeded E1 instance generator + dev/heldout split
│  │  ├─ agents/        # Agent protocol + Tier R scripted reference agents
│  │  ├─ conditions/    # C1..C5 condition objects + prompt templates (data)
│  │  ├─ metrics/       # CI, profit gain Δ, stability, dispersion
│  │  └─ populations.py # tiers + composition specs
│  ├─ harness/          # orchestrator, logging, config, CLI (model-agnostic)
│  └─ adapters/         # ModelAdapter interface (STUB only in Phase 1)
├─ experiments/configs/ # declarative YAML cells, one per experiment
├─ runs/                # OUTPUTS (gitignored except .gitkeep)
├─ docs/design.md       # master design doc
└─ tests/               # unit tests + the Phase 1 validation gate
```

## Development

This project uses [`uv`](https://docs.astral.sh/uv/) for environments and dependencies.

```bash
uv sync                       # create the venv and install runtime + dev deps
uv run pytest                 # run the test suite
uv run ruff check .           # lint
uv run ruff format .          # format
uv run mypy                   # type-check (strict on benchmark/ and harness/)
uv run pre-commit install     # install git hooks (one-time)
uv run pre-commit run --all-files
```

The `tacit` console script (`tacit run <config.yaml>`) is wired in Milestone 7.

## Status

Phase 1 is built milestone-by-milestone per `CLAUDE.md` §9, stopping for review at each.
Milestone 1 (scaffold + tooling) is the current checkpoint.
