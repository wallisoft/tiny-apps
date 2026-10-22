# TinyApps

Tiny one-job tools for Windows and Linux — each fixes a single annoying thing, and
installs with one pasted line or a small download. No bloat, no accounts, nothing
left behind you can't remove in a breath.

Live shop window: **https://tiny-apps.vml.onl**

## What's here

TinyApps is a *generated* site. You don't edit HTML — you describe each app in a
small folder and the generator builds the shop window from the lot:

```
catalog/<slug>/
  app.vml      what the app is: name, platforms, what it fixes, install lines, downloads
  icon.svg     a 300x300 tile
  *.txt        the app's scripts (served verbatim on the site)
build.py       renders the whole site from catalog/ into a folder ready to publish
site/          the page template, stylesheet and fez logo
recipe.vml     lets Wallisoft's builder (Bob) regenerate the site in one click
```

## Building it

```
python3 build.py                          # builds into ~/.cache/tinyapps/site
TINYAPPS_OUT=/tmp/site python3 build.py   # ...or anywhere, for a look
```

Open the resulting `index.html` to preview. Stdlib Python only — nothing to install.

## Adding an app

See **[CONTRIBUTING.md](CONTRIBUTING.md)** — it's one folder and a pull request.

## Licence

MIT (c) Wallisoft. Each listed tool keeps its own licence; see its `catalog/<slug>/`.
