"""
LoCoMo benchmark — answer accuracy phase.

For each adapter, runs a stratified sample of LoCoMo questions through query()
and uses Claude as LLM-as-judge to score answer accuracy against ground truth.

Sample: 500 questions stratified across categories 1-4 (excludes adversarial cat 5).
"""

import json
import os
import sys
import time
import random
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv
import anthropic

load_dotenv()

RESULTS_DIR = Path(__file__).parent / "results"
DATA_FILE = Path(__file__).parent / "data" / "locomo10.json"

sys.path.insert(0, str(Path(__file__).parent / "adapters"))
from mem0_runner import Mem0Adapter
from aurra_runner import AurraAdapter

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Stratified sample: 125 + 125 + 96 (all of cat 3) + 154 = 500
SAMPLE_PER_CATEGORY = {1: 125, 2: 125, 3: 96, 4: 154}
RANDOM_SEED = 42  # Reproducible


def stratified_sample(locomo_data: list) -> list:
    """Build a stratified sample of 500 questions across all 10 conversations."""
    random.seed(RANDOM_SEED)

    # Group all questions by category, with conv reference
    by_category = defaultdict(list)
    for conv in locomo_data:
        sample_id = conv["sample_id"]
        for q in conv["qa"]:
            cat = q.get("category")
            if cat in (1, 2, 3, 4):
                by_category[cat].append({
                    "sample_id": sample_id,
                    "question": q["question"],
                    "answer": q["answer"],
                    "evidence": q.get("evidence", []),
                    "category": cat,
                })

    # Sample
    sample = []
    for cat, target in SAMPLE_PER_CATEGORY.items():
        pool = by_category[cat]
        n = min(target, len(pool))
        sample.extend(random.sample(pool, n))
        print(f"  Cat {cat}: sampled {n}/{len(pool)}")

    print(f"\nTotal sample: {len(sample)} questions")
    return sample


def run_adapter_qa(adapter, sample: list) -> list:
    """Query each question and capture answer."""
    results = []
    for i, q in enumerate(sample):
        tenant_id = f"locomo_{q['sample_id']}"
        try:
            r = adapter.query(tenant_id, q["question"])
            results.append({
                "sample_id": q["sample_id"],
                "category": q["category"],
                "question": q["question"],
                "ground_truth": q["answer"],
                "retrieved_context": r.get("context", "")[:1500],
                "retrieved_count": r.get("memory_count", 0),
                "raw_response": r.get("raw_response", {}),
            })
        except Exception as e:
            results.append({
                "sample_id": q["sample_id"],
                "category": q["category"],
                "question": q["question"],
                "ground_truth": q["answer"],
                "error": str(e),
            })

        if (i + 1) % 25 == 0:
            print(f"   Queried {i+1}/{len(sample)}")

    return results


def grade_answer(question: str, ground_truth: str, retrieved_context: str) -> dict:
    """Use Claude to judge if the retrieved context can answer the question correctly."""
    if not retrieved_context.strip():
        return {"correct": False, "reason": "No memories retrieved"}

    prompt = f"""You are grading an AI memory system. Given a question, the correct answer, and what the system retrieved, determine if the retrieved context contains enough information to answer correctly.

QUESTION: {question}
CORRECT ANSWER: {ground_truth}
RETRIEVED MEMORIES:
{retrieved_context}

Score this:
- "correct": true if the retrieved context contains information that would let you derive the correct answer
- "partial": true if some relevant info but not enough for the full answer
- "reason": brief (max 20 words)

Return ONLY a JSON object like {{"correct": true, "partial": false, "reason": "..."}}."""

    try:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        return {"correct": False, "partial": False, "reason": f"Judge error: {e}"}


def grade_all(qa_results: list) -> list:
    """Grade every QA result."""
    graded = []
    for i, r in enumerate(qa_results):
        if "error" in r:
            graded.append({**r, "grade": {"correct": False, "reason": "Query error"}})
            continue
        g = grade_answer(r["question"], r["ground_truth"], r["retrieved_context"])
        graded.append({**r, "grade": g})
        if (i + 1) % 25 == 0:
            print(f"   Graded {i+1}/{len(qa_results)}")
    return graded


def compute_accuracy(graded: list) -> dict:
    """Compute per-category and overall accuracy."""
    by_cat = defaultdict(lambda: {"total": 0, "correct": 0, "partial": 0})
    for r in graded:
        cat = r["category"]
        by_cat[cat]["total"] += 1
        if r["grade"].get("correct"):
            by_cat[cat]["correct"] += 1
        if r["grade"].get("partial"):
            by_cat[cat]["partial"] += 1

    summary = {"per_category": {}}
    total = 0
    correct = 0
    for cat, stats in by_cat.items():
        acc = round(stats["correct"] / stats["total"] * 100, 1) if stats["total"] else 0
        summary["per_category"][cat] = {**stats, "accuracy_pct": acc}
        total += stats["total"]
        correct += stats["correct"]
    summary["overall"] = {
        "total": total,
        "correct": correct,
        "accuracy_pct": round(correct / total * 100, 1) if total else 0,
    }
    return summary


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "both"

    with open(DATA_FILE) as f:
        locomo_data = json.load(f)

    print("Building stratified sample...")
    sample = stratified_sample(locomo_data)

    # Save sample for reference
    with open(RESULTS_DIR / "qa_sample.json", "w") as f:
        json.dump(sample, f, indent=2)

    for adapter_name in (["mem0", "aurra"] if which == "both" else [which]):
        print(f"\n{'='*70}")
        print(f"Q&A: {adapter_name.upper()}")
        print(f"{'='*70}")

        adapter = Mem0Adapter() if adapter_name == "mem0" else AurraAdapter()

        print(f"\nQuerying {len(sample)} questions...")
        qa_results = run_adapter_qa(adapter, sample)

        print(f"\nGrading answers...")
        graded = grade_all(qa_results)

        accuracy = compute_accuracy(graded)
        print(f"\n{adapter_name.upper()} ACCURACY:")
        print(f"  Overall: {accuracy['overall']['correct']}/{accuracy['overall']['total']} = {accuracy['overall']['accuracy_pct']}%")
        for cat, stats in sorted(accuracy['per_category'].items()):
            print(f"  Cat {cat}: {stats['correct']}/{stats['total']} = {stats['accuracy_pct']}%")

        out_path = RESULTS_DIR / f"qa_accuracy_{adapter_name}.json"
        with open(out_path, "w") as f:
            json.dump({"adapter": adapter_name, "accuracy": accuracy, "graded": graded}, f, indent=2)
        print(f"\n✅ Saved {out_path}")


if __name__ == "__main__":
    main()
