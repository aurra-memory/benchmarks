# memorybench — comparison

How Aurra compares to other memory infrastructure systems on LongMemEval-S.

---

## Headline comparison

| System | Score | Configuration | Notes |
|---|---|---|---|
| MemPalace | 96.6% | as reported by authors | Top public score on LongMemEval-S |
| OMEGA | 95.4% | as reported by authors | |
| MemMachine | 93.0% | as reported by authors | |
| Hindsight | 91.4% | as reported by authors | |
| **Aurra** | **85.3%** | **K=30, 232-Q subset, May 11 2026** | **Subset, not full LongMemEval-S** |
| Letta | 83.2% | as reported by authors | |
| Zep | 71.2% | as reported by authors | |
| Mem0 | 49.0% | as reported by authors | |

---

## Important caveat — read this before citing

**Aurra's 85.3% is on a 232-question subset of LongMemEval-S, not the full 500-question evaluation.** Every other system in this table reports its score on the full 500. We are not yet making an apples-to-apples claim.

What we ARE claiming:
- On a balanced 232-question subset of LongMemEval-S, with the same prompts and scoring rubric, Aurra at K=30 production default scores 85.3%.
- This is meaningfully above Letta, Zep, and Mem0 within the subset.
- Whether this generalizes to the full 500 questions is **what the September 2026 run will determine**.

We will not claim "Aurra beats Letta on LongMemEval-S" until the full-500 run is published with the same configuration.

---

## What's different about Aurra

The headline number alone is not the story. Aurra's positioning on memorybench is about *how* the number is achieved and *what else* you get with it.

### Bi-temporal correctness

Every Aurra memory tracks both valid time (what was true in the world) and transaction time (what the system believed). Most competitor systems track neither, or only one. Practical impact: on the temporal-reasoning subtask, Aurra scores 89.2% (Day 14 PM) — the subtask where bi-temporal information matters most.

This is also why Aurra hallucinates dates at 0% on the LoCoMo benchmark (see parent repo `README.md`) while Mem0 hallucinates at 22.95%. The bi-temporal model is the same architecture; benchmarks just measure different facets of it.

### Source citations

Every retrieved memory carries a `source_citation` object: where the memory came from (Slack message, agent extraction, manual upload), the original input, and provenance metadata. Customers can prove which memories drove an answer.

This is not measured by LongMemEval. But it's what the basic Verifiable Graph (Tier 1 backlog) renders into a per-citation proof tree on every `/agent/query` response.

### Full audit trail

`/memories/{memory_id}/audit` returns the complete provenance + history for any memory. Customers can answer "what did the AI know at time T?" with a verifiable trace.

Again, not measured by LongMemEval. But essential for the customer story: bi-temporal correctness + citations + audit trail is the differentiation triangle.

### BYO-LLM

Customers bring their own LLM provider key. Anthropic, OpenAI, Azure, Gemini, and Grok (xAI) are supported as of May 13, 2026. Aurra is the memory layer; customers pick the brain.

Benchmark variants per provider are Tier 2 backlog. Initial sanity check (Gemini 2.5 Flash as extraction) on a small sample shows similar accuracy to Claude Opus 4.7 with significantly lower per-query cost. Full numbers in a future revision.

---

## Methodology parity

We compare against other systems' reported numbers from public sources. We have not re-run other systems through Aurra's evaluation pipeline. When we run the full-500 in September 2026, we will note any methodology differences explicitly (judge LLM choice, scoring rubric, etc.) so the comparison is verifiable.

What we will NOT do:
- Cherry-pick subsets that favor Aurra
- Run other systems with handicapped configurations
- Compare numbers from different LongMemEval variants (S vs M vs L) as if they were the same

If you find a methodology issue in this directory, open an issue on the [parent repo](https://github.com/aurra-memory/benchmarks). Honest critique is welcome.

---

## What this comparison is not

- Not a marketing leaderboard ranking memory systems on a single number
- Not a substitute for evaluating any system on your own data
- Not the full story of why customers pick one memory layer over another

The full story includes: pricing, latency, deployment model (cloud vs self-host), ecosystem (integrations, SDKs), governance (audit, security), and the team building it. memorybench measures one dimension — multi-session question-answering accuracy on a public benchmark. Important, but one dimension.

---

## When this file updates

This file updates when any of the following ships:

1. Full-500 LongMemEval-S run (Aurra) — September 2026
2. Multi-run variance reporting (median-of-3, ±std) — Tier 2 backlog
3. BYO-LLM variants benchmarked (Aurra-Gemini, Aurra-Grok) — Tier 2 backlog
4. Independent re-runs of other systems on the same questions + scoring rubric — Tier 3, contingent on customer / community interest

Until then, treat this file as a snapshot of one specific benchmark configuration.
