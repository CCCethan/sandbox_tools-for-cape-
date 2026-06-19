#!/usr/bin/env python3
"""
Create graphs from windows_sdk_api_stats.py JSON output.

Usage:
    python plot_windows_sdk_api_stats.py windows_sdk_api_stats_1520.json
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

# Keep matplotlib cache inside this workspace so the script works in restricted environments.
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent.parent / "work" / "mplconfig"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter


def _load_entries(json_path: Path) -> tuple[dict, list[dict]]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    entries = sorted(data["apis"], key=lambda e: (-e["total_count"], e["api"]))
    return data, entries


def _plot_top_apis(entries: list[dict], out_path: Path, top: int) -> None:
    visible = entries[:top]
    labels = [e["api"] for e in visible][::-1]
    direct = [e["direct_count"] for e in visible][::-1]
    dynamic = [e["dynamic_count"] for e in visible][::-1]

    fig_h = max(7, top * 0.34)
    fig, ax = plt.subplots(figsize=(12, fig_h))
    y = range(len(labels))

    ax.barh(y, direct, color="#3B82F6", label="Direct call")
    ax.barh(y, dynamic, left=direct, color="#F97316", label="GetProcAddress target")

    for idx, total in enumerate([d + dy for d, dy in zip(direct, dynamic)]):
        ax.text(total + max(total * 0.01, 2), idx, str(total), va="center", fontsize=8)

    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Call/reference count")
    ax.set_title(f"Top {top} Windows SDK APIs by count")
    ax.grid(axis="x", linestyle="--", alpha=0.28)
    ax.legend(loc="lower right")
    ax.set_xlim(0, max([d + dy for d, dy in zip(direct, dynamic)]) * 1.12)

    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def _plot_pareto(entries: list[dict], out_path: Path) -> None:
    counts = [e["total_count"] for e in entries]
    total = sum(counts)
    cumulative = []
    running = 0
    for count in counts:
        running += count
        cumulative.append(running / total if total else 0)

    ranks = list(range(1, len(entries) + 1))

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(ranks, cumulative, color="#16A34A", linewidth=2.2)
    ax.axhline(0.8, color="#EF4444", linestyle="--", linewidth=1, label="80%")
    ax.axhline(0.9, color="#F59E0B", linestyle="--", linewidth=1, label="90%")
    ax.fill_between(ranks, cumulative, color="#86EFAC", alpha=0.25)

    ax.set_xlabel("API rank by count")
    ax.set_ylabel("Cumulative share of total calls")
    ax.set_title("Cumulative concentration of Windows SDK API calls")
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.set_xlim(1, len(entries))
    ax.set_ylim(0, 1.02)
    ax.grid(True, linestyle="--", alpha=0.28)
    ax.legend(loc="lower right")

    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def _plot_summary(data: dict, out_path: Path) -> None:
    labels = ["Direct call", "GetProcAddress target"]
    values = [data["direct_call_count"], data["dynamic_call_count"]]
    colors = ["#3B82F6", "#F97316"]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, values, color=colors, width=0.55)
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + max(values) * 0.015,
            str(value),
            ha="center",
            va="bottom",
            fontsize=10,
        )

    ax.set_ylabel("Count")
    ax.set_title("Direct calls vs GetProcAddress targets")
    ax.grid(axis="y", linestyle="--", alpha=0.28)
    ax.set_ylim(0, max(values) * 1.12)

    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot Windows SDK API statistics JSON")
    parser.add_argument("json", type=Path)
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--prefix", type=Path)
    args = parser.parse_args()

    data, entries = _load_entries(args.json)
    prefix = args.prefix or args.json.with_suffix("")

    top_path = prefix.with_name(prefix.name + f"_top{args.top}.png")
    pareto_path = prefix.with_name(prefix.name + "_pareto.png")
    summary_path = prefix.with_name(prefix.name + "_direct_dynamic.png")

    _plot_top_apis(entries, top_path, args.top)
    _plot_pareto(entries, pareto_path)
    _plot_summary(data, summary_path)

    print(top_path)
    print(pareto_path)
    print(summary_path)


if __name__ == "__main__":
    main()
