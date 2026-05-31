## Batch Extraction Utilities

This repository provides two utilities for processing CAPEv2 analysis reports:

* `extract_behavior.py` — Extracts behavior-related information from CAPEv2 JSON reports.
* `extract_logs.py` — Extracts debug log information from CAPEv2 JSON reports.

---

## Behavior Extraction

Extract the dynamic analysis (`behavior`) section from multiple CAPEv2 JSON reports.

### Usage

```bash
python3 extract_behavior.py <input_directory>
```

Example:

```bash
python3 extract_behavior.py reports/
```

By default, extracted files are saved to:

```text
behaviors/
```

### Specify Output Directory

You can specify a custom output directory using the `-o` or `--output` option.

```bash
python3 extract_behavior.py reports/ -o extracted_behaviors
```

Output:

```text
extracted_behaviors/
├── sample1_behavior.json
├── sample2_behavior.json
└── sample3_behavior.json
```

### Arguments

| Argument         | Description                                                          |
| ---------------- | -------------------------------------------------------------------- |
| `input_dir`      | Directory containing CAPEv2 JSON reports                             |
| `-o`, `--output` | Output directory for extracted behavior files (default: `behaviors`) |

### Example Workflow

Input:

```text
reports/
├── sample1.json
├── sample2.json
└── sample3.json
```

Command:

```bash
python3 extract_behavior.py reports/ -o behaviors
```

Output:

```text
behaviors/
├── sample1_behavior.json
├── sample2_behavior.json
└── sample3_behavior.json
```

These extracted behavior files can be used for malware behavior analysis, signature generation, and signature matching experiments.

---

## Debug Log Extraction

Extract debug-related log entries from CAPEv2 JSON reports.

### Usage

```bash
python3 extract_logs.py report.json
```

Example:

```bash
python3 extract_logs.py report.json
```

### Save Output to a File

```bash
python3 extract_logs.py report.json -o debug_logs.txt
```

### Arguments

| Argument         | Description                          |
| ---------------- | ------------------------------------ |
| `report`         | Path to a CAPEv2 JSON report         |
| `-o`, `--output` | Output file for extracted debug logs |

### Example Output

```text
[ERRORS] Example error message
[WARNINGS] Example warning message
[ANALYSIS] Example analysis message
```

The extracted logs can be used for malware analysis, debugging CAPEv2 executions, and identifying behavioral indicators.
