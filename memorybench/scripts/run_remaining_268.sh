#!/usr/bin/env bash
#
# !!! READ FIRST BEFORE RUNNING !!!
#
# This script ASSUMES ingest.py, query.py, and scripts/score.py accept
# --dataset, --qids, and --output flags. Those flag names were NOT
# verified against the actual scripts when this was written (May 14
# 2026 00:30 ET).
#
# BEFORE FIRST RUN, verify the flags exist:
#     cd ~/Desktop/aurra/benchmarks/longmemeval
#     python3 ingest.py --help
#     python3 query.py --help
#     python3 scripts/score.py --help
#
# If the actual flag names differ, edit this script. The shape of the
# pipeline (3 steps: ingest -> query -> score) is correct; only the
# flag names may need adjustment.
#
# !!! END WARNING !!!
#
# memorybench — run the remaining 268 LongMemEval-S questions
#
# Cost basis: ~$13-15 estimated (see memorybench/methodology.md cost section)
# Wall clock: 3-5 hours including ingestion + query + scoring
# Hard abort threshold: ~$30 spend with no completion in sight
#
# Prereqs (verify before running):
#   1. ANTHROPIC_API_KEY set in env (judge + extraction)
#   2. AURRA_API_KEY set in env (calls to /agent/memories and /agent/query)
#   3. Existing 232-Q memories still in database (see Verification step below)
#   4. Aurra backend deployed with K=30 default (B4, shipped May 13)
#
# Outputs land in benchmarks/longmemeval/outputs/ with a 'remaining_268_' prefix
# so they don't collide with the existing 232-Q outputs.
#
# Last updated: May 14, 2026 ~00:28 ET

set -euo pipefail

# Resolve paths from the script's location
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCHMARK_REPO="$HERE/../.."
AURRA_REPO="${AURRA_REPO:-$HOME/Desktop/aurra}"
LME_DIR="$AURRA_REPO/benchmarks/longmemeval"
DATA_FILE="$HOME/Desktop/aurra-benchmarks/longmemeval/data/longmemeval_s_cleaned.json"
SUBSET_QIDS="$LME_DIR/outputs/clean_qids.txt"
OUTPUTS_DIR="$LME_DIR/outputs"

mkdir -p "$OUTPUTS_DIR"

# ============================================================================
# 0. Prerequisite checks
# ============================================================================
echo "=== Prereq checks ==="

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "ERROR: ANTHROPIC_API_KEY not set"
    exit 1
fi
if [ -z "${AURRA_API_KEY:-}" ]; then
    echo "ERROR: AURRA_API_KEY not set"
    exit 1
fi
if [ ! -f "$DATA_FILE" ]; then
    echo "ERROR: longmemeval_s_cleaned.json not at $DATA_FILE"
    exit 1
fi
if [ ! -f "$SUBSET_QIDS" ]; then
    echo "ERROR: clean_qids.txt not at $SUBSET_QIDS"
    exit 1
fi

echo "  - ANTHROPIC_API_KEY set (prefix: ${ANTHROPIC_API_KEY:0:8}...)"
echo "  - AURRA_API_KEY set (prefix: ${AURRA_API_KEY:0:8}...)"
echo "  - Dataset at $DATA_FILE"
echo "  - 232-Q subset list at $SUBSET_QIDS"
echo ""

# ============================================================================
# 1. Compute the 268-Q remainder list
# ============================================================================
echo "=== Computing remainder QIDs ==="
REMAINING_QIDS="$OUTPUTS_DIR/remaining_268_qids.txt"

python3 - <<PY
import json
from pathlib import Path
with open("$DATA_FILE") as f:
    data = json.load(f)
with open("$SUBSET_QIDS") as f:
    subset = {ln.strip() for ln in f if ln.strip()}
remaining = [q["question_id"] for q in data if q["question_id"] not in subset]
Path("$REMAINING_QIDS").write_text("\n".join(remaining) + "\n")
print(f"  Wrote {len(remaining)} remaining QIDs to $REMAINING_QIDS")
assert len(remaining) == 268, f"expected 268 remaining, got {len(remaining)}"
PY

# ============================================================================
# 2. Verification: are existing 232-Q memories still in the database?
# ============================================================================
echo ""
echo "=== Verifying existing 232-Q ingestion state ==="
echo "  TODO before running: open Supabase and check memory count for the"
echo "  benchmark tenant matches the May 11 baseline (~9,994 sessions"
echo "  ingested). If counts are off by >10%, run a 10-question calibration"
echo "  re-ingest first to verify the pipeline is comparable."
echo ""
read -p "  Have you verified existing memories are intact? (y/N): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "  Aborting. Re-run after verification."
    exit 0
fi

# ============================================================================
# 3. Ingest new sessions (the 9,201 not yet in DB)
# ============================================================================
echo ""
echo "=== Step 3/5: Ingestion (~2-3 hrs, ~$5-7) ==="
echo "  Streaming output to $OUTPUTS_DIR/remaining_268_ingest.log"
echo "  Monitor in another terminal: tail -f $OUTPUTS_DIR/remaining_268_ingest.log"

cd "$LME_DIR"
python3 ingest.py \
    --dataset "$DATA_FILE" \
    --qids "$REMAINING_QIDS" \
    --output "$OUTPUTS_DIR/remaining_268_ingest.log" \
    2>&1 | tee "$OUTPUTS_DIR/remaining_268_ingest.console"

# ============================================================================
# 4. Query the 268 questions
# ============================================================================
echo ""
echo "=== Step 4/5: Query (~30-45 min, ~$5) ==="
echo "  Using K=30 (production default since May 13)"

LME_QUERY_K=30 python3 query.py \
    --dataset "$DATA_FILE" \
    --qids "$REMAINING_QIDS" \
    --output "$OUTPUTS_DIR/remaining_268_hypotheses.jsonl" \
    2>&1 | tee "$OUTPUTS_DIR/remaining_268_query.console"

# ============================================================================
# 5. Judge scoring
# ============================================================================
echo ""
echo "=== Step 5/5: Judge scoring (~15 min, ~$2-3) ==="

python3 scripts/score.py \
    --hypotheses "$OUTPUTS_DIR/remaining_268_hypotheses.jsonl" \
    --dataset "$DATA_FILE" \
    --output "$OUTPUTS_DIR/remaining_268_hypotheses.eval-results" \
    2>&1 | tee "$OUTPUTS_DIR/remaining_268_judge.console"

# ============================================================================
# 6. Combine with the existing 232-Q results
# ============================================================================
echo ""
echo "=== Combine 232 + 268 = 500 ==="
cat "$OUTPUTS_DIR/aurra_hypotheses.day14_k10.jsonl" \
    "$OUTPUTS_DIR/remaining_268_hypotheses.jsonl" \
    > "$OUTPUTS_DIR/full_500_hypotheses.jsonl"

python3 scripts/score.py \
    --hypotheses "$OUTPUTS_DIR/full_500_hypotheses.jsonl" \
    --dataset "$DATA_FILE" \
    --output "$OUTPUTS_DIR/full_500_hypotheses.eval-results" \
    2>&1 | tee "$OUTPUTS_DIR/full_500_judge.console"

echo ""
echo "=== DONE ==="
echo "Full 500-Q results: $OUTPUTS_DIR/full_500_hypotheses.eval-results"
echo "Next: update memorybench/results.md with the new headline number"
echo "Next: update memorybench/comparison.md \u2014 the 'subset' caveat dissolves"
