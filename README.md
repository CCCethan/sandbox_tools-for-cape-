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


## Signature Matching

`signature_matching.py` provides a simple YARA-like signature matching framework for evaluating behavior-based signatures against CAPEv2 analysis reports.

The tool loads a YARA rule file and matches it against either a single JSON report or a directory containing multiple JSON reports.

---

### Supported Rule Format

Example rule:

```yara
rule antivirus_from_registry
{
    strings:
        $display = "DisplayName" nocase

    condition:
        $display
}
```

Currently supported features:

* Rule name extraction
* String matching
* `and`, `or`, `not` conditions
* Case-insensitive matching via JSON text search

---

### Single Report Evaluation

Evaluate a signature against a single behavior report.

```bash
python3 signature_matching.py \
    -r test_yara_registry.yar \
    -j behaviors/460_report_behavior.json
```

Example output:

```text
Rule: antivirus_from_registry
File: behaviors/460_report_behavior.json
Matched: True
```

---

### Batch Evaluation

Evaluate a signature against all JSON files within a directory.

```bash
python3 signature_matching.py \
    -r test_yara_registry.yar \
    -d behaviors/
```

Example output:

```text
===== RESULT =====
Rule Name      : antivirus_from_registry
Total Samples  : 100
Matched        : 37
Not Matched    : 63
Match Rate     : 37.00%
==================
```

---

### Arguments

| Argument            | Description                       |
| ------------------- | --------------------------------- |
| `-r`, `--rule`      | Path to the YARA rule file        |
| `-j`, `--json`      | Path to a single JSON report      |
| `-d`, `--directory` | Directory containing JSON reports |

**Note:** Either `--json` or `--directory` must be specified.

---

### Evaluation Metrics

The batch evaluation mode provides:

| Metric        | Description                                  |
| ------------- | -------------------------------------------- |
| Total Samples | Number of JSON reports processed             |
| Matched       | Number of reports matching the signature     |
| Not Matched   | Number of reports not matching the signature |
| Match Rate    | Percentage of reports matching the signature |

---

### Example Workflow

1. Extract behavior data from CAPEv2 reports

```bash
python3 extract_behavior.py reports/ -o behaviors
```

2. Create a signature rule

```yara
rule antivirus_from_registry
{
    strings:
        $display = "DisplayName" nocase

    condition:
        $display
}
```

3. Evaluate the signature

```bash
python3 signature_matching.py \
    -r antivirus_registry.yar \
    -d behaviors/
```

4. Analyze the results

```text
Total Samples : 100
Matched       : 37
Not Matched   : 63
Match Rate    : 37.00%
```

This workflow can be used to evaluate manually generated behavior signatures and assess their effectiveness against CAPEv2 behavioral analysis reports.

