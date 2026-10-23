#!/usr/bin/env python3
"""
tinyapps-submit: publish a tiny-app to the INFORMAL shop (https://tiny-apps.vml.onl) as
UNVERIFIED — no GitHub pull request, no review. Its card loads client-side from the site's
unverified.json, so a verified rebuild (CI regenerates the page from the reviewed catalog/)
never touches it. Unverified shows a warning badge; the org store is verified-only.

    python3 submit.py path/to/app-folder     publish or update an unverified app
    python3 submit.py --remove <slug>         take one down
    python3 submit.py --list                  show what's up

The folder holds app.vml (same shape as a catalog app) and its icon (300x300 svg/png).
For safety, unverified apps carry DOWNLOADS only — no "paste this command" installers;
those arbitrary-code one-liners belong to reviewed (verified) apps.

Environment:
  TINYAPPS_SUBMIT_KEY  (or TINYHOST_KEY)   your TinyApps submit key
  TINYAPPS_MCP   (default https://tiny-web.uk/api/mcp.php)
  TINYAPPS_SITE  (default tiny-apps)
"""
import base64
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

URL = os.environ.get("TINYAPPS_MCP", "https://tiny-web.uk/api/mcp.php")
SITE = os.environ.get("TINYAPPS_SITE", "tiny-apps")
KEY = (os.environ.get("TINYAPPS_SUBMIT_KEY") or os.environ.get("TINYHOST_KEY", "")).strip()
KINDS = {"windows", "deb", "appimage", "apk"}
PLATS = {"linux", "windows", "android"}


def die(m):
    sys.exit("submit: " + m)


def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Content-Type": "application/json", "Authorization": "Bearer " + KEY,
        "User-Agent": "TinyApps-CI/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def call(name, args):
    res = rpc("tools/call", {"name": name, "arguments": args})
    if res.get("error"):
        die(f"gateway error: {res['error']}")
    return res.get("result", {})


def text_of(result):
    return "".join(p.get("text", "") for p in result.get("content", []) if p.get("type") == "text")


def parse_vml(t):
    blocks, cur = [], None
    for raw in t.splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("@"):
            kind, _, name = s[1:].partition(" ")
            cur = {"type": kind.strip(), "name": name.strip(), "props": {}}
            blocks.append(cur)
        elif "=" in raw and cur is not None:
            k, _, v = raw.partition("=")
            cur["props"][k.strip()] = v.strip()
    return blocks


def slugify(s):
    return re.sub(r"[^a-z0-9_-]+", "-", str(s).lower()).strip("-") or "app"


def hello():
    rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                       "clientInfo": {"name": "tinyapps-submit", "version": "1.0"}})


def load_manifest():
    res = call("tinyhost_read_file", {"site": SITE, "path": "unverified.json"})
    if res.get("isError"):
        return []
    try:
        return json.loads(text_of(res)) or []
    except ValueError:
        return []


def build_entry(folder):
    vml = folder / "app.vml"
    if not vml.is_file():
        die(f"no app.vml in {folder}")
    blocks = parse_vml(vml.read_text(encoding="utf-8"))
    head = next((b for b in blocks if b["type"] == "App"), None)
    if not head:
        die("no @App block in app.vml")
    h = head["props"]
    slug = slugify(head["name"] or h.get("Name") or folder.name)
    plats = [p.strip().lower() for p in h.get("Platforms", "").split(",")
             if p.strip().lower() in PLATS]
    downloads = []
    for b in blocks:
        if b["type"] == "Download":
            k = (b["props"].get("Kind") or "").strip().lower()
            u = b["props"].get("Url", "")
            if k in KINDS and re.match(r"^https?://", u):
                downloads.append({"kind": k, "url": u})
    if not downloads:
        die("an unverified app needs at least one @Download with a Kind (windows|deb|appimage|apk) and an https Url")
    icon_name = h.get("Icon", "icon.svg")
    icon = folder / icon_name
    if not icon.is_file():
        die(f"icon {icon_name} not found in {folder}")
    ext = icon.suffix.lower() or ".svg"
    if ext not in (".svg", ".png", ".jpg", ".jpeg", ".webp"):
        die("icon must be an svg or png/jpg/webp")
    entry = {"slug": slug, "name": (h.get("Name", slug))[:60], "platforms": plats,
             "fixes": h.get("Fixes", "")[:120], "description": h.get("Description", "")[:400],
             "icon": f"u/{slug}{ext}", "downloads": downloads}
    return entry, icon, ext


def publish(folder):
    entry, icon, ext = build_entry(folder)
    hello()
    man = [e for e in load_manifest() if e.get("slug") != entry["slug"]]
    man.append(entry)
    man.sort(key=lambda e: e.get("name", "").lower())
    files = [{"path": "unverified.json",
              "content": json.dumps(man, ensure_ascii=False, indent=1), "encoding": "text"}]
    data = icon.read_bytes()
    if ext == ".svg":
        files.append({"path": f"u/{entry['slug']}.svg", "content": data.decode("utf-8", "replace"),
                      "encoding": "text"})
    else:
        files.append({"path": f"u/{entry['slug']}{ext}",
                      "content": base64.b64encode(data).decode(), "encoding": "base64"})
    res = call("tinyhost_write_files", {"site": SITE, "files": files})
    if res.get("isError"):
        die("publish rejected: " + text_of(res)[:400])
    print(f"published unverified '{entry['slug']}' -> https://tiny-apps.vml.onl/#{entry['slug']}")
    print(f"  {len(man)} unverified app(s) now listed.")


def remove(slug):
    slug = slugify(slug)
    hello()
    man = load_manifest()
    keep = [e for e in man if e.get("slug") != slug]
    if len(keep) == len(man):
        die(f"no unverified app '{slug}' is listed")
    call("tinyhost_write_files", {"site": SITE, "files": [
        {"path": "unverified.json", "content": json.dumps(keep, ensure_ascii=False, indent=1),
         "encoding": "text"}]})
    print(f"removed '{slug}'. {len(keep)} unverified app(s) remain. (its icon under u/ is left; harmless)")


def show():
    hello()
    man = load_manifest()
    if not man:
        print("no unverified apps listed.")
        return
    for e in man:
        print(f"  {e.get('slug'):<20} {e.get('name','')}  [{', '.join(e.get('platforms', []))}]")


def main(argv):
    if not KEY:
        die("set TINYAPPS_SUBMIT_KEY (or TINYHOST_KEY) to your TinyApps submit key.")
    if not argv:
        die("usage: submit.py <app-folder> | --remove <slug> | --list")
    if argv[0] == "--remove":
        if len(argv) < 2:
            die("usage: submit.py --remove <slug>")
        remove(argv[1])
    elif argv[0] == "--list":
        show()
    else:
        folder = Path(argv[0]).expanduser()
        if not folder.is_dir():
            die(f"not a folder: {folder}")
        publish(folder)


if __name__ == "__main__":
    main(sys.argv[1:])
