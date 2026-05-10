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
