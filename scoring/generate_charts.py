"""
Generate publication-quality charts comparing Mem0 and Aurra junk rates.

Outputs to charts/ directory.
"""

import json
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

RESULTS_DIR = Path(__file__).parent.parent / "results"
CHARTS_DIR = Path(__file__).parent.parent / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

# Aurra brand colors (clean, professional)
AURRA_COLOR = "#2563EB"  # blue
MEM0_COLOR = "#F87171"   # warm red
USEFUL_COLOR = "#10B981" # green
HALLUC_COLOR = "#EF4444" # red
JUNK_COLOR = "#94A3B8"   # gray
MISAT_COLOR = "#F59E0B"  # amber

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})


def load_scores():
    """Load junk_score JSONs for both adapters."""
    out = {}
    for name in ["mem0", "aurra"]:
        path = RESULTS_DIR / f"junk_score_{name}.json"
        if path.exists():
            with open(path) as f:
                out[name] = json.load(f)
        else:
            print(f"⚠️ {path} not found")
    return out


def chart_junk_rate_overall(scores: dict):
    """Bar chart: stacked composition of memories per system."""
    fig, ax = plt.subplots(figsize=(8, 5))

    systems = []
    useful = []
    halluc = []
    junk = []
    misat = []

    for name in ["mem0", "aurra"]:
        if name not in scores:
            continue
        agg = scores[name]["aggregate"]
        systems.append(name.capitalize())
        useful.append(agg["useful_pct"])
        halluc.append(agg["hallucinated_pct"])
        junk.append(agg["junk_pct"])
        misat.append(agg["misattributed_pct"])

    x = range(len(systems))
    width = 0.6

    p1 = ax.bar(x, useful, width, label="Useful", color=USEFUL_COLOR)
    p2 = ax.bar(x, halluc, width, bottom=useful, label="Hallucinated", color=HALLUC_COLOR)
    bottoms_for_junk = [u + h for u, h in zip(useful, halluc)]
    p3 = ax.bar(x, junk, width, bottom=bottoms_for_junk, label="Junk", color=JUNK_COLOR)
    bottoms_for_misat = [u + h + j for u, h, j in zip(useful, halluc, junk)]
    p4 = ax.bar(x, misat, width, bottom=bottoms_for_misat, label="Misattributed", color=MISAT_COLOR)

    ax.set_ylabel("% of Stored Memories")
    ax.set_title("Memory Quality: Mem0 vs Aurra (LoCoMo benchmark, n=10 conversations)")
    ax.set_xticks(x)
    ax.set_xticklabels(systems)
    ax.set_ylim(0, 105)
    ax.legend(loc="upper right", frameon=False)
    ax.grid(True, axis="y", alpha=0.3)

    # Annotate useful percentages prominently
    for i, (s, u) in enumerate(zip(systems, useful)):
        ax.text(i, u/2, f"{u}%", ha="center", va="center",
                fontweight="bold", color="white", fontsize=14)

    plt.tight_layout()
    out = CHARTS_DIR / "01_overall_quality.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"✅ {out}")


def chart_memories_per_conversation(scores: dict):
    """Bar chart: total memories stored per conversation, side-by-side."""
    fig, ax = plt.subplots(figsize=(11, 5))

    if "mem0" not in scores or "aurra" not in scores:
        print("⚠️ Need both adapters for comparison chart")
        return

    sample_ids_mem0 = {p["sample_id"]: p["total"] for p in scores["mem0"]["per_conv"]}
    sample_ids_aurra = {p["sample_id"]: p["total"] for p in scores["aurra"]["per_conv"]}

    sample_ids = sorted(set(sample_ids_mem0.keys()) | set(sample_ids_aurra.keys()))

    mem0_counts = [sample_ids_mem0.get(s, 0) for s in sample_ids]
    aurra_counts = [sample_ids_aurra.get(s, 0) for s in sample_ids]

    x = range(len(sample_ids))
    width = 0.4

    ax.bar([i - width/2 for i in x], mem0_counts, width, label="Mem0", color=MEM0_COLOR)
    ax.bar([i + width/2 for i in x], aurra_counts, width, label="Aurra", color=AURRA_COLOR)

    ax.set_ylabel("Memories Stored")
    ax.set_title("Memories Captured per Conversation (LoCoMo)")
    ax.set_xticks(x)
    ax.set_xticklabels(sample_ids, rotation=45, ha="right")
    ax.legend(frameon=False)
    ax.grid(True, axis="y", alpha=0.3)

    plt.tight_layout()
    out = CHARTS_DIR / "02_memories_per_conv.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"✅ {out}")


def chart_hallucination_rate(scores: dict):
    """Bar chart: hallucination rate per conversation, comparing systems."""
    fig, ax = plt.subplots(figsize=(11, 5))

    if "mem0" not in scores or "aurra" not in scores:
        return

    sample_ids_mem0 = {p["sample_id"]: p["hallucinated_pct"] for p in scores["mem0"]["per_conv"]}
    sample_ids_aurra = {p["sample_id"]: p["hallucinated_pct"] for p in scores["aurra"]["per_conv"]}

    sample_ids = sorted(set(sample_ids_mem0.keys()) | set(sample_ids_aurra.keys()))

    mem0_pct = [sample_ids_mem0.get(s, 0) for s in sample_ids]
    aurra_pct = [sample_ids_aurra.get(s, 0) for s in sample_ids]

    x = range(len(sample_ids))
    width = 0.4

    ax.bar([i - width/2 for i in x], mem0_pct, width, label="Mem0", color=MEM0_COLOR)
    ax.bar([i + width/2 for i in x], aurra_pct, width, label="Aurra", color=AURRA_COLOR)

    ax.set_ylabel("% of Memories Hallucinated")
    ax.set_title("Hallucination Rate per Conversation (Lower is Better)")
    ax.set_xticks(x)
    ax.set_xticklabels(sample_ids, rotation=45, ha="right")
    ax.legend(frameon=False)
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_ylim(40, 85)  # Zoom in to amplify visible gap

    plt.tight_layout()
    out = CHARTS_DIR / "03_hallucination_per_conv.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"✅ {out}")


def chart_date_hallucination(scores_unused: dict):
    """Bar chart showing the killer finding: % of memories with absolute years.

    Reads ingestion JSONs directly (not score JSONs) to count years.
    """
    import re
    year_pattern = re.compile(r'\b(202[0-9])\b')

    counts = {}
    for name in ["mem0", "aurra"]:
        path = RESULTS_DIR / f"ingestion_{name}.json"
        if not path.exists():
            continue
        with open(path) as f:
            data = json.load(f)
        total = 0
        with_dates = 0
        for conv in data.get("results", []):
            for mem in conv.get("stored_memories", []):
                text = mem.get("memory") or mem.get("content") or mem.get("text") or ""
                if not text:
                    continue
                total += 1
                if year_pattern.search(text):
                    with_dates += 1
        counts[name] = {
            "total": total,
            "with_dates": with_dates,
            "pct": (100 * with_dates / total) if total else 0,
        }

    if "mem0" not in counts or "aurra" not in counts:
        print("⚠️ Need both ingestion files for date chart")
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    systems = ["Mem0", "Aurra"]
    pcts = [counts["mem0"]["pct"], counts["aurra"]["pct"]]
    raw_counts = [counts["mem0"]["with_dates"], counts["aurra"]["with_dates"]]
    totals = [counts["mem0"]["total"], counts["aurra"]["total"]]
    colors = [MEM0_COLOR, AURRA_COLOR]

    bars = ax.bar(systems, pcts, color=colors, width=0.5)

    for bar, pct, n, total in zip(bars, pcts, raw_counts, totals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"{pct:.2f}%\n({n} of {total})",
                ha="center", va="bottom", fontsize=11, fontweight="bold")

    ax.set_ylabel("% of Memories Containing an Absolute Year (2020-2029)")
    ax.set_title("Date Hallucination Rate (Lower is Better)\nLoCoMo conversations are dated 2023; Mem0 stamps them 2026.")
    ax.set_ylim(0, max(pcts) * 1.4 if max(pcts) > 0 else 5)
    ax.grid(True, axis="y", alpha=0.3)

    plt.tight_layout()
    out = CHARTS_DIR / "04_date_hallucination.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"✅ {out}")


def main():
    scores = load_scores()
    if not scores:
        print("❌ No score files found. Run junk_classifier.py first.")
        return

    print(f"\n{'='*70}")
    print("Generating charts...")
    print(f"{'='*70}\n")

    chart_junk_rate_overall(scores)
    chart_memories_per_conversation(scores)
    chart_hallucination_rate(scores)
    chart_date_hallucination(scores)

    print(f"\n✅ All charts saved to {CHARTS_DIR}")


if __name__ == "__main__":
    main()
