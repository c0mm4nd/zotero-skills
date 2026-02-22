---
name: zotero-better-bibtex
description: "Use when bibliography or citation output is needed through Better BibTeX JSON-RPC for either a Zotero collection scope or a single-item scope."
---

# Zotero Better BibTeX JSON-RPC

Provide export and citation services for collection and item targets.

## When to use
- Export one collection to BibTeX/BibLaTeX/CSL JSON.
- Export one specific item to BibTeX/BibLaTeX/RIS/CSL JSON.
- Generate citation payloads for either one item or one collection.
- Resolve or update citation keys for specific items.

## When not to use
- Need collection inventory, query, sync, or troubleshooting: use `$zotero-library`.

## Service flow
1. Confirm target scope: `collectionKey` or `itemKey`.
2. If target context is not ready, invoke `$zotero-library` first.
3. Probe BBT with JSON-RPC method `api.ready`.
4. Run collection or item export/citation operation at BBT endpoint.
5. If BBT is unavailable, fallback to Local API bibliography-compatible responses.

## Endpoint
- `http://127.0.0.1:23119/better-bibtex/json-rpc`

## Fallback rule
- If BBT methods fail, continue workflow via Local API and report fallback mode and target scope.

## References
- `references/better-bibtex-jsonrpc.md`
