# memorybench — comparison

How Aurra compares to other memory infrastructure systems on LongMemEval.

---

## Headline comparison (verified-published-sources only)

This table lists ONLY systems with publicly-cited LongMemEval scores from the system's own publications or peer-reviewed sources. For systems where we could not find a public, citable LongMemEval result, we mark "N/A — not publicly published." See `SOURCES.md` for the URL backing each row.

| System | LongMemEval-S score | Configuration | Source |
|---|---|---|---|
| MemPalace | 96.6% | local, GPT-4 class | mempalace.tech/benchmarks |
| OMEGA | 95.4% | GPT-4.1 | omegamax.co/benchmarks |
| Emergence AI | 86% | RAG-based, GPT-4o | emergence.ai/blog/sota-on-longmemeval-with-rag |
| **Aurra** | **85.3%** | **K=30, 232-Q subset, May 11 2026** | this repo, `results.md` |
| Zep / Graphiti | 71.2% | GPT-4o, full 500-Q | LongMemEval paper + Zep blog |
| Letta | N/A — not published | — | Letta has not released a LongMemEval score as of May 2026 |
| Mem0 | N/A — not published | — | Mem0 has published LoCoMo numbers but not LongMemEval as of May 2026 |

---

## The two important caveats

**1. Aurra's 85.3% is on a 232-question subset, not the full 500.**

Every other published score in the table above is on the full 500. We are not yet making an apples-to-apples claim. The full-500 run is scheduled for September 2026; until then, all cross-system rankings carry an asterisk.

**2. "Not published" is not "lost to."**

Where we list Letta, Mem0, MemMachine, or other systems as N/A, that means *we couldn't find a public number for them on LongMemEval as of May 13, 2026*. It does NOT mean those systems perform poorly. Several have published strong results on different benchmarks (Mem0 on LoCoMo, for example). LongMemEval is one of many ways to measure memory quality; absence from this table is absence from this specific benchmark, nothing more.

---

## What's different about Aurra

The headline number alone is not the story. Aurra's positioning on memorybench is about *how* the number is achieved and *what else* you get with it.

### Bi-temporal correctness

Every Aurra memory tracks both valid time (what was true in the world) and transaction time (what the system believed). Most competitor systems track neither, or only one. Practical impact: on the temporal-reasoning subtask, Aurra scores 89.2% (Day 14 PM) — the subtask where bi-temporal information matters most.

This is also why Aurra hallucinates dates at 0% on the LoCoMo benchmark (see the parent repo's main `README.md`) while Mem0 hallucinates at 22.95%. The bi-temporal model is the same architecture; benchmarks just measure different facets of it.

See: [Mem0 thinks our 2023 conversation happened in 2026](https://aurra.us/blog/mem0-vs-aurra)

### Source citations

Every retrieved memory carries a `source_citation` object: where the memory came from (Slack message, agent extraction, manual upload), the original input, and provenance metadata. Customers can prove which memories drove an answer.

This is not measured by LongMemEval. But it's what the upcoming basic Verifiable Graph renders into a per-citation proof tree on every `/agent/query` response.

### Full audit trail

`/memories/{memory_id}/audit` returns the complete provenance + history for any memory. Customers can answer "what did the AI know at time T?" with a verifiable trace.

Not measured by LongMemEval. Essential for the customer story: bi-temporal correctness + citations + audit trail is the differentiation triangle.

### BYO-LLM

Customers bring their own LLM provider key. Anthropic, OpenAI, Azure, Gemini, and Grok (xAI) supported as of May 13, 2026. Aurra is the memory layer; customers pick the brain.

---

## Methodology parity

We compare against other systems' reported numbers from public sources. We have NOT re-run other systems through Aurra's evaluation pipeline. When we run the full-500 in September 2026, we will note any methodology differences explicitly (judge LLM choice, scoring rubric, retrieval limit) so the comparison is verifiable.

What we will NOT do:
- Cherry-pick subsets that favor Aurra
- Run other systems with handicapped configurations
- Compare numbers from different LongMemEval variants (S vs M vs L) as if they were the same
- Attribute scores to systems that have not publicly published them

If you find a methodology issue or an incorrect citation, open an issue on this repo. Honest critique is welcome.

---

## What this comparison is not

- Not a marketing leaderboard ranking all memory systems on a single number
- Not a substitute for evaluating any system on your own data
- Not the full story of why customers pick one memory layer over another

The full picture includes: pricing, latency, deployment model (cloud vs self-host), ecosystem (integrations, SDKs), governance (audit, security), and the team building it. memorybench measures one dimension — multi-session question-answering accuracy on a public benchmark. Important, but one dimension.

---

## When this file updates

This file updates when any of the following changes:

1. Full-500 LongMemEval-S run (Aurra) — September 2026
2. A "not published" system publishes a verifiable LongMemEval score — we add the row with the citation
3. Multi-run variance reporting (median-of-3, ±std) — Tier 2 backlog
4. BYO-LLM variants benchmarked (Aurra-Gemini, Aurra-Grok) — Tier 2 backlog

Until then, treat this file as a snapshot of one specific benchmark configuration with the citation discipline we've committed to maintaining.
