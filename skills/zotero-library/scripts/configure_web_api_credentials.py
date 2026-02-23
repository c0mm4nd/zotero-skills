#!/usr/bin/env python3
"""Configure Zotero Web API credentials directly in skills/zotero-library/SKILL.md."""

from __future__ import annotations

import argparse
import getpass
import re
import sys
from pathlib import Path


USER_PLACEHOLDER = "__ZOTERO_WEB_API_USER_ID__"
KEY_PLACEHOLDER = "__ZOTERO_WEB_API_KEY__"
USER_PATTERN = re.compile(r"(- WEB_API_USER_ID: `)([^`]+)(`)")
KEY_PATTERN = re.compile(r"(- WEB_API_KEY: `)([^`]+)(`)")


def _mask_key(key: str) -> str:
    if len(key) <= 8:
        return "*" * len(key)
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


def _replace_once(text: str, pattern: re.Pattern[str], value: str, label: str) -> str:
    updated, count = pattern.subn(rf"\1{value}\3", text, count=1)
    if count != 1:
        raise RuntimeError(f"Failed to locate {label} marker in SKILL.md")
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Write Zotero Web API credentials into SKILL.md")
    parser.add_argument(
        "--skill-path",
        default=str(Path(__file__).resolve().parents[1] / "SKILL.md"),
        help="Path to zotero-library SKILL.md",
    )
    parser.add_argument("--user-id", help="Zotero Web API user ID")
    parser.add_argument("--api-key", help="Zotero Web API key")
    parser.add_argument("--force", action="store_true", help="Overwrite existing non-placeholder values")
    args = parser.parse_args()

    skill_path = Path(args.skill_path)
    if not skill_path.exists():
        raise FileNotFoundError(f"SKILL file not found: {skill_path}")

    text = skill_path.read_text(encoding="utf-8")
    user_match = USER_PATTERN.search(text)
    key_match = KEY_PATTERN.search(text)
    if not user_match or not key_match:
        raise RuntimeError("WEB_API_USER_ID / WEB_API_KEY markers not found in SKILL.md")

    current_user = user_match.group(2).strip()
    current_key = key_match.group(2).strip()

    if not args.force:
        if current_user not in ("", USER_PLACEHOLDER) or current_key not in ("", KEY_PLACEHOLDER):
            print("Credentials already configured. Re-run with --force to overwrite.", file=sys.stderr)
            return 2

    user_id = (args.user_id or input("Zotero Web API user ID: ").strip())
    if not user_id.isdigit():
        print("User ID must be numeric.", file=sys.stderr)
        return 2

    api_key = (args.api_key or getpass.getpass("Zotero Web API key (input hidden): ").strip())
    if not api_key:
        print("API key cannot be empty.", file=sys.stderr)
        return 2

    updated = _replace_once(text, USER_PATTERN, user_id, "WEB_API_USER_ID")
    updated = _replace_once(updated, KEY_PATTERN, api_key, "WEB_API_KEY")
    skill_path.write_text(updated, encoding="utf-8")

    print(f"Updated credentials in: {skill_path}")
    print(f"WEB_API_USER_ID={user_id}")
    print(f"WEB_API_KEY={_mask_key(api_key)}")
    print("Note: API key is stored in plaintext in SKILL.md by design.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
