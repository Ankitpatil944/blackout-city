import json
import os
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

LOG_PATH = "artifacts/results_log.jsonl"
PLOT_PATH = "artifacts/reward_comparison.png"
RECOLLAPSE_PLOT_PATH = "artifacts/recollapse_rate.png"

POLICY_LABELS = {
    "greedy":    "Greedy (untrained)",
    "heuristic": "Heuristic baseline",
    "sft":       "SFT 300 steps",
    "rl":        "RL fine-tuned",
}

POLICY_COLORS = {
    "greedy":    "#e74c3c",
    "heuristic": "#e67e22",
    "sft":       "#3498db",
    "rl":        "#2ecc71",
}

DIFFICULTIES = ["easy", "medium", "hard"]

def log_result(tag: str, scores: dict) -> None:
    """
    Append one eval result to the JSONL log.

    Args:
        tag:    policy identifier, e.g. "greedy", "sft", "rl"
        scores: dict with keys easy, medium, hard (floats 0-1)
                and optionally recollapse (float 0-1, lower is better)
    """
    os.makedirs("artifacts", exist_ok=True)
    entry = {"ts": datetime.utcnow().isoformat(), "tag": tag, **scores}
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"✓ Logged [{tag}]: easy={scores.get('easy','?'):.2f}  "
          f"medium={scores.get('medium','?'):.2f}  hard={scores.get('hard','?'):.2f}")

def load_results() -> list[dict]:
    """Load all logged results. Returns list of dicts."""
    if not Path(LOG_PATH).exists():
        return []
    with open(LOG_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]

def plot_comparison(save: bool = True, show: bool = True) -> None:
    """
    Generate a two-panel figure:
      Left:  grouped bar chart — reward by policy × difficulty
      Right: horizontal bar chart — re-collapse rate (lower is better)

    Saves to artifacts/reward_comparison.png
    """
    results = load_results()
    if not results:
        print("No results logged yet. Call log_result() first.")
        return

    # Build ordered list of policies (preserve insertion order, deduplicate)
    seen = {}
    for r in results:
        seen[r["tag"]] = r
    ordered = list(seen.values())   # last logged entry wins per tag

    tags   = [r["tag"]   for r in ordered]
    labels = [POLICY_LABELS.get(t, t) for t in tags]
    colors = [POLICY_COLORS.get(t, "#95a5a6") for t in tags]

    n_policies = len(tags)
    n_diff     = len(DIFFICULTIES)
    x          = np.arange(n_diff)
    width      = 0.8 / n_policies

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5),
                                    gridspec_kw={"width_ratios": [2, 1]})
    fig.patch.set_facecolor("#0f172a")
    for ax in (ax1, ax2):
        ax.set_facecolor("#1e293b")
        ax.tick_params(colors="#cbd5e1")
        ax.spines["bottom"].set_color("#334155")
        ax.spines["left"].set_color("#334155")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # ── Left panel: reward bars ──────────────────────────────────────────────
    for i, (r, color) in enumerate(zip(ordered, colors)):
        vals   = [r.get(d, 0) for d in DIFFICULTIES]
        offset = (i - n_policies / 2 + 0.5) * width
        bars   = ax1.bar(x + offset, vals, width * 0.9, color=color,
                         label=labels[i], zorder=3)
        for bar, v in zip(bars, vals):
            if v > 0:
                ax1.text(bar.get_x() + bar.get_width() / 2,
                         bar.get_height() + 0.012,
                         f"{v:.2f}", ha="center", va="bottom",
                         fontsize=7.5, color="#f8fafc", fontweight="bold")

    ax1.set_xticks(x)
    ax1.set_xticklabels(["Easy", "Medium", "Hard"], color="#cbd5e1", fontsize=11)
    ax1.set_ylabel("Normalized Reward  (0 → 1)", color="#94a3b8", fontsize=10)
    ax1.set_xlabel("Task Difficulty", color="#94a3b8", fontsize=10)
    ax1.set_title("Policy Reward by Difficulty Tier",
                  color="#f8fafc", fontsize=13, fontweight="bold", pad=12)
    ax1.set_ylim(0, 1.12)
    ax1.yaxis.grid(True, color="#334155", linestyle="--", alpha=0.7, zorder=0)
    ax1.legend(facecolor="#1e293b", edgecolor="#334155",
               labelcolor="#f8fafc", fontsize=9, loc="upper right")

    # ── Right panel: re-collapse rate ────────────────────────────────────────
    recollapse_vals = [r.get("recollapse", None) for r in ordered]

    if any(v is not None for v in recollapse_vals):
        y_pos = np.arange(n_policies)
        hbars = ax2.barh(
            y_pos,
            [v if v is not None else 0 for v in recollapse_vals],
            color=colors, zorder=3, height=0.5
        )
        for bar, v in zip(hbars, recollapse_vals):
            if v is not None:
                ax2.text(v + 0.01, bar.get_y() + bar.get_height() / 2,
                         f"{v:.0%}", va="center", color="#f8fafc",
                         fontsize=9, fontweight="bold")
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(labels, color="#cbd5e1", fontsize=9)
        ax2.set_xlabel("Re-collapse Rate  (lower is better)", color="#94a3b8", fontsize=10)
        ax2.set_title("Second Collapse Frequency",
                      color="#f8fafc", fontsize=13, fontweight="bold", pad=12)
        ax2.set_xlim(0, 1.0)
        ax2.xaxis.grid(True, color="#334155", linestyle="--", alpha=0.7, zorder=0)
        ax2.axvline(x=0.5, color="#ef4444", linestyle=":", alpha=0.5,
                    label="50% threshold")
    else:
        ax2.text(0.5, 0.5, "No re-collapse\ndata logged yet",
                 ha="center", va="center", color="#64748b",
                 fontsize=12, transform=ax2.transAxes)
        ax2.set_title("Second Collapse Frequency",
                      color="#f8fafc", fontsize=13, fontweight="bold", pad=12)

    plt.suptitle("Blackstart City — Training Progress",
                 color="#f8fafc", fontsize=15, fontweight="bold", y=1.01)
    plt.tight_layout()

    if save:
        os.makedirs("artifacts", exist_ok=True)
        plt.savefig(PLOT_PATH, dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        print(f"✓ Plot saved → {PLOT_PATH}")

    if show:
        plt.show()
    else:
        plt.close()

def print_summary_table() -> None:
    """Print a formatted comparison table to stdout."""
    results = load_results()
    if not results:
        print("No results logged yet.")
        return

    seen = {}
    for r in results:
        seen[r["tag"]] = r

    header = f"{'Policy':<22} {'Easy':>8} {'Medium':>8} {'Hard':>8} {'Re-collapse':>12}"
    print("\n" + "="*62)
    print("  BLACKSTART CITY — RESULTS SUMMARY")
    print("="*62)
    print(header)
    print("-"*62)
    for tag, r in seen.items():
        label    = POLICY_LABELS.get(tag, tag)
        easy     = f"{r.get('easy', '-'):.2f}"   if "easy"      in r else "-"
        medium   = f"{r.get('medium', '-'):.2f}" if "medium"    in r else "-"
        hard     = f"{r.get('hard', '-'):.2f}"   if "hard"      in r else "-"
        recoll   = f"{r.get('recollapse'):.0%}"  if "recollapse" in r else "-"
        print(f"  {label:<20} {easy:>8} {medium:>8} {hard:>8} {recoll:>12}")
    print("="*62 + "\n")

# ── Quick self-test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Populate with example data and render the plot
    import tempfile, os
    os.makedirs("artifacts", exist_ok=True)

    log_result("greedy",    {"easy": 0.41, "medium": 0.29, "hard": 0.18, "recollapse": 0.60})
    log_result("heuristic", {"easy": 0.63, "medium": 0.44, "hard": 0.31, "recollapse": 0.35})
    log_result("sft",       {"easy": 0.74, "medium": 0.58, "hard": 0.42, "recollapse": 0.18})
    log_result("rl",        {"easy": 0.81, "medium": 0.66, "hard": 0.51, "recollapse": 0.12})

    print_summary_table()
    plot_comparison(save=True, show=False)
    print("Self-test complete. Check artifacts/reward_comparison.png")