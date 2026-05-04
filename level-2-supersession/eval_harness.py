"""
Level 2 Supersession Classifier — Eval Harness

Runs prompt v0 (or vN) against test_cases_v3.jsonl on both haiku and sonnet
in parallel, computes stratified precision/recall/accuracy, outputs results JSON.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python eval_harness.py --prompt level2_prompt_v0.md --cases test_cases_v3.jsonl

Requirements:
    pip install anthropic>=0.40.0
"""

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict, Counter
from datetime import datetime, timezone

try:
    import anthropic
except ImportError:
    print("Install: pip install anthropic --break-system-packages")
    sys.exit(1)


MODELS_TO_TEST = [
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-6",
]

MAX_PARALLEL = 2   # Tier 1 limits force low parallelism (50 req/min haiku, 30k input tok/min sonnet)
MAX_RETRIES = 5
RETRY_BACKOFF = 2.0


def extract_system_prompt(md_path: str) -> tuple[str, str]:
    """Pull the system prompt block and few-shot examples from the markdown file."""
    with open(md_path) as f:
        text = f.read()

    # System prompt is the first ``` block
    m = re.search(r"## System prompt\s*\n```\s*\n(.*?)\n```", text, re.DOTALL)
    if not m:
        raise ValueError(f"Could not find system prompt block in {md_path}")
    system = m.group(1).strip()

    # Few-shot examples are inline; we'll prepend them to the user prompt
    # by parsing each "### Example N — verdict" block
    examples = []
    for em in re.finditer(
        r"### Example \d+ — \w+\s*\n\s*OLD memory:\s*(.+?)\n\s*NEW memory:\s*(.+?)\n\s*(\{.*?\})",
        text,
        re.DOTALL,
    ):
        examples.append({
            "old": em.group(1).strip(),
            "new": em.group(2).strip(),
            "answer": em.group(3).strip(),
        })

    return system, examples


def build_user_message(old: str, new: str, examples: list) -> str:
    """Build the user-side prompt with few-shot examples followed by the actual query."""
    parts = []
    for ex in examples:
        parts.append(f"OLD memory: {ex['old']}\nNEW memory: {ex['new']}\n\n{ex['answer']}\n")
    parts.append(f"OLD memory: {old}\nNEW memory: {new}\n\nClassify the relationship between OLD and NEW.")
    return "\n---\n".join(parts)


def parse_response(text: str) -> dict | None:
    """Extract the JSON verdict object from the model output. Robust to common LLM wrappers."""
    if not text:
        return None
    # Strip markdown code fences
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Drop opening fence (might be ```json or just ```)
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        # Drop closing fence
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    cleaned = cleaned.strip()
    # Try direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Find any { ... } block containing "verdict" — handles nested quotes too
    # Greedy match for the outermost JSON object that contains "verdict"
    matches = re.findall(r"\{[^{}]*?\"verdict\"[^{}]*?\}", cleaned, re.DOTALL)
    for m in matches:
        try:
            return json.loads(m)
        except json.JSONDecodeError:
            continue
    # Last resort: find anything that looks like a JSON object with verdict key
    # This handles cases where the JSON has nested objects we didn't account for
    m = re.search(r"(\{(?:[^{}]|\{[^{}]*\})*\})", cleaned, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None


_last_request_times = []
_throttle_lock = None

def _throttle():
    """Limit to ~25 requests/min globally. Call before each API request."""
    import threading, time as _time
    global _throttle_lock
    if _throttle_lock is None:
        _throttle_lock = threading.Lock()
    with _throttle_lock:
        now = _time.time()
        # Drop entries older than 60s
        cutoff = now - 60.0
        while _last_request_times and _last_request_times[0] < cutoff:
            _last_request_times.pop(0)
        # If at limit, wait until the oldest entry expires
        MAX_REQ_PER_MIN = 25
        if len(_last_request_times) >= MAX_REQ_PER_MIN:
            wait = 60.0 - (now - _last_request_times[0]) + 0.1
            if wait > 0:
                _time.sleep(wait)
            now = _time.time()
            cutoff = now - 60.0
            while _last_request_times and _last_request_times[0] < cutoff:
                _last_request_times.pop(0)
        _last_request_times.append(now)


def classify_one(client, model: str, system: str, user: str, case_id: str) -> dict:
    """Send one classification call; retry on transient errors."""
    last_err = None
    for attempt in range(MAX_RETRIES):
        _throttle()
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=200,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            text = resp.content[0].text if resp.content else ""
            parsed = parse_response(text)
            if parsed and "verdict" in parsed:
                return {
                    "case_id": case_id,
                    "model": model,
                    "raw": text,
                    "parsed": parsed,
                    "error": None,
                    "input_tokens": resp.usage.input_tokens,
                    "output_tokens": resp.usage.output_tokens,
                }
            last_err = f"could not parse verdict from: {text[:200]}"
        except Exception as e:
            last_err = str(e)
            # Longer backoff for rate limits
            if "429" in last_err or "rate_limit" in last_err.lower():
                time.sleep(15 + (RETRY_BACKOFF ** attempt))
                continue
        time.sleep(RETRY_BACKOFF ** attempt)

    return {
        "case_id": case_id,
        "model": model,
        "raw": "",
        "parsed": None,
        "error": last_err,
        "input_tokens": 0,
        "output_tokens": 0,
    }


def run_eval(prompt_path: str, cases_path: str, models: list[str]) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY env var not set")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    system, examples = extract_system_prompt(prompt_path)

    print(f"System prompt: {len(system)} chars")
    print(f"Few-shot examples: {len(examples)}")

    # Load cases
    cases = []
    with open(cases_path) as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    print(f"Loaded {len(cases)} test cases")

    # Build all jobs
    jobs = []
    for model in models:
        for case in cases:
            user = build_user_message(case["old"], case["new"], examples)
            jobs.append((model, case["id"], system, user))

    print(f"Total API calls: {len(jobs)} ({len(models)} models x {len(cases)} cases)")
    print(f"Running with {MAX_PARALLEL} parallel workers...\n")

    results = []
    started = time.time()
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        futures = {
            pool.submit(classify_one, client, m, s, u, cid): (m, cid)
            for (m, cid, s, u) in jobs
        }
        done = 0
        for fut in as_completed(futures):
            r = fut.result()
            results.append(r)
            done += 1
            if done % 20 == 0:
                print(f"  {done}/{len(jobs)} done ({time.time()-started:.0f}s)")

    elapsed = time.time() - started
    print(f"\nAll calls done in {elapsed:.0f}s")

    return {"results": results, "cases": cases, "elapsed_seconds": elapsed, "timestamp": datetime.now(timezone.utc).isoformat()}


def compute_metrics(eval_data: dict) -> dict:
    cases_by_id = {c["id"]: c for c in eval_data["cases"]}
    results = eval_data["results"]

    by_model = defaultdict(list)
    for r in results:
        by_model[r["model"]].append(r)

    metrics = {}
    for model, model_results in by_model.items():
        total = 0
        correct = 0
        errors = 0
        # Per-verdict counts for precision/recall
        # tp[v]: predicted v AND ground truth v
        # fp[v]: predicted v AND ground truth != v
        # fn[v]: ground truth v AND predicted != v
        tp = Counter()
        fp = Counter()
        fn = Counter()
        # Per-category accuracy
        cat_total = Counter()
        cat_correct = Counter()
        # Confidence-gated precision (only count "supersedes" predictions with confidence >= 0.85)
        gated_supersedes_predicted = 0
        gated_supersedes_correct = 0
        # Token usage
        in_tok = 0
        out_tok = 0
        # Per-case detail
        case_details = []
        # Disagreements list
        disagreements = []

        for r in model_results:
            case = cases_by_id[r["case_id"]]
            in_tok += r["input_tokens"]
            out_tok += r["output_tokens"]
            if r["error"] or not r["parsed"]:
                errors += 1
                case_details.append({
                    "case_id": r["case_id"],
                    "category": case["category"],
                    "ground_truth": case["ground_truth"],
                    "predicted": None,
                    "confidence": None,
                    "match": False,
                    "error": r.get("error"),
                })
                continue

            predicted = r["parsed"].get("verdict")
            confidence = r["parsed"].get("confidence", 0)
            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                confidence = 0
            ground_truth = case["ground_truth"]
            match = predicted == ground_truth

            total += 1
            cat_total[case["category"]] += 1
            if match:
                correct += 1
                cat_correct[case["category"]] += 1
                tp[predicted] += 1
            else:
                if predicted:
                    fp[predicted] += 1
                fn[ground_truth] += 1
                disagreements.append({
                    "case_id": r["case_id"],
                    "category": case["category"],
                    "old": case["old"],
                    "new": case["new"],
                    "ground_truth": ground_truth,
                    "predicted": predicted,
                    "confidence": confidence,
                    "reasoning": r["parsed"].get("reasoning", ""),
                })

            # Confidence-gated supersedes precision
            if predicted == "supersedes" and confidence >= 0.85:
                gated_supersedes_predicted += 1
                if ground_truth == "supersedes":
                    gated_supersedes_correct += 1

            case_details.append({
                "case_id": r["case_id"],
                "category": case["category"],
                "ground_truth": ground_truth,
                "predicted": predicted,
                "confidence": confidence,
                "match": match,
            })

        accuracy = correct / total if total else 0
        precision = {}
        recall = {}
        for v in ["supersedes", "refines", "independent"]:
            p_denom = tp[v] + fp[v]
            r_denom = tp[v] + fn[v]
            precision[v] = tp[v] / p_denom if p_denom else None
            recall[v] = tp[v] / r_denom if r_denom else None

        gated_precision = (
            gated_supersedes_correct / gated_supersedes_predicted
            if gated_supersedes_predicted else None
        )

        cat_accuracy = {
            cat: (cat_correct[cat] / cat_total[cat]) for cat in sorted(cat_total)
        }

        # Cost (pricing as of May 2026)
        prices = {
            "claude-haiku-4-5-20251001": (1.0, 5.0),
            "claude-sonnet-4-6": (3.0, 15.0),
            "claude-opus-4-7": (5.0, 25.0),
        }
        in_price, out_price = prices.get(model, (0, 0))
        cost = (in_tok * in_price + out_tok * out_price) / 1_000_000

        metrics[model] = {
            "total": total,
            "correct": correct,
            "errors": errors,
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "gated_supersedes_precision": gated_precision,
            "gated_supersedes_predicted_count": gated_supersedes_predicted,
            "category_accuracy": cat_accuracy,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "cost_usd": round(cost, 4),
            "case_details": case_details,
            "disagreements": disagreements,
        }

    return metrics


def print_summary(metrics: dict):
    print("\n" + "=" * 70)
    print("EVAL SUMMARY")
    print("=" * 70)
    for model, m in metrics.items():
        print(f"\n{model}")
        print(f"  Accuracy:        {m['accuracy']*100:.1f}% ({m['correct']}/{m['total']})")
        print(f"  Errors (no parse): {m['errors']}")
        print(f"  Cost: ${m['cost_usd']}")
        print(f"  Precision per verdict:")
        for v, p in m["precision"].items():
            p_str = f"{p*100:.1f}%" if p is not None else "n/a"
            print(f"    {v:14}: {p_str}")
        print(f"  Recall per verdict:")
        for v, r in m["recall"].items():
            r_str = f"{r*100:.1f}%" if r is not None else "n/a"
            print(f"    {v:14}: {r_str}")
        gp = m["gated_supersedes_precision"]
        gp_str = f"{gp*100:.1f}%" if gp is not None else "n/a"
        print(f"  GATED supersedes precision (conf>=0.85): {gp_str} ({m['gated_supersedes_predicted_count']} predictions)")
        print(f"  Per-category accuracy:")
        for cat, acc in sorted(m["category_accuracy"].items(), key=lambda x: x[1]):
            flag = " <-- WORST" if acc < 0.7 else ""
            print(f"    {cat:24} {acc*100:5.1f}%{flag}")

    # Acceptance criteria check
    print("\n" + "=" * 70)
    print("ACCEPTANCE CRITERIA CHECK")
    print("=" * 70)
    print("Required: gated supersedes precision >= 95%, recall >= 60%, overall accuracy >= 80%")
    for model, m in metrics.items():
        gp = m["gated_supersedes_precision"] or 0
        sup_recall = m["recall"].get("supersedes") or 0
        acc = m["accuracy"]
        passes = gp >= 0.95 and sup_recall >= 0.60 and acc >= 0.80
        status = "PASS" if passes else "FAIL"
        print(f"  {model}: {status}")
        print(f"    gated precision: {gp*100:.1f}% (need 95%)")
        print(f"    supersedes recall: {sup_recall*100:.1f}% (need 60%)")
        print(f"    accuracy: {acc*100:.1f}% (need 80%)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--prompt", default="level2_prompt_v0.md")
    p.add_argument("--cases", default="test_cases_v3.jsonl")
    p.add_argument("--out", default="eval_results.json")
    p.add_argument("--models", nargs="+", default=MODELS_TO_TEST)
    args = p.parse_args()

    eval_data = run_eval(args.prompt, args.cases, args.models)
    metrics = compute_metrics(eval_data)

    # Build raw lookup for debugging — keyed by (model, case_id)
    raw_responses = {}
    for r in eval_data["results"]:
        raw_responses[f"{r['model']}|{r['case_id']}"] = {
            "raw": r["raw"],
            "error": r["error"],
        }

    output = {
        "prompt_file": args.prompt,
        "cases_file": args.cases,
        "models": args.models,
        "elapsed_seconds": eval_data["elapsed_seconds"],
        "timestamp": eval_data["timestamp"],
        "metrics": metrics,
        "raw_responses": raw_responses,
    }

    with open(args.out, "w") as f:
        json.dump(output, f, indent=2)

    print_summary(metrics)
    print(f"\nFull results: {args.out}")
    print(f"Disagreements per model are inside metrics[model]['disagreements']")


if __name__ == "__main__":
    main()
