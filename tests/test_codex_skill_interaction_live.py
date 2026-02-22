import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_BASE_URL = "http://127.0.0.1:23119"
LOCAL_HEADERS = {"Zotero-API-Version": "3", "Zotero-Allowed-Request": "1"}
COVERAGE_FILE = REPO_ROOT / "tests" / "functional_coverage_latest.json"
SKILL_PATHS = {
    "zotero-library": REPO_ROOT / "skills" / "zotero-library" / "SKILL.md",
    "zotero-better-bibtex": REPO_ROOT / "skills" / "zotero-better-bibtex" / "SKILL.md",
}
CAPABILITY_MATRIX = {
    "zotero-library": [
        "bootstrap_local_api",
        "collections_inventory",
        "collection_items_read",
        "query_qmode",
        "query_include_trashed",
        "incremental_since_versions",
        "troubleshoot_failure_capture",
        "troubleshoot_recovery",
    ],
    "zotero-better-bibtex": [
        "api_ready",
        "item_search",
        "item_citationkey",
        "item_export_bibtex",
        "item_export_biblatex",
        "collection_scope_resolve",
        "collection_citationkeys",
        "collection_export_bibtex",
    ],
}


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _http_get_raw(url: str, headers: dict, timeout: float = 8.0) -> tuple[int, bytes, dict, str]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(), dict(resp.headers), ""
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers), str(exc.reason)
    except Exception as exc:
        return 0, b"", {}, str(exc)


def _wait_for_local_api_ready(timeout_sec: float = 30.0) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", "-a", "Zotero"], check=False, capture_output=True, text=True)

    endpoint = f"{LOCAL_BASE_URL}/api/users/0/collections?limit=1"
    deadline = time.time() + timeout_sec
    last_error = None
    while time.time() < deadline:
        status, _, _, error = _http_get_raw(endpoint, LOCAL_HEADERS, timeout=5.0)
        if status == 200:
            return
        last_error = error or f"status={status}"
        time.sleep(1.0)
    raise RuntimeError(
        "Local Zotero API is not ready on 127.0.0.1:23119. "
        "Ensure Zotero Desktop is running and Local API is enabled. "
        f"last_error={last_error}"
    )


def _run_codex_with_schema(prompt: str, schema: dict) -> dict:
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        schema_path = tmpdir / "schema.json"
        out_path = tmpdir / "out.json"
        schema_path.write_text(json.dumps(schema, ensure_ascii=True), encoding="utf-8")

        cmd = [
            "codex",
            "exec",
            "-C",
            str(REPO_ROOT),
            "-s",
            "danger-full-access",
            "-c",
            "approval_policy=never",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(out_path),
            prompt,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=480, check=False)
        if proc.returncode != 0:
            stderr_tail = "\n".join((proc.stderr or "").splitlines()[-40:])
            stdout_tail = "\n".join((proc.stdout or "").splitlines()[-40:])
            raise AssertionError(
                "codex exec failed.\n"
                f"returncode={proc.returncode}\n"
                f"stdout_tail=\n{stdout_tail}\n"
                f"stderr_tail=\n{stderr_tail}\n"
            )

        if not out_path.exists():
            raise AssertionError("codex output file missing; --output-last-message was not written")
        return json.loads(out_path.read_text(encoding="utf-8"))


def _assert_skill_identity(testcase: unittest.TestCase, result: dict, skill_name: str) -> None:
    testcase.assertEqual(result["skill_name"], skill_name)
    testcase.assertEqual(result["skill_sha256"], _sha256_file(SKILL_PATHS[skill_name]))


def _record_coverage(skill_name: str, capability_pass: dict[str, bool]) -> None:
    report = {}
    if COVERAGE_FILE.exists():
        report = json.loads(COVERAGE_FILE.read_text(encoding="utf-8"))

    expected = CAPABILITY_MATRIX[skill_name]
    passed = [c for c in expected if capability_pass.get(c, False)]
    failed = [c for c in expected if not capability_pass.get(c, False)]

    report[skill_name] = {
        "expected": expected,
        "passed": passed,
        "failed": failed,
        "covered": len(passed),
        "total": len(expected),
        "coverage_percent": round((len(passed) / len(expected)) * 100, 2) if expected else 0.0,
    }

    entries = [v for k, v in report.items() if not k.startswith("_")]
    total_expected = sum(v["total"] for v in entries)
    total_passed = sum(v["covered"] for v in entries)
    report["_summary"] = {
        "covered": total_passed,
        "total": total_expected,
        "coverage_percent": round((total_passed / total_expected) * 100, 2) if total_expected else 0.0,
    }
    COVERAGE_FILE.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")


class CodexCollectionServiceLiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not shutil.which("codex"):
            raise unittest.SkipTest("codex binary not found in PATH")
        if COVERAGE_FILE.exists():
            COVERAGE_FILE.unlink()
        _wait_for_local_api_ready(timeout_sec=30.0)

    def test_zotero_library_service_flow(self) -> None:
        skill_name = "zotero-library"

        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "skill_name": {"type": "string"},
                "skill_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                "bootstrap_status": {"type": "integer"},
                "collections_status": {"type": "integer"},
                "collection_count": {"type": "integer", "minimum": 0},
                "sample_collection_key": {"type": "string"},
                "sample_items_status": {"type": "integer"},
                "query_status": {"type": "integer"},
                "include_trashed_status": {"type": "integer"},
                "seed_version": {"type": "string", "pattern": "^[0-9]+$"},
                "delta_status": {"type": "integer"},
                "bad_status": {"type": "integer"},
                "recovery_status": {"type": "integer"},
            },
            "required": [
                "skill_name",
                "skill_sha256",
                "bootstrap_status",
                "collections_status",
                "collection_count",
                "sample_collection_key",
                "sample_items_status",
                "query_status",
                "include_trashed_status",
                "seed_version",
                "delta_status",
                "bad_status",
                "recovery_status",
            ],
            "additionalProperties": False,
        }

        prompt = (
            "Read skills/zotero-library/SKILL.md and run a full validation flow. "
            "Output JSON only, matching the schema exactly: "
            "1) Bootstrap: GET /api/users/0/collections?limit=1 and return bootstrap_status. "
            "2) Inventory: GET /api/users/0/collections/top?limit=10&format=json&include=data and return collections_status and collection_count. "
            "3) Use the first collection key as sample_collection_key, then request /api/users/0/collections/<key>/items?limit=3&format=json&include=data and return sample_items_status. "
            "4) Query shaping: request /api/users/0/items/top?limit=3&q=learning&qmode=everything&format=json&include=data and return query_status. "
            "5) Include trashed: request /api/users/0/items/top?limit=3&includeTrashed=1&format=json&include=data and return include_trashed_status. "
            "6) Incremental: read Last-Modified-Version from /api/users/0/collections?limit=1 as seed_version, then request /api/users/0/collections?since=<seed_version>&format=versions and return delta_status. "
            "7) Troubleshooting: request /api/users/0/collections/THISDOESNOTEXIST and return bad_status, then request /api/users/0/collections/top?limit=1&format=json and return recovery_status. "
            "8) Every local API request must include Zotero-API-Version:3 and Zotero-Allowed-Request:1. "
            "9) Return SKILL.md sha256."
        )

        result = _run_codex_with_schema(prompt, schema)
        _assert_skill_identity(self, result, skill_name)

        capability_pass = {
            "bootstrap_local_api": result["bootstrap_status"] == 200,
            "collections_inventory": result["collections_status"] == 200 and result["collection_count"] > 0,
            "collection_items_read": bool(result["sample_collection_key"]) and result["sample_items_status"] == 200,
            "query_qmode": result["query_status"] == 200,
            "query_include_trashed": result["include_trashed_status"] == 200,
            "incremental_since_versions": result["delta_status"] == 200,
            "troubleshoot_failure_capture": result["bad_status"] != 200,
            "troubleshoot_recovery": result["recovery_status"] == 200,
        }
        _record_coverage(skill_name, capability_pass)

        for cap in CAPABILITY_MATRIX[skill_name]:
            self.assertTrue(capability_pass[cap], f"capability failed: {cap}")

    def test_zotero_better_bibtex_plugin_flow(self) -> None:
        skill_name = "zotero-better-bibtex"

        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "skill_name": {"type": "string"},
                "skill_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                "api_ready_status": {"type": "integer"},
                "item_search_status": {"type": "integer"},
                "item_search_hits": {"type": "integer", "minimum": 0},
                "sample_item_key": {"type": "string"},
                "item_citationkey_status": {"type": "integer"},
                "sample_citekey": {"type": "string"},
                "item_export_bibtex_status": {"type": "integer"},
                "item_export_biblatex_status": {"type": "integer"},
                "collection_key": {"type": "string"},
                "collection_items_status": {"type": "integer"},
                "collection_citationkey_status": {"type": "integer"},
                "collection_export_status": {"type": "integer"},
                "collection_export_item_count": {"type": "integer", "minimum": 0},
                "fallback_collections_status": {"type": "integer"},
            },
            "required": [
                "skill_name",
                "skill_sha256",
                "api_ready_status",
                "item_search_status",
                "item_search_hits",
                "sample_item_key",
                "item_citationkey_status",
                "sample_citekey",
                "item_export_bibtex_status",
                "item_export_biblatex_status",
                "collection_key",
                "collection_items_status",
                "collection_citationkey_status",
                "collection_export_status",
                "collection_export_item_count",
                "fallback_collections_status",
            ],
            "additionalProperties": False,
        }

        prompt = (
            "Read skills/zotero-better-bibtex/SKILL.md and validate both item-scope and collection-scope exports. "
            "Output JSON only, matching the schema exactly: "
            "1) api.ready: POST /better-bibtex/json-rpc with method=api.ready, return api_ready_status. "
            "2) item.search: method=item.search with params={terms:'learning'}, return item_search_status and item_search_hits. "
            "3) Pick one usable item from item.search results and return sample_item_key and sample_citekey. "
            "4) item.citationkey: method=item.citationkey with params={item_keys:[sample_item_key]}, return item_citationkey_status. "
            "5) Item export scope: "
            "method=item.export with params={citekeys:[sample_citekey],translator:'Better BibTeX'} and return item_export_bibtex_status; "
            "method=item.export with params={citekeys:[sample_citekey],translator:'Better BibLaTeX'} and return item_export_biblatex_status. "
            "6) Collection scope: "
            "query /api/users/0/collections/top?limit=20&format=json&include=data to choose collection_key; "
            "query /api/users/0/collections/<collection_key>/items?limit=20&format=json&include=data and return collection_items_status; "
            "use item keys with item.citationkey to get non-empty citekeys (at least one), return collection_citationkey_status; "
            "use those citekeys with item.export translator='Better BibTeX', return collection_export_status and collection_export_item_count. "
            "7) Fallback check: query /api/users/0/collections/top?limit=1&format=json and return fallback_collections_status. "
            "8) Every local API request must include Zotero-API-Version:3 and Zotero-Allowed-Request:1. "
            "9) Return SKILL.md sha256."
        )

        result = _run_codex_with_schema(prompt, schema)
        _assert_skill_identity(self, result, skill_name)

        capability_pass = {
            "api_ready": result["api_ready_status"] == 200,
            "item_search": result["item_search_status"] == 200 and result["item_search_hits"] > 0,
            "item_citationkey": bool(result["sample_item_key"]) and result["item_citationkey_status"] == 200 and bool(result["sample_citekey"]),
            "item_export_bibtex": result["item_export_bibtex_status"] == 200,
            "item_export_biblatex": result["item_export_biblatex_status"] == 200,
            "collection_scope_resolve": bool(result["collection_key"]) and result["collection_items_status"] == 200,
            "collection_citationkeys": result["collection_citationkey_status"] == 200 and result["collection_export_item_count"] > 0,
            "collection_export_bibtex": result["collection_export_status"] == 200 and result["fallback_collections_status"] == 200,
        }
        _record_coverage(skill_name, capability_pass)

        for cap in CAPABILITY_MATRIX[skill_name]:
            self.assertTrue(capability_pass[cap], f"capability failed: {cap}")


if __name__ == "__main__":
    unittest.main()
