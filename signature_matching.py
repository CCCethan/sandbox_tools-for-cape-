from pathlib import Path
import argparse

from utils.extract_behavior import (
    extract_behavior_json,
    save_extracted_data
)

parser = argparse.ArgumentParser(
    description="Extract behavior sections from CAPEv2 reports"
)

parser.add_argument(
    "input_dir",
    help="Directory containing JSON files"
)

parser.add_argument(
    "-o",
    "--output",
    default="behaviors",
    help="Output directory (default: behaviors)"
)

args = parser.parse_args()

input_dir = Path(args.input_dir)
output_dir = Path(args.output)

print(f"Input Directory : {input_dir.resolve()}")
print(f"Output Directory: {output_dir.resolve()}")

if not input_dir.exists():
    raise FileNotFoundError(
        f"Input directory does not exist: {input_dir}"
    )

output_dir.mkdir(parents=True, exist_ok=True)

for json_file in input_dir.glob("*.json"):

    print(f"[+] Processing: {json_file}")

    result = extract_behavior_json(json_file)

    output_file = output_dir / (
        f"{json_file.stem}_behavior.json"
    )

    save_extracted_data(result, output_file)

    print(f"[+] Saved: {output_file}")
