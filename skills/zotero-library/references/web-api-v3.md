# Web API v3 essentials (Local API uses these semantics)

## Base patterns
- Library prefix: `/api/users/<userID>` or `/api/groups/<groupID>` (Local API uses `users/0`).
- Common resources:
  - Collections: `/collections`, `/collections/top`, `/collections/<collectionKey>`, `/collections/<collectionKey>/collections`
  - Items: `/items`, `/items/top`, `/items/trash`, `/items/<itemKey>`, `/items/<itemKey>/children`, `/collections/<collectionKey>/items`
  - Searches: `/searches`, `/searches/<searchKey>` (web API exposes only search metadata)
  - Tags: `/tags`, `/tags/<encodedTag>`, and tag endpoints under items/collections

## Format and include
- `format`: `json` (default), `bib`, `citation`, `keys`, `versions`, or export formats (e.g., `bibtex`, `ris`, `csljson`).
- `include` (when `format=json`): `data` (default), `bib`, `citation`, `csljson`.
- `style`/`locale`/`linkwrap` for bibliography/citation output.

## Search and filtering
- `itemKey` (comma-separated, up to 50)
- `itemType` (boolean search syntax)
- `q` (quick search); `qmode=titleCreatorYear|everything`
- `tag` (boolean search syntax)
- `includeTrashed=1` (items)
- `qmode=contains|startsWith` for tag search
- Tag endpoints also support item filters: `itemQ`, `itemQMode=titleCreatorYear|everything`, `itemTag` (boolean search).

## Versioning and incremental reads
- `Zotero-API-Version: 3` (or `v=3` query param).
- `Last-Modified-Version` response header indicates library/object version.
- `since=<version>` returns objects modified after a version.
- `format=versions` returns a map of keys to versions.

## Full-text
- `GET <userOrGroupPrefix>/fulltext?since=<version>`
- `GET <userOrGroupPrefix>/items/<itemKey>/fulltext` (attachment items)

## Attachment file download
- `GET <userOrGroupPrefix>/items/<itemKey>/file`

## Sources
- https://www.zotero.org/support/dev/web_api/v3/basics
- https://www.zotero.org/support/dev/web_api/v3/syncing
- https://www.zotero.org/support/dev/web_api/v3/fulltext_content
- https://www.zotero.org/support/dev/web_api/v3/file_upload
