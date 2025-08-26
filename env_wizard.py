#!/usr/bin/env python3
# Terminal .env wizard (stdlib only)
# - Reads a .env.copy template with optional metadata comments
# - Prompts user for values (masking secrets)
# - Writes a .env with safe quoting
#
# Template rules:
#   #@title=Your App Name             (optional window/heading title)
#   #@validate=URL|INT|FLOAT|BOOL     (per-field validator)
#   #@choices=opt1|opt2|opt3          (mutually exclusive list)
#   #: Human label here                (nice label for the next KEY)
#   KEY=default                       (env entry; defaults allowed)
#
# Secrets are auto-detected if KEY includes KEY|TOKEN|SECRET|PASSWORD

from __future__ import annotations
import argparse
import os
import re
import sys
from getpass import getpass
from pathlib import Path
from typing import List, Tuple, Dict, Optional

TEMPLATE_FILENAME = ".env.copy"
OUTPUT_FILENAME = ".env"
SECRET_HINTS = ("KEY", "SECRET", "TOKEN", "PASSWORD")

Field = Dict[str, str | bool | list]

def parse_template(path: Path) -> Tuple[str, List[Field]]:
    title = "Environment Setup"
    fields: List[Field] = []
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")

    label_buf: Optional[str] = None
    validate_buf: Optional[str] = None
    choices_buf: Optional[List[str]] = None

    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")

            if not line.strip():
                # blank line: reset only the user-facing label buffer
                label_buf = None
                validate_buf = None
                choices_buf = None
                continue

            if line.startswith("#@title="):
                title = line.split("=", 1)[1].strip() or title
                continue

            if line.startswith("#@validate="):
                validate_buf = line.split("=", 1)[1].strip().upper() or None
                continue

            if line.startswith("#@choices="):
                choices_buf = [s.strip() for s in line.split("=", 1)[1].split("|") if s.strip()]
                continue

            if line.startswith("#:"):
                label_buf = line[2:].strip() or None
                continue

            if line.startswith("#"):
                continue

            if "=" in line:
                key, default = line.split("=", 1)
                key = key.strip()
                default = default.strip()

                if not re.fullmatch(r"[A-Z0-9_]+", key):
                    raise ValueError(f"Invalid env key in template: {key}")

                secret = any(h in key.upper() for h in SECRET_HINTS)
                label = label_buf or key.replace("_", " ").title()

                fields.append({
                    "key": key,
                    "label": label,
                    "default": default,
                    "secret": secret,
                    "validate": validate_buf or "",
                    "choices": choices_buf or [],
                })

                # reset field-scoped buffers
                label_buf = None
                validate_buf = None
                choices_buf = None

    if not fields:
        raise ValueError("No fields found in template.")
    return title, fields

def load_existing_env(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    if not path.exists():
        return data
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip()
            if v.startswith('"') and v.endswith('"'):
                v = v[1:-1].replace('\\"', '"')
            data[k] = v
    return data

# ---------- Validators ----------
def is_bool(s: str) -> bool:
    return s.lower() in {"1","0","true","false","yes","no","y","n","on","off"}

def norm_bool(s: str) -> str:
    return "true" if s.lower() in {"1","true","yes","y","on"} else "false"

def is_int(s: str) -> bool:
    try:
        int(s)
        return True
    except ValueError:
        return False

def is_float(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False

def is_url(s: str) -> bool:
    return bool(re.match(r"^https?://", s, flags=re.I))

def is_email(s: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", s))

def run_validator(kind: str, value: str, choices: List[str]) -> Tuple[bool, str]:
    k = (kind or "").upper()
    if choices:
        if value in choices:
            return True, value
        return False, f"Value must be one of: {', '.join(choices)}"

    if not k or k == "ANY":
        return True, value
    if k == "BOOL":
        if is_bool(value):
            return True, norm_bool(value)
        return False, "Enter a boolean: true/false/yes/no/1/0"
    if k == "INT":
        return (is_int(value), "Enter an integer (e.g., 42)")
    if k == "FLOAT":
        return (is_float(value), "Enter a number (e.g., 3.14)")
    if k == "URL":
        return (is_url(value), "Enter a URL starting with http:// or https://")
    if k == "EMAIL":
        return (is_email(value), "Enter a valid email address")
    if k == "PATH":
        # Accept any string, but expand and normalize
        p = os.path.expanduser(value)
        return True, os.path.abspath(p)
    return True, value  # unknown validator -> accept

# ---------- I/O ----------
def quote_if_needed(v: str) -> str:
    needs_quote = bool(re.search(r"\s|#", v)) or v != v.strip()
    if needs_quote:
        return '"' + v.replace('"', '\\"') + '"'
    return v

def save_env(path: Path, pairs: List[Tuple[str, str]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for k, v in pairs:
            f.write(f"{k}={quote_if_needed(v)}\n")

def prompt(label: str, default: str, secret: bool) -> str:
    shown_default = f" [{default}]" if default else ""
    if secret:
        # Show hint of default length without revealing
        if default:
            print(f"{label}{shown_default} (hidden). Press Enter to keep default.")
        else:
            print(f"{label}")
        val = getpass("> ").strip()
        if not val and default:
            return default
        return val
    else:
        raw = input(f"{label}{shown_default}: ").strip()
        if not raw and default:
            return default
        return raw

def main():
    ap = argparse.ArgumentParser(description="Terminal wizard to create a .env from .env.copy")
    ap.add_argument("--template", "-t", default=TEMPLATE_FILENAME, help="Template file path (default: .env.copy)")
    ap.add_argument("--output", "-o", default=OUTPUT_FILENAME, help="Output .env path (default: .env)")
    ap.add_argument("--load-existing", "-l", action="store_true", help="Pre-fill from existing .env if found")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite output if it exists")
    args = ap.parse_args()

    template_path = Path(args.template).resolve()
    output_path = Path(args.output).resolve()

    try:
        title, fields = parse_template(template_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print("=" * len(title))
    print(title)
    print("=" * len(title))
    print("Press Enter to accept defaults. Ctrl+C to abort.\n")

    existing: Dict[str, str] = {}
    if args.load_existing:
        existing = load_existing_env(output_path)
        if existing:
            print(f"Loaded existing values from {output_path}\n")

    answers: List[Tuple[str, str]] = []
    for f in fields:
        key = str(f["key"])
        label = str(f["label"])
        default = existing.get(key, str(f["default"]))
        secret = bool(f["secret"])
        validate_kind = str(f.get("validate", "") or "")
        choices = list(f.get("choices", []) or [])

        # choices hint
        if choices:
            print(f"(choices: {', '.join(choices)})")

        while True:
            val = prompt(label, default, secret)
            ok, msg_or_val = run_validator(validate_kind, val, choices)
            if ok:
                # msg_or_val may be normalized value
                answers.append((key, str(msg_or_val if validate_kind else val)))
                break
            else:
                print(f"  ✖ {msg_or_val}")

    if output_path.exists() and not args.overwrite:
        # ask confirmation
        yn = input(f"\n{output_path} exists. Overwrite? [y/N]: ").strip().lower()
        if yn not in {"y", "yes"}:
            print("Aborted.")
            sys.exit(0)

    try:
        save_env(output_path, answers)
        print(f"\n✔ Wrote {OUTPUT_FILENAME} to: {output_path}")
    except Exception as e:
        print(f"Error writing {output_path}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted by user.")
        sys.exit(130)
