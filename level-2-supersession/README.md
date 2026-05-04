# Level 2 Supersession Classifier Benchmark

A 121-case hand-labeled benchmark for memory supersession detection — the task an agent memory system performs when deciding whether a new fact replaces an existing one.

**See the writeup:** [When your agent's facts go stale, who decides what to keep?](https://aurra.us/blog/level-2-auto-supersede-beta)

## Why this benchmark exists

When an LLM-based memory layer auto-detects supersession, two things can go wrong:

1. **False positive** — the classifier marks an old fact as superseded when it shouldn't be. The agent loses information it needed. Unrecoverable without an audit log review.
2. **False negative** — the classifier fails to mark a real supersession. Both facts stay. Recoverable via a manual API call.

These failure modes are not symmetric. A system that is 80% accurate but 100% precise on its "supersedes" verdict is safer than a system that is 95% accurate with 5% false positives.

The implication: the right metric is **precision on the "supersedes" verdict at a confidence threshold**, not overall accuracy. This benchmark is structured around that decision.

## Headline results

Two models, prompt v1, all 121 cases, 0 errors:

| Metric | claude-haiku-4-5 | claude-sonnet-4-6 |
|---|---|---|
| Overall accuracy | 93.4% (113/121) | 94.2% (114/121) |
| **Gated supersedes precision (conf >= 0.85)** | **100% (55/55)** | 98.3% (57/58) |
| Supersedes recall | 91.7% | 96.7% |
| Cost per classification | ~$0.0005 | ~$0.0015 |
| Latency P50 | ~500ms | ~1500ms |

Haiku is the production winner. Every time it was confident enough to act on a supersession judgment (>=0.85 confidence), it acted correctly. The 8 cases haiku scored "wrong" were all false negatives — situations where the classifier kept both memories instead of superseding. Recoverable.

Sonnet's one false positive at the 0.85 threshold was a medical-related case that would normally be filtered by the per-category opt-out gate before the LLM ever ran in production. For 3x the cost and 3x the latency, sonnet doesn't pay back.

## What "gated precision" means

The classifier returns one of three verdicts per candidate (`supersedes`, `refines`, `independent`) with a confidence score in `[0.0, 1.0]`. In production, only `verdict == "supersedes"` AND `confidence >= 0.85` triggers an actual supersession.

Gated precision = (correct supersedes at conf >= 0.85) / (total supersedes verdicts at conf >= 0.85).

This is the metric that matters for the customer. A high-confidence supersedes verdict is the only thing that mutates state.

## Test cases

121 hand-labeled cases across 25 categories. Distribution:

| Category | Count | What it tests |
|---|---|---|
| `clear_supersession` | 8 | Explicit replacement language |
| `subtle_supersession` | 8 | Implicit replacement, no marker words |
| `independent` | 18 | Different entities, additive facts, time-shifted |
| `refinement` | 10 | Detail added to existing fact |
| `b2b_agent` | 7 | Seat counts, champion changes, competitor mentions |
| `recurring_schedule` | 6 | Time-based pattern changes |
| `negation` | 4 | "Cancelled," "stopped," "no longer" |
| `ambiguous` | 4 | Genuinely uncertain — ground truth = independent |
| `identity` | 4 | Name changes, marriage, alias updates |
| `hedging` | 4 | "Thinking about," "may," "considering" — should NOT supersede |
| `multi_entity` | 4 | "Second pet," "second car," "second job" — distinct entities |
| `generalization` | 4 | "Allergic to one fruit" -> "allergic to all pome fruits" |
| `temporal_recency` | 4 | Historical vs current facts |
| `travel_location` | 4 | City/region moves |
| `reversion` | 4 | "Tried X then went back to Y" |
| `legal_status` | 3 | Marriage, citizenship — DEFAULT EXCLUDED in production |
| `payment_method` | 3 | Card on file, payment provider |
| `subscription` | 3 | Plan changes |
| `financial` | 3 | Salary, account balance |
| `workplace_role` | 3 | Job title, employer |
| `hardware_os` | 3 | Device, OS version |
| `project_status` | 4 | "Working on X" -> "Shipped X" |
| `dietary` | 2 | Vegetarian, allergies (non-medical) |
| `health_medical` | 2 | DEFAULT EXCLUDED in production |
| `subscription_tier` | 2 | Free -> paid, tier upgrades |

Plus a small `do_not_classify.jsonl` set validating that the per-category opt-out gate filters the right things before the LLM runs.

## Methodology

- **Models tested:** `claude-haiku-4-5-20251001` and `claude-sonnet-4-6`
- **Prompt:** v1 (frozen). System prompt includes 5 few-shot examples covering all three verdicts, calibration scaffolding for confidence scores, linguistic-signal hints, and 6 explicit tiebreaker rules
- **Eval harness:** runs each case through the model in parallel, parses the JSON response, computes precision/recall at multiple confidence thresholds
- **Ground truth:** hand-labeled by the Aurra team. Each case has `expected_verdict`, `expected_confidence_min`, and a one-line rationale
- **Acceptance criteria** (set before running): >=95% gated precision, >=60% recall, >=80% overall accuracy

## What this benchmark does NOT measure

Honest caveats so other teams can decide if these results transfer:

- **No measure of latency under load.** Latency numbers above are single-request P50 against the Anthropic API on Tier 1 limits. Burst behavior is not measured here
- **English only.** All 121 cases are in English. Non-English supersession detection is untested
- **Single-fact pairs.** Each case is one new fact + one candidate. Multi-fact ambiguity (new fact relates to 3 existing facts) is not directly tested, though the production system handles it by running the classifier per-candidate
- **Synthetic cases.** Hand-written by the Aurra team. Real production traffic distribution may differ
- **No measure of LLM grader variance.** Hand labels are deterministic; we did not use an LLM grader

If you have real conversational data with hand-labeled supersession ground truth and want to contribute it, open an issue or PR.

## Reproducing

```bash
git clone https://github.com/aurra-memory/benchmarks
cd benchmarks/level-2-supersession
pip install anthropic>=0.40.0

export ANTHROPIC_API_KEY=sk-ant-...

# Run prompt v1 against haiku and sonnet on all 121 cases
python3 eval_harness.py --prompt prompts/v1.md --cases test_cases.jsonl

# Output written to results/eval_<timestamp>.json
```

The harness runs both models in parallel within Tier 1 rate limits (~10 minutes for the full 121 cases on both models).

## Files

```
level-2-supersession/
  README.md              <- this file
  eval_harness.py        <- runner + scoring
  test_cases.jsonl       <- 121 hand-labeled cases
  prompts/
    v1.md                <- production prompt (frozen)
  results/
    haiku-v1.json        <- haiku full results
    sonnet-v1.json       <- sonnet full results
```

## Improving on this

Three things would meaningfully strengthen this benchmark:

1. **Real-world cases.** Replace synthetic test cases with anonymized real production supersession events. Aurra customers who want to contribute their own ground-truth data: open an issue
2. **More models.** GPT-4o, Gemini 2.5, Llama 3.3 70B, etc. The harness is model-agnostic in design but currently only wired for Anthropic. PRs welcome
3. **Multi-candidate cases.** Test the case where one new fact relates to multiple existing memories. Production handles this by running the classifier per-candidate, but a benchmark for the joint case would catch failure modes single-candidate testing misses

PRs that contribute test cases or model adapters welcome. PRs that change scoring methodology should be paired with a justification for why the new methodology better captures real-world failure modes.

## License

MIT
