# CAPEv2 Report Processing Utilities

A collection of Python utilities for extracting and preprocessing information from CAPEv2 `report.json` files.

These tools are designed to support malware behavior analysis, behavioral signature generation, threat hunting research, and machine learning-based malware detection.

---

## Included Tools

### 1. Dynamic Analysis Extractor

E## Batch Behavior Extraction

Extract the behavior section from multiple CAPEv2 `report.json` files at once.

### Usage

```bash
python3 extract_behavior_batch.py <input_directory>
```

Example:

```bash
python3 extract_behavior_batch.py reports/
```

By default, extracted files are saved to:

```text
behaviors/
```

---

### Specify Output Directory

You can specify a custom output directory using the `-o` or `--output` option.

```bash
python3 extract_behavior_batch.py reports/ -o extracted_behaviors
```

Output:

```text
extracted_behaviors/
├── sample1_behavior.json
├── sample2_behavior.json
└── sample3_behavior.json
```

---

### Arguments

| Argument | Description |
|-----------|-------------|
| `input_dir` | Directory containing CAPEv2 JSON reports |
| `-o`, `--output` | Output directory for extracted behavior files (default: `behaviors`) |

---

### Example Workflow

1. Collect CAPEv2 reports

```text
reports/
├── sample1.json
├── sample2.json
└── sample3.json
```

2. Extract behavior data

```bash
python3 extract_behavior_batch.py reports/ -o behaviors
```

3. Generated files

```text
behaviors/
├── sample1_behavior.json
├── sample2_behavior.json
└── sample3_behavior.json
```

These extracted behavior files can then be used for signature generation and signature matching experiments.

### 2. Debug Log Extractor

Extracts entries from the `debug` section of a CAPEv2 report.

#### Usage

```bash
python extract_logs.py report.json
```

Save output to a file:

```bash
python extract_debug.py report.json -o debug.logs
```

#### Example Output

```text
[ERRORS]API timeout
[ERRORS]Connection failed
[INFO:sandbox]CAPE
[INFO:version]2.4
```

#### Output Format

##### List Entries

```text
[FIELD_NAME]value
```

##### Dictionary Entries

```text
[FIELD_NAME:subkey]value
```

##### Single Values

```text
[FIELD_NAME]value
```

---

## Requirements

* Python 3.6+
* No external dependencies required

---

## Example Workflow

### Step 1: Extract Dynamic Analysis Data

```bash
python extract_dynamic_analysis.py \
    -i report.json \
    -o dynamic_analysis.json
```

Output:

```text
dynamic_analysis.json
```

containing:

* Behavioral activity
* Process information
* Network activity
* Dropped files

---

### Step 2: Extract Debug Logs

```bash
python extract_debug.py \
    report.json \
    -o debug.logs
```

Output:

```text
debug.logs
```

containing:

* Sandbox debug information
* Execution errors
* Internal CAPEv2 messages

---

## Error Handling

### Missing Input File

```text
Error: report.json not found.
```

### Invalid JSON Format

```text
Error decoding JSON: ...
```

### Missing Behavior Section

```text
Warning: No dynamic analysis (behavior) data found in this report.
```

### Missing Debug Section

```text
[!] No debug logs found
```

---

## Research Applications

These utilities are particularly useful for:

* Malware behavioral analysis
* Behavioral signature engineering
* Sandbox evasion analysis
* CAPEv2 report preprocessing
* Feature extraction for machine learning
* LLM-based malware analysis
* Automated signature generation research

---

## Project Structure

```text
project/
├── extract_dynamic_analysis.py
├── extract_debug.py
├── report.json
├── dynamic_analysis.json
├── debug.logs
└── README.md
```

---

## License

This project is provided for educational, research, and malware analysis purposes.
