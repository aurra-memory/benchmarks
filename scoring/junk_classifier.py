"""
Junk classifier — uses Claude as LLM-as-judge to score each stored memory.

For each memory, classifies as:
  - useful: a substantive, true fact from the conversation
  - duplicate: substantively the same as another memory in the same conversation
  - hallucinated: includes facts/dates/details NOT in the source conversation
  - junk: filler, vague, or trivially obvious
  - misattributed: attributes a fact to the wrong person

Outputs per-conversation and aggregate stats.
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import anthropic

load_dotenv()

RESULTS_DIR = Path(__file__).parent.parent / "results"
DATA_FILE = Path(__file__).parent.parent / "data" / "locomo10.json"

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def build_ground_truth(conv: dict) -> str:
    """Build a ground truth context from LoCoMo annotations."""
    parts = []
    parts.append(f"Speakers: {conv['conversation']['speaker_a']} and {conv['conversation']['speaker_b']}")

    # Session timestamps
    for k in sorted(conv['conversation'].keys()):
        if k.endswith('_date_time'):
            parts.append(f"{k}: {conv['conversation'][k]}")

    # Event summaries (these are the gold standard for "what happened")
    if 'event_summary' in conv:
        parts.append("\nEvent summaries (ground truth of significant events):")
        for k in sorted(conv['event_summary'].keys()):
            events = conv['event_summary'][k]
            if isinstance(events, list):
                for e in events[:10]:  # Limit to avoid huge contexts
                    parts.append(f"  - {e}")
            elif isinstance(events, str):
                parts.append(f"  - {events}")

    # Session summaries
    if 'session_summary' in conv:
        parts.append("\nSession summaries:")
        for k in sorted(conv['session_summary'].keys()):
            summ = conv['session_summary'][k]
            if isinstance(summ, str):
                parts.append(f"  {k}: {summ[:200]}")

    return "\n".join(parts)


def classify_memory_batch(memories: list, ground_truth: str, batch_size: int = 10) -> list:
    """Classify a batch of memories at once for efficiency."""
    if not memories:
        return []

    results = []
    for i in range(0, len(memories), batch_size):
        batch = memories[i:i+batch_size]

        memory_list_text = "\n".join([
            f"{idx+1}. {m.get('memory', m.get('text', ''))[:200]}"
            for idx, m in enumerate(batch)
        ])

        prompt = f"""You are a fact-checking judge for AI memory systems. Given a conversation's ground truth and a list of memories a system extracted, classify each memory.

CONVERSATION GROUND TRUTH:
{ground_truth}

MEMORIES TO CLASSIFY:
{memory_list_text}

For EACH memory, return a JSON object with:
- "useful": true if the memory is a substantive, accurate fact supported by the ground truth
- "hallucinated": true if it contains facts, dates, or details NOT in the ground truth (e.g., wrong year, invented people, fabricated events)
- "junk": true if it's filler, vague, or trivially obvious (e.g., greetings, "user said hi")
- "misattributed": true if attributes a fact to the wrong speaker
- "reason": brief explanation (max 15 words)

A memory can have multiple flags true. If "useful" is true, the others should typically be false.

Return ONLY a valid JSON array of {len(batch)} objects in the same order as the memories. No other text."""

        try:
            response = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            classifications = json.loads(raw.strip())

            for j, c in enumerate(classifications):
                if j < len(batch):
                    results.append({
                        "memory_id": batch[j].get("id"),
                        "memory_text": batch[j].get("memory", "")[:200],
                        "useful": bool(c.get("useful", False)),
                        "hallucinated": bool(c.get("hallucinated", False)),
                        "junk": bool(c.get("junk", False)),
                        "misattributed": bool(c.get("misattributed", False)),
                        "reason": c.get("reason", ""),
                    })
        except Exception as e:
            print(f"   ⚠️ Batch {i}-{i+batch_size} failed: {e}")
            for j, m in enumerate(batch):
                results.append({
                    "memory_id": m.get("id"),
                    "memory_text": m.get("memory", "")[:200],
                    "useful": False,
                    "hallucinated": False,
                    "junk": False,
                    "misattributed": False,
                    "reason": f"classification error: {str(e)[:50]}",
                    "error": True,
                })

        print(f"   classified {min(i+batch_size, len(memories))}/{len(memories)}")

    return results


def score_adapter(adapter_name: str, ingestion_results: dict, locomo_data: list) -> dict:
    """Score all memories from an adapter run."""
    print(f"\n{'='*70}")
    print(f"SCORING: {adapter_name.upper()}")
    print(f"{'='*70}")

    # Build sample_id → conversation map for ground truth lookup
    conv_map = {c['sample_id']: c for c in locomo_data}

    all_classifications = []
    per_conv_stats = []

    for conv_result in ingestion_results['results']:
        sample_id = conv_result.get('sample_id')
        memories = conv_result.get('stored_memories', [])
        if not memories or sample_id not in conv_map:
            continue

        ground_truth = build_ground_truth(conv_map[sample_id])

        print(f"\n[{adapter_name}] {sample_id} — {len(memories)} memories to classify")
        classifications = classify_memory_batch(memories, ground_truth)

        # Per-conv stats
        useful = sum(1 for c in classifications if c['useful'])
        halluc = sum(1 for c in classifications if c['hallucinated'])
        junk = sum(1 for c in classifications if c['junk'])
        misat = sum(1 for c in classifications if c['misattributed'])

        stats = {
            'sample_id': sample_id,
            'total': len(classifications),
            'useful': useful,
            'hallucinated': halluc,
            'junk': junk,
            'misattributed': misat,
            'useful_pct': round(useful / len(classifications) * 100, 1) if classifications else 0,
            'hallucinated_pct': round(halluc / len(classifications) * 100, 1) if classifications else 0,
            'junk_pct': round(junk / len(classifications) * 100, 1) if classifications else 0,
            'misattributed_pct': round(misat / len(classifications) * 100, 1) if classifications else 0,
        }
        per_conv_stats.append(stats)
        all_classifications.extend([{**c, 'sample_id': sample_id} for c in classifications])

        print(f"   📊 {sample_id}: {stats['useful_pct']}% useful, {stats['hallucinated_pct']}% halluc, {stats['junk_pct']}% junk")

    # Aggregate stats
    total = len(all_classifications)
    if total == 0:
        return {'adapter': adapter_name, 'total': 0, 'per_conv': [], 'classifications': []}

    aggregate = {
        'adapter': adapter_name,
        'total_memories': total,
        'useful_count': sum(1 for c in all_classifications if c['useful']),
        'hallucinated_count': sum(1 for c in all_classifications if c['hallucinated']),
        'junk_count': sum(1 for c in all_classifications if c['junk']),
        'misattributed_count': sum(1 for c in all_classifications if c['misattributed']),
    }
    aggregate['useful_pct'] = round(aggregate['useful_count'] / total * 100, 1)
    aggregate['hallucinated_pct'] = round(aggregate['hallucinated_count'] / total * 100, 1)
    aggregate['junk_pct'] = round(aggregate['junk_count'] / total * 100, 1)
    aggregate['misattributed_pct'] = round(aggregate['misattributed_count'] / total * 100, 1)

    print(f"\n{'='*70}")
    print(f"{adapter_name.upper()} AGGREGATE: {total} memories")
    print(f"  Useful:        {aggregate['useful_count']:4d} ({aggregate['useful_pct']}%)")
    print(f"  Hallucinated:  {aggregate['hallucinated_count']:4d} ({aggregate['hallucinated_pct']}%)")
    print(f"  Junk:          {aggregate['junk_count']:4d} ({aggregate['junk_pct']}%)")
    print(f"  Misattributed: {aggregate['misattributed_count']:4d} ({aggregate['misattributed_pct']}%)")
    print(f"{'='*70}")

    return {
        'adapter': adapter_name,
        'aggregate': aggregate,
        'per_conv': per_conv_stats,
        'classifications': all_classifications,
    }


def main():
    # Load LoCoMo
    with open(DATA_FILE) as f:
        locomo_data = json.load(f)

    which = sys.argv[1] if len(sys.argv) > 1 else "both"

    for adapter_name in (['mem0', 'aurra'] if which == 'both' else [which]):
        ingestion_path = RESULTS_DIR / f"ingestion_{adapter_name}.json"
        if not ingestion_path.exists():
            print(f"❌ {ingestion_path} not found — run ingestion first")
            continue

        with open(ingestion_path) as f:
            ingestion = json.load(f)

        scored = score_adapter(adapter_name, ingestion, locomo_data)

        out_path = RESULTS_DIR / f"junk_score_{adapter_name}.json"
        with open(out_path, 'w') as f:
            json.dump(scored, f, indent=2)
        print(f"\n✅ Saved {out_path}")


if __name__ == "__main__":
    main()
