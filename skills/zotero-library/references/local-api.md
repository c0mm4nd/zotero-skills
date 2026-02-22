# Zotero Local API notes

## Core facts
- Local API is a near-complete, read-only implementation of the Zotero Web API (v3 semantics) intended for Zotero Desktop.
- Default base URL: `http://localhost:23119/api/` (same machine only).
- Use `users/0` for the local “My Library”.
- Local API does **not** use Zotero Web API keys.
- Pagination is not required for the Local API (but still useful for large libraries).
- Local API can expose file URLs for attachments and can return actual results for saved searches.

## Enablement and prefs
- Enable via Zotero settings: “Allow other applications on this computer to communicate with Zotero”.
- Advanced prefs keys (about:config):
  - `extensions.zotero.httpServer.enabled`
  - `extensions.zotero.httpServer.port` (default `23119`)

## Browser/Connector headers
If you see `Request not allowed`, add one of these headers:
- `Zotero-Allowed-Request: 1`
- `X-Zotero-Connector-API-Version: 2`

## Example
- `curl 'http://localhost:23119/api/users/0/items?limit=10&sort=dateAdded'`

## Sources
- https://forums.zotero.org/discussion/114484/using-local-api-with-local-api-key
- https://forums.zotero.org/discussion/107527/feature-request-zotero-7-local-api
- https://groups.google.com/g/zotero-dev/c/MI0d7Fj06aw
