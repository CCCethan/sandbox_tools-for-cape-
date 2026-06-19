#!/usr/bin/env python3
"""
Enumerate Windows SDK APIs explicitly referenced by C/C++ source code.

The script uses Clang AST call nodes, so comments, strings, and unrelated
identifiers are not counted as calls. Direct calls are kept only when Clang
resolves the callee to a declaration from MinGW-w64 Windows SDK headers.
GetProcAddress string-literal targets are kept only when the name appears in
the SDK function registry built from Windows SDK headers.

Requirements:
    pip install libclang
    brew install mingw-w64

Usage:
    python windows_sdk_api_stats.py <src_dir> [<src_dir2> ...] [options]

Options:
    --output <file>       output JSON file (default: windows_sdk_api_stats.json)
    --mingw <dir>         MinGW-w64 x86_64 include dir (auto-detected)
    --sdk-header <name>   extra SDK header for GetProcAddress name filtering
    --jobs, -j <n>        parallel worker count (default: CPU count)
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# libclang の Python binding を読み込む。
# これがないと Clang AST を使った構文解析ができない。
try:
    import clang.cindex as cx
except ImportError:
    sys.exit("ERROR: pip install libclang")


def _find_libclang() -> str:
    """Return the Xcode libclang.dylib path on macOS."""
    # macOS では Xcode Command Line Tools の clang から libclang の場所を推定する。
    try:
        clang_bin = subprocess.run(
            ["xcrun", "--find", "clang"],
            capture_output=True,
            check=False,
            text=True,
        ).stdout.strip()
        lib = Path(clang_bin).parent.parent / "lib" / "libclang.dylib"
        if lib.exists():
            return str(lib)
    except FileNotFoundError:
        pass
    sys.exit("ERROR: libclang.dylib not found. Install Xcode Command Line Tools.")


cx.Config.set_library_file(_find_libclang())


def _find_mingw_include() -> Path:
    # Homebrew の mingw-w64 が置く Windows ヘッダの標準的な場所を探す。
    # 見つからない場合は --mingw で明示してもらう。
    candidates = sorted(
        Path("/opt/homebrew/Cellar/mingw-w64").glob(
            "*/toolchain-x86_64/x86_64-w64-mingw32/include"
        ),
        reverse=True,
    )
    if candidates:
        return candidates[0]
    sys.exit(
        "ERROR: MinGW-w64 headers not found. Run: brew install mingw-w64\n"
        "       Or specify --mingw <include_dir>"
    )


def _clang_args(mingw_inc: Path) -> list[str]:
    # 解析対象を Windows x64 向け C++ として Clang に読ませるためのオプション。
    # 実際にビルドするためではなく、Windows API の宣言を解決するために使う。
    return [
        "-x",
        "c++",
        "--target=x86_64-w64-mingw32",
        "-std=c++17",
        "-w",
        "-ferror-limit=0",
        f"-I{mingw_inc}",
        "-DWIN32",
        "-D_WIN32",
        "-DUNICODE",
        "-D_UNICODE",
        "-D__MINGW32__",
        "-D__MINGW64__",
        "-D_WIN32_WINNT=0x0A00",
        "-DNTDDI_VERSION=0x0A000000",
    ]


# 不完全な PoC コードでも AST をできるだけ作るため、途中で諦めにくい解析モードにする。
_PARSE_OPTS = (
    cx.TranslationUnit.PARSE_INCOMPLETE
    | cx.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
)

# 集計対象にする C/C++ 系の拡張子。
_SRC_EXTS = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}

# GetProcAddress の文字列ターゲットを SDK API か判定するため、
# 代表的な Windows SDK ヘッダを一度まとめて読み込んで関数名一覧を作る。
_DEFAULT_SDK_HEADERS = (
    "winsock2.h",
    "ws2tcpip.h",
    "windows.h",
    "wininet.h",
    "winhttp.h",
    "wincrypt.h",
    "bcrypt.h",
    "ncrypt.h",
    "iphlpapi.h",
    "psapi.h",
    "tlhelp32.h",
    "dbghelp.h",
    "shellapi.h",
    "shlobj.h",
    "shlwapi.h",
    "aclapi.h",
    "sddl.h",
    "wtsapi32.h",
    "lm.h",
    "ntsecapi.h",
    "powrprof.h",
    "setupapi.h",
    "winternl.h",
)

# MinGW include 配下には C ランタイムや POSIX 互換ヘッダも混ざっている。
# それらに定義された printf/malloc などを Windows SDK API と誤判定しないため除外する。
_NON_SDK_HEADER_NAMES = {
    "_mingw.h",
    "_mingw_mac.h",
    "_mingw_off_t.h",
    "_mingw_print_push.h",
    "_mingw_print_pop.h",
    "_mingw_secapi.h",
    "_mingw_stat64.h",
    "_mingw_unicode.h",
    "_timeval.h",
    "assert.h",
    "complex.h",
    "conio.h",
    "crtdefs.h",
    "ctype.h",
    "direct.h",
    "dirent.h",
    "dos.h",
    "errno.h",
    "excpt.h",
    "fcntl.h",
    "fenv.h",
    "float.h",
    "inttypes.h",
    "io.h",
    "limits.h",
    "locale.h",
    "malloc.h",
    "math.h",
    "memory.h",
    "process.h",
    "pthread.h",
    "sched.h",
    "search.h",
    "semaphore.h",
    "setjmp.h",
    "share.h",
    "signal.h",
    "stdarg.h",
    "stdbool.h",
    "stddef.h",
    "stdint.h",
    "stdio.h",
    "stdlib.h",
    "string.h",
    "strings.h",
    "time.h",
    "uchar.h",
    "unistd.h",
    "wchar.h",
    "wctype.h",
}

# C++ 標準ライブラリや sys 系ディレクトリ由来の宣言を SDK API から外す。
_NON_SDK_PATH_PARTS = {
    "c++",
    "experimental",
    "ext",
    "sys",
}


def _cursor_file(cursor: cx.Cursor) -> Path | None:
    # Clang の cursor が指しているソース/ヘッダファイルのパスを取り出す。
    # マクロ展開や組み込み宣言ではファイルが取れないことがある。
    if cursor.location is None or cursor.location.file is None:
        return None
    return Path(cursor.location.file.name)


def _is_under(path: Path, root: Path) -> bool:
    # path が root 配下にあるかを判定する。SDK ヘッダ配下かどうかの判定に使う。
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _same_file(left: Path | None, right: Path) -> bool:
    # AST には include 先ヘッダ内のノードも出てくる。
    # ここで「解析対象ファイル自身に書かれた呼び出しか」を判定する。
    if left is None:
        return False
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left == right


def _is_windows_sdk_header(path: Path | None, mingw_inc: Path) -> bool:
    # 宣言元が MinGW の include 配下で、かつ C ランタイム/標準ライブラリ由来でなければ
    # Windows SDK ヘッダ由来の宣言として扱う。
    if path is None or not _is_under(path, mingw_inc):
        return False
    rel_parts = path.resolve().relative_to(mingw_inc.resolve()).parts
    lowered_parts = {part.lower() for part in rel_parts[:-1]}
    if lowered_parts & _NON_SDK_PATH_PARTS:
        return False
    return path.name.lower() not in _NON_SDK_HEADER_NAMES


def _walk_ast(root: cx.Cursor):
    # AST を深さ優先でたどる。再帰ではなく stack を使い、大きなファイルでも落ちにくくする。
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(node.get_children())


def _decode_string_literal(spelling: str) -> str | None:
    # Clang が返す "CreateFileA" や L"CreateFileW" のような表記から、
    # Python の文字列として中身だけを取り出す。
    match = re.match(r'^(?:u8|u|U|L)?(".*")$', spelling, re.DOTALL)
    if not match:
        return None
    quoted = match.group(1)
    try:
        value = ast.literal_eval(quoted)
    except (SyntaxError, ValueError):
        return quoted[1:-1]
    return value if isinstance(value, str) else None


def _find_string_literal(cursor: cx.Cursor) -> str | None:
    # GetProcAddress の第 2 引数はキャストや括弧を挟むことがある。
    # そのため引数ノードの内側をたどって最初の文字列リテラルを探す。
    queue = [cursor]
    while queue:
        node = queue.pop(0)
        if node.kind == cx.CursorKind.STRING_LITERAL:
            return _decode_string_literal(node.spelling)
        queue.extend(node.get_children())
    return None


def _get_proc_address_target(cursor: cx.Cursor) -> str | None:
    # GetProcAddress(hModule, "API名") の形なら "API名" を返す。
    # 変数経由の API 名は静的に確定できないため、このスクリプトでは数えない。
    if cursor.spelling != "GetProcAddress":
        return None
    args = list(cursor.get_arguments())
    if len(args) < 2:
        return None
    return _find_string_literal(args[1])


def _normalise_export_name(name: str, sdk_names: set[str]) -> str | None:
    # DLL export 文字列が SDK 関数名一覧に存在する場合だけ採用する。
    # 32-bit stdcall 形式の _Function@16 も Function に戻して照合する。
    if name in sdk_names:
        return name
    decorated = re.match(r"^_([A-Za-z]\w*)@\d+$", name)
    if decorated and decorated.group(1) in sdk_names:
        return decorated.group(1)
    return None


def _is_sdk_free_function_call(
    cursor: cx.Cursor,
    mingw_inc: Path,
) -> tuple[bool, str | None]:
    # CALL_EXPR が free function への直接呼び出しで、かつ宣言元が Windows SDK ヘッダなら採用する。
    # これにより、同名のローカル関数や printf などの C ランタイム関数は除外される。
    ref = cursor.referenced
    if ref is None or ref.kind != cx.CursorKind.FUNCTION_DECL:
        return False, None
    if not _is_windows_sdk_header(_cursor_file(ref), mingw_inc):
        return False, None
    return True, ref.spelling or cursor.spelling


def collect_sdk_function_names(
    mingw_inc: Path,
    clang_args: list[str],
    headers: list[str],
) -> set[str]:
    # GetProcAddress は文字列だけでは宣言元を直接たどれない。
    # そこで先に SDK ヘッダをまとめて Clang に読ませ、SDK に存在する関数名 set を作る。
    existing_headers = []
    for header in dict.fromkeys(headers):
        clean = header.strip("<>\" ")
        if (mingw_inc / clean).exists():
            existing_headers.append(clean)
        else:
            print(f"WARN: SDK header not found, skipped: {clean}", file=sys.stderr)

    # 実ファイルは作らず、unsaved_files として一時的な #include 群を Clang に渡す。
    source = "\n".join(f"#include <{header}>" for header in existing_headers)
    index = cx.Index.create()
    tu = index.parse(
        "sdk_probe.cpp",
        args=clang_args,
        unsaved_files=[("sdk_probe.cpp", source)],
        options=_PARSE_OPTS,
    )

    names: set[str] = set()
    for node in _walk_ast(tu.cursor):
        # SDK ヘッダ内で宣言された関数だけを登録する。
        if node.kind != cx.CursorKind.FUNCTION_DECL or not node.spelling:
            continue
        if _is_windows_sdk_header(_cursor_file(node), mingw_inc):
            names.add(node.spelling)
    return names


def parse_file(
    path: Path,
    index: cx.Index,
    clang_args: list[str],
    mingw_inc: Path,
    sdk_names: set[str],
) -> tuple[dict[str, int], dict[str, int]]:
    # 1 ファイルを Clang で AST 化し、直接呼び出しと GetProcAddress 由来の参照を別々に数える。
    tu = index.parse(str(path), args=clang_args, options=_PARSE_OPTS)
    source_path = path.resolve()
    direct: dict[str, int] = {}
    dynamic: dict[str, int] = {}

    for node in _walk_ast(tu.cursor):
        # 関数呼び出しノードだけを見る。コメント/文字列/単なる識別子はここに来ない。
        if node.kind != cx.CursorKind.CALL_EXPR or not node.spelling:
            continue
        # include 先ヘッダ内部で発生したノードは除外し、元ソースに書かれた呼び出しだけ数える。
        if not _same_file(_cursor_file(node), source_path):
            continue

        # CreateFileA(...) のように直接呼ばれた SDK API を 1 回として加算する。
        is_sdk_call, api_name = _is_sdk_free_function_call(node, mingw_inc)
        if is_sdk_call and api_name:
            direct[api_name] = direct.get(api_name, 0) + 1

        # GetProcAddress(..., "CreateFileA") のような動的解決文字列も SDK API 名なら加算する。
        target = _get_proc_address_target(node)
        if target:
            sdk_target = _normalise_export_name(target, sdk_names)
            if sdk_target:
                dynamic[sdk_target] = dynamic.get(sdk_target, 0) + 1

    return direct, dynamic


def _worker(args_tuple: tuple) -> tuple[dict[str, int], dict[str, int]]:
    # 並列実行時に各プロセスで 1 ファイルを解析するための関数。
    # Clang の Index はプロセスごとに作る。
    path_str, mingw_inc_str, clang_args, sdk_names = args_tuple
    index = cx.Index.create()
    return parse_file(Path(path_str), index, clang_args, Path(mingw_inc_str), sdk_names)


def _source_files(src_dirs: list[str]) -> list[Path]:
    # 指定されたディレクトリ群から解析対象の C/C++ ファイルを再帰的に集める。
    files: list[Path] = []
    for raw in src_dirs:
        src_dir = Path(raw)
        if not src_dir.is_dir():
            sys.exit(f"ERROR: {src_dir} not found")
        files.extend(
            f for f in sorted(src_dir.rglob("*")) if f.suffix.lower() in _SRC_EXTS
        )
    return sorted(dict.fromkeys(files))


def _merge_entries(
    direct: dict[str, int],
    dynamic: dict[str, int],
) -> list[dict[str, int | str]]:
    # direct/dynamic を API 名単位に統合し、JSON に出しやすい形へ整える。
    apis = sorted(set(direct) | set(dynamic))
    entries = [
        {
            "api": api,
            "total_count": direct.get(api, 0) + dynamic.get(api, 0),
            "direct_count": direct.get(api, 0),
            "dynamic_count": dynamic.get(api, 0),
        }
        for api in apis
    ]
    return sorted(entries, key=lambda e: (-int(e["total_count"]), str(e["api"])))


def _add_counts(dst: dict[str, int], src: dict[str, int]) -> None:
    # ファイル単位の集計結果を全体集計へ足し込む。
    for api, count in src.items():
        dst[api] += count


def _parse_files_serial(
    files: list[Path],
    clang_args: list[str],
    mingw_inc: Path,
    sdk_names: set[str],
    all_direct: dict[str, int],
    all_dynamic: dict[str, int],
) -> tuple[int, int]:
    # 直列で全ファイルを解析する。--jobs 1 のときや並列が使えない環境で使う。
    parsed_files = 0
    failed_files = 0
    index = cx.Index.create()
    for done, path in enumerate(files, start=1):
        if done % 50 == 0:
            print(f"  {done}/{len(files)} ...", flush=True)
        try:
            # 1 ファイル分の direct/dynamic count を取得して全体へ加算する。
            direct, dynamic = parse_file(path, index, clang_args, mingw_inc, sdk_names)
        except Exception as exc:
            failed_files += 1
            print(f"  WARN: {path}: {exc}", file=sys.stderr)
            continue
        _add_counts(all_direct, direct)
        _add_counts(all_dynamic, dynamic)
        parsed_files += 1
    return parsed_files, failed_files


def _parse_files_parallel(
    files: list[Path],
    clang_args: list[str],
    mingw_inc: Path,
    sdk_names: set[str],
    all_direct: dict[str, int],
    all_dynamic: dict[str, int],
    jobs: int,
) -> tuple[int, int]:
    # 複数プロセスでファイル解析を並列化する。大きなデータセット向け。
    parsed_files = 0
    failed_files = 0
    worker_args = [
        (str(path), str(mingw_inc), clang_args, sdk_names)
        for path in files
    ]
    with ProcessPoolExecutor(max_workers=jobs) as executor:
        futures = {executor.submit(_worker, item): item[0] for item in worker_args}
        for done, fut in enumerate(as_completed(futures), start=1):
            if done % 50 == 0:
                print(f"  {done}/{len(files)} ...", flush=True)
            try:
                # 完了したファイルから順に結果を取り出して全体集計へ足し込む。
                direct, dynamic = fut.result()
            except Exception as exc:
                failed_files += 1
                print(f"  WARN: {futures[fut]}: {exc}", file=sys.stderr)
                continue
            _add_counts(all_direct, direct)
            _add_counts(all_dynamic, dynamic)
            parsed_files += 1
    return parsed_files, failed_files


def main() -> None:
    # コマンドライン引数を定義する。
    parser = argparse.ArgumentParser(
        description="Enumerate explicitly referenced Windows SDK APIs via Clang AST"
    )
    parser.add_argument("src_dirs", nargs="+", metavar="SRC_DIR")
    parser.add_argument("--output", default="windows_sdk_api_stats.json")
    parser.add_argument("--mingw", metavar="DIR")
    parser.add_argument(
        "--sdk-header",
        action="append",
        default=[],
        metavar="HEADER",
        help="extra SDK header used to recognise GetProcAddress targets",
    )
    parser.add_argument(
        "--jobs",
        "-j",
        type=int,
        default=os.cpu_count() or 1,
        help="parallel worker count (default: CPU count)",
    )
    args = parser.parse_args()

    # 解析に必要な Windows ヘッダ位置、Clang オプション、SDK 関数名一覧を準備する。
    mingw_inc = Path(args.mingw) if args.mingw else _find_mingw_include()
    clang_args = _clang_args(mingw_inc)
    sdk_headers = list(_DEFAULT_SDK_HEADERS) + args.sdk_header

    print(f"MinGW headers : {mingw_inc}")
    print("Building Windows SDK function registry ...")
    sdk_names = collect_sdk_function_names(mingw_inc, clang_args, sdk_headers)
    print(f"  -> {len(sdk_names)} function names")

    # 入力ディレクトリから解析対象ファイルを集める。
    files = _source_files(args.src_dirs)
    print(f"Parsing {len(files)} source files ...")

    # 全ファイル分の direct/dynamic 呼び出し回数をここに集約する。
    all_direct: dict[str, int] = defaultdict(int)
    all_dynamic: dict[str, int] = defaultdict(int)

    # 指定された worker 数に応じて直列または並列で解析する。
    if args.jobs <= 1 or len(files) <= 1:
        parsed_files, failed_files = _parse_files_serial(
            files, clang_args, mingw_inc, sdk_names, all_direct, all_dynamic
        )
    else:
        try:
            parsed_files, failed_files = _parse_files_parallel(
                files,
                clang_args,
                mingw_inc,
                sdk_names,
                all_direct,
                all_dynamic,
                args.jobs,
            )
        except PermissionError as exc:
            # 一部の制限環境では ProcessPoolExecutor が使えないため、直列に戻す。
            print(f"WARN: parallel execution unavailable ({exc}); using one worker")
            parsed_files, failed_files = _parse_files_serial(
                files, clang_args, mingw_inc, sdk_names, all_direct, all_dynamic
            )

    # JSON 出力用に総数、成功/失敗ファイル数、API ごとの回数一覧をまとめる。
    entries = _merge_entries(all_direct, all_dynamic)
    result = {
        "source_files_found": len(files),
        "source_files_parsed": parsed_files,
        "source_files_failed": failed_files,
        "sdk_function_names": len(sdk_names),
        "api_count": len(entries),
        "direct_call_count": sum(all_direct.values()),
        "dynamic_call_count": sum(all_dynamic.values()),
        "total_call_count": sum(e["total_count"] for e in entries),
        "apis": entries,
    }

    out_path = Path(args.output)
    # ensure_ascii=False にしておくと、将来日本語フィールド等を入れても読みやすく出力される。
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    # 標準出力には概要と上位 30 件だけを表示する。詳細は JSON を見る。
    print(f"\nResult -> {out_path}")
    print(f"  Source files : {parsed_files}/{len(files)} parsed")
    print(f"  SDK APIs     : {len(entries)}")
    print(f"  Calls        : {result['total_call_count']} "
          f"(direct: {result['direct_call_count']}, "
          f"GetProcAddress: {result['dynamic_call_count']})")

    if entries:
        print("\nTop APIs:")
        for entry in entries[:30]:
            print(
                f"  {entry['total_count']:>6}x  {entry['api']} "
                f"(direct={entry['direct_count']}, dyn={entry['dynamic_count']})"
            )


if __name__ == "__main__":
    # スクリプトとして直接実行されたときだけ main() を走らせる。
    main()
