# zotero-skills

`zotero-skills` provides:
- `zotero-library` (Web API CRUD for collections, items, notes, and attachments)
- `zotero-better-bibtex` (local Better BibTeX JSON-RPC export/citation operations)

`zotero-library` now uses Zotero Web API (`https://api.zotero.org`) instead of local connector write flows.

## Usage Examples
1. Request: "Create a new paper titled 'Transformer Notes 2026' in my Zotero library."
Expected behavior: Use Web API authenticated write to create the item and return created key/version.

2. Request: "Update that paper title and add a note saying 'Needs replication package'."
Expected behavior: Patch the item, create/update child note, and confirm note content via children query.

3. Request: "Add a linked attachment to that paper."
Expected behavior: Create child attachment item via Web API and verify attachment appears under children.

4. Request: "Delete that note, attachment, and finally delete the paper."
Expected behavior: Delete child note first, then attachment, then parent item; verify each target returns `404` on read-back.

5. Request: "Create a temporary collection and then remove it."
Expected behavior: Create collection via Web API, verify it exists, delete it, and confirm deletion.

6. Request: "List papers in collection 'My Reading Queue' tagged 'to-read'."
Expected behavior: Resolve collection key and run collection-scoped item query.

7. Request: "Refresh changes since my last sync version."
Expected behavior: Read `Last-Modified-Version`, call `since=<version>` with `format=versions`, and return deltas.

8. Request: "Export BibTeX for collection 'My Reading Queue'."
Expected behavior: Use Better BibTeX JSON-RPC and return export result/count.

## Skill Architecture
- `skills/zotero-library`: Web API authenticated library management (CRUD).
- `skills/zotero-better-bibtex`: local BBT plugin operations.

## Prerequisites
1. Zotero account with Web API access.
2. Zotero Web API key with required library write permissions.
3. Better BibTeX plugin if using `zotero-better-bibtex`.
4. Local `codex` CLI (for live tests).

## Installation

### Claude Code
1. Add marketplace:
```text
/plugin marketplace add c0mm4nd/zotero-skills
```
2. Install plugin:
```text
/plugin install zotero-skills@zotero-skills
```
3. Locate installed `zotero-library/SKILL.md` (macOS/Linux):
```bash
find "$HOME/.claude" -type f -path "*/zotero-library/SKILL.md" 2>/dev/null
```
4. Edit that file and replace placeholders:
- `WEB_API_USER_ID: __ZOTERO_WEB_API_USER_ID__`
- `WEB_API_KEY: __ZOTERO_WEB_API_KEY__`
5. Example helper command (if this repo is cloned locally):
```bash
python3 skills/zotero-library/scripts/configure_web_api_credentials.py --skill-path "<FOUND_SKILL_PATH>"
```
6. Restart Claude Code so it reloads the updated skill.

How to get `WEB_API_USER_ID` from your key:
```bash
curl -sS -H "Zotero-API-Version: 3" -H "Zotero-API-Key: <WEB_API_KEY>" \
  "https://api.zotero.org/keys/current"
```
Read `userID` from the JSON response and use it as `WEB_API_USER_ID`.

### Codex
Quick install:
1. Ask Codex to follow:
`https://raw.githubusercontent.com/c0mm4nd/zotero-skills/refs/heads/main/.codex/INSTALL.md`

Manual install:
```bash
git clone https://github.com/c0mm4nd/zotero-skills
ln -s "$(pwd)/zotero-skills/skills" "$HOME/.agents/skills/zotero-skills"
python3 zotero-skills/skills/zotero-library/scripts/configure_web_api_credentials.py
```

The configuration step prompts for Web API user id/key and writes them in plaintext to:
- `skills/zotero-library/SKILL.md`

## Web API Credential Storage
By request, credentials are stored in plaintext inside `skills/zotero-library/SKILL.md`:
- `WEB_API_USER_ID: <value>`
- `WEB_API_KEY: <value>`

## Endpoint Verification
Quick Web API probe (replace values):

```bash
curl -sS -H "Zotero-API-Version: 3" -H "Zotero-API-Key: <WEB_API_KEY>" \
  "https://api.zotero.org/users/<WEB_API_USER_ID>/collections?limit=1"
```

Local BBT probe:

```bash
python3 skills/zotero-library/scripts/zotero_local_probe.py
```

## Live Integration Tests
Run:

```bash
RUN_CODEX_AGENT_TESTS=1 python3 -m unittest tests.test_codex_skill_interaction_live -v
```

Notes:
- `zotero-library` live test reads credentials in this order:
- `skills/zotero-library/SKILL.md` (`WEB_API_USER_ID` / `WEB_API_KEY`)
- `.env` (`ZOTERO_WEB_API_USER_ID` or `WEB_API_USER_ID`, and `ZOTERO_WEB_API_KEY` or `WEB_API_KEY`)
- If neither source is configured, `zotero-library` test is skipped.
- `zotero-better-bibtex` still requires local Zotero on `127.0.0.1:23119`.

Coverage artifact:
- `tests/functional_coverage_latest.json`
- The artifact only includes tests that actually ran (for example, `zotero-library` is absent when Web API credentials are not configured).

## Functional Coverage
Latest run:

| Skill | Covered | Total | Coverage |
|---|---:|---:|---:|
| `zotero-library` | 18 | 18 | 100.0% |
| `zotero-better-bibtex` | 8 | 8 | 100.0% |
| **Overall** | **26** | **26** | **100.0%** |

`zotero-library` CRUD coverage now includes:
- Collection: create, read, query, incremental sync, delete.
- Item: create, read, update, delete.
- Child note: create, update, delete.
- Child attachment: create, delete.
