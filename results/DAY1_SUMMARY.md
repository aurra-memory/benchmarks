# Day 1 Benchmark Results — April 29, 2026

## Headline numbers

| Metric | Aurra | Mem0 |
|---|---|---|
| Total memories | 2,685 | 780 (capped at 100/conv) |
| Conversations | 10/10 | 10/10 |
| Sessions OK | 264/272 (97%) | 272/272 |
| Memories with absolute years | 0 (0.00%) | 179 (22.95%) |
| LLM-as-judge useful% | 42.4% | 28.2% |
| LLM-as-judge hallucinated% | 55.3% | 64.5% |
| LLM-as-judge junk% | 2.6% | 5.9% |
| LLM-as-judge misattributed% | 1.7% | 7.2% |

## Key findings

1. **Mem0 fabricates dates.** 23% of Mem0 memories contain absolute years; nearly all use 2026 (today) for conversations dated 2023.
2. **Aurra preserves source language.** 0 memories contain absolute years.
3. **Aurra captures 3.4× more memories** (2,685 vs 780).
4. **Mem0 hits an API cap at exactly 100 memories per user_id** (6/10 convs maxed out at exactly 100).
5. **LLM-as-judge methodology has issues** — high "hallucination" rates on both systems are partly due to incomplete event_summary ground truth. Relative comparison still has signal.

## Sample evidence

### Mem0 fabricated dates (real conversation: July-October 2023)
- "User attended an LGBTQ support group on April 28, 2026..."
- "Assistant noted she has been married for five years as of April 2026..."
- "Camping trip in May 2026"
- "Assistant purchased figurines on 2026-04-28"

### Aurra equivalent (preserving source language)
- "Caroline attended an LGBTQ+ counseling workshop last Friday"
- "User went on a meetup with friends last week"
- "User began their gender transition three years ago"

## Methodology notes

- LoCoMo10 dataset, 10 conversations, 5,882 turns, 272 sessions
- Each conversation isolated under unique tenant_id
- Mem0: 30s throttle between sessions, 120s wait after each conv (free-tier rate limiting)
- Aurra: extracts memories per-session via Claude Opus
- Judge: Claude Opus, classifies each memory as useful/hallucinated/junk/misattributed against LoCoMo's event_summary
- Judge limitation: event_summary is brief; memories about real but unsummarized content get flagged as hallucinated
- Date detection: regex match for absolute years 2020-2029 in memory text
