# memorybench — results

**Last updated:** May 13, 2026
**Latest run:** Day 14 PM (Mon May 11, 2026), K=30 retrieval
**Subset size:** 232 of 500 LongMemEval-S questions
**Full 500-Q run scheduled:** September 2026

---

## Headline number

| Configuration | Overall accuracy | Caveat |
|---|---|---|
| **Aurra (K=30, 232-Q subset, May 11 2026)** | **85.3%** (198/232) | 232 of 500; subset, not full LongMemEval-S |

K=30 is now Aurra's production default for `/agent/query`. Customers who don't pass an explicit `limit` get the same K=30 retrieval the benchmark uses. Production behavior and benchmark behavior are aligned as of May 13, 2026.

---

## Subtask breakdown — Day 14 PM run

| Subtask | Score | Notes |
|---|---|---|
| single-session-user | 95.7% | At ceiling; harder questions in this category are rare in the subset |
| temporal-reasoning | 89.2% | The subtask where bi-temporal correctness contributes most. Aurra's `reference_date` parameter (shipped Day 14 AM) caused most of this lift |
| multi-session | 78.3% | Multi-step reasoning across multiple memory sessions. K=30 retrieval over K=10 contributed +7.0 |
| single-session-preference | (n=5, excluded) | Subset only contains 5 questions in this category; result is noise, not signal. Excluded from headline number |
| **Overall (excluding noise)** | **85.3%** | 198 of 232 questions |

---

## What changed to get here

Two changes between the Day 12 (Sat May 9) baseline of 71.1% and the Day 14 PM (Mon May 11) score of 85.3%:

1. **`reference_date` parameter on /agent/query** (Day 14 AM, shipped to production).
   - Without this, the LLM had no signal about when the user is asking the question. Multi-step temporal questions ("did this happen before or after X?") were near-random.
   - Lifted temporal-reasoning subtask from 52.3% to 83.1% (+30.8).
   - No cost increase; no customer-facing change beyond accepting the new optional parameter.

2. **K=30 retrieval** (Day 14 PM, was benchmark-only at the time, became production default on May 13).
   - More memories included in the LLM context per query. Cost ~3x context tokens per `/agent/query`.
   - Lifted overall accuracy from 79.3% (K=10) to 85.3% (K=30).
   - Largest gains: temporal-reasoning (+6.1), multi-session (+7.0).
   - On May 13, 2026, this became the production default. Customers who don't pass an explicit `limit` get K=30.

---

## What did NOT change

- The underlying memory extraction prompt
- The bi-temporal model (valid time + transaction time tracking)
- The embedding model (OpenAI text-embedding-3-small)
- The answer-generation LLM (Claude Opus 4.7)

The score lift from Day 12 to Day 14 came entirely from how memories are retrieved (K) and what context the model has about the question (`reference_date`), not from changing what is stored.

---

## Honest caveats — read before citing this number

1. **232 of 500 questions.** The 85.3% is the subset score, not the full LongMemEval-S score. Full-500 is scheduled for September 2026, requires Anthropic credits and cloud-hosted ingestion (not laptop-runnable cost-effectively). When the full run lands, this file is updated and the headline number changes.

2. **K=30 is the production default as of May 13.** Earlier internal benchmark publications said "K=30 is benchmark-only." That is no longer true. /agent/query default is now 30. Cost implications documented in `methodology.md`.

3. **single-session-preference n=5 is noise.** Subset doesn't have enough questions in this category for a meaningful percentage. Excluded from the overall headline.

4. **No multi-run variance reported yet.** Single-run numbers can drift ±1-2 points based on LLM nondeterminism. Tier 2 backlog: median-of-3 runs with variance bars.

---

## Historical progression

| Date | Configuration | Subset | Score |
|---|---|---|---|
| Day 11 (May 8) | K=10, no reference_date | first 50 | n/a (single-day calibration) |
| Day 12 (May 9) | K=10, no reference_date | 232 | 71.1% |
| Day 14 AM (May 11) | K=10, **with** reference_date | 232 | 79.3% |
| Day 14 PM (May 11) | K=30, with reference_date | 232 | **85.3%** |
| **Future (Sept 2026)** | K=30, full LongMemEval-S | 500 | TBD |

---

## Cost

- Day 14 AM run (K=10, query+eval): ~$3
- Day 14 PM run (K=30, query+eval): ~$8-10
- Cumulative benchmark spend across all Days: ~$525

Full-500 run at K=30 estimate: ~$200 ceiling. Required for production-validated public number.
