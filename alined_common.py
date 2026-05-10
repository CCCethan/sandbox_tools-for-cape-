#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate common log template while preserving line positions.

Differences become blank lines.

Usage:
    python aligned_common.py debug_logs/

Output:
    aligned_common.txt
"""

import re
import argparse
from pathlib import Path
from difflib import SequenceMatcher


def normalize_line(line):

    # Remove timestamp
    line = re.sub(
        r'^\d{4}-\d{2}-\d{2}\s+'
        r'\d{2}:\d{2}:\d{2},\d+\s+',
        '',
        line
    )

    return line.strip()


def load_lines(log_file):

    lines = []

    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:

        for line in f:

            line = line.rstrip()

            if not line:
                continue

            lines.append(normalize_line(line))

    return lines


def align_common(base, other):

    matcher = SequenceMatcher(None, base, other)

    result = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():

        if tag == "equal":

            result.extend(base[i1:i2])

        else:
            # 差分部分は空行で埋める
            result.extend([""] * (i2 - i1))

    return result


def main():

    parser = argparse.ArgumentParser(
        description="Aligned common logs with blanks for differences"
    )

    parser.add_argument(
        "log_dir",
        help="Directory containing log files"
    )

    parser.add_argument(
        "-o",
        "--output",
        default="aligned_common.txt",
        help="Output file"
    )

    args = parser.parse_args()

    log_files = sorted(Path(args.log_dir).glob("*.log"))

    if len(log_files) < 2:
        print("[-] Need at least 2 log files")
        return

    print(f"[+] Found {len(log_files)} log files")

    common = load_lines(log_files[0])

    for log_file in log_files[1:]:

        current = load_lines(log_file)

        common = align_common(common, current)

    with open(args.output, "w", encoding="utf-8") as out:

        for line in common:
            out.write(line + "\n")

    print(f"[+] Saved aligned output to: {args.output}")


if __name__ == "__main__":
    main()