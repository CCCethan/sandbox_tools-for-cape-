import json
import argparse
import os

def load_behavior(file_path):
    """JSONからbehaviorセクションを抽出して返す"""
    if not os.path.exists(file_path):
        print(f"Error: ファイルが見つかりません -> {file_path}")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # すでに抜き出し済みのファイルなら全体を、
            # 未加工のreport.jsonなら behavior 部分を返す
            return data.get("behavior", data)
    except Exception as e:
        print(f"Error: {file_path} の読み込みに失敗しました: {e}")
        return None

def compare_json(file1, file2):
    print(f"Comparing:\n  1: {file1}\n  2: {file2}\n")
    
    b1 = load_behavior(file1)
    b2 = load_behavior(file2)

    if b1 is None or b2 is None:
        return

    # データの比較
    if b1 == b2:
        print("Result: [ MATCH ]")
        print("両方のファイルの動的解析結果は完全に一致しています。")
    else:
        print("Result: [ NO MATCH ]")
        print("動的解析結果に差異があります。")
        
        # 簡易的な差異の分析
        keys1 = set(b1.keys()) if isinstance(b1, dict) else set()
        keys2 = set(b2.keys()) if isinstance(b2, dict) else set()
        
        if keys1 != keys2:
            print(f"- 存在するキー（項目）が異なります。")
            print(f"  File1のみ: {keys1 - keys2}")
            print(f"  File2のみ: {keys2 - keys1}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="2つの動的解析ログが一致するか比較します。")
    parser.add_argument("-f1", "--file1", required=True, help="1つ目のJSONファイル")
    parser.add_argument("-f2", "--file2", required=True, help="2つ目のJSONファイル")

    args = parser.parse_args()
    compare_json(args.file1, args.file2)
