#!/usr/bin/env python3
"""
Fez: builds the tiny-apps shop window (https://tiny-apps.vml.onl) from a folder of app
definitions. One tiny-app = one folder under catalog/<slug>/ holding app.vml, an icon,
and its scripts. Bob runs this as a script build (apps/fez/recipe.vml); it's fine by hand:

    python3 apps/fez/build.py                 build the site into the out dir
    FEZ_OUT=/tmp/fez python3 apps/fez/build.py   build it somewhere else (for a look)

Add a tiny-app: copy catalog/ff-refresh to catalog/<slug>, edit app.vml + icon.svg + the
scripts, run Bob. app.vml is plain VML (see tools/bob/recipe.py for the shape):

    @App my-tool
    Name=my-tool
    Platforms=linux, windows
    Fixes=the one annoying thing it fixes
    Icon=icon.svg
    Category=UtilitiesApplication
    Description=What it does. **bold** and `code` work here.

    @Install one
    Platform=linux
    Label=run it
    Cmd=curl -fsSL https://tiny-apps.vml.onl/apps/my-tool.txt | bash
    Note=what happens. `code` works here too.

    @Script linux
    File=linux.txt                 the script in this folder...
    Publish=apps/my-tool.txt       ...served here on the site (the Cmd's URL)

Stdlib only. Publishing the built files to TinyHost is the one remaining step (see the
note printed at the end) - the generator is complete and deterministic.
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
PLATFORMS = {"linux": ("lin", "Linux"), "windows": ("win", "Windows")}


def step(text):
    print(f"==> {text}", flush=True)


def parse_vml(text):
    """VML's plain shape: @Type Name blocks of Key=Value lines (# comments)."""
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
    """Escape, then **bold** -> <strong>, `code` -> <code>."""
    out = html.escape(text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    return out


def plain(text):
    return re.sub(r"[*`]", "", text)


def platform_list(head):
    return [p.strip().lower() for p in head.get("Platforms", "").split(",") if p.strip()]


def chips(platforms):
    out = []
    for p in platforms:
        cls, lbl = PLATFORMS.get(p, ("", p.title()))
        out.append(f'<span class="chip {cls}">{lbl}</span>')
    return "".join(out)


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


def render_card(app):
    h = app["head"]
    slug = app["slug"]
    name = h.get("Name", slug)
    dls = ""
    if app["downloads"]:
        btns = "".join(f'<a class="dl" href="{html.escape(d.get("Url", ""))}">{html.escape(d.get("Label", d.get("Platform", "Download")))}</a>' for d in app["downloads"])
        dls = f'        <div class="inst"><div class="label">Download</div><div class="dls">{btns}</div></div>'
    rows = [dls] if dls else []
    for p in app["installs"]:
        plat = p.get("Platform", "").lower()
        cls, lbl = PLATFORMS.get(plat, ("", plat.title()))
        label = f'<span class="chip {cls}">{lbl}</span> {html.escape(p.get("Label", ""))}'
        rows.append(
            '        <div class="inst">\n'
            f'          <div class="label">{label}</div>\n'
            f'          <div class="cmd"><code>{html.escape(p.get("Cmd", ""))}</code>'
            '<button class="copy" type="button">Copy</button></div>\n'
            f'          <p class="run">{inline(p.get("Note", ""))}</p>\n'
            '        </div>')
    links = [f'<a href="{html.escape(b["props"]["Publish"])}">{b["name"].title()}</a>'
             for b in app["scripts"] if b["props"].get("Publish")]
    more = (f'        <p class="more">Read the script first if you like — it\'s plain text: '
            f'{" · ".join(links)}</p>\n') if links else ""
    return (
        f'    <div class="app" id="{slug}">\n'
        f'      <img class="appicon" src="{slug}.svg" alt="{html.escape(name)} icon">\n'
        '      <div>\n'
        f'        <div class="apphead"><h3>{html.escape(name)}</h3>{chips(platform_list(h))}</div>\n'
        f'        <p class="appdesc">{inline(h.get("Description", ""))}</p>\n'
        f'        <p class="fixes"><b>Fixes:</b> {inline(h.get("Fixes", ""))}</p>\n'
        + "\n".join(rows) + "\n"
        + more +
        '      </div>\n'
        '    </div>')


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
              "url": f"{BASE}/", "description": "Tiny apps that fix one thing, perfectly — "
              "one-line installs for Windows and Linux.",
              "publisher": {"@type": "Organization", "name": "Wallisoft"}}


def copy_assets(apps):
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("site.css", "fez.svg"):
        shutil.copy2(SITE / name, OUT / name)
    for app in apps:
        icon = app["dir"] / app["head"].get("Icon", "icon.svg")
        shutil.copy2(icon, OUT / f'{app["slug"]}.svg')
        for b in app["scripts"]:
            pub, src = b["props"].get("Publish"), b["props"].get("File")
            if pub and src:
                dst = OUT / pub
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(app["dir"] / src, dst)


def build():
    step(f"Fez: reading {CATALOG}")
    apps = load_apps()
    if not apps:
        print("FAILED: no apps in catalog/", flush=True)
        sys.exit(1)
    print(f"    {len(apps)} app(s): " + ", ".join(a["slug"] for a in apps), flush=True)
    if OUT.exists():
        shutil.rmtree(OUT)
    copy_assets(apps)
    ld = [WEBSITE_LD] + [app_jsonld(a) for a in apps]
    jsonld = "\n".join(f'<script type="application/ld+json">\n{json.dumps(b)}\n</script>' for b in ld)
    cards = "\n\n".join(render_card(a) for a in apps)
    page = (HERE / "site" / "index.template.html").read_text(encoding="utf-8")
    page = page.replace("%%JSONLD%%", jsonld).replace("%%CARDS%%", cards)
    (OUT / "index.html").write_text(page, encoding="utf-8")
    step("Built:")
    for f in sorted(OUT.rglob("*")):
        if f.is_file():
            print(f"    {f.stat().st_size:7d}  {f.relative_to(OUT)}", flush=True)
    step(f"Site ready in {OUT}")
    print("    To publish to tiny-apps.vml.onl: push these files with the TinyHost "
          "connector (vmlonl_publish), or wire a token here - see the recipe note.", flush=True)


if __name__ == "__main__":
    build()
