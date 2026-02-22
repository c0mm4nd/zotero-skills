#!/usr/bin/env python3
"""Probe Zotero Local API and Better BibTeX JSON-RPC availability."""

import argparse
import json
import sys
import urllib.error
import urllib.request


def http_get(url, headers, timeout):
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read(), dict(resp.headers)


def http_post(url, payload, headers, timeout):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read(), dict(resp.headers)


def main():
    parser = argparse.ArgumentParser(description="Probe Zotero Local API and BBT JSON-RPC")
    parser.add_argument("--base", default="http://127.0.0.1:23119", help="Base URL (scheme://host:port)")
    parser.add_argument("--timeout", type=float, default=3.0, help="Request timeout in seconds")
    parser.add_argument("--no-allow-header", action="store_true", help="Do not send Zotero-Allowed-Request header")
    parser.add_argument("--connector-header", action="store_true", help="Send X-Zotero-Connector-API-Version header")
    parser.add_argument("--skip-bbt", action="store_true", help="Skip Better BibTeX probe")
    args = parser.parse_args()

    headers = {"Zotero-API-Version": "3"}
    if not args.no_allow_header:
        headers["Zotero-Allowed-Request"] = "1"
    if args.connector_header:
        headers["X-Zotero-Connector-API-Version"] = "2"

    local_url = f"{args.base}/api/users/0/items?limit=1"
    print(f"Local API: {local_url}")
    try:
        status, body, resp_headers = http_get(local_url, headers, args.timeout)
        lm_version = resp_headers.get("Last-Modified-Version", "<missing>")
        print(f"  status={status} last_modified_version={lm_version} bytes={len(body)}")
    except urllib.error.HTTPError as e:
        print(f"  HTTPError status={e.code} reason={e.reason}")
        try:
            print(f"  body={e.read().decode('utf-8', errors='replace')}")
        except Exception:
            pass
    except Exception as e:
        print(f"  error={e}")

    if args.skip_bbt:
        return 0

    bbt_url = f"{args.base}/better-bibtex/json-rpc"
    payload = {"jsonrpc": "2.0", "method": "api.ready", "params": {}, "id": 1}
    print(f"BBT JSON-RPC: {bbt_url}")
    try:
        status, body, _ = http_post(bbt_url, payload, {"Content-Type": "application/json"}, args.timeout)
        decoded = body.decode("utf-8", errors="replace")
        print(f"  status={status} body={decoded}")
    except urllib.error.HTTPError as e:
        print(f"  HTTPError status={e.code} reason={e.reason}")
        try:
            print(f"  body={e.read().decode('utf-8', errors='replace')}")
        except Exception:
            pass
    except Exception as e:
        print(f"  error={e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
