# memorybench

**Aurra's public benchmark for memory infrastructure on the LongMemEval dataset.**

This directory tracks Aurra's performance on [LongMemEval](https://arxiv.org/abs/2410.10813), a 500-question evaluation of long-term conversational memory across multi-session traces. It complements the LoCoMo results in the parent repo: LoCoMo is shorter-form conversational memory; LongMemEval is the harder, multi-session, temporal-reasoning benchmark.

## Why a separate memorybench

The LoCoMo work (April 29-30, 2026 baseline) measured **what Aurra captures vs Mem0** on conversational data: date hallucination, junk rate, useful-vs-hallucinated. LoCoMo answered "is your memory accurate?"

LongMemEval measures something different: **given 50-session memory traces, can you answer multi-step questions that require temporal reasoning?** Different audience (engineers, AI researchers), different methodology, different conclusions. It deserves its own home.

## Current results

See `results.md` for the latest scored run.

**Headline:** Aurra scores **85.3%** on a 232-question subset of LongMemEval-S, with K=30 retrieval as the production default. Among systems with verifiable public LongMemEval scores, this places Aurra below MemPalace (96.6%), OMEGA (95.4%), and Emergence AI (86%), and above Zep/Graphiti (71.2%). Full-500-question run scheduled for September 2026. See `comparison.md` and `SOURCES.md` for citations and N/A notes on systems that have not published LongMemEval scores.

Production default of K=30 was shipped May 13, 2026; the benchmark configuration and production configuration are now the same.

## What's here

- `README.md` — this file, scope + index
- `results.md` — current scored runs, with caveats
- `methodology.md` — how the benchmark runs: dataset selection, K parameter, prompt versions, scoring
- `comparison.md` — Aurra vs other memory systems with verified public LongMemEval scores. Systems without public scores are listed as N/A with explanatory notes.
- `SOURCES.md` — explicit URL citation for every number in this directory

## What's NOT here yet

- Full 500-question run (scheduled September 2026, requires pre-paid Anthropic credits + cloud-hosted ingestion)
- Submission infrastructure for other memory systems to be benchmarked against Aurra
- Live leaderboard with auto-updating numbers

Those land in the next iteration. The data in this directory is hand-curated from internal benchmark runs.

## Honest framing

The published 85.3% is on a 232-question subset, not the full 500-question LongMemEval-S. The subset was selected to balance the four subtask categories (single-session-user, temporal-reasoning, multi-session, single-session-preference) so the subtask-level breakdown is statistically meaningful within each. We do not claim 85.3% generalizes to the full 500 questions until we run the full eval.

Methodology is in `methodology.md`. Reproduction code is in the parent `aurra-memory/benchmarks` repo plus Aurra's API.

## See also

- LoCoMo benchmark (parent repo README) — the April 2026 baseline
- [Aurra blog: Mem0 thinks our 2023 conversation happened in 2026](https://aurra.us/blog/mem0-vs-aurra)
- [LongMemEval paper](https://arxiv.org/abs/2410.10813) — original benchmark
