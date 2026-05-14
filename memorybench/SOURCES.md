# memorybench — sources

Every number in this directory's `comparison.md` is cited here. If you spot a stale, wrong, or missing citation, open an issue.

Last verified: May 13, 2026.

---

## Aurra (85.3%, 232-Q subset, May 11 2026)

- **Source:** This repository, `memorybench/results.md`
- **Configuration:** K=30 retrieval (Aurra's production default since May 13, 2026), reference_date parameter set per question, judge LLM Claude Opus 4.7
- **Caveat:** 232 of 500 questions. Full-500 run scheduled September 2026.
- **Reproduction code:** Aurra backend repo, `benchmarks/longmemeval/` directory. Requires an Aurra API key + Anthropic credits for the judge LLM.

---

## MemPalace (96.6%)

- **Source URL:** https://www.mempalace.tech/benchmarks
- **Cross-reference:** Independent fact-check article also at https://www.mempalace.tech/benchmarks
- **Configuration:** local-only, fully open-source, GPT-4 class evaluator
- **Date verified:** May 13, 2026
- **Notes:** MemPalace publishes a "raw 96.6%" and a "100% hybrid" score with explicit methodology notes about the hybrid. We use the 96.6% raw number, which the fact-check article explicitly endorses as "the highest published local-only LongMemEval result."

---

## OMEGA (95.4%)

- **Source URL:** https://omegamax.co/benchmarks
- **Configuration:** local, GPT-4.1 as the evaluation model, full 500 questions
- **Date verified:** May 13, 2026
- **Notes:** OMEGA also publishes the same leaderboard at omegamax.co/compare with method documentation. Reproduction code is referenced from their benchmarks page.

---

## Emergence AI (86%)

- **Source URL:** https://www.emergence.ai/blog/sota-on-longmemeval-with-rag
- **Configuration:** RAG-based method, GPT-4o
- **Date verified:** May 13, 2026 (post originally published June 18, 2025)
- **Notes:** Achieved 86% on LongMemEval-S, explicitly noted to surpass Oracle GPT-4o's 82.4% (which has access to only the relevant sessions). Code released alongside the post.

---

## Zep / Graphiti (71.2%)

- **Source:** LongMemEval paper (Wu et al., 2024, ICLR 2025), plus Zep's own blog post
- **arXiv URL:** https://arxiv.org/abs/2410.10813
- **Configuration:** GPT-4o, full 500 questions, temporal knowledge graph instance
- **Date verified:** May 13, 2026
- **Notes:** Achieved 71.2% with 2.6s latency vs. 60.2% for vanilla full-context at 29s. Reported in the LongMemEval paper itself and confirmed by Rasmussen et al. (Jan 2025) and multiple secondary sources.

---

## Letta — N/A

- **Source URL searched:** omegamax.co/benchmarks (which lists "Letta · N/A · no published benchmark"), arXiv 2410.10813 LongMemEval paper, Letta's own documentation
- **Date verified:** May 13, 2026
- **Notes:** As of May 13, 2026, Letta has not publicly published a LongMemEval score. If Letta publishes one, this row updates. Earlier internal Aurra documents listed "Letta 83.2%" without a citation; the source for that number could not be verified.

---

## Mem0 — N/A on LongMemEval

- **Source URL searched:** mem0.ai/blog/state-of-ai-agent-memory-2026 (their latest, focused on LoCoMo), Mem0 documentation, ECAI 2025 paper (arXiv:2504.19413, on LoCoMo not LongMemEval)
- **Date verified:** May 13, 2026
- **Notes:** Mem0 has published numbers on LoCoMo (where Aurra also has results — see parent repo's `README.md`). We have not found a publicly cited LongMemEval-specific Mem0 score. Earlier internal Aurra documents listed "Mem0 49.0%" without a citation; the source for that number could not be verified.

---

## Citation discipline

Every number in `comparison.md` must have a row in this file with a working URL OR be marked N/A.

When updating `comparison.md`:
1. Add the URL to this file FIRST.
2. Verify the URL returns 200 and the score is on the page.
3. Note the date verified.
4. THEN update `comparison.md`.

If a competitor's score updates (e.g., they re-run on a new model), we update this file and `comparison.md` together. We don't update one without the other.

---

## What this file is

Insurance. Anyone reading `comparison.md` who wants to verify a claim should be able to find the source in 30 seconds. This file is that source map.

If a competitor disputes our citation of their number, this file is the first place we point. If the citation is wrong, we fix it. If the citation is right, the dispute resolves itself.
