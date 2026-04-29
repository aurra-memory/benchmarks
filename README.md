# Aurra Memory Benchmarks

Benchmarks comparing memory infrastructure systems for AI agents on the [LoCoMo](https://arxiv.org/abs/2402.17753) long-term conversational memory dataset.

## Background

We built [Aurra](https://aurra.us) as a memory layer for AI agents and wanted to compare it honestly against existing systems. This repo contains the benchmark code, results, and methodology.

**See the writeup:** [Mem0 thinks our 2023 conversation happened in 2026](https://aurra.us/blog/mem0-vs-aurra) *(blog link — update before publishing)*

## April 29, 2026 baseline

| Metric | Aurra | Mem0 |
|---|---|---|
| Total memories captured | **2,685** | 780 *(capped at 100/conv by free-tier API)* |
| Memories with fabricated dates | **0 (0.00%)** | 179 (22.95%) |
| Judge-rated useful | **42.4%** | 28.2% |
| Judge-rated hallucinated | **55.3%** | 64.5% |
| Judge-rated junk | **2.6%** | 5.9% |
| Judge-rated misattributed | **1.7%** | 7.2% |

LoCoMo conversations are dated 2023; Mem0 stamps most memories with 2026 (today's date). See `results/date_audit.txt` for examples and `results/DAY1_SUMMARY.md` for full details.

**Caveat on judge scoring:** the LLM judge scores against LoCoMo's `event_summary` ground truth, which is brief and incomplete. Memories about real but unsummarized content get flagged as hallucinated, so absolute numbers are inflated for both systems. Relative comparison is the meaningful signal.

## What this measures

Two metrics, both with LLM-as-judge scoring:

1. **Memory quality (junk rate)** — Of the memories a system stores from a conversation, what percentage are useful vs hallucinated vs duplicates vs junk?
2. **Answer accuracy** — Given questions about the conversation, can the system retrieve the right memories to answer correctly?

## Systems tested

- **Mem0** (cloud, free tier) — `mem0ai` Python SDK
- **Aurra** — direct API calls

## Reproducing

```bash
git clone https://github.com/aurra-memory/benchmarks
cd benchmarks
pip install -r requirements.txt

cp .env.example .env
# Edit .env to add MEM0_API_KEY, ANTHROPIC_API_KEY, AURRA_API_KEY

# 1. Run ingestion for both systems
python3 run_ingestion.py both

# 2. Score memories for junk rate
python3 scoring/junk_classifier.py both

# 3. Run Q&A accuracy
python3 run_qa_accuracy.py both

# 4. Generate charts
python3 scoring/generate_charts.py
```

## Methodology notes

- 10 conversations, 5,882 turns, 272 sessions (full LoCoMo10 dataset)
- Each conversation runs as isolated `tenant_id` to prevent cross-contamination
- Q&A: stratified random sample of 500 questions across categories 1-4 (excluding adversarial cat 5)
- Judge model: Claude Opus
- Mem0 ingests asynchronously; we wait 120s after each conversation. 30s throttle between sessions to avoid free-tier rate limiting.

## Caveats

- Mem0 free tier vs paid tier may differ
- Mem0's extraction LLM is closed-source; Aurra uses Claude Opus
- LoCoMo conversations are synthetic
- LLM-as-judge introduces grader variance

## License

MIT

## Citation

```bibtex
@inproceedings{maharana2024locomo,
  title={Evaluating Very Long-Term Conversational Memory of LLM Agents},
  author={Maharana, Adyasha and Lee, Dong-Ho and Tulyakov, Sergey and Bansal, Mohit and Barbieri, Francesco and Fang, Yuwei},
  booktitle={ACL},
  year={2024}
}
```
