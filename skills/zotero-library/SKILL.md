---
name: zotero-library
description: "Use when managing papers in Zotero collections, including collection bootstrap, collection-scoped queries, incremental refresh, and collection workflow troubleshooting."
---

# Zotero Library

Manage collection-centered literature workflows on local Zotero Desktop.

## When to use
- Build or operate a collection-based literature service.
- List collections and read papers inside one collection.
- Refresh collection data incrementally with version checkpoints.
- Diagnose and recover failing collection requests.

## When not to use
- Need Better BibTeX export/citation operations: use `$zotero-better-bibtex`.
- Need cloud Zotero Web API workflows: out of scope.

## Service contract
- Local-only: `http://127.0.0.1:23119/`.
- Local library scope: `users/0`.
- Read-only behavior for Local API resources.
- Required header: `Zotero-API-Version: 3`.
- If "Request not allowed", add `Zotero-Allowed-Request: 1` or `X-Zotero-Connector-API-Version: 2`.

## Workflow
1. Bootstrap
- Ensure Zotero Desktop is running and Local API is enabled.
- Probe with `scripts/zotero_local_probe.py` or `GET /api/users/0/collections?limit=1`.

2. Collection inventory
- Discover scope via `/api/users/0/collections/top` or `/api/users/0/collections`.
- Pick target collection key and read papers via `/api/users/0/collections/<collectionKey>/items`.

3. Collection query shaping
- Apply `q`, `qmode`, `itemType`, `tag`, `includeTrashed`.
- Use `format=` and `include=` for response shape.

4. Incremental refresh
- Capture `Last-Modified-Version` from a seed request.
- Request deltas with `since=<version>`.
- Use `format=versions` for compact update maps.

5. Troubleshooting
- Reproduce with one failing request and capture status/body.
- Classify failures: connectivity, headers, collection key, endpoint.
- Re-run a known-good endpoint (`/api/users/0/collections/top`) to confirm recovery.

## Handoff
- `$zotero-better-bibtex` for collection bibliography/citation export services.

## References
- `references/local-api.md`
- `references/web-api-v3.md`
