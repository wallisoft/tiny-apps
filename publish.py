#!/usr/bin/env python3
"""
Publish the built TinyApps site to its vml.onl home through the TinyHost gateway.

Reads the site that build.py wrote and POSTs a single `vmlonl_publish` call to the
MCP endpoint, authenticated with a TinyHost API key. No assistant in the loop - this
is what GitHub Actions runs after an approved PR merges.

Environment:
  TINYHOST_KEY   (required)  a TinyHost API key; in CI it's an Actions secret
  TINYAPPS_OUT   (default ~/.cache/tinyapps/site)  the dir build.py wrote
  TINYAPPS_SITE  (default tiny-apps)
  TINYAPPS_MCP   (default https://tiny-web.uk/api/mcp.php)
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

OUT = Path(os.environ.get("TINYAPPS_OUT") or (Path.home() / ".cache" / "tinyapps" / "site"))
URL = os.environ.get("TINYAPPS_MCP", "https://tiny-web.uk/api/mcp.php")
SITE = os.environ.get("TINYAPPS_SITE", "tiny-apps")
KEY = os.environ.get("TINYHOST_KEY", "").strip()
TEXT_EXT = {".html", ".css", ".svg", ".txt", ".js", ".json", ".xml", ".md"}


def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Content-Type": "application/json", "Authorization": "Bearer " + KEY,
        "User-Agent": "TinyApps-CI/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    if not KEY:
        print("TINYHOST_KEY not set - skipping publish. Add it as an Actions secret "
              "(repo Settings -> Secrets and variables -> Actions) to enable auto-publish.", flush=True)
        return
    if not OUT.is_dir():
        sys.exit(f"no built site at {OUT} - run build.py first.")
    files = []
    for p in sorted(OUT.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(OUT)).replace(os.sep, "/")
        if p.suffix.lower() in TEXT_EXT:
            files.append({"path": rel, "content": p.read_text(encoding="utf-8"), "encoding": "text"})
        else:
            import base64
            files.append({"path": rel, "content": base64.b64encode(p.read_bytes()).decode(), "encoding": "base64"})
    print(f"==> publishing {len(files)} files to '{SITE}' via {URL}", flush=True)
    rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                       "clientInfo": {"name": "tinyapps-ci", "version": "1.0"}})
    res = rpc("tools/call", {"name": "vmlonl_publish", "arguments": {"site": SITE, "files": files}})
    if res.get("error"):
        sys.exit(f"FAILED: gateway error: {res['error']}")
    result = res.get("result", {})
    if result.get("isError"):
        sys.exit(f"FAILED: publish rejected: {json.dumps(result)[:600]}")
    text = ""
    for part in result.get("content", []):
        if part.get("type") == "text":
            text += part.get("text", "")
    print("==> published OK " + (text[:400] if text else json.dumps(result)[:400]), flush=True)


if __name__ == "__main__":
    main()
