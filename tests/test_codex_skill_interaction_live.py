import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_BASE_URL = "http://127.0.0.1:23119"
WEB_API_BASE_URL = "https://api.zotero.org"
LOCAL_HEADERS = {"Zotero-API-Version": "3", "Zotero-Allowed-Request": "1"}
WEB_API_USER_PLACEHOLDER = "__ZOTERO_WEB_API_USER_ID__"
WEB_API_KEY_PLACEHOLDER = "__ZOTERO_WEB_API_KEY__"
WEB_API_USER_ENV_KEYS = ("ZOTERO_WEB_API_USER_ID", "WEB_API_USER_ID", "ZOTERO_USER_ID")
WEB_API_KEY_ENV_KEYS = ("ZOTERO_WEB_API_KEY", "WEB_API_KEY", "ZOTERO_API_KEY")
COVERAGE_FILE = REPO_ROOT / "tests" / "functional_coverage_latest.json"
SKILL_PATHS = {
    "zotero-library": REPO_ROOT / "skills" / "zotero-library" / "SKILL.md",
    "zotero-better-bibtex": REPO_ROOT / "skills" / "zotero-better-bibtex" / "SKILL.md",
}
CAPABILITY_MATRIX = {
    "zotero-library": [
        "bootstrap_web_api",
        "web_collections_inventory",
        "web_collection_items_read",
        "web_query_qmode",
        "web_query_include_trashed",
        "web_incremental_since_versions",
        "web_collection_create",
        "web_collection_delete",
        "web_write_item_create",
        "web_write_item_update",
        "web_write_note_create",
        "web_write_note_update",
        "web_write_attachment_create",
        "web_write_note_delete",
        "web_write_attachment_delete",
        "web_write_item_delete",
        "web_troubleshoot_failure_capture",
        "web_troubleshoot_recovery",
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


def _load_dotenv_into_environ(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key, value)


_load_dotenv_into_environ(REPO_ROOT / ".env")


def _resolve_web_api_user_id_from_key(api_key: str) -> str:
    req = urllib.request.Request(
        f"{WEB_API_BASE_URL}/keys/current",
        headers={"Zotero-API-Version": "3", "Zotero-API-Key": api_key},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    user_id = str(payload.get("userID", "")).strip()
    return user_id


def _read_web_api_credentials_from_skill(skill_path: Path) -> Optional[Tuple[str, str]]:
    text = skill_path.read_text(encoding="utf-8")
    user_match = re.search(r"WEB_API_USER_ID:\s*`([^`]+)`", text)
    key_match = re.search(r"WEB_API_KEY:\s*`([^`]+)`", text)
    if user_match and key_match:
        user_id = user_match.group(1).strip()
        api_key = key_match.group(1).strip()
        if user_id and api_key and user_id != WEB_API_USER_PLACEHOLDER and api_key != WEB_API_KEY_PLACEHOLDER:
            return user_id, api_key

    env_user_id = ""
    env_api_key = ""
    for key in WEB_API_USER_ENV_KEYS:
        if os.environ.get(key):
            env_user_id = os.environ[key].strip()
            break
    for key in WEB_API_KEY_ENV_KEYS:
        if os.environ.get(key):
            env_api_key = os.environ[key].strip()
            break

    if env_api_key and not env_user_id:
        try:
            env_user_id = _resolve_web_api_user_id_from_key(env_api_key)
        except Exception:
            env_user_id = ""

    if env_user_id and env_api_key:
        return env_user_id, env_api_key
    return None


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


def _run_codex_with_schema(prompt: str, schema: dict, timeout_sec: int = 480) -> dict:
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
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec, check=False)
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

    def test_zotero_library_service_flow(self) -> None:
        skill_name = "zotero-library"
        credentials = _read_web_api_credentials_from_skill(SKILL_PATHS[skill_name])
        if not credentials:
            raise unittest.SkipTest(
                "zotero-library Web API credentials are missing. Configure SKILL.md "
                "(WEB_API_USER_ID / WEB_API_KEY) or set .env vars "
                "(ZOTERO_WEB_API_USER_ID or WEB_API_USER_ID, and ZOTERO_WEB_API_KEY or WEB_API_KEY)."
            )
        web_api_user_id, _ = credentials

        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "skill_name": {"type": "string"},
                "skill_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                "web_bootstrap_status": {"type": "integer"},
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
                "collections_write_seed_version": {"type": "string", "pattern": "^[0-9]+$"},
                "write_collection_status": {"type": "integer"},
                "created_collection_key": {"type": "string"},
                "created_collection_status": {"type": "integer"},
                "delete_collection_status": {"type": "integer"},
                "deleted_collection_check_status": {"type": "integer"},
                "write_seed_version": {"type": "string", "pattern": "^[0-9]+$"},
                "write_item_status": {"type": "integer"},
                "created_item_search_status": {"type": "integer"},
                "created_item_hits": {"type": "integer", "minimum": 0},
                "created_item_key": {"type": "string"},
                "created_item_status": {"type": "integer"},
                "created_item_version": {"type": "string", "pattern": "^[0-9]+$"},
                "update_item_status": {"type": "integer"},
                "write_note_status": {"type": "integer"},
                "created_note_key": {"type": "string"},
                "update_note_status": {"type": "integer"},
                "write_attachment_status": {"type": "integer"},
                "created_attachment_key": {"type": "string"},
                "children_status": {"type": "integer"},
                "created_note_count": {"type": "integer", "minimum": 0},
                "created_attachment_count": {"type": "integer", "minimum": 0},
                "updated_note_visible": {"type": "boolean"},
                "delete_note_status": {"type": "integer"},
                "deleted_note_check_status": {"type": "integer"},
                "delete_attachment_status": {"type": "integer"},
                "deleted_attachment_check_status": {"type": "integer"},
                "delete_item_status": {"type": "integer"},
                "deleted_item_check_status": {"type": "integer"},
            },
            "required": [
                "skill_name",
                "skill_sha256",
                "web_bootstrap_status",
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
                "collections_write_seed_version",
                "write_collection_status",
                "created_collection_key",
                "created_collection_status",
                "delete_collection_status",
                "deleted_collection_check_status",
                "write_seed_version",
                "write_item_status",
                "created_item_search_status",
                "created_item_hits",
                "created_item_key",
                "created_item_status",
                "created_item_version",
                "update_item_status",
                "write_note_status",
                "created_note_key",
                "update_note_status",
                "write_attachment_status",
                "created_attachment_key",
                "children_status",
                "created_note_count",
                "created_attachment_count",
                "updated_note_visible",
                "delete_note_status",
                "deleted_note_check_status",
                "delete_attachment_status",
                "deleted_attachment_check_status",
                "delete_item_status",
                "deleted_item_check_status",
            ],
            "additionalProperties": False,
        }

        prompt = (
            "Read skills/zotero-library/SKILL.md and run a full Zotero Web API CRUD validation flow. "
            "Output JSON only, matching the schema exactly: "
            f"Use base URL {WEB_API_BASE_URL} and user id {web_api_user_id}. "
            "Use credentials from skill; if placeholders are present, use environment variables "
            "ZOTERO_WEB_API_USER_ID and ZOTERO_WEB_API_KEY. Do not print or return the key. "
            "Every request must include headers Zotero-API-Version:3 and Zotero-API-Key:<from skill>. "
            "1) Bootstrap: GET /users/<id>/collections?limit=1 and return web_bootstrap_status. "
            "2) Inventory: GET /users/<id>/collections/top?limit=10&format=json&include=data and return collections_status and collection_count. "
            "3) Use first collection key as sample_collection_key, then GET /users/<id>/collections/<key>/items?limit=3&format=json&include=data and return sample_items_status. "
            "4) Query shaping: GET /users/<id>/items/top?limit=3&q=learning&qmode=everything&format=json&include=data and return query_status. "
            "5) Include trashed: GET /users/<id>/items/top?limit=3&includeTrashed=1&format=json&include=data and return include_trashed_status. "
            "6) Incremental: read Last-Modified-Version from GET /users/<id>/collections?limit=1 as seed_version; GET /users/<id>/collections?since=<seed_version>&format=versions and return delta_status. "
            "7) Troubleshooting: GET /users/<id>/collections/THISDOESNOTEXIST return bad_status; then GET /users/<id>/collections/top?limit=1&format=json return recovery_status. "
            "8) Collection create seed: GET /users/<id>/collections?limit=1 and read Last-Modified-Version as collections_write_seed_version. "
            "9) Create collection: with run_id=timestamp string, POST /users/<id>/collections with If-Unmodified-Since-Version:collections_write_seed_version and body "
            "[{name:'Codex Web Collection '+run_id}] and return write_collection_status and created_collection_key (or empty string). "
            "10) Verify created collection: if created_collection_key non-empty, GET /users/<id>/collections/<created_collection_key>?format=json&include=data return created_collection_status; else created_collection_status=0. "
            "11) Delete created collection: if created_collection_key non-empty, refresh Last-Modified-Version from GET /users/<id>/collections?limit=1 and DELETE /users/<id>/collections/<created_collection_key> with If-Unmodified-Since-Version; return delete_collection_status. "
            "If created_collection_key empty, return delete_collection_status=0. "
            "12) Deleted collection check: if created_collection_key non-empty, GET /users/<id>/collections/<created_collection_key>?format=json and return deleted_collection_check_status (expect 404); else 0. "
            "13) Write seed: GET /users/<id>/items?limit=1 and read Last-Modified-Version as write_seed_version. "
            "14) Create item: with run_id=timestamp string, POST /users/<id>/items with If-Unmodified-Since-Version:write_seed_version and body "
            "[{itemType:'webpage',title:'Codex Web Library Live '+run_id,url:'https://example.com/codex-web-library-live/'+run_id,tags:[{tag:'codex-web-write'}]}]. "
            "Return write_item_status and created_item_key from successful write result (or empty string). "
            "15) Verify created item: GET /users/<id>/items/top?limit=5&q=<exact title>&qmode=titleCreatorYear&format=json&include=data and return created_item_search_status, created_item_hits. "
            "Then GET /users/<id>/items/<created_item_key>?format=json&include=data and return created_item_status and created_item_version. "
            "16) Update created item: PATCH /users/<id>/items/<created_item_key> with If-Unmodified-Since-Version:created_item_version and body "
            "{title:'Codex Web Library Live '+run_id+' Updated',tags:[{tag:'codex-web-write-updated'}]} and return update_item_status. "
            "17) Create note: GET /users/<id>/items?limit=1 to refresh library version, then POST /users/<id>/items with If-Unmodified-Since-Version and body "
            "[{itemType:'note',parentItem:created_item_key,note:'<p>Codex Web Note A '+run_id+'</p>'}] and return write_note_status and created_note_key. "
            "18) Update note: GET /users/<id>/items/<created_note_key>?format=json&include=data to get note version; "
            "PATCH /users/<id>/items/<created_note_key> with If-Unmodified-Since-Version:<note version> and body "
            "{note:'<p>Codex Web Note B '+run_id+'</p>'} and return update_note_status. "
            "19) Create attachment child: GET /users/<id>/items?limit=1 for library version; POST /users/<id>/items with If-Unmodified-Since-Version and body "
            "[{itemType:'attachment',parentItem:created_item_key,linkMode:'linked_url',title:'Codex Web Attachment '+run_id,url:'https://example.com/codex-web-attachment/'+run_id,contentType:'text/html'}] "
            "and return write_attachment_status and created_attachment_key. "
            "20) Verify children: GET /users/<id>/items/<created_item_key>/children?format=json&include=data and return children_status, created_note_count, created_attachment_count, updated_note_visible "
            "(true if any note child contains 'Codex Web Note B'). "
            "21) Delete note: if created_note_key non-empty, refresh Last-Modified-Version from GET /users/<id>/items?limit=1 and DELETE /users/<id>/items/<created_note_key> with If-Unmodified-Since-Version. "
            "Return delete_note_status; then GET /users/<id>/items/<created_note_key>?format=json and return deleted_note_check_status. If key empty, both are 0. "
            "22) Delete attachment: if created_attachment_key non-empty, refresh Last-Modified-Version from GET /users/<id>/items?limit=1 and DELETE /users/<id>/items/<created_attachment_key> with If-Unmodified-Since-Version. "
            "Return delete_attachment_status; then GET /users/<id>/items/<created_attachment_key>?format=json and return deleted_attachment_check_status. If key empty, both are 0. "
            "23) Delete item: if created_item_key non-empty, refresh Last-Modified-Version from GET /users/<id>/items?limit=1 and DELETE /users/<id>/items/<created_item_key> with If-Unmodified-Since-Version. "
            "Return delete_item_status; then GET /users/<id>/items/<created_item_key>?format=json and return deleted_item_check_status. If key empty, both are 0. "
            "24) Return SKILL.md sha256."
        )

        result = _run_codex_with_schema(prompt, schema, timeout_sec=1200)
        _assert_skill_identity(self, result, skill_name)

        capability_pass = {
            "bootstrap_web_api": result["web_bootstrap_status"] == 200,
            "web_collections_inventory": result["collections_status"] == 200 and result["collection_count"] > 0,
            "web_collection_items_read": bool(result["sample_collection_key"]) and result["sample_items_status"] == 200,
            "web_query_qmode": result["query_status"] == 200,
            "web_query_include_trashed": result["include_trashed_status"] == 200,
            "web_incremental_since_versions": result["delta_status"] == 200,
            "web_collection_create": (
                result["write_collection_status"] in (200, 201)
                and bool(result["created_collection_key"])
                and result["created_collection_status"] == 200
            ),
            "web_collection_delete": result["delete_collection_status"] in (200, 204) and result["deleted_collection_check_status"] == 404,
            "web_write_item_create": (
                result["write_item_status"] in (200, 201)
                and result["created_item_search_status"] == 200
                and result["created_item_hits"] > 0
                and bool(result["created_item_key"])
                and result["created_item_status"] == 200
            ),
            "web_write_item_update": result["update_item_status"] in (200, 204),
            "web_write_note_create": result["write_note_status"] in (200, 201) and bool(result["created_note_key"]),
            "web_write_note_update": result["update_note_status"] in (200, 204) and result["updated_note_visible"],
            "web_write_attachment_create": (
                result["write_attachment_status"] in (200, 201)
                and bool(result["created_attachment_key"])
                and result["children_status"] == 200
                and result["created_attachment_count"] > 0
            ),
            "web_write_note_delete": result["delete_note_status"] in (200, 204) and result["deleted_note_check_status"] == 404,
            "web_write_attachment_delete": result["delete_attachment_status"] in (200, 204) and result["deleted_attachment_check_status"] == 404,
            "web_write_item_delete": result["delete_item_status"] in (200, 204) and result["deleted_item_check_status"] == 404,
            "web_troubleshoot_failure_capture": result["bad_status"] != 200,
            "web_troubleshoot_recovery": result["recovery_status"] == 200,
        }
        _record_coverage(skill_name, capability_pass)

        for cap in CAPABILITY_MATRIX[skill_name]:
            self.assertTrue(capability_pass[cap], f"capability failed: {cap}")

    def test_zotero_better_bibtex_plugin_flow(self) -> None:
        skill_name = "zotero-better-bibtex"
        _wait_for_local_api_ready(timeout_sec=30.0)

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
