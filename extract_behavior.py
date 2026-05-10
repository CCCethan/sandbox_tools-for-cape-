import json
import os
import argparse

def extract_dynamic_analysis(input_file, output_file):
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    print(f"Reading {input_file}...")

    with open(input_file, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decodingJSON: {e}")
            return

    #動的解析の部分（behavior）を抽出
    #behavior内にはprocesses, summary, network等が含まれる
    behavior_data = data.get("behavior", {})

    if not behavior_data:
        print("Warning: No dynamic analysis (behavior) data found in this report.")

    #抽出したい項目を整理
    extracted_output = {
            "info": data.get("info", {}),
            "target": data.get("target", {}),
            "behavior": behavior_data,
            "network": data.get("network", {}),
            "dropped": data.get("dropped", [])
            }

    print(f"Writing extracted data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(extracted_output, f, indent=4, ensure_ascii=False)

    print("Done!")

if __name__ == "__main__":
    #CAPEv2のreport.jsonのパス指定
    parser = argparse.ArgumentParser(description="CAPEv2のJSONレポートから動的解析部分のみを抽出．")

    #引数の指定
    parser.add_argument("-i", "--input", required=True, help="解析対象のreport.jsonのパス")
    parser.add_argument("-o", "--output", required=True, help="出力するJSONファイルのパス")

    args = parser.parse_args()

    extract_dynamic_analysis(args.input, args.output)
