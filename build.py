#!/usr/bin/env python3
"""
RWX-Luna Build & Sync
Author: rwyn (@rwyn)

Usage:
    python build.py
    python build.py --watch
    python build.py --check
"""

import os
import sys
import time
import hashlib
import shutil
import re

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_CSS = os.path.join(ROOT_DIR, "RWX-Luna.css")
LOADER_CSS = os.path.join(ROOT_DIR, "RWX-Luna.theme.css")
CLIENT_THEME_DIR = os.path.join(ROOT_DIR, "clientTheme")
ADDONS_DIR = os.path.join(ROOT_DIR, "addons")
VENCORD_THEMES_DIR = os.path.expandvars(r"%APPDATA%\Vencord\themes")

MODULES = [
    {
        "name": "clientTheme/_VencordOptions.css",
        "file": os.path.join(CLIENT_THEME_DIR, "_VencordOptions.css"),
        "begin_marker": "/* === BEGIN: clientTheme/_VencordOptions.css === */",
        "end_marker": "/* === END: clientTheme/_VencordOptions.css === */",
    }
]

def get_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def validate(content: str) -> bool:
    opens = content.count("{")
    closes = content.count("}")
    if opens != closes:
        print(f"[ERROR] Syntax Error: Unbalanced braces! {{ = {opens}, }} = {closes} (diff: {opens - closes})", file=sys.stderr)
        return False

    # check for :has() 
    clean = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    has_matches = list(re.finditer(r":has\(", clean))
    if has_matches:
        print(f"[ERROR] Found {len(has_matches)} prohibited ':has()' pseudo-class selectors!", file=sys.stderr)
        return False

    return True

def build() -> bool:
    if not os.path.exists(MAIN_CSS):
        print(f"[ERROR] {MAIN_CSS} not found!", file=sys.stderr)
        return False

    with open(MAIN_CSS, "r", encoding="utf-8") as f:
        content = f.read()

    modified = False
    for mod in MODULES:
        if not os.path.exists(mod["file"]):
            continue

        with open(mod["file"], "r", encoding="utf-8") as f:
            mod_content = f.read().strip()

        if mod_content.startswith("/**"):
            end_hdr = mod_content.find("*/")
            if end_hdr != -1:
                mod_content = mod_content[end_hdr + 2:].strip()

        begin = mod["begin_marker"]
        end = mod["end_marker"]

        if begin in content and end in content:
            idx_start = content.find(begin) + len(begin)
            idx_end = content.find(end)
            new_block = "\n" + mod_content + "\n"
            if content[idx_start:idx_end] != new_block:
                content = content[:idx_start] + new_block + content[idx_end:]
                modified = True
                print(f"[MODULE] Injected: {mod['name']}")

    if not validate(content):
        return False

    if os.path.exists(LOADER_CSS):
        with open(LOADER_CSS, "r", encoding="utf-8") as f_loader:
            if not validate(f_loader.read()):
                return False

    if modified:
        with open(MAIN_CSS, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print(f"[OK] Rebuilt {os.path.basename(MAIN_CSS)} (SHA256: {get_hash(content)[:12]}...)")
    else:
        print(f"[OK] {os.path.basename(MAIN_CSS)} is up to date (SHA256: {get_hash(content)[:12]}...)")

    # sync vencord folder if it exists
    if os.path.isdir(VENCORD_THEMES_DIR):
        targets = [
            (MAIN_CSS, os.path.join(VENCORD_THEMES_DIR, "RWX-Luna-Rework.css")),
            (LOADER_CSS, os.path.join(VENCORD_THEMES_DIR, "RWX-Luna.theme.css")),
        ]
        for src, target in targets:
            if os.path.exists(src):
                try:
                    shutil.copyfile(src, target)
                except Exception as e:
                    print(f"[WARN] Failed to copy to {target}: {e}")
        print(f"[SYNC] Synchronized to Vencord themes folder: {VENCORD_THEMES_DIR}")

    return True

def watch():
    print("[WATCH] Watching clientTheme/ for changes... Press Ctrl+C to exit.")
    last_mtimes = {}

    def get_mtimes():
        mtimes = {}
        for mod in MODULES:
            if os.path.exists(mod["file"]):
                mtimes[mod["file"]] = os.path.getmtime(mod["file"])
        return mtimes

    last_mtimes = get_mtimes()
    build()

    try:
        while True:
            time.sleep(0.5)
            curr_mtimes = get_mtimes()
            if curr_mtimes != last_mtimes:
                last_mtimes = curr_mtimes
                print("\n[WATCH] Detected file changes. Rebuilding...")
                build()
    except KeyboardInterrupt:
        print("\n[WATCH] Stopped watching.")

if __name__ == "__main__":
    if "--watch" in sys.argv:
        watch()
    elif "--check" in sys.argv:
        valid = True
        check_paths = [MAIN_CSS, LOADER_CSS]
        if os.path.isdir(ADDONS_DIR):
            for af in os.listdir(ADDONS_DIR):
                if af.endswith(".css"):
                    check_paths.append(os.path.join(ADDONS_DIR, af))
        for path in check_paths:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    if not validate(f.read()):
                        valid = False
        sys.exit(0 if valid else 1)
    else:
        success = build()
        sys.exit(0 if success else 1)

