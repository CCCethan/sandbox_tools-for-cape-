# Windows SDK API Statistics Script

This README explains the purpose, usage, counting rules, output format, and helper tools for `windows_sdk_api_stats.py`.

## Overview

`windows_sdk_api_stats.py` extracts **Windows SDK APIs explicitly called or referenced from C/C++ source code** and counts their occurrences per API.

It uses Clang AST instead of plain text search, so comments, strings, and unrelated identifiers are not counted as function calls.

The script mainly counts two kinds of references:

- Direct calls such as `CreateFileA(...)`
- Dynamic-resolution targets such as `GetProcAddress(..., "CreateFileA")`

## Requirements

The script is primarily intended for macOS.

```bash
pip install libclang
brew install mingw-w64
```

It also requires `libclang.dylib` from Xcode Command Line Tools.

```bash
xcode-select --install
```

## Basic Usage

```bash
python3 windows_sdk_api_stats.py <source_code_directory> --output result.json --jobs 8
```

Example:

```bash
python3 /Users/takabayashirizumu/Documents/Codex/2026-06-19/k/outputs/windows_sdk_api_stats.py \
  "/Users/takabayashirizumu/Downloads/matsuzawa-hikitsugi-main/1. PoC本体（ソースコード・実行ファイル）/ソースコード/3_ビルド・実行可能・サンドボックス検知精度を確認した1520件/source_codes/" \
  --output /Users/takabayashirizumu/Documents/Codex/2026-06-19/k/outputs/windows_sdk_api_stats_1520.json \
  --jobs 8
```

You can also pass multiple source directories.

```bash
python3 windows_sdk_api_stats.py src1 src2 src3 --output result.json
```

## Options

| Option | Description |
|---|---|
| `--output <file>` | Output JSON file. Default: `windows_sdk_api_stats.json` |
| `--mingw <dir>` | Explicit MinGW-w64 include directory |
| `--sdk-header <header>` | Additional SDK header used to recognize `GetProcAddress` targets |
| `--jobs`, `-j` | Number of parallel workers. Default: CPU count |

If you need APIs from additional SDK headers, pass them explicitly.

```bash
python3 windows_sdk_api_stats.py src --sdk-header d3d11.h --sdk-header wlanapi.h
```

## Output JSON Format

Example:

```json
{
  "source_files_found": 1520,
  "source_files_parsed": 1520,
  "source_files_failed": 0,
  "sdk_function_names": 8105,
  "api_count": 545,
  "direct_call_count": 14398,
  "dynamic_call_count": 48,
  "total_call_count": 14446,
  "apis": [
    {
      "api": "GetLastError",
      "total_count": 1948,
      "direct_count": 1948,
      "dynamic_count": 0
    }
  ]
}
```

Top-level fields:

| Field | Meaning |
|---|---|
| `source_files_found` | Number of C/C++ files found |
| `source_files_parsed` | Number of files successfully parsed by Clang |
| `source_files_failed` | Number of files that failed to parse |
| `sdk_function_names` | Number of function names collected from SDK headers |
| `api_count` | Number of unique Windows SDK APIs detected |
| `direct_call_count` | Total number of direct calls |
| `dynamic_call_count` | Total number of `GetProcAddress` string-literal targets |
| `total_call_count` | `direct_call_count + dynamic_call_count` |
| `apis` | Per-API statistics |

Fields inside each `apis` entry:

| Field | Meaning |
|---|---|
| `api` | API name |
| `total_count` | Total occurrences of the API |
| `direct_count` | Number of direct calls |
| `dynamic_count` | Number of `GetProcAddress` string-literal targets |

## What Is Counted

### Direct Calls

The script counts source-level function calls resolved by Clang to Windows SDK function declarations.

```c
GetLastError();
Sleep(1000);
CreateFileA("x.txt", GENERIC_READ, 0, NULL, OPEN_EXISTING, 0, NULL);
```

A call is accepted only when Clang resolves the callee to a function declaration from a Windows SDK header.

This prevents local functions with the same name from being counted as Windows APIs.

```c
void CreateFileA(void) {}

int main() {
    CreateFileA();  // Local function, not counted as a Windows API call.
}
```

### Dynamic Resolution Targets

The script also counts string-literal targets in `GetProcAddress`.

```c
GetProcAddress(hModule, "CreateFileA");
```

The target string is counted only if it exists in the SDK function-name registry built from Windows SDK headers.

## What Is Not Counted

### Comments

```c
// Sleep(1000);
```

### Strings

```c
printf("Sleep(1000)");
```

### Plain Identifiers or Declarations

```c
auto p = Sleep;
DWORD err;
```

### C Runtime or Standard Library Functions

```c
printf("hello");
malloc(100);
```

MinGW include directories also contain C runtime and compatibility headers. The script excludes headers such as `stdio.h`, `stdlib.h`, and `string.h` to avoid treating C runtime functions as Windows SDK APIs.

### Variable-Based GetProcAddress Targets

```c
const char *name = "CreateFileA";
GetProcAddress(hModule, name);
```

This is not counted because the second argument is not a string literal.

### API Hashing or Manual Export Table Walking

```c
resolve_api_by_hash(0x12345678);
```

Custom loaders, API hashing, PEB walking, and manual export table resolution are not counted in `dynamic_count`.

### Compiler- or Linker-Inserted Calls

The script analyzes source-level ASTs. It does not inspect binaries or generated code.

Therefore, calls inserted later by the compiler or linker, such as CRT startup, stack probes, security cookie checks, and exception runtime helpers, are not counted.

## Macro Caveat

Because this script uses Clang AST, calls introduced by macro expansion may be counted if the expanded AST contains a Windows API call.

Example:

```c
#define HIDDEN_API_CALL() LoadLibraryA("kernel32.dll")

int main() {
    HIDDEN_API_CALL();
}
```

In this case, `windows_sdk_api_stats.py` may count `LoadLibraryA`, because the expanded AST contains that call.

If you want to count only API names that are written directly at the source call site, use `windows_sdk_api_textual_stats.py`.

```bash
python3 windows_sdk_api_textual_stats.py <source_code_directory> --output textual_result.json
```

## Querying Results

Show statistics for a specific API:

```bash
jq '.apis[] | select(.api == "Sleep")' windows_sdk_api_stats_1520.json
```

Show the top 20 APIs:

```bash
jq '.apis[:20]' windows_sdk_api_stats_1520.json
```

Print API names and counts:

```bash
jq -r '.apis[] | "\(.total_count)\t\(.api)"' windows_sdk_api_stats_1520.json
```

## Inspecting Call Sites

Use `windows_sdk_api_call_sites.py` to print file, line, column, and source snippet for one API.

```bash
python3 windows_sdk_api_call_sites.py <source_code_directory> \
  --api Sleep \
  --output sleep_call_sites.json \
  --jobs 8
```

Print saved call sites:

```bash
jq -r '.call_sites[] | "\(.file):\(.line):\(.column): [\(.kind)] \(.snippet)"' sleep_call_sites.json
```

## Plotting

Use `plot_windows_sdk_api_stats.py` to generate PNG graphs from the JSON output.

```bash
python3 plot_windows_sdk_api_stats.py windows_sdk_api_stats_1520.json --top 30
```

The script generates:

- Top API horizontal bar chart
- Cumulative concentration chart
- Direct-call vs `GetProcAddress` target summary chart

## Comparing with capemon Hooks

Use `compare_windows_sdk_api_hooks.py` to compare the API statistics with capemon's `hooks.h`.

```bash
python3 compare_windows_sdk_api_hooks.py windows_sdk_api_stats_1520.json \
  --hooks /path/to/capemon/hooks.h \
  --output windows_sdk_api_stats_1520_capemon_coverage.json
```

The comparison output includes:

- Number of hook definitions in capemon
- Number of detected APIs that are already hooked
- Number of unhooked APIs
- Call-count-based coverage
- Top unhooked APIs

## Known Limitations

- `GetProcAddress` targets passed through variables are not tracked.
- API hashing and manual export table walking are not detected.
- Files that Clang cannot parse are skipped.
- `GetProcAddress` string targets from headers not included in the SDK registry may not be recognized.
- Calls introduced by macro expansion may be counted even if the API name is not written directly at the call site.

## Result for the 1520-File Dataset

For `windows_sdk_api_stats_1520.json`, the result was:

```text
Parsed files              : 1520/1520
Unique Windows SDK APIs   : 545
Total calls/references    : 14446
Direct calls              : 14398
GetProcAddress targets    : 48
```

Top APIs:

```text
GetLastError          1948
CoUninitialize        1393
CloseHandle           1201
GetTickCount64         623
RegCloseKey            427
VariantClear           330
CoInitializeEx         268
WaitForSingleObject    240
CoCreateInstance       231
```
