#!/usr/bin/env python3
"""
auto-update discord classes using syndishanx mappings
"""

import re
import urllib.request
from pathlib import Path

# resolve repo root whether running from root or scripts/
CURRENT_DIR = Path(__file__).resolve().parent
ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "scripts" else CURRENT_DIR

TARGET_FILES = [
    ROOT / "RWX-Luna.css",
    ROOT / "clientTheme/_VencordOptions.css",
]

CHANGES_URL = "https://raw.githubusercontent.com/SyndiShanX/Update-Classes/main/Changes.txt"

CLASS_REGEX = re.compile(r"(?<=\.)([a-zA-Z0-9]+(?:_{1,2}[a-zA-Z0-9]+)*_{1,2}[a-f0-9]{5,6})\b")


def fetch_mappings() -> dict[str, str]:
    print("fetching class diff...")
    req = urllib.request.Request(
        CHANGES_URL,
        headers={"User-Agent": "rwx-luna/1.0"}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        lines = resp.read().decode("utf-8", errors="ignore").splitlines()

    mapping: dict[str, str] = {}
    for i in range(0, len(lines) - 1, 2):
        old_c = lines[i].strip()
        new_c = lines[i + 1].strip()
        if old_c and new_c and old_c != new_c:
            mapping[old_c] = new_c

    resolved: dict[str, str] = {}
    for k, v in mapping.items():
        visited = {k}
        curr = v
        while curr in mapping and curr not in visited:
            visited.add(curr)
            curr = mapping[curr]
        if k != curr:
            resolved[k] = curr

    print(f"loaded {len(resolved):,} mappings")
    return resolved


def update_file(path: Path, mapping: dict[str, str]) -> int:
    if not path.exists():
        return 0

    content = path.read_text(encoding="utf-8")
    changes: list[tuple[str, str]] = []

    def replacer(match: re.Match) -> str:
        cls_name = match.group(1)
        if cls_name in mapping:
            new_cls = mapping[cls_name]
            if new_cls != cls_name:
                changes.append((cls_name, new_cls))
                return new_cls
        return cls_name

    new_content = CLASS_REGEX.sub(replacer, content)

    if changes:
        path.write_text(new_content, encoding="utf-8")
        unique_pairs = sorted(set(changes))
        print(f"\n{path.name} -> {len(changes)} replaced ({len(unique_pairs)} unique):")
        for old_c, new_c in unique_pairs:
            print(f"  .{old_c} -> .{new_c}")
    else:
        print(f"{path.name} -> all classes up to date")

    return len(changes)


def main():
    mapping = fetch_mappings()
    total = sum(update_file(f, mapping) for f in TARGET_FILES)
    print(f"\ndone. total {total} changes.")


if __name__ == "__main__":
    main()

