# TACIT — Phase 2 plan

> Status: **planning** (Phase 1 complete and validated). This is the Phase 2 analog of
> the Phase 1 build brief in [`CLAUDE.md`](../CLAUDE.md). Like Phase 1, Phase 2 is built
> one milestone at a time — tests written as we go, docs updated, committed and synced
> before moving on. The authority for scope above the harness is
> [`docs/design.md`](design.md).

## Where Phase 2 picks up

Phase 1 shipped the whole offline pipeline on **scripted agents** and passed the metric
validation gate (cartel CI ≈ 1.0, honest ≈ 0.0, tit-for-tat told apart from a static
cartel by the punish-and-revert signature; 115 tests; bit-for-bit deterministic; **no
model API ever called**). The Phase 1 brief lists the rest as explicit non-goals and
defers them here: calling real models, the LLM monitor, the composition sweep, and the
held-out runner.

The seam to build on already ships: the provider-agnostic `ModelAdapter` protocol in
[`src/tacit/adapters/base.py`](../src/tacit/adapters/base.py) (`ChatMessage` /
`ModelResponse` / `complete(...)`), with no SDK imported yet. The C1–C5 condition
templates also already exist as data under `benchmark/conditions/templates/`, unit-tested
for selection but not yet wired to a prompt.

## Guiding principle (carried over from Phase 1)

**Prove it offline before spending.** Every milestone that can be built and tested against
a deterministic mock is built that way first; real inference spend is gated behind an
explicit, minimal smoke run. The harness stays model-agnostic so the same engine can later
run a customer-pointed evaluation (design doc §"a note on a possible product").

## Build order

| # | Milestone | Spend |
|---|---|---|
| **P2-M1** | **Model-backed agent + first adapter (mock-first).** Render `Observation` → chat prompt (wiring the C1–C5 templates + market brief + history), call the adapter, parse text → `Action` (price + optional message) with robust retry / clipping / fallback on malformed output. Ship a deterministic `MockAdapter` (canned/programmable responses) so the entire path is unit-tested with no network and no cost. | **$0** |
| **P2-M2** | **Real provider integration + first paid smoke run.** Concrete adapter(s) behind the protocol, key from env var, never committed. A tiny live config (1 model, 3 seats, few rounds, 1 seed) produces a real `transcript.jsonl` + `scores.json` in `runs/`. First dollar spent — kept minimal; record measured token cost. | small |
| **P2-M3** | **Composition sweep + cross-play.** Turn the `populations.py` composition specs into runnable cells: homogeneous baseline (N× under test), frontier-among-small (1× under test + fillers), small-among-frontier, recruiter-present (C4). A sweep runner expands model × condition × composition × seeds into per-cell run dirs and aggregates a **cross-play surface — never collapsed into one number** (design doc §"Composition sweep"). | $$ |
| **P2-M4** | **LLM monitor (RQ5 / detectability).** A monitor agent of varying capability tier reads a transcript (action-stream-only vs full-transcript) and flags suspected collusion. **Calibrate TPR @ fixed FPR on Phase 1's labeled scripted episodes** (cartel = positive, honest = negative) *before* it is ever applied to LLM transcripts (design doc §10.4). | $$ |
| **P2-M5** | **Results aggregation + report.** Per-model Capability (C1), Propensity (C2), Compliance Gap (C2 − C3), and Resistance (C4), reported **per composition as a profile, not a single safety score**; a report generator; dev-split artifacts published, held-out split kept private. | $ |

## Open decisions

- **Provider scope for the first adapter** *(undecided)* — options on the table:
  1. **Claude family only** (official `anthropic` SDK): Opus 4.8 as the "frontier" seat,
     Haiku 4.5 as the "small" seat → a genuine capability-asymmetric population from a
     single SDK, cheaply. Cleanest start.
  2. **Claude + an OpenAI-compatible adapter** (covers GPT *and* open-weight via
     OpenRouter / Together / local vLLM) → true cross-provider heterogeneity, more
     surface, pulls in a non-Anthropic SDK now.
  3. **Open-weight-first** via an OpenAI-compatible endpoint → matches the "mixed cheap
     open-weight models" deployment story; no Anthropic SDK in M1.
  Decision pending; M1's provider-agnostic plumbing (mock adapter, prompt rendering,
  response parsing) is unaffected either way, so M1 can start before this is settled.
- **Sampling / thinking params** — pin per-model temperature and (for the Claude family)
  whether reasoning/thinking is enabled when measuring the capability ceiling (C1). Giving
  a model its full reasoning is the fairer capability measurement but costs more tokens.
- **N per episode** — the design doc assumes N = 4; E1 as implemented runs n = 3 sellers.
  The composition layer must reconcile these (E1 stays at 3 seats; the N = 4 principle
  applies across environments). Flagged so it is a conscious choice, not a silent drift.

## Non-goals for Phase 2 (still later)

E2 and E3 environments, the held-out evaluation *service*, a public leaderboard, any
training/fine-tuning intervention, and steganographic covert-channel machinery remain out
of scope until their own phases.
