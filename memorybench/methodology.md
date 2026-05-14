# memorybench — methodology

How Aurra runs LongMemEval. Reproduction details, parameter choices, and what we measure.

---

## Dataset: LongMemEval-S

- Source: [Wu et al., 2024](https://arxiv.org/abs/2410.10813), the LongMemEval benchmark for long-term conversational memory
- Variant: LongMemEval-S (the standard track; LongMemEval-M and -L exist but are not yet evaluated here)
- Size: 500 questions total
- Structure: each question references a memory trace of ~50 conversation sessions. Answering correctly requires the system to (a) have stored relevant facts from those sessions, (b) retrieve the right facts when the question is asked, (c) reason correctly across them.

### Subtask categories

LongMemEval-S questions are tagged with one of:

- **single-session-user** — answer lies in a single session, about the user
- **temporal-reasoning** — requires inferring time/order from session timestamps
- **multi-session** — answer requires combining facts from 2+ sessions
- **single-session-preference** — answer is a user preference stated in a single session
- **single-session-assistant** — (not present in current subset)

The subset used in current runs (232 questions) is balanced across the first four categories with these counts approximately: single-session-user 80, temporal-reasoning 70, multi-session 77, single-session-preference 5. The preference count is too small to be statistically meaningful and is excluded from headline numbers.

---

## Pipeline

1. **Ingestion.** For each LongMemEval session in the dataset, we POST the session content to Aurra's `/agent/memories` endpoint with the session's timestamp as `recorded_at`. Aurra extracts memories using its standard extraction prompt + Claude Opus 4.7.

2. **Querying.** For each evaluation question, we POST to `/agent/query` with:
   - The question text
   - `reference_date` set to the question's asked-at timestamp (added Day 14 AM)
   - `limit=30` (default since May 13, 2026)
   - `tenant_id` set to the question's user identifier

3. **Scoring.** Each retrieved answer is compared against the expected answer using an LLM judge (Claude Opus 4.7) with a fixed scoring rubric. Binary scoring: 1 if correct, 0 if wrong. Partial credit is not awarded.

4. **Aggregation.** Per-subtask accuracy is computed independently; overall accuracy is the unweighted mean across questions (not subtasks).

---

## Key parameters

### K (retrieval limit)

- **Value:** 30
- **Default since:** May 13, 2026 (B4 change to `AgentQueryInput.limit` default)
- **Why 30:** Empirically lifts overall accuracy from 79.3% (K=10) to 85.3% on the 232-Q subset. Largest gains on temporal-reasoning (+6.1) and multi-session (+7.0).
- **Cost tradeoff:** ~3x context tokens per query. Documented in B4 decision log in the Aurra backend repo.

### reference_date

- **Added:** May 11, 2026 (Day 14 AM)
- **What it does:** tells the answer-generation LLM what date the user is treating as "now" for the question. Without it, the LLM cannot resolve relative time references.
- **Production-shipped:** yes, customers benefit immediately. Optional parameter; defaults to the request timestamp if not passed.
- **Impact:** lifted temporal-reasoning subtask from 52.3% to 83.1% on the 232-Q subset.

### Models

- **Extraction LLM:** Claude Opus 4.7 (`claude-opus-4-7`)
- **Answer generation LLM:** Claude Opus 4.7
- **Judge LLM:** Claude Opus 4.7
- **Embedding model:** OpenAI `text-embedding-3-small`

Customers who use Aurra's BYO-LLM feature can swap the extraction model. The benchmark uses the default. Per-provider benchmark variants (Anthropic, OpenAI, Gemini, Grok extraction) are Tier 2 backlog.

---

## What we don't yet measure

- **Variance across runs.** Single-run numbers can drift ±1-2 points due to LLM nondeterminism. Median-of-3 with variance bars is on the Tier 2 backlog.
- **Latency.** Wall-clock query time is not currently part of the published headline. Reported informally: K=30 query latency is ~5-8 seconds end-to-end for the average question.
- **Cost per question.** Estimated at ~$0.04-0.06 per `/agent/query` at K=30 on the default Anthropic model. Customers using BYO-LLM with cheaper models (Gemini Flash, Grok Code Fast) see lower per-question cost.
- **Other LongMemEval variants.** -M (medium) and -L (long) variants are not yet evaluated. Future work.

---

## Reproducing the benchmark

Aurra's LongMemEval driver code is in the Aurra backend repo at `benchmarks/longmemeval/`. It contains:

- `ingest.py` — POSTs LongMemEval sessions to `/agent/memories` with proper `recorded_at` timestamps
- `query.py` — runs the 232-question subset against `/agent/query` and writes raw outputs
- `scripts/` — judge scoring + per-subtask aggregation

Public reproduction requires (a) an Aurra API key, (b) Anthropic credits for the judge LLM scoring step (~$10 for a full 232-Q run), (c) the LongMemEval-S dataset from the original paper's release.

When the full 500-Q run lands (September 2026), reproduction code + raw outputs + judge transcripts will be published in the parent `aurra-memory/benchmarks` repo for independent verification.

---

## Comparison to other systems

See `comparison.md` for side-by-side numbers across Aurra, Letta, Mem0, Zep, MemMachine, OMEGA, and MemPalace.

**Important caveat:** comparing the 232-Q subset score to other systems' full-500 scores is apples-to-oranges. The full-500 run is the apples-to-apples comparison, scheduled for September 2026. Until then, all cross-system comparisons in this directory carry an asterisk.

---

## Cost-efficient resumption path (added May 14, 2026 ~12:25 AM ET)

The original September 2026 timeline assumed a full-500-Q run cost of ~$200 (full re-ingestion). After analyzing trace overlap between the May 11 232-Q subset and the remaining 268 questions, we have a cheaper path that brings the full-500 number into reach without waiting for September.

### The finding

LongMemEval-S has 19,195 unique haystack sessions across all 500 questions. The May 11 232-Q subset ingested 9,994 of them. The remaining 268 questions share 2,128 sessions with the subset (already ingested) and introduce 9,201 net-new sessions.

**Net effect: resuming the run from the existing 232-Q ingestion needs ~52% less ingestion work than a full re-run.**

### Cost basis

Reference: Day 14 PM run, 232 questions, K=30, cost ~$11-13 total (extraction + query + judge). Scaling proportionally for the 268-Q remainder:

| Component | Day 14 actual (232 Q) | Remaining 268 Q (est) | Notes |
|---|---|---|---|
| Ingestion (extraction) | ~$5 | ~$5-7 | 9,201 new sessions, ~$0.0006/session at Opus rates |
| Query (K=30) | ~$4 | ~$5 | 268 Q × ~$0.018 each |
| Judge (Opus) | ~$2-3 | ~$2-3 | 268 Q × ~$0.01 each |
| **Total** | **~$11-13** | **~$13-15** | At current model defaults |

This estimate assumes no failed runs. The Day 12 baseline (May 9) cost $510 across 6 dead runs while the pipeline was being debugged; that failure mode is not the steady state.

### Further cost reductions (Tier 2, only after the $15 run is verified working)

If the $15 baseline run succeeds, future re-runs (e.g. variance bars, BYO-LLM variants) can be cheaper still:

| Optimization | Expected savings | Risk |
|---|---|---|
| Haiku 4.5 for extraction (vs Opus 4.7) | ~5x cheaper extraction (~$1 vs ~$5) | Quality unknown; 50-Q calibration first |
| Sonnet 4.6 for judge (vs Opus 4.7) | ~3x cheaper judge (~$1 vs ~$3) | Judge calibration vs existing Opus-scored 232-Q |
| Cache ingested traces across re-runs | Ingestion only runs once for life of dataset | Already true if Supabase memory store stays stable |
| Gemini 2.5 Flash extraction (BYO-LLM, May 13 ship) | ~10x cheaper than Opus | Different model family, accuracy unknown |
| Grok 4 fast extraction (BYO-LLM, May 13 ship) | xAI pricing competitive | Same calibration step |

Combined Tier 2 path could bring future full-500 runs to ~$3-5 each. Not relevant for the first run; flagged for repeat runs.

### Resumption preconditions

Before running the 268-Q remainder, verify these things are still true:

1. **Existing 232-Q memories are still in the database.** SELECT count by tenant on the company_id used for the run.
2. **The extraction prompt has not changed materially since May 11.** Diff `app/memory_extractor.py` prompt strings.
3. **The bi-temporal model shape has not changed.** Verify `valid_from`, `valid_to`, `superseded_by` semantics are unchanged.

If any of those have drifted, do a 10-question calibration re-ingest first (~$0.50) to confirm new outputs match old outputs.

### Run plan

See `scripts/run_remaining_268.sh` for the exact command sequence. Wall-clock estimate: 3-5 hours including ingestion + query + scoring. Should be supervised (or run with output logging + periodic checks), not unattended overnight.

Estimated budget: $15 hard ceiling. If spend approaches $30 with no end in sight, abort and investigate.
