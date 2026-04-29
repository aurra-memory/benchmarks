"""
LoCoMo benchmark — ingestion phase.

Runs both Mem0 and Aurra adapters on all 10 LoCoMo conversations.
For each conversation, feeds every session and captures:
  - Total memories created
  - Time taken
  - Per-memory content for later scoring

Saves raw outputs to results/ for downstream scoring.
"""

import json
import time
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add adapters to path
sys.path.insert(0, str(Path(__file__).parent / "adapters"))
from mem0_runner import Mem0Adapter
from aurra_runner import AurraAdapter

DATA_FILE = Path(__file__).parent / "data" / "locomo10.json"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def parse_session_messages(session_turns: list) -> list:
    """Convert LoCoMo session format to our standard messages format."""
    messages = []
    for turn in session_turns:
        speaker = turn.get("speaker", "user")
        text = turn.get("text", "").strip()
        if not text:
            continue
        # LoCoMo speakers are personal names, not user/assistant
        # Map first speaker to "user", second to "assistant" by alphabetical order
        # (we'll normalize per-conversation)
        messages.append({
            "speaker_name": speaker,
            "content": text,
        })
    return messages


def normalize_speakers_for_chat(messages: list, speaker_a: str, speaker_b: str) -> list:
    """Map LoCoMo speakers to user/assistant roles."""
    normalized = []
    for msg in messages:
        if msg["speaker_name"] == speaker_a:
            role = "user"
        elif msg["speaker_name"] == speaker_b:
            role = "assistant"
        else:
            role = "user"
        normalized.append({"role": role, "content": msg["content"]})
    return normalized


def run_adapter_on_conversation(adapter, conv: dict, conv_idx: int, total_convs: int):
    """Feed one LoCoMo conversation (all sessions) into the adapter."""
    sample_id = conv["sample_id"]
    speaker_a = conv["conversation"]["speaker_a"]
    speaker_b = conv["conversation"]["speaker_b"]

    # Use sample_id as tenant_id for isolation
    tenant_id = f"locomo_{sample_id}"

    print(f"\n[{adapter.name}] [{conv_idx + 1}/{total_convs}] {sample_id} — {speaker_a} & {speaker_b}")

    # Reset any prior data for this tenant
    adapter.reset_user(tenant_id)

    # Find all session keys
    conv_data = conv["conversation"]
    session_keys = sorted([
        k for k in conv_data.keys()
        if k.startswith("session_") and not k.endswith("_date_time") and not k.endswith("_summary")
    ], key=lambda k: int(k.split("_")[1]))

    total_sessions = len(session_keys)
    successful_sessions = 0
    session_results = []
    start_time = time.time()

    for i, sk in enumerate(session_keys):
        session_turns = conv_data.get(sk, [])
        if not isinstance(session_turns, list) or not session_turns:
            continue

        raw_messages = parse_session_messages(session_turns)
        if not raw_messages:
            continue

        messages = normalize_speakers_for_chat(raw_messages, speaker_a, speaker_b)
        if not messages:
            continue

        session_start = time.time()
        result = adapter.add_session(tenant_id, messages)
        session_time = time.time() - session_start

        if result.get("success"):
            successful_sessions += 1

        session_results.append({
            "session_key": sk,
            "n_messages": len(messages),
            "result": {
                "success": result.get("success"),
                "memories_created": result.get("memories_created", 0),
                "error": result.get("error"),
            },
            "time_sec": round(session_time, 2),
        })

        # Print progress
        status = "✓" if result.get("success") else "✗"
        print(f"   {status} session {i+1}/{total_sessions} ({len(messages)} msgs, {session_time:.1f}s, +{result.get('memories_created', 0)} mems)")

    # Wait for any async indexing (longer for Mem0 to settle)
    wait_time = 120 if adapter.name == "mem0" else 30
    print(f"   ⏳ Waiting for indexing (up to {wait_time}s)...")
    final_count = adapter.wait_for_processing(tenant_id, expected_min=1, max_wait=wait_time) if hasattr(adapter, "wait_for_processing") else 0

    # Fetch all memories for the conversation
    print(f"   📥 Fetching all stored memories...")
    all_memories = adapter.get_all_memories(tenant_id)

    elapsed = time.time() - start_time

    print(f"   📊 {sample_id} complete: {successful_sessions}/{total_sessions} sessions OK, {len(all_memories)} memories stored, {elapsed:.1f}s total")

    return {
        "sample_id": sample_id,
        "tenant_id": tenant_id,
        "speaker_a": speaker_a,
        "speaker_b": speaker_b,
        "total_sessions": total_sessions,
        "successful_sessions": successful_sessions,
        "session_results": session_results,
        "stored_memories": [
            {"id": m["id"], "memory": m["memory"], "topic": m.get("topic")}
            for m in all_memories
        ],
        "stored_count": len(all_memories),
        "elapsed_sec": round(elapsed, 2),
    }


def run_full_benchmark(adapter, conversations):
    """Run adapter on all conversations, save results."""
    out_path = RESULTS_DIR / f"ingestion_{adapter.name}.json"
    print(f"\n{'='*70}")
    print(f"INGESTION: {adapter.name.upper()}")
    print(f"Output: {out_path}")
    print(f"{'='*70}")

    benchmark_start = time.time()
    all_results = []
    for i, conv in enumerate(conversations):
        try:
            result = run_adapter_on_conversation(adapter, conv, i, len(conversations))
            all_results.append(result)
            # Save incrementally so a crash doesn't lose progress
            with open(out_path, "w") as f:
                json.dump({
                    "adapter": adapter.name,
                    "completed_count": len(all_results),
                    "total_count": len(conversations),
                    "results": all_results,
                }, f, indent=2)
        except Exception as e:
            print(f"   ❌ FAILED on {conv.get('sample_id')}: {e}")
            all_results.append({
                "sample_id": conv.get("sample_id"),
                "error": str(e),
            })

    elapsed = time.time() - benchmark_start
    total_memories = sum(r.get("stored_count", 0) for r in all_results)
    print(f"\n{'='*70}")
    print(f"{adapter.name.upper()} DONE: {len(all_results)} convs, {total_memories} total memories, {elapsed/60:.1f} min")
    print(f"{'='*70}")

    return all_results


def main():
    # Load LoCoMo data
    with open(DATA_FILE) as f:
        conversations = json.load(f)
    print(f"Loaded {len(conversations)} LoCoMo conversations")

    # Pick which adapter(s) to run
    which = sys.argv[1] if len(sys.argv) > 1 else "both"

    if which in ("both", "mem0"):
        mem0 = Mem0Adapter()
        run_full_benchmark(mem0, conversations)

    if which in ("both", "aurra"):
        aurra = AurraAdapter()
        run_full_benchmark(aurra, conversations)

    print("\n✅ All ingestion complete.")
    print(f"Results saved to: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
