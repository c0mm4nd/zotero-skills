---
name: zotero-library
description: "Use when managing Zotero collections through Zotero Web API with authenticated CRUD operations for collections, items, notes, and attachments, plus query, sync, and troubleshooting workflows."
---

# Zotero Library

Manage collection-centered literature workflows through Zotero Web API with authenticated CRUD paths.

## When to use
- Build or operate a collection-based literature service.
- List collections and read papers inside one collection through Web API.
- Create, update, and delete collections through Web API.
- Create, update, and delete papers through Web API.
- Create, update, and delete child notes and attachments through Web API.
- Refresh collection data incrementally with version checkpoints.
- Diagnose and recover failing collection requests.

## When not to use
- Need Better BibTeX export/citation operations: use `$zotero-better-bibtex`.
- Need local plugin-only operations without cloud access: out of scope here.

## Web API credentials (plaintext, required)
- WEB_API_USER_ID: `__ZOTERO_WEB_API_USER_ID__`
- WEB_API_KEY: `__ZOTERO_WEB_API_KEY__`

## Service contract
- Base URL: `https://api.zotero.org`.
- Library scope prefix: `/users/<WEB_API_USER_ID>` or `/groups/<groupID>`.
- Required headers:
- `Zotero-API-Version: 3`
- `Zotero-API-Key: <WEB_API_KEY>`
- Write safety:
- For create/update/delete requests, include `If-Unmodified-Since-Version` (or object `version`) to avoid conflicts.

## Workflow
1. Bootstrap
- Confirm `WEB_API_USER_ID` and `WEB_API_KEY` are configured in this SKILL.
- Probe with `GET /users/<WEB_API_USER_ID>/collections?limit=1`.

2. Collection inventory
- Discover scope via `/users/<WEB_API_USER_ID>/collections/top` or `/users/<WEB_API_USER_ID>/collections`.
- Pick target collection key and read papers via `/users/<WEB_API_USER_ID>/collections/<collectionKey>/items`.

3. Collection CRUD
- Create collection with `POST /users/<WEB_API_USER_ID>/collections`.
- Read collection detail with `GET /users/<WEB_API_USER_ID>/collections/<collectionKey>`.
- Update collection metadata with `PATCH /users/<WEB_API_USER_ID>/collections/<collectionKey>`.
- Delete collection with `DELETE /users/<WEB_API_USER_ID>/collections/<collectionKey>`.

4. Collection query shaping
- Apply `q`, `qmode`, `itemType`, `tag`, `includeTrashed`.
- Use `format=` and `include=` for response shape.

5. Incremental refresh
- Capture `Last-Modified-Version` from a seed request.
- Request deltas with `since=<version>`.
- Use `format=versions` for compact update maps.

6. Item create and read
- Get current library version from a read request `Last-Modified-Version`.
- `POST /users/<WEB_API_USER_ID>/items` with an item array payload.
- Include `If-Unmodified-Since-Version` for conflict-safe writes.
- Verify creation with `/users/<WEB_API_USER_ID>/items/<itemKey>`.

7. Item and note update
- Update item fields with `PATCH /users/<WEB_API_USER_ID>/items/<itemKey>`.
- Create child note via `POST /users/<WEB_API_USER_ID>/items` with `parentItem=<itemKey>`.
- Update note with `PATCH /users/<WEB_API_USER_ID>/items/<noteKey>`.

8. Attachment create
- Create child attachment item (for example `linked_url`) via `POST /users/<WEB_API_USER_ID>/items`.
- Assign `parentItem=<itemKey>`.
- Verify via `/users/<WEB_API_USER_ID>/items/<itemKey>/children`.

9. Delete path (item children first)
- Delete note with `DELETE /users/<WEB_API_USER_ID>/items/<noteKey>`.
- Delete attachment with `DELETE /users/<WEB_API_USER_ID>/items/<attachmentKey>`.
- Delete parent item with `DELETE /users/<WEB_API_USER_ID>/items/<itemKey>`.
- Verify deletes with `GET` returning `404`.

10. Troubleshooting
- Reproduce with one failing request and capture status/body.
- Classify failures: auth (`401/403`), conflict (`412`), missing precondition (`428`), bad key/endpoint (`404`).
- Re-run a known-good endpoint (`/users/<WEB_API_USER_ID>/collections?limit=1`) to confirm recovery.

## Handoff
- `$zotero-better-bibtex` for collection bibliography/citation export services.

## References
- `references/web-api-v3.md`
