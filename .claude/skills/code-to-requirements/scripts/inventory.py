#!/usr/bin/env python3
"""
Deterministic structural inventory of C-family source (C, C++, Arduino .ino).

No third-party dependencies. Regex + brace matching, not a real parser, so it
is best-effort: good enough to give the analyst a checklist of every function,
global, macro and call edge so nothing gets skipped or invented.

Usage:
    python3 inventory.py <file-or-dir> [more paths...] [--json OUT] [--md OUT]

With no --json/--md flags, prints the markdown summary to stdout.
"""
import argparse
import json
import os
import re
import sys

EXTS = {".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hh", ".ino"}
KEYWORDS = {
    "if", "for", "while", "switch", "return", "sizeof", "do", "else", "case",
    "break", "continue", "goto", "default", "typedef", "struct", "union", "enum",
    "static", "extern", "const", "volatile", "inline", "register", "auto",
    "void", "int", "char", "float", "double", "long", "short", "unsigned",
    "signed", "bool", "true", "false", "NULL", "defined", "class", "public",
    "private", "protected", "new", "delete", "template", "namespace", "using",
}

# Function definition: return-type tokens, name, (params), then an opening brace.
FUNC_RE = re.compile(
    r"""(?P<sig>
          (?:[A-Za-z_][\w:<>\*&\s,]*?\s+)?     # return type (optional for ctors)
          [\*&\s]*
          (?P<name>[A-Za-z_]\w*(?:::[A-Za-z_]\w*)?)   # name
          \s*\((?P<params>[^;{}()]*)\)         # params, no nested parens
        )
        \s*(?:const\s*)?\{""",
    re.VERBOSE,
)
PROTO_RE = re.compile(r"^\s*[A-Za-z_][\w\s\*&:<>,]*?\b([A-Za-z_]\w*)\s*\(([^;{}()]*)\)\s*;", re.M)
DEFINE_RE = re.compile(r"^\s*#\s*define\s+(\w+)(\([^)]*\))?\s*(.*)$", re.M)
INCLUDE_RE = re.compile(r"^\s*#\s*include\s*[<\"]([^>\"]+)[>\"]", re.M)
CALL_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
GLOBAL_RE = re.compile(
    r"^(?!\s*#)(?!\s*(?:typedef|return|else|case)\b)\s*"
    r"((?:static\s+|extern\s+|const\s+|volatile\s+|unsigned\s+|signed\s+)*"
    r"[A-Za-z_][\w:<>]*(?:\s*[\*&]+\s*|\s+)[\*&]*[A-Za-z_]\w*(?:\s*\[[^\]]*\])*"
    r"(?:\s*=\s*[^;]+)?)\s*;",
    re.M,
)
CONTROL_RE = re.compile(r"\b(if|else|for|while|do|switch|case|goto|return)\b")
IO_RE = re.compile(
    r"\b(printf|scanf|fprintf|fscanf|puts|gets|fgets|fputs|getchar|putchar|"
    r"fopen|fclose|fread|fwrite|Serial\.\w+|digitalRead|digitalWrite|analogRead|"
    r"analogWrite|pinMode|delay|millis|micros|Wire\.\w+|SPI\.\w+|EEPROM\.\w+|"
    r"exit|abort|malloc|calloc|realloc|free|rand|srand|time)\b"
)


def strip_comments_and_strings(src: str) -> str:
    """Blank out comments and string/char literals while preserving line numbers."""
    out = []
    i, n = 0, len(src)
    while i < n:
        ch = src[i]
        two = src[i:i + 2]
        if two == "//":
            j = src.find("\n", i)
            j = n if j == -1 else j
            out.append(" " * (j - i))
            i = j
        elif two == "/*":
            j = src.find("*/", i + 2)
            j = n if j == -1 else j + 2
            out.append("".join("\n" if c == "\n" else " " for c in src[i:j]))
            i = j
        elif ch in "\"'":
            q = ch
            j = i + 1
            while j < n and src[j] != q:
                if src[j] == "\\":
                    j += 1
                if src[j:j + 1] == "\n":
                    break
                j += 1
            j = min(j + 1, n)
            out.append(q + " " * max(0, j - i - 2) + (q if j - i >= 2 else ""))
            i = j
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def match_brace(text: str, open_idx: int) -> int:
    depth = 0
    for k in range(open_idx, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return k
    return len(text) - 1


def analyze_file(path: str) -> dict:
    with open(path, "r", errors="replace") as fh:
        raw = fh.read()
    clean = strip_comments_and_strings(raw)
    # Blank preprocessor lines so "#include <x.h>" text cannot leak into a
    # following function's return type.
    clean = re.sub(r"^[ \t]*#.*$", lambda m: " " * len(m.group(0)), clean, flags=re.M)
    raw_lines = raw.splitlines()

    functions = []
    body_spans = []
    for m in FUNC_RE.finditer(clean):
        name = m.group("name")
        if name in KEYWORDS or name.split("::")[-1] in KEYWORDS:
            continue
        sig_start = m.start("sig")
        # skip if this "definition" sits inside an earlier function body
        if any(a <= sig_start <= b for a, b in body_spans):
            continue
        open_idx = m.end() - 1
        close_idx = match_brace(clean, open_idx)
        body = clean[open_idx:close_idx + 1]
        body_spans.append((open_idx, close_idx))
        start_line = line_of(clean, sig_start)
        end_line = line_of(clean, close_idx)
        sig_text = " ".join(clean[sig_start:m.end() - 1].split())
        controls = {}
        for c in CONTROL_RE.findall(body):
            controls[c] = controls.get(c, 0) + 1
        functions.append({
            "name": name,
            "signature": sig_text,
            "params": " ".join(m.group("params").split()),
            "start_line": start_line,
            "end_line": end_line,
            "lines": end_line - start_line + 1,
            "control_keywords": controls,
            "io_and_runtime_calls": sorted(set(IO_RE.findall(body))),
            "_body": body,
        })

    # Calls: identifiers followed by "(" inside each body, excluding keywords.
    for f in functions:
        calls = []
        for c in CALL_RE.findall(f["_body"][1:]):
            if c not in KEYWORDS and c != f["name"]:
                calls.append(c)
            elif c == f["name"]:
                calls.append(c)  # recursion is worth seeing
        f["calls"] = sorted(set(calls))
        del f["_body"]

    # Text outside function bodies = file scope.
    scope = list(clean)
    for a, b in body_spans:
        for k in range(a, b + 1):
            if scope[k] != "\n":
                scope[k] = " "
    file_scope = "".join(scope)

    prototypes = [{"name": m.group(1), "params": " ".join(m.group(2).split()),
                   "line": line_of(file_scope, m.start())}
                  for m in PROTO_RE.finditer(file_scope)
                  if m.group(1) not in KEYWORDS]

    func_names = {f["name"] for f in functions}
    globals_ = []
    for m in GLOBAL_RE.finditer(file_scope):
        decl = " ".join(m.group(1).split())
        # skip prototypes and things that look like calls
        if "(" in decl or decl.split()[-1].rstrip(";") in func_names:
            continue
        globals_.append({"declaration": decl, "line": line_of(file_scope, m.start())})

    defines = [{"name": m.group(1), "args": (m.group(2) or "").strip() or None,
                "value": m.group(3).strip(), "line": line_of(raw, m.start())}
               for m in DEFINE_RE.finditer(raw)]
    includes = [m.group(1) for m in INCLUDE_RE.finditer(raw)]

    return {
        "file": path,
        "line_count": len(raw_lines),
        "includes": includes,
        "defines": defines,
        "globals": globals_,
        "prototypes": prototypes,
        "functions": functions,
    }


def collect_paths(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            for root, _dirs, names in os.walk(p):
                for nme in sorted(names):
                    if os.path.splitext(nme)[1].lower() in EXTS:
                        files.append(os.path.join(root, nme))
        elif os.path.isfile(p):
            files.append(p)
        else:
            print(f"warning: {p} not found", file=sys.stderr)
    return sorted(set(files))


def build_inventory(paths):
    files = [analyze_file(p) for p in collect_paths(paths)]
    # Names can repeat across files (six exercise files each with main), so
    # track every definition and resolve calls by name.
    defined = {}
    for fi in files:
        for f in fi["functions"]:
            defined.setdefault(f["name"], []).append((fi["file"], f))
    called_by = {name: [] for name in defined}
    for fi in files:
        for f in fi["functions"]:
            for c in f["calls"]:
                if c in called_by:
                    called_by[c].append(f["name"])
    total = 0
    for fi in files:
        for f in fi["functions"]:
            total += 1
            f["called_by"] = sorted(set(called_by[f["name"]]))
            f["external_calls"] = sorted(c for c in f["calls"] if c not in defined)
            f["internal_calls"] = sorted(c for c in f["calls"] if c in defined)
            del f["calls"]
    entry_names = {"main", "setup", "loop"}
    entry_points = sorted(f"{os.path.basename(fi['file'])}:{f['name']}"
                          for fi in files for f in fi["functions"] if f["name"] in entry_names)
    unreached = sorted(n for n, defs in defined.items()
                       if not called_by[n] and n not in entry_names)
    return {
        "files": files,
        "summary": {
            "file_count": len(files),
            "function_count": total,
            "entry_points": entry_points,
            "functions_never_called_internally": unreached,
        },
    }


def to_markdown(inv: dict) -> str:
    out = ["# Code inventory", ""]
    s = inv["summary"]
    out.append(f"- Files: {s['file_count']}  Functions: {s['function_count']}")
    out.append(f"- Entry points: {', '.join(s['entry_points']) or 'none found'}")
    if s["functions_never_called_internally"]:
        out.append("- Defined but never called from this code (public API, callbacks, or dead code): "
                   + ", ".join(s["functions_never_called_internally"]))
    out.append("")
    for fi in inv["files"]:
        out.append(f"## {fi['file']}  ({fi['line_count']} lines)")
        if fi["includes"]:
            out.append(f"- Includes: {', '.join(fi['includes'])}")
        if fi["defines"]:
            out.append("- Macros:")
            for d in fi["defines"]:
                out.append(f"  - `{d['name']}{d['args'] or ''}` = `{d['value']}` (line {d['line']})")
        if fi["globals"]:
            out.append("- File-scope variables:")
            for g in fi["globals"]:
                out.append(f"  - `{g['declaration']}` (line {g['line']})")
        out.append("")
        out.append("| Function | Lines | Calls (internal) | I/O & runtime | Called by |")
        out.append("|---|---|---|---|---|")
        for f in fi["functions"]:
            out.append(
                f"| `{f['signature']}` | {f['start_line']}-{f['end_line']} | "
                f"{', '.join(f['internal_calls']) or '-'} | "
                f"{', '.join(f['io_and_runtime_calls']) or '-'} | "
                f"{', '.join(f['called_by']) or '-'} |"
            )
        out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--json", help="write JSON inventory here")
    ap.add_argument("--md", help="write markdown summary here")
    args = ap.parse_args()
    inv = build_inventory(args.paths)
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(inv, fh, indent=2)
        print(f"wrote {args.json}", file=sys.stderr)
    if args.md:
        with open(args.md, "w") as fh:
            fh.write(to_markdown(inv))
        print(f"wrote {args.md}", file=sys.stderr)
    if not args.json and not args.md:
        print(to_markdown(inv))


if __name__ == "__main__":
    main()
