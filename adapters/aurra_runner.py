"""
Aurra adapter for the LoCoMo benchmark.
Mirrors the Mem0Adapter interface. Uses tenant_id for per-conversation isolation.
"""

import os
import time
from typing import List, Dict, Any
import httpx


class AurraAdapter:
    """Wraps Aurra agent API. Same interface as Mem0Adapter."""

    name = "aurra"

    def __init__(self, base_url: str = None):
        self.api_key = os.getenv("AURRA_API_KEY")
        if not self.api_key:
            raise ValueError("AURRA_API_KEY not set in environment")
        self.base_url = base_url or "https://aurra-production-ace3.up.railway.app"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self.client = httpx.Client(timeout=60.0)

    def add_session(self, user_id: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Feed a dialog session to Aurra.
        We extract decisions from the conversation by sending the full session as one
        memory write, letting Aurra's extraction pipeline process it.

        Note: Aurra's agent API currently writes one memory per call. To match Mem0's
        session-level extraction, we concatenate the dialog and write it as one block.
        """
        # Convert messages to a single dialog block
        dialog_text = "\n".join([
            f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}"
            for msg in messages
        ])

        try:
            r = self.client.post(
                f"{self.base_url}/agent/memories",
                headers=self.headers,
                json={
                    "messages": messages,
                    "tenant_id": user_id,
                    "session_id": user_id,
                },
            )
            r.raise_for_status()
            data = r.json()
            return {
                "success": True,
                "raw_response": data,
                "memories_created": data.get("saved_count", 0),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "memories_created": 0}

    def wait_for_processing(self, user_id: str, expected_min: int = 1, max_wait: int = 30) -> int:
        """
        Aurra writes synchronously, but embeddings may be generated async.
        Brief poll for any indexing latency.
        """
        start = time.time()
        while time.time() - start < max_wait:
            mems = self.get_all_memories(user_id)
            if len(mems) >= expected_min:
                return len(mems)
            time.sleep(1)
        return len(self.get_all_memories(user_id))

    def get_all_memories(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieve every memory stored for a tenant."""
        try:
            r = self.client.get(
                f"{self.base_url}/agent/memories",
                headers=self.headers,
                params={"tenant_id": user_id, "limit": 1000},
            )
            r.raise_for_status()
            data = r.json()
            memories = data.get("memories", [])
            return [
                {
                    "id": m.get("id"),
                    "memory": m.get("decision") or m.get("summary") or m.get("original_message", ""),
                    "topic": m.get("topic"),
                    "importance": m.get("importance"),
                    "created_at": m.get("created_at"),
                    "raw": m,
                }
                for m in memories
            ]
        except Exception as e:
            print(f"⚠️ Aurra get_all failed for {user_id}: {e}")
            return []

    def query(self, user_id: str, question: str, limit: int = 10) -> Dict[str, Any]:
        """Query Aurra's agent endpoint with semantic search."""
        try:
            r = self.client.post(
                f"{self.base_url}/agent/query",
                headers=self.headers,
                json={"question": question, "limit": limit, "tenant_id": user_id},
            )
            r.raise_for_status()
            data = r.json()
            memories = data.get("memories", []) or data.get("results", [])

            context = "\n".join([
                f"- {m.get('decision') or m.get('summary') or m.get('memory', '') or m.get('original_message', '')}"
                for m in memories
            ])

            return {
                "success": True,
                "retrieved_memories": memories,
                "context": context,
                "memory_count": len(memories),
                "raw_response": data,
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
        """Delete all memories for a tenant."""
        try:
            r = self.client.delete(
                f"{self.base_url}/agent/memories",
                headers=self.headers,
                params={"tenant_id": user_id},
            )
            r.raise_for_status()
            return True
        except Exception as e:
            print(f"⚠️ Aurra reset failed for {user_id}: {e}")
            return False


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    adapter = AurraAdapter()
    test_user = f"benchmark_smoketest_{int(time.time())}"

    print(f"Testing with tenant_id: {test_user}")

    print("→ Adding session...")
    result = adapter.add_session(test_user, [
        {"role": "user", "content": "Hi, my name is Alice and I love pickleball."},
        {"role": "assistant", "content": "Nice to meet you, Alice! How long have you been playing?"},
        {"role": "user", "content": "About 2 years now. I play in a league on Tuesdays."},
    ])
    print(f"   Add result: success={result['success']}, memory_id={result.get('raw_response', {}).get('memory_id', 'n/a')[:8] if result.get('raw_response', {}).get('memory_id') else 'n/a'}")

    print("→ Waiting for embedding generation (up to 30s)...")
    n = adapter.wait_for_processing(test_user, expected_min=1, max_wait=30)
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

    print("→ Resetting tenant...")
    adapter.reset_user(test_user)
    print("✅ Smoke test complete")
