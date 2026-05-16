# memorybench — results

**Last updated:** May 16, 2026
**Latest run:** Day 18 PM (Fri May 15, 2026), K=30 retrieval, two-judge validation
**Subset size:** 432 of 500 LongMemEval-S questions (combining May 11 curated 232 + May 15 remaining 200)
**Full 500-Q run scheduled:** September 2026 (remaining 68 questions need ingest re-run; see caveats below)

---

## Headline numbers

We tested Aurra at two scopes and against two independent judges. All numbers are published; no result is hidden in favor of another.

### GPT-4o judge

| Configuration | Subset | Score | Notes |
|---|---|---|---|
| Aurra (K=30, v0 prompt, May 11) | 232-Q | **85.3%** (198/232) | Curated subset, original extractor prompt — represents Aurra's May 11 baseline |
| Aurra (K=30, v2 prompt, May 15) | 200-Q (remaining) | **76.5%** (153/200) | The other 200 questions, v2 extractor prompt (currently shipped to production) |
| **Combined 432-Q (mixed methodology)** | **432-Q** | **81.3%** (351/432) | v0 prompt on 232, v2 prompt on 200 — see methodology note below |

### Claude Opus 4.7 judge

| Configuration | Subset | Score | Notes |
|---|---|---|---|
| Aurra (K=30, v0 prompt, May 11) | 232-Q | **83.2%** (193/232) | Same hypotheses as GPT-4o run, scored by stricter judge |
| Aurra (K=30, v2 prompt, May 15) | 200-Q (remaining) | **74.5%** (149/200) | Same hypotheses as GPT-4o run, scored by stricter judge |
| **Combined 432-Q (mixed methodology)** | **432-Q** | **79.2%** (342/432) | Two-judge mean with GPT-4o: 80.2% |

### What these numbers mean together

- Two judges agree within ~2.1 percentage points across all 432 questions — the result is robust to judge choice
- The 232-Q May 11 subset used the **v0 extractor prompt**, which is no longer shipped to production
- The 200-Q May 15 subset uses the **v2 extractor prompt** (commit `1f6485c`, deployed May 15) — this is the production prompt new users get
- The combined 432-Q number reflects mixed methodology; we plan to re-run the 232 with v2 prompt for full consistency

K=30 is Aurra's production default for `/agent/query` (effective May 13, 2026).

---

## Per-category breakdown (Claude Opus, the stricter judge)

| Category | Aurra (Claude) | Aurra (GPT-4o) | Sample size |
|---|---|---|---|
| single-session-user | 93.6% (44/47) | (May 11 set only) | 47 |
| knowledge-update | 93.6% (73/78) | 94.9% (74/78) | 78 |
| temporal-reasoning | 87.7% / 86.4% | 89.2% / 89.4% | 65 + 66 |
| single-session-preference | 80.0% (4/5) | (May 11 set only) | 5 |
| multi-session | 76.5% (88/115) | (May 11 set only) | 115 |
| **single-session-assistant** | **33.9% (19/56)** | **35.7% (20/56)** | 56 |

The single-session-assistant category is Aurra's weakest. We disclose this prominently and discuss the root cause below.

---

## What changed since May 11 (the 85.3% baseline)

Two changes between the May 11 result (85.3% on 232-Q, GPT-4o judge only) and the May 15 result (multi-judge 432-Q):

1. **Extractor prompt v2** (deployed to production May 15, 2026 — commit `1f6485c`).
   - Previous extractor was structurally biased toward user-attributed facts; assistant-attributed content (recommendations, lookups, plans) was filtered out as "filler."
   - v2 adds narrow extraction for specific named recallable assistant content: "Assistant recommended X," "Assistant confirmed Y," "Assistant identified Z."
   - On the 200-Q May 15 subset, this lifted single-session-assistant from 14.3% to 35.7% (+21.4pp) and overall from 68.0% to 76.5% (+8.5pp).
   - Knowledge-update and temporal-reasoning also improved (+7.7pp and +1.5pp respectively).

2. **Added Claude Opus 4.7 as a second judge alongside GPT-4o** (May 15, 2026).
   - Cross-judge validation strengthens the result: a 2.1pp delta between judges across 432 questions confirms the score isn't a one-judge artifact.
   - Both judges show the same per-category pattern (strong knowledge-update and temporal-reasoning, weak single-session-assistant).

---

## What did NOT change

- The bi-temporal model (valid time + transaction time tracking)
- The embedding model (OpenAI text-embedding-3-small)
- The answer-generation LLM (Claude Opus 4.7) used by /agent/query
- K=30 production default

The score variation across subsets comes from question composition and the v2 extractor prompt, not from changes to the retrieval architecture.

---

## What we're working on (single-session-assistant)

Aurra's weakest category is single-session-assistant retrieval (33.9-35.7%). The v2 prompt deployed May 15 nearly tripled the score from its 14.3% baseline, but this category still lags Aurra's strong categories by ~50pp.

The remaining failures cluster into patterns that prompt-only changes cannot fully address:
- Questions requiring fusion of multiple assistant turns within a session
- Questions about specific visual or non-text content discussed
- Open-ended questions where the assistant gave nuanced multi-option responses

Closing this gap requires retrieval-side engineering (source-typed reranking, query intent classification), not prompt changes. This work is in progress and we'll update this page when it ships.

---

## Honest caveats — read before citing these numbers

1. **432 of 500 questions tested.** The full 500-Q run requires re-ingesting the remaining 68 questions with the v2 extractor prompt. Estimated cost ~$5 in Anthropic Haiku. Scheduled.

2. **Two different extraction methodologies were used across the 432 questions:**
   - May 11 subset (232 Q): Opus extraction, v0 prompt
   - May 15 subset (200 Q): Haiku extraction, v2 prompt (assistant-aware)

   We have not re-run the May 11 subset with v2 prompt for consistency. A future run will re-extract the full 500 with v2 for full consistency.

3. **K=30 is the production default as of May 13.** Customers who don't pass an explicit `limit` to /agent/query get K=30 retrieval — the same K used in this benchmark.

4. **single-session-preference n=5 is small.** The 232-Q subset only contains 5 questions in this category; the 80.0% result is from the May 15 subset's contribution alone.

5. **No multi-run variance reported yet.** Single-run numbers can drift ±1-2 points based on LLM nondeterminism. Tier 2 backlog: median-of-3 runs with variance bars.

6. **Raw data available for verification.** The hypothesis files and both judge result files are committed to this repo. Anyone can re-run the judges with their own evaluation model and verify.

---

## Competitive landscape

We tested Aurra under the standard LongMemEval-S methodology (K=30 retrieval, 432-Q subset). Where competitors publish comparable measurements, we cite them. Where they don't, we mark N/A rather than guess.

### Aggregate scores

| System | Score | Methodology | Independently verified |
|---|---|---|---|
| OMEGA | 95.4% | GPT-4.1 judge | Self-published |
| Mastra OM | 94.87% | GPT-5-mini judge | Self-published |
| Mem0 v3 (self-reported) | 94.8% | Mem0's own evaluation | Not independently verified at time of writing |
| Hindsight | 91.4% | Multi-strategy retrieval | Self-published |
| Letta | ~83.2% | Per third-party comparison sites | Yes |
| Evermind / EverOS | 83.0% | Self-published | Yes |
| **Aurra** | **80.2% mean (GPT-4o 81.3%, Claude Opus 79.2%)** | **K=30, two-judge validated, 432/500-Q** | **Self-published, raw data linked** |
| Zep | 63.8%-71.2% | Varies by methodology | Yes |
| Mem0 (older versions, multiple independent benchmarks) | 49.0% | GPT-4o judge | Yes |

Notes on the Mem0 numbers: Mem0 v3 (April 2026) reports 94.8% in their README, characterized as a +27 point improvement over a previous Mem0 algorithm. Independent third-party benchmarks of older Mem0 versions (Atlan, vectorize.io, evermind.ai blog) measured Mem0 at 49.0% on LongMemEval with GPT-4o judge. We have not independently verified Mem0 v3's 94.8% claim.

### Per-category — what's publicly available

Most competitors do not publish full per-category breakdowns. Below is what we found on public materials as of May 15, 2026:

| Category | Aurra (Claude) | OMEGA | Mem0 (v3) | Letta | Evermind | Zep | Hindsight |
|---|---|---|---|---|---|---|---|
| knowledge-update | 93.6% | N/A | gain only (no absolute) | N/A | N/A | N/A | N/A |
| temporal-reasoning | 87.7% | 94% | gain only (+42.1, baseline unspecified) | N/A | N/A | N/A | N/A |
| multi-session | 76.5% | 83% | N/A | N/A | N/A | N/A | N/A |
| single-session-user | 93.6% | N/A | category near-saturated ≥97% (general, not Mem0-specific) | N/A | N/A | N/A | N/A |
| single-session-assistant | 33.9% | N/A | gain only (+53.6, baseline unspecified) | N/A | N/A | N/A | N/A |
| single-session-preference | 80.0% | N/A | N/A | N/A | N/A | N/A | N/A |

Notes on the Mem0 cells: Mem0 reports gains (+42.1 on temporal, +53.6 on assistant) over their previous algorithm version but does not publish absolute per-category scores. We do not have a clean baseline to compute absolute Mem0 v3 category scores. The "near-saturated 97%+" comment in Mem0's docs characterizes the single-session-user category in general across the field, not a specific Mem0 measurement.

We publish per-category data because we believe in methodological transparency. The N/A cells reflect what competitors have or have not published.

---

## Aurra's architectural choices that LongMemEval doesn't directly measure

LongMemEval measures recall across six question types. It does not directly measure:

- **Date hallucination rate**: does the memory system stamp facts with correct dates?
- **Supersession correctness**: when a fact changes, is the old version preserved or overwritten?
- **Audit completeness**: can you query the full provenance of any memory?
- **Bi-temporal queries**: can you ask "what did the system believe on date X" natively?

These are dimensions Aurra optimizes for. Our separate LoCoMo benchmark (run April 29, 2026, published at `aurra-mem-benchmarks/results/`) measured:

| Metric (LoCoMo dataset, 10 conversations, 5,882 turns) | Aurra | Mem0 (free tier) |
|---|---|---|
| Memories with fabricated dates (2026 stamp on 2023 content) | **0 (0.00%)** | 179 (22.95%) |
| Total memories captured | 2,685 | 780* |

*Mem0 free tier caps at 100 memories per conversation. Free tier vs paid tier may differ.

The 0% date hallucination is a deterministic count (date stamp on memory vs date of source conversation), not a judge-rated metric. Full reproducibility data in the LoCoMo benchmark results directory.

For agents that need to prove what they knew when — financial agents, healthcare agents, legal agents, agents in any audited workflow — bi-temporal correctness and full audit trails matter more than aggregate recall. This is the wedge Aurra is built around.

---

## Historical progression

| Date | Configuration | Subset | GPT-4o judge | Claude Opus judge |
|---|---|---|---|---|
| Day 11 (May 8) | K=10, no reference_date | first 50 | calibration only | — |
| Day 12 (May 9) | K=10, no reference_date | 232 | 71.1% | — |
| Day 14 AM (May 11) | K=10, with reference_date | 232 | 79.3% | — |
| Day 14 PM (May 11) | K=30, v0 prompt | 232 | 85.3% | 83.2% (added May 15) |
| Day 17 (May 14) | K=30, v0 prompt | 200 (remaining) | 68.0% | — |
| **Day 18 (May 15)** | **K=30, v2 prompt (assistant-aware)** | **200 (remaining)** | **76.5%** | **74.5%** |
| **Combined Day 14 PM + Day 18** | **Mixed: v0 on 232, v2 on 200** | **432** | **81.3%** | **79.2%** |
| Future (TBD) | K=30, v2 prompt, full 500-Q | 500 | TBD | TBD |

---

## Cost

- Day 14 PM run (K=30, 232 questions, query+eval): ~$8-10
- Day 18 run (K=30, 200 questions, query + two judges): ~$15-20
- Day 17-18 v2 prompt ingest + recovery: ~$8 in Haiku
- Cumulative benchmark spend across all Days: ~$555

Full-500 v2 prompt run estimate: ~$15-20 incremental.

---

## Methodology

- **Dataset:** LongMemEval-S (cleaned), 500 manually crafted questions across six categories
- **Retrieval:** K=30 memories per query (Aurra's production default)
- **Answer LLM:** Claude Opus 4.7 (claude-opus-4-7)
- **Extraction LLM:**
  - May 11 subset (232 Q): Claude Opus, v0 prompt
  - May 15 subset (200 Q): Claude Haiku 4.5, v2 prompt (assistant-aware, commit 1f6485c)
- **Embeddings:** OpenAI text-embedding-3-small
- **Judges:** GPT-4o and Claude Opus 4.7 (run independently, both results published)
- **Question-type-specific judge prompts** from the LongMemEval paper, identical for both judges

Raw data:
- Hypotheses: outputs/aurra_hypotheses.jsonl (232-Q), outputs/aurra_hypotheses.may15_v2_200q_k30.jsonl (200-Q)
- Judge results: .eval-results-gpt-4o and .eval-results-claude-opus for each hypothesis file
- Ingest logs: outputs/ingest_log.may15_v2_combined.jsonl (9,518 unique sessions across the 200-Q v2 run)

Anyone can re-run the judges with their own evaluation model against the published hypotheses files.
