"""
Mem0 adapter for the LoCoMo benchmark.
"""

import os
import time
from typing import List, Dict, Any
from mem0 import MemoryClient


class Mem0Adapter:
    """Wraps Mem0 cloud API. Same interface as AurraAdapter."""

    name = "mem0"

    def __init__(self):
        api_key = os.getenv("MEM0_API_KEY")
        if not api_key:
            raise ValueError("MEM0_API_KEY not set in environment")
        self.client = MemoryClient(api_key=api_key)

    def add_session(self, user_id: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Feed a dialog session to Mem0 (async — needs wait_for_processing).

        Throttles after every call to avoid silent free-tier rate limiting.
        """
        try:
            result = self.client.add(messages, user_id=user_id)
            # Throttle: 30s between sessions to avoid free-tier silent drops
            time.sleep(30)
            return {
                "success": True,
                "raw_response": result,
                "memories_created": len(result.get("results", [])) if isinstance(result, dict) else 0,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "memories_created": 0}

    def wait_for_processing(self, user_id: str, expected_min: int = 1, max_wait: int = 60) -> int:
        """Poll until at least expected_min memories appear, or timeout."""
        start = time.time()
        while time.time() - start < max_wait:
            mems = self.get_all_memories(user_id)
            if len(mems) >= expected_min:
                return len(mems)
            time.sleep(2)
        return len(self.get_all_memories(user_id))

    def get_all_memories(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieve every memory stored for a user. Uses new filters API."""
        try:
            memories = self.client.get_all(filters={"user_id": user_id}, version="v2")
            if isinstance(memories, dict):
                memories = memories.get("results", [])
            return [
                {
                    "id": m.get("id"),
                    "memory": m.get("memory") or m.get("text") or "",
                    "metadata": m.get("metadata", {}),
                    "created_at": m.get("created_at"),
                    "raw": m,
                }
                for m in memories
            ]
        except Exception as e:
            # Try without version param (older SDKs)
            try:
                memories = self.client.get_all(filters={"user_id": user_id})
                if isinstance(memories, dict):
                    memories = memories.get("results", [])
                return [
                    {
                        "id": m.get("id"),
                        "memory": m.get("memory") or m.get("text") or "",
                        "metadata": m.get("metadata", {}),
                        "created_at": m.get("created_at"),
                        "raw": m,
                    }
                    for m in memories
                ]
            except Exception as e2:
                print(f"⚠️ Mem0 get_all failed for {user_id}: {e2}")
                return []

    def query(self, user_id: str, question: str, limit: int = 10) -> Dict[str, Any]:
        """Search memories for a question. Returns retrieved context."""
        try:
            # Try v2 filters API first
            try:
                results = self.client.search(
                    query=question,
                    filters={"user_id": user_id},
                    limit=limit,
                    version="v2",
                )
            except Exception:
                # Fallback to old API
                results = self.client.search(query=question, user_id=user_id, limit=limit)

            if isinstance(results, dict):
                results = results.get("results", [])

            context = "\n".join([
                f"- {m.get('memory') or m.get('text') or ''}"
                for m in results
            ])

            return {
                "success": True,
                "retrieved_memories": results,
                "context": context,
                "memory_count": len(results),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "context": "",
                "retrieved_memories": [],
                "memory_count": 0,
            }

    def reset_user(self, user_id: str) -> bool:
        """Delete all memories for a user. Tries multiple API shapes."""
        # Get all memory IDs and delete one by one (most reliable)
        try:
            memories = self.get_all_memories(user_id)
            for m in memories:
                mid = m.get("id")
                if mid:
                    try:
                        self.client.delete(memory_id=mid)
                    except Exception:
                        pass
            return True
        except Exception as e:
            print(f"⚠️ Mem0 reset (per-id) failed for {user_id}: {e}")
            return False


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    adapter = Mem0Adapter()
    test_user = f"benchmark_smoketest_{int(time.time())}"

    print(f"Testing with user_id: {test_user}")

    print("→ Adding session...")
    result = adapter.add_session(test_user, [
        {"role": "user", "content": "Hi, my name is Alice and I love pickleball."},
        {"role": "assistant", "content": "Nice to meet you, Alice! How long have you been playing?"},
        {"role": "user", "content": "About 2 years now. I play in a league on Tuesdays."},
    ])
    print(f"   Add result: success={result['success']}, status={result.get('raw_response', {}).get('status', 'n/a')}")

    print("→ Waiting for async processing (up to 60s)...")
    n = adapter.wait_for_processing(test_user, expected_min=1, max_wait=60)
    print(f"   Found {n} memories after wait")

    print("→ Retrieving memories...")
    memories = adapter.get_all_memories(test_user)
    print(f"   Got {len(memories)} memories:")
    for m in memories[:5]:
        print(f"   • {m['memory'][:120]}")

    print("→ Querying 'When does Alice play pickleball?'...")
    q_result = adapter.query(test_user, "When does Alice play pickleball?")
    print(f"   Success: {q_result['success']}, retrieved {q_result['memory_count']} memories")
    if q_result['context']:
        print(f"   Context preview: {q_result['context'][:300]}")

    print("→ Resetting user...")
    adapter.reset_user(test_user)
    print("✅ Smoke test complete")
