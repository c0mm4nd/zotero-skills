# Better BibTeX JSON-RPC

## Endpoint
- `http://127.0.0.1:23119/better-bibtex/json-rpc`

## Transport
- JSON-RPC 2.0 over HTTP POST
- Request body: `{ "jsonrpc": "2.0", "method": "<method>", "params": {...}, "id": 1 }`

## Common methods (non-exhaustive)
- `api.ready`
- `item.search`
- `item.citationkey` / `item.citationkey.set`
- `item.get`
- `item.bibtex` / `item.biblatex` / `item.ris` / `item.csljson`
- `library.export` / `collection.export`
- `autoexport.list` / `autoexport.add` / `autoexport.remove`

## Notes
- Prefer BBT for citation-key workflows and export formats.
- If a method fails or is unavailable, fall back to Local API equivalents.

## Source
- https://retorque.re/zotero-better-bibtex/json-rpc/
