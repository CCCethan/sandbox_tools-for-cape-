#!/usr/bin/env python3
"""
Compare Windows SDK API statistics with capemon hook definitions.

Input:
  - JSON produced by windows_sdk_api_stats.py
  - capemon hooks.h, or a capemon source directory containing hooks.h

Output:
  - JSON with hooked/unhooked API entries and coverage metrics

Usage:
    python compare_windows_sdk_api_hooks.py windows_sdk_api_stats_1520.json \
      --capemon /path/to/capemon \
      --output windows_sdk_api_stats_1520_capemon_coverage.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _find_hooks_h(capemon: Path | None, hooks: Path | None) -> Path:
    # --hooks が指定されていればそれを使う。そうでなければ capemon/hooks.h を使う。
    if hooks:
        if not hooks.is_file():
            sys.exit(f"ERROR: hooks.h not found: {hooks}")
        return hooks
    if not capemon:
        sys.exit("ERROR: specify --capemon DIR or --hooks FILE")
    hooks_h = capemon / "hooks.h"
    if hooks_h.is_file():
        return hooks_h
    matches = sorted(capemon.rglob("hooks.h"))
    if matches:
        return matches[0]
    sys.exit(f"ERROR: hooks.h not found under {capemon}")


def _strip_comments(text: str) -> str:
    # コメント内に残った HOOKDEF を誤検出しないよう、C/C++ コメントを落とす。
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def extract_hooked_apis(hooks_h: Path) -> set[str]:
    # capemon の hooks.h では HOOKDEF(..., API名, ...) 形式で hook 対象が並ぶ想定。
    # 元スクリプトと同じく、第 3 引数の API 名を基本として抽出する。
    text = _strip_comments(_read_text(hooks_h))
    hooked: set[str] = set()

    patterns = [
        re.compile(r"\bHOOKDEF\s*\(\s*[^,]+,\s*[^,]+,\s*([A-Za-z_]\w*)"),
        re.compile(r"\bHOOKDEF_[A-Za-z0-9_]*\s*\(\s*[^,]+,\s*[^,]+,\s*([A-Za-z_]\w*)"),
    ]
    for pattern in patterns:
        hooked.update(match.group(1) for match in pattern.finditer(text))
    return hooked


def _generic_name(api: str) -> str | None:
    # CreateFileA/W と CreateFile のような対応を見るため、末尾 A/W を外した候補を作る。
    if len(api) > 1 and api[-1] in {"A", "W"} and api[-2].isalnum():
        return api[:-1]
    return None


def _hook_match(api: str, hooked: set[str]) -> tuple[bool, str | None]:
    # exact match を最優先し、なければ A/W suffix を外した generic 名でも照合する。
    if api in hooked:
        return True, api
    generic = _generic_name(api)
    if generic and generic in hooked:
        return True, generic

    # hook 側が A/W suffix 付きで、統計側が generic 名の場合にも対応する。
    for suffix in ("A", "W"):
        suffixed = api + suffix
        if suffixed in hooked:
            return True, suffixed
    return False, None


def _split_entries(entries: list[dict], hooked: set[str]) -> tuple[list[dict], list[dict]]:
    hooked_entries: list[dict] = []
    unhooked_entries: list[dict] = []

    for entry in entries:
        api = str(entry["api"])
        is_hooked, matched_hook = _hook_match(api, hooked)
        enriched = dict(entry)
        enriched["hooked"] = is_hooked
        enriched["matched_hook"] = matched_hook
        if is_hooked:
            hooked_entries.append(enriched)
        else:
            unhooked_entries.append(enriched)

    sort_key = lambda e: (-int(e.get("total_count", e.get("src_count", 0))), str(e["api"]))
    hooked_entries.sort(key=sort_key)
    unhooked_entries.sort(key=sort_key)
    return hooked_entries, unhooked_entries


def _sum_count(entries: list[dict], field: str) -> int:
    return sum(int(entry.get(field, 0)) for entry in entries)


def build_comparison(stats_json: Path, hooks_h: Path) -> dict:
    stats = json.loads(_read_text(stats_json))
    entries = list(stats.get("apis", []))
    if not entries:
        sys.exit(f"ERROR: no 'apis' entries found in {stats_json}")

    hooked_api_names = extract_hooked_apis(hooks_h)
    hooked_entries, unhooked_entries = _split_entries(entries, hooked_api_names)

    total_api_count = len(entries)
    hooked_api_count = len(hooked_entries)
    total_call_count = _sum_count(entries, "total_count")
    hooked_call_count = _sum_count(hooked_entries, "total_count")
    unhooked_call_count = _sum_count(unhooked_entries, "total_count")

    return {
        "stats_json": str(stats_json),
        "hooks_h": str(hooks_h),
        "source_files_found": stats.get("source_files_found"),
        "source_files_parsed": stats.get("source_files_parsed"),
        "capemon_hook_total": len(hooked_api_names),
        "api_count": total_api_count,
        "hooked_api_count": hooked_api_count,
        "unhooked_api_count": len(unhooked_entries),
        "api_coverage_rate": round(hooked_api_count / total_api_count, 6)
        if total_api_count
        else 0.0,
        "total_call_count": total_call_count,
        "hooked_call_count": hooked_call_count,
        "unhooked_call_count": unhooked_call_count,
        "call_coverage_rate": round(hooked_call_count / total_call_count, 6)
        if total_call_count
        else 0.0,
        "hooked_apis": hooked_entries,
        "unhooked_apis": unhooked_entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare Windows SDK API stats JSON with capemon hooks.h"
    )
    parser.add_argument("stats_json", type=Path)
    parser.add_argument("--capemon", type=Path, metavar="DIR")
    parser.add_argument("--hooks", type=Path, metavar="FILE")
    parser.add_argument("--output", type=Path, default=Path("windows_sdk_api_capemon_coverage.json"))
    parser.add_argument("--top", type=int, default=30)
    args = parser.parse_args()

    hooks_h = _find_hooks_h(args.capemon, args.hooks)
    result = build_comparison(args.stats_json, hooks_h)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    print(f"Result -> {args.output}")
    print(f"  hooks.h          : {hooks_h}")
    print(f"  capemon hooks    : {result['capemon_hook_total']}")
    print(f"  APIs in stats    : {result['api_count']}")
    print(
        f"  Hooked APIs      : {result['hooked_api_count']} "
        f"({result['api_coverage_rate']:.1%})"
    )
    print(
        f"  Hooked calls     : {result['hooked_call_count']}/{result['total_call_count']} "
        f"({result['call_coverage_rate']:.1%})"
    )
    print(f"  Unhooked APIs    : {result['unhooked_api_count']}")
    print(f"  Unhooked calls   : {result['unhooked_call_count']}")

    if result["unhooked_apis"]:
        print("\nTop unhooked APIs:")
        for entry in result["unhooked_apis"][: args.top]:
            print(
                f"  {int(entry['total_count']):>6}x  {entry['api']} "
                f"(direct={entry.get('direct_count', 0)}, dyn={entry.get('dynamic_count', 0)})"
            )


if __name__ == "__main__":
    main()
