# zotero-skills

`zotero-skills` is a local-first skill suite for Zotero service management.

It is organized into:
- Core library skill: `zotero-library`
- Plugin skill(s): `zotero-better-bibtex`

The project focuses on collection-centered literature workflows, plus plugin-powered export/citation workflows.
It uses local Zotero endpoints only (`127.0.0.1:23119`) and does not use Zotero cloud endpoints.

## Skill Architecture
- `skills/zotero-library`: core Zotero library operations for collection management.
- `skills/zotero-better-bibtex`: Better BibTeX JSON-RPC operations for item/collection export and citation keys.

## Capability Map
- `zotero-library`
- Local API bootstrap and health check
- Collection inventory
- Collection item reads
- Query shaping (`q`, `qmode`, `includeTrashed`)
- Incremental refresh (`since`, `format=versions`)
- Troubleshooting and recovery
- `zotero-better-bibtex`
- BBT readiness (`api.ready`)
- Item scope: search, citation key, BibTeX/BibLaTeX export
- Collection scope: resolve, citation key aggregation, BibTeX export
- Fallback to Local API when BBT endpoint is unavailable

## Prerequisites
1. Install Zotero Desktop.
2. Enable Local API in Zotero:
`Settings -> Advanced -> Allow other applications on this computer to communicate with Zotero`.
3. Confirm local endpoint: `http://127.0.0.1:23119`.
4. Install Better BibTeX if using `zotero-better-bibtex`.
5. Ensure `codex` CLI is installed and logged in for live integration tests.

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
3. Restart Claude Code.

### Codex
Quick install inside Codex:
1. Ask Codex to follow:
`https://raw.githubusercontent.com/c0mm4nd/zotero-skills/refs/heads/main/.codex/INSTALL.md`

Manual install (macOS/Linux):
```bash
git clone https://github.com/c0mm4nd/zotero-skills
ln -s "$(pwd)/zotero-skills/skills" "$HOME/.agents/skills/zotero-skills"
```

Manual install (Windows PowerShell):
```powershell
git clone https://github.com/c0mm4nd/zotero-skills
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.agents\skills\zotero-skills" -Target "$PWD\zotero-skills\skills"
```

### Gemini CLI
1. Create `GEMINI.md` in your project.
2. Paste the target skill content, for example `skills/zotero-library/SKILL.md`.
3. Run `gemini` in that directory.

## Local Endpoint Verification
Run:

```bash
python3 skills/zotero-library/scripts/zotero_local_probe.py
```

Expected:
- Local API probe returns HTTP `200`.
- Better BibTeX JSON-RPC probe returns HTTP `200` (if BBT is installed).

## Live Integration Tests (Codex + SKILL + Local Zotero)
Run:

```bash
RUN_CODEX_AGENT_TESTS=1 python3 -m unittest tests.test_codex_skill_interaction_live -v
```

What this validates:
- Codex reads each `SKILL.md`.
- Codex executes real requests against local Zotero on `127.0.0.1:23119`.
- All declared skill capabilities are checked with structured JSON assertions.

Coverage artifact:
- `tests/functional_coverage_latest.json` (updated by the live suite).

## Functional Coverage
Latest measured coverage from `tests/functional_coverage_latest.json`:

| Skill | Covered | Total | Coverage |
|---|---:|---:|---:|
| `zotero-library` | 8 | 8 | 100.0% |
| `zotero-better-bibtex` | 8 | 8 | 100.0% |
| **Overall** | **16** | **16** | **100.0%** |

Capability IDs under coverage:
- `zotero-library`: `bootstrap_local_api`, `collections_inventory`, `collection_items_read`, `query_qmode`, `query_include_trashed`, `incremental_since_versions`, `troubleshoot_failure_capture`, `troubleshoot_recovery`
- `zotero-better-bibtex`: `api_ready`, `item_search`, `item_citationkey`, `item_export_bibtex`, `item_export_biblatex`, `collection_scope_resolve`, `collection_citationkeys`, `collection_export_bibtex`

## Usage Examples
```text
Use $zotero-library to initialize collection management for my Zotero library.
Use $zotero-library to list papers in collection "My Reading Queue" and filter by tag "to-read".
Use $zotero-library to refresh collection changes using since/version checkpoints.
Use $zotero-better-bibtex to export BibTeX for collection "My Reading Queue".
Use $zotero-better-bibtex to export BibLaTeX for item key "ABCD1234".
```

## Notes
- Local API behavior is read-only in this skill suite.
- When Better BibTeX is not available, plugin flows fall back to Local API-compatible behavior where possible.
