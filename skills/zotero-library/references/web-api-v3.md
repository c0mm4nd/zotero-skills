# Web API v3 essentials

## Base patterns
- Library prefix on Web API host: `/users/<userID>` or `/groups/<groupID>`.
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
- Auth header for private libraries: `Zotero-API-Key: <key>`.
- `Last-Modified-Version` response header indicates library/object version.
- `since=<version>` returns objects modified after a version.
- `format=versions` returns a map of keys to versions.

## Writes
- Create collections: `POST <prefix>/collections` with JSON array body.
- Update collections: `PATCH <prefix>/collections/<collectionKey>` with JSON object body.
- Delete collections: `DELETE <prefix>/collections/<collectionKey>`.
- Create items: `POST <prefix>/items` with JSON array body.
- Update items: `PATCH <prefix>/items/<itemKey>` with JSON object body.
- Delete items: `DELETE <prefix>/items/<itemKey>`.
- For conflict-safe writes, include `If-Unmodified-Since-Version`.
- Precondition failures use HTTP `412` or `428`.

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
