#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Extract DEBUG logs from CAPEv2 report.json

Usage:
    python extract_debug.py /path/to/report.json

Optional:
    python extract_debug.py report.json -o debug.logs
"""

import json
import argparse
from pathlib import Path

def extract_debug(report_path):
    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

        debug_section = data.get("debug", {})

        extracted = []

        #Common CAPE debug fields
        for key, value in debug_section.items():

            if isinstance(value, list):
                for item in value:
                    extracted.append(f"[{key.upper()}]{item}")

            elif isinstance(value, dict):
                for subkey, subval in value.items():
                    extracted.append(f"[{key.upper()}:{subkey}]{subval}")

            else:
                extracted.append(f"[{key.upper()}]{value}")

            return extracted

def main():
    parser = argparse.ArgumentParser(
        description = "Extract DEBUG section from CAPEv2 report.json"
    )

    parser.add_argument(
        "report",
        help = "Path to report.json"
    )

    parser.add_argument(
        "-o",
        "--output",
        help = "Path file"
    )

    args = parser.parse_args()

    report_path = Path(args.report)

    if not report_path.exists():
        print(f"[-] File not found: {report_path}")
        return

    logs = extract_debug(report_path)

    if not logs:
        print("[!] No debug logs found")
        return

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            for line in logs:
                f.write(line + "\n")

        print(f"[+] Saved {len(logs)} lines to {args.output}")

    else:
        for line in logs:
            print(line)

if __name__ == "__main__":
    main()