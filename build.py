#!/usr/bin/env python3
"""
Fez: builds the TinyApps shop window (https://tiny-apps.vml.onl) from a folder of app
definitions. One tiny-app = one folder under catalog/<slug>/ holding app.vml, a 300x300
icon (icon.svg or icon.png), and any scripts. Bob runs this as a script build; by hand:

    python3 build.py                 build the site into the out dir
    TINYAPPS_OUT=/tmp/t python3 build.py   build it somewhere else (for a look)

Add a tiny-app: copy catalog/ff-refresh to catalog/<slug>, edit app.vml + icon + scripts.
app.vml is plain VML:

    @App my-tool
    Name=My Tool
    Verified=yes               yes = submitted via GitHub and reviewed; no = author upload
    Platforms=linux, windows, android
    Fixes=the one annoying thing it fixes
    Icon=icon.svg              300x300 (svg or png)
    Category=UtilitiesApplication
    Description=What it does. **bold** and `code` work here.

    @Download win               a download button; Kind is windows | deb | appimage | apk
    Kind=windows
    Url=https://.../My-Tool-Setup.exe

    @Install linux-run          an optional one-line installer (shown under "Install & commands")
    Platform=linux
    Label=run it
    Cmd=curl -fsSL https://tiny-apps.vml.onl/apps/my-tool.txt | bash
    Note=what happens. `code` works here too.

    @Script linux
    File=linux.txt                 the script in this folder...
    Publish=apps/my-tool.txt       ...served here on the site (the Cmd's URL)

Stdlib only; deterministic.
"""
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATALOG = HERE / "catalog"
SITE = HERE / "site"
OUT = Path(os.environ.get("TINYAPPS_OUT") or (Path.home() / ".cache" / "tinyapps" / "site"))
BASE = "https://tiny-apps.vml.onl"

PLATFORMS = {"linux": ("lin", "Linux"), "windows": ("win", "Windows"), "android": ("and", "Android")}
# download kinds, in display order: slug -> (label, css class, sub-label, platform)
KINDS = {
    "windows":  ("Windows",  "win",      "installer (.exe)",       "windows"),
    "deb":      (".deb",     "deb",      "Ubuntu · Debian · Mint", "linux"),
    "appimage": ("AppImage", "appimage", "any Linux",              "linux"),
    "apk":      ("Android",  "apk",      "sideload (.apk)",        "android"),
}


def step(text):
    print(f"==> {text}", flush=True)


def parse_vml(text):
    blocks, cur = [], None
    for raw in text.splitlines():
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


def inline(text):
    out = html.escape(text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    return out


def plain(text):
    return re.sub(r"[*`]", "", text)


def yes(v):
    return str(v).strip().lower() in ("1", "yes", "true", "y", "on")


def platform_list(head):
    return [p.strip().lower() for p in head.get("Platforms", "").split(",") if p.strip()]


def chips(platforms):
    out = []
    for p in platforms:
        cls, lbl = PLATFORMS.get(p, ("", p.title()))
        out.append(f'<span class="chip {cls}">{lbl}</span>')
    return "".join(out)


def dl_kind(d):
    k = (d.get("Kind") or "").strip().lower()
    if k in KINDS:
        return k
    plat = (d.get("Platform") or "").lower()
    lab = (d.get("Label") or "").lower()
    if "appimage" in lab:
        return "appimage"
    if ".deb" in lab or " deb" in lab or lab.endswith("deb"):
        return "deb"
    if "apk" in lab or plat == "android":
        return "apk"
    if plat == "windows":
        return "windows"
    return "deb" if plat == "linux" else ""


def load_apps():
    apps = []
    if not CATALOG.is_dir():
        return apps
    for d in sorted(CATALOG.iterdir()):
        vml = d / "app.vml"
        if not d.is_dir() or not vml.is_file():
            continue
        blocks = parse_vml(vml.read_text(encoding="utf-8"))
        head = next((b for b in blocks if b["type"] == "App"), None)
        if not head:
            print(f"    (skipped {d.name}: no @App block)", flush=True)
            continue
        apps.append({"dir": d, "slug": head["name"] or d.name, "head": head["props"],
                     "downloads": [b["props"] for b in blocks if b["type"] == "Download"],
                     "installs": [b["props"] for b in blocks if b["type"] == "Install"],
                     "scripts": [b for b in blocks if b["type"] == "Script"]})
    return apps


def icon_ext(app):
    return Path(app["head"].get("Icon", "icon.svg")).suffix or ".svg"


def render_downloads(app):
    items = {}
    for d in app["downloads"]:
        k = dl_kind(d)
        if k and k not in items and d.get("Url"):
            items[k] = d
    if not items:
        return ""
    btns = []
    for k in KINDS:
        if k in items:
            lbl, cls, sub, _ = KINDS[k]
            url = html.escape(items[k]["Url"])
            btns.append(f'<a class="dl {cls}" href="{url}" title="{html.escape(sub)}">'
                        f'<span class="dlk">{lbl}</span><span class="dlsub">{html.escape(sub)}</span></a>')
    return '<div class="dls-row">' + "".join(btns) + '</div>'


def render_installs(app):
    rows = []
    for p in app["installs"]:
        plat = (p.get("Platform") or "").lower()
        cls, lbl = PLATFORMS.get(plat, ("", plat.title()))
        label = f'<span class="chip {cls}">{lbl}</span> {html.escape(p.get("Label", ""))}'
        rows.append(
            '<div class="inst">'
            f'<div class="label">{label}</div>'
            f'<div class="cmd"><code>{html.escape(p.get("Cmd", ""))}</code>'
            '<button class="copy" type="button">Copy</button></div>'
            + (f'<p class="run">{inline(p.get("Note", ""))}</p>' if p.get("Note") else '')
            + '</div>')
    links = [f'<a href="{html.escape(b["props"]["Publish"])}">{b["name"].title()}</a>'
             for b in app["scripts"] if b["props"].get("Publish")]
    if links:
        rows.append(f'<p class="more-scripts">Read the script first if you like — plain text: {" · ".join(links)}</p>')
    return "".join(rows)


def render_card(app):
    h = app["head"]
    slug = app["slug"]
    name = h.get("Name", slug)
    verified = yes(h.get("Verified", "no"))
    badge = ('<span class="badge ok" title="Submitted through GitHub and reviewed by Wallisoft.">✓ Verified</span>'
             if verified else
             '<span class="badge warn" title="Uploaded by its author, not reviewed. Read the script or check the download before running.">⚠ Unverified</span>')
    plats = platform_list(h)
    dls = render_downloads(app)
    installs = render_installs(app)
    search = " ".join([name, plain(h.get("Description", "")), h.get("Fixes", ""),
                       " ".join(PLATFORMS.get(p, ("", p))[1] for p in plats)]).lower()
    more = (f'<button class="more-btn" type="button" aria-expanded="false">Install &amp; commands</button>'
            f'<div class="more" hidden>{installs}</div>') if installs else ""
    fixes = f'<p class="fixes"><b>Fixes:</b> {inline(h.get("Fixes", ""))}</p>' if h.get("Fixes") else ""
    return (
        f'<article class="card" id="{slug}" data-search="{html.escape(search)}" '
        f'data-platforms="{" ".join(plats)}" data-verified="{1 if verified else 0}">\n'
        f'  <div class="card-top">\n'
        f'    <img class="icon" src="{slug}{icon_ext(app)}" alt="{html.escape(name)} icon" loading="lazy">\n'
        f'    <div class="card-id">\n'
        f'      <div class="card-name"><h3>{html.escape(name)}</h3>{badge}</div>\n'
        f'      <div class="chips">{chips(plats)}</div>\n'
        f'    </div>\n'
        f'  </div>\n'
        f'  <p class="desc">{inline(h.get("Description", ""))}</p>\n'
        + f'  {fixes}\n'
        + (f'  {dls}\n' if dls else '')
        + (f'  {more}\n' if more else '')
        + f'</article>')


def app_jsonld(app):
    h = app["head"]
    oses = [PLATFORMS.get(p, ("", p.title()))[1] for p in platform_list(h)]
    return {"@context": "https://schema.org", "@type": "SoftwareApplication",
            "name": h.get("Name", app["slug"]), "operatingSystem": ", ".join(oses),
            "applicationCategory": h.get("Category", "UtilitiesApplication"),
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "GBP"},
            "description": plain(h.get("Description", "")), "url": f'{BASE}/#{app["slug"]}',
            "author": {"@type": "Organization", "name": "Wallisoft", "url": "https://tiny-web.uk"}}


WEBSITE_LD = {"@context": "https://schema.org", "@type": "WebSite", "name": "TinyApps",
              "url": f"{BASE}/", "description": "Tiny apps that each fix one thing, perfectly — "
              "one-line installs and small downloads for Windows, Linux and Android.",
              "publisher": {"@type": "Organization", "name": "Wallisoft"}}


def copy_assets(apps):
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("site.css", "fez.svg"):
        shutil.copy2(SITE / name, OUT / name)
    for app in apps:
        icon = app["dir"] / app["head"].get("Icon", "icon.svg")
        shutil.copy2(icon, OUT / f'{app["slug"]}{icon_ext(app)}')
        for b in app["scripts"]:
            pub, src = b["props"].get("Publish"), b["props"].get("File")
            if pub and src:
                dst = OUT / pub
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(app["dir"] / src, dst)


def build():
    step(f"TinyApps: reading {CATALOG}")
    apps = load_apps()
    if not apps:
        print("FAILED: no apps in catalog/", flush=True)
        sys.exit(1)
    nv = sum(1 for a in apps if yes(a["head"].get("Verified", "no")))
    print(f"    {len(apps)} app(s), {nv} verified: " + ", ".join(a["slug"] for a in apps), flush=True)
    if OUT.exists():
        shutil.rmtree(OUT)
    copy_assets(apps)
    ld = [WEBSITE_LD] + [app_jsonld(a) for a in apps]
    jsonld = "\n".join(f'<script type="application/ld+json">\n{json.dumps(b)}\n</script>' for b in ld)
    cards = "\n\n".join(render_card(a) for a in apps)
    page = (SITE / "index.template.html").read_text(encoding="utf-8")
    page = page.replace("%%JSONLD%%", jsonld).replace("%%CARDS%%", cards).replace("%%COUNT%%", str(len(apps)))
    (OUT / "index.html").write_text(page, encoding="utf-8")
    step("Built:")
    for f in sorted(OUT.rglob("*")):
        if f.is_file():
            print(f"    {f.stat().st_size:7d}  {f.relative_to(OUT)}", flush=True)
    step(f"Site ready in {OUT}")


if __name__ == "__main__":
    build()
