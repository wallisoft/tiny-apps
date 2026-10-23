# Submitting an app to TinyApps

Thanks for adding to the shelf. A TinyApp does **one** job well, is **readable**
before it's run, and leaves nothing behind that a normal uninstall won't remove.

There are **two ways in**:

- **Verified** — open a pull request here. We review it and it lands with a green
  ✓ Verified badge. This is also the only tier the org store (verified-only) pulls from.
- **Unverified** — publish it yourself in one command with `submit.py`, no review. It
  shows a ⚠ Unverified badge and carries **downloads only** (no paste-and-run installers).
  Quicker, but it's on the user to check the download — same as anything off the open web.

tiny-apps.vml.onl is the **informal shop**: it carries both. Pick the tier that fits.

## The shape

One folder under `catalog/<your-slug>/` (verified) or any folder you keep locally (unverified):

- `app.vml` — the description (schema below)
- `icon.svg` or `icon.png` — a 300×300 tile
- your script(s), and/or links to release downloads

Copy `catalog/ff-refresh/` as a starting point.

## app.vml

```
@App my-tool
Name=My Tool
Verified=yes                      yes for a reviewed PR; omit/no for an unverified upload
Platforms=linux, windows, android which it supports
Fixes=the one annoying thing it fixes.
Icon=icon.svg
Category=UtilitiesApplication
Description=What it does. **bold** and `code` work here (verified cards only).

@Download win                     a download button; Kind is windows | deb | appimage | apk
Kind=windows
Url=https://github.com/you/your-repo/releases/latest/download/My-Tool-Setup.exe

@Download deb
Kind=deb
Url=https://github.com/you/your-repo/releases/latest/download/my-tool_1.0_amd64.deb

@Install linux-run                one-line installers — VERIFIED apps only (reviewed before merge)
Platform=linux
Label=run it
Cmd=curl -fsSL https://tiny-apps.vml.onl/apps/my-tool.txt | bash
Note=what happens when you run it.

@Script linux                     a script shipped on the site as plain text (verified apps)
File=linux.txt
Publish=apps/my-tool.txt          the URL it's served at (matches the Cmd)
```

Repeat `@Download`, `@Install` and `@Script` as needed. Download `Kind` is one of
`windows`, `deb`, `appimage`, `apk`; only the kinds you provide show up.

## The rules (guardrails)

- **One job.** If it needs a settings screen, it isn't a TinyApp.
- **Readable.** Scripts are plain text — no obfuscation, no minified blobs. A person
  should be able to read it in a minute.
- **Say what it touches.** If it needs `sudo`, or changes or deletes anything, the
  Description and Note say so plainly.
- **No surprises.** No telemetry, no account, no network calls beyond the job itself.
- **Downloads are open.** `.exe` / `.deb` / AppImage / `.apk` link to a public release.
  (Heads-up: an unsigned Windows `.exe` off the web trips SmartScreen/Defender — sign it,
  or point Windows users to a Store build where you have one.)

## Verified: pull request

1. Fork, add your `catalog/<slug>/` folder, set `Verified=yes`.
2. Run `python3 build.py` and open the result to check your card looks right.
3. Open a pull request. Every submission is **test-run in an isolated sandbox** before
   it's merged — the script is executed in a throwaway environment and its behaviour
   checked against what `app.vml` claims. Keep it honest and readable and it'll sail through.

## Unverified: self-service upload

No PR, no review — your card loads client-side from the site's `unverified.json`, so a
verified rebuild never touches it. Downloads only (no one-line installers).

```
export TINYAPPS_SUBMIT_KEY=...            your TinyApps submit key
python3 submit.py path/to/my-tool-folder  publish or update it
python3 submit.py --list                  see what's up
python3 submit.py --remove my-tool        take it down
```

The folder needs `app.vml` (with at least one `@Download`) and its icon. That's it.
