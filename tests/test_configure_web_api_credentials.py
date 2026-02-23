import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "skills" / "zotero-library" / "scripts" / "configure_web_api_credentials.py"
USER_PLACEHOLDER = "__ZOTERO_WEB_API_USER_ID__"
KEY_PLACEHOLDER = "__ZOTERO_WEB_API_KEY__"


class ConfigureWebApiCredentialsTests(unittest.TestCase):
    def test_numeric_user_id_replacement_preserves_line_format(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            skill_path = Path(td) / "SKILL.md"
            skill_path.write_text(
                "\n".join(
                    [
                        "---",
                        "name: zotero-library",
                        "---",
                        "## Web API credentials (plaintext, required)",
                        f"- WEB_API_USER_ID: `{USER_PLACEHOLDER}`",
                        f"- WEB_API_KEY: `{KEY_PLACEHOLDER}`",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    "python3",
                    str(SCRIPT_PATH),
                    "--skill-path",
                    str(skill_path),
                    "--user-id",
                    "10593900",
                    "--api-key",
                    "TESTKEY123",
                    "--force",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)

            updated = skill_path.read_text(encoding="utf-8")
            self.assertIn("- WEB_API_USER_ID: `10593900`", updated)
            self.assertIn("- WEB_API_KEY: `TESTKEY123`", updated)
            self.assertNotIn("H593900`", updated)


if __name__ == "__main__":
    unittest.main()
