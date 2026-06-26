# Pricing

**Independent, reproducible collusion-risk evaluations for AI models.**

TACIT measures whether a model forms, sustains, or resists collusion — price-fixing,
tacit coordination, recruitment into a cartel — when it's deployed alongside other
agents. Every result is graded against a metric **validated on known-behaviour
baselines** (cartel scores ~1, honest play ~0, reactive cooperation is told apart from
a static cartel) and every episode is **logged verbatim** so findings are auditable and
reproducible.

Useful when you need a defensible answer for **AI safety review, antitrust/competition
risk, vendor due diligence, or pre-deployment sign-off**.

---

## Packages

| | **Snapshot** | **Full Evaluation** ★ | **Continuous** |
|---|---|---|---|
| Models under test | 1 | 1 | multiple |
| Environment | E1 pricing game | E1 + heterogeneity sweep | custom |
| Conditions | C1–C5 | C1–C5 × comms regimes | full matrix |
| Seeds per cell | ~20 | ~30 | ~30+ |
| Monitor detectability pass | — | ✓ | ✓ |
| Report | Summary + scores | Detailed, per-pairing + recommendations | Dashboard + quarterly readout |
| Turnaround | ~1 week | ~2–3 weeks | ongoing |
| **Pilot price** | **$3,500** | **$12,000** | **from $8,000 / quarter** |

★ Most popular. *Introductory pilot pricing — now booking.*

---

## Every engagement includes

- **The full metric suite** — Collusion Index, profit-gain Δ, collusion stability
  (punish-and-revert signature), and price dispersion — reported **per condition** and,
  in the heterogeneity sweep, **per population pairing**.
- **Raw run artifacts** — verbatim JSONL transcripts, the exact config snapshot, and
  per-episode scores for every run, so a third party can re-check the numbers.
- **A written report** — what the model did, where the risk concentrates, and concrete
  recommendations.
- **Reproducibility** — the environment, scenario generation, and orchestration are
  fully seeded; results are distributions over many seeds, not single rollouts.

## Add-ons

- **Each additional model:** $2,000
- **Custom environment** (procurement, auctions, allocation — beyond the E1 pricing
  game): from $15,000
- **Rush turnaround:** +50%

## How billing works

The package fee covers the engineering, the analysis, and the report. **Model inference
is separate and cheap** — typically **$10–$600** of API spend for a full evaluation —
and handled one of two ways:

1. **Your key (recommended):** you grant scoped API access to the model under test and
   pay the provider directly. Your COGS line is $0 from us.
2. **Passthrough:** we run it and bill compute at cost as a flat line.

Open-weight models are hosted on rented GPUs at cost.

## How it works

1. **Scope call** — pick the model(s) and package.
2. **We run the harness** — fully seeded and reproducible, no model fine-tuning, no data
   leaves the loop you authorize.
3. **You get the report + raw artifacts** within the turnaround window.

---

### Get in touch

**[mcgaugheyjack@gmail.com](mailto:mcgaugheyjack@gmail.com)** · [github.com/jackmcgaughey/tacit](https://github.com/jackmcgaughey/tacit)

*Pricing is introductory and adjustable to scope — reach out for a custom quote or a
multi-model / continuous-monitoring arrangement.*
