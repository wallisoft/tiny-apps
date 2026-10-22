# Submitting an app to TinyApps

Thanks for adding to the shelf. A TinyApp does **one** job well, is **readable**
before it's run, and leaves nothing behind that a normal uninstall won't remove.

## The shape

One folder under `catalog/<your-slug>/`:

- `app.vml` — the description (schema below)
- `icon.svg` — a 300x300 tile
- your script(s), and/or links to release downloads

Copy `catalog/ff-refresh/` as a starting point.

## app.vml

```
@App my-tool
Name=my-tool
Platforms=linux, windows          which it supports
Fixes=the one annoying thing it fixes.
Icon=icon.svg
Category=UtilitiesApplication
Description=What it does. **bold** and `code` both work here.

@Download linux-deb                a real download (best for anything that should stick around)
Platform=linux
Label=Ubuntu / Mint / Debian - .deb
Url=https://github.com/wallisoft/tiny-apps/releases/latest/download/my-tool.deb

@Install linux-run                 ...or a one-line script
Platform=linux
Label=run it
Cmd=curl -fsSL https://tiny-apps.vml.onl/apps/my-tool.txt | bash
Note=what happens when you run it.

@Script linux                      a script shipped on the site as plain text
File=linux.txt                     the file in your folder
Publish=apps/my-tool.txt           the URL it's served at (matches the Cmd)
```

Repeat `@Download`, `@Install` and `@Script` as needed; `Platform` is `linux` or `windows`.

## The rules (guardrails)

- **One job.** If it needs a settings screen, it isn't a TinyApp.
- **Readable.** Scripts are plain text — no obfuscation, no minified blobs, nothing that
  hides what it does. A person should be able to read it in a minute.
- **Say what it touches.** If it needs `sudo`, or deletes or changes anything, the
  Description and Note say so plainly.
- **No surprises.** No telemetry, no account, no network calls beyond the job itself.
- **Downloads are open.** `.deb` / AppImage / `.exe` link to a public release built from
  source in the open (GitHub release assets on this repo are ideal).
- **Cross-platform is welcome, never required.** Linux-only or Windows-only is fine.

## How it's tested

Every submission is **test-run in an isolated sandbox** before it's merged: the script is
executed in a throwaway environment and its behaviour checked against what the `app.vml`
claims. Keep it honest and readable and it'll sail through.

## Submitting

1. Fork, add your `catalog/<slug>/` folder.
2. Run `python3 build.py` and open the result to check your card looks right.
3. Open a pull request. That's it.
