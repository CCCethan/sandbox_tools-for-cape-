extract_behavior.py extracts behavior part from cape report json file.

for use,
  python3 extract_behavior.py -i /path/to/cape_report.json -o /path/to/extracted_data.json

compare_behavior.py compares two behavior log

for use,
  python3 compare_behavior.py -f1 /path/to/behavior_part1.json -f2 /path/to/behavior_part2.json


extract_logs extracts CAPE analysis logs from report.json

for use,
  python3 extract_logs.py /path/to/report.json -o /path/to/output.log

aligned_common.py outputs common logs from some .log files

for use,
  python3 aligned_common.py /path/to/logs_directory

# CAPEv2 Debug Log Extractor

A simple Python utility to extract the `debug` section from a CAPEv2 `report.json` file and display or save the extracted debug logs.

## Features

* Extracts entries from the `debug` section of a CAPEv2 analysis report.
* Supports:

  * Lists
  * Dictionaries
  * Single values
* Prints extracted logs to the console or saves them to a file.
* Preserves the source field name in the output.

---

## Requirements

* Python 3.6+

No external dependencies are required.

---

## Usage

### Print debug logs to the terminal

```bash
python extract_debug.py report.json
```

### Save debug logs to a file

```bash
python extract_debug.py report.json -o debug.logs
```

or

```bash
python extract_debug.py report.json --output debug.logs
```

---

## Example Output

Given a CAPEv2 report containing:

```json
{
  "debug": {
    "errors": [
      "API timeout",
      "Connection failed"
    ],
    "info": {
      "sandbox": "CAPE",
      "version": "2.4"
    }
  }
}
```

The script produces:

```text
[ERRORS]API timeout
[ERRORS]Connection failed
[INFO:sandbox]CAPE
[INFO:version]2.4
```

---

## Output Format

### List entries

```text
[FIELD_NAME]value
```

Example:

```text
[ERRORS]API timeout
```

### Dictionary entries

```text
[FIELD_NAME:subkey]value
```

Example:

```text
[INFO:version]2.4
```

### Single values

```text
[FIELD_NAME]value
```

Example:

```text
[STATUS]completed
```

---

## Command-Line Arguments

| Argument         | Description                   |
| ---------------- | ----------------------------- |
| `report`         | Path to CAPEv2 `report.json`  |
| `-o`, `--output` | Save extracted logs to a file |

---

## Example

```bash
python extract_debug.py analysis/report.json -o extracted_debug.log
```

Output:

```text
[+] Saved 42 lines to extracted_debug.log
```

---

## Notes

* If the specified report file does not exist, the script will display an error message.
* If the report does not contain a `debug` section, the script will notify the user.
* The tool is intended for CAPEv2 analysis reports generated in JSON format.

```

## License

This project is provided as-is for research and analysis purposes.
```
