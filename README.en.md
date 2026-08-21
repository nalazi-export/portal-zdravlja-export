# portal-zdravlja-export

*Hrvatski: [README.md](README.md)*

Download **all of your own** lab results and specialist findings from
[Portal zdravlja](https://portal.zdravlje.hr), Croatia's national health
portal, as PDFs in one go.

The portal has no bulk export - documents are downloaded one at a time, by
hand. This script automates that: it reads the list of reports, fetches every
attachment, and saves each one as a sensibly named PDF.

> **This is a tool for accessing your own data.** It works only with your own
> login and your own records, using the same API calls the portal itself makes
> in your browser. The right to a copy of your own health data is guaranteed by
> the GDPR (Art. 15 and Art. 20).

## Installation

```
git clone https://github.com/nalazi-export/portal-zdravlja-export
cd portal-zdravlja-export
pip install -r requirements.txt
```

## Usage

Logging in is **manual** by design. NIAS requires a second factor (mToken,
eOsobna, mobile ID); that is not automated here and should not be.

1. Log in to Portal zdravlja in Firefox as you normally would, via e-Građani.
2. While still logged in, run one command:

```
python3 pz_download.py
```

That is the whole thing. The script reads the live session straight out of
Firefox, so there is no cookie file to create, copy or keep up to date. On
Windows use `python` instead of `python3`.

Useful first step, which checks the session and prints how many reports exist
without downloading anything:

```
python3 pz_download.py --probe
```

Result:

```
nalazi/
├── laboratorijski/2024-03-15_dom-zdravlja_r12345678_a12345678.pdf
├── specijalisticki/2024-05-02_opca-bolnica_r87654321_a87654321.pdf
└── manifest.json      # metadata for every report (institution, date, specialty)
```

Sessions are short, so run the script right after logging in. If the session
expires, the script detects it and stops cleanly - log in again and re-run it,
and anything already downloaded is skipped.

### Windows

The simplest option is the
**[latest release](https://github.com/nalazi-export/portal-zdravlja-export/releases/latest)**: download
`portal-zdravlja-export.exe` and run it. No Python installation needed.

Windows will warn that the file is unsigned ("Windows protected your PC" ->
More info -> Run anyway). That warning is expected: code signing certificates
cost money and this project has none. The executable is built by GitHub Actions
from this repository and carries a build provenance attestation, so you can
check that it came from this source and this commit:

```
gh attestation verify portal-zdravlja-export.exe --repo nalazi-export/portal-zdravlja-export
```

Double-clicking runs it with no options, which downloads everything into a
`nalazi` folder beside the executable. It accepts the same options as the
scripts, so you can also run it from PowerShell:

```
PS> ./portal-zdravlja-export.exe --probe
PS> ./portal-zdravlja-export.exe --only lab
PS> ./portal-zdravlja-export.exe -o D:\nalazi --delay 1
```

```
PS> ./portal-zdravlja-export.exe --help
usage: portal-zdravlja-export.exe [-h] [-o OUTDIR] [--cookie-file COOKIE_FILE] [--delay DELAY]
                                  [--active {true,false,both}] [--only {lab,skzz}] [--probe]

Bulk-download Portal zdravlja nalazi

options:
  -h, --help            show this help message and exit
  -o OUTDIR, --outdir OUTDIR
                        where to save the PDFs (default: nalazi)
  --cookie-file COOKIE_FILE
                        read the Cookie header from this file instead of reading the live session
                        straight out of Firefox
  --delay DELAY         seconds between requests
  --active {true,false,both}
                        which listing to request; the server appears to ignore this
  --only {lab,skzz}     restrict to one category
  --probe               just verify the session and print counts
```

If you would rather not run an unsigned binary, which is a reasonable position
for a tool that touches medical records, use the Python route below instead.

#### With Python

Install Python from [python.org](https://www.python.org/downloads/) (any recent
3.x), then double-click **`run_windows.bat`**. It installs the two dependencies,
runs the download, and keeps the window open at the end so you can read what
happened.

If you prefer a terminal, use the `py` launcher, which works even when Python
was not added to PATH:

```
py -m pip install -r requirements.txt
py pz_download.py
```

Typing `python` on Windows often opens the Microsoft Store instead of running
Python. `py` does not have that problem.

### Saving the cookie by hand

If reading Firefox automatically does not work, or you use a different browser,
supply the cookie yourself:

1. Log in to Portal zdravlja.
2. Press F12 for developer tools and open the **Network** tab.
3. Reload the page, then click any request to `api/rest`.
4. In its request headers, find the line starting `Cookie:` and copy it.
5. Save it in a plain text file called `cookie.txt`, next to the scripts.
6. Run `py pz_download.py --cookie-file cookie.txt`, or just double-click
   `run_windows.bat`, which picks up `cookie.txt` on its own.

Easier still: install a browser extension such as **Cookie Editor** or **Get
cookies.txt**, export the cookies for `portal.zdravlje.hr`, and save them as
`cookie.txt`.

The file may hold a Netscape `cookies.txt` export, the bare cookie string, the
full `Cookie: ...` line, or the whole header block - all of them are accepted,
so whichever export you pick will work. Cookies for other sites in the same
file are ignored.

**That file is working access to your account.** Delete it when you are done and
never share it; `.gitignore` already keeps it out of git. It also stops working
on its own once the session expires, at which point you repeat the steps.

### Options

| | |
|---|---|
| `-o, --outdir DIR` | where to save (default `nalazi/`) |
| `--only lab\|skzz` | lab results only, or specialist findings only |
| `--delay SEC` | pause between requests (default 0.4) |
| `--probe` | only check the session and print counts |

**Please do not lower `--delay`.** The portal is public health infrastructure.
Downloading your entire history is a two-minute job at the default rate anyway.

## How it works

Portal zdravlja is an Angular SPA over a JSON REST API at
`/portalzdravlja/api/rest/`. Authentication is by cookie alone
(`JSESSIONID_PZ`), with no CSRF token, so lifting the cookie from a logged-in
browser session is enough.

| | Lab results | Specialist findings (SKZZ) |
|---|---|---|
| listing | `labreports/getlabreports` | `medicalreports/getmedicalreports` + `type=SKZZ` |
| attachments | `labreports/getattachments?report_id=` | `medicalreports/getattachments?report_id=&type=SKZZ` |
| file | **POST** `labreports/getattachment?attachment_id=` | **GET** `medicalreports/getattachment?attachment_id=&type=SKZZ` |

Two traps. The PDF does not arrive as a binary body but as **base64 inside
JSON** (`{"mime_type":"application/pdf","encoding":"B64","attachment":"JVBERi..."}`).
And the lab `getattachment` is a POST whose body is an Angular `HttpHeaders`
object that the app sends by mistake - the script reproduces it faithfully
rather than betting it is ignored.

`pz_cookie.py` reads cookies from Firefox. `JSESSIONID_PZ` has no expiry, which
makes it a session cookie, so it **is not in `cookies.sqlite`** - Firefox keeps
it in memory and mirrors it into `sessionstore-backups/recovery.jsonlz4`
(mozlz4), which is where the script gets it from. Of the two session store
files, the newest by mtime wins: `recovery.baklz4` is a stale backup of
`recovery.jsonlz4`, and preferring it by accident yields a dead session id.

## Record types and the manifest

The specialist listing returns two kinds of record, distinguished by the
`report_type` field:

| `report_type` | What it is | PDF? |
|---|---|---|
| `SKZZ` | Specialist findings (specijalisticko-konzilijarna zdravstvena zastita) | yes |
| `HOSP` | Hospitalisation records | no |

`HOSP` records have no attachment: `getattachments` returns an empty list
because the portal holds no document for them, and they use a separate id range
(~3M, against ~100M for `SKZZ`). This is not a failure of the script, and it is
worth knowing before you conclude that something failed to download. In
testing, every `SKZZ` record had a PDF and no `HOSP` record did.

Nothing is lost in that case: every record is written to `nalazi/manifest.json`
with its full metadata - institution, date, specialty, doctor, and attachment
ids - whether or not a PDF existed to download. The manifest is the complete
index of your records; the PDFs are the subset that have documents behind them.

## Known limitations

- **The API is undocumented and unversioned - it can change without notice.**
  If the specialist listing stops working, extend `SKZZ_LIST_CANDIDATES` at the
  top of `pz_download.py`; the script tries each candidate in turn and reports
  which one worked.
- The server **ignores** the `type` parameter on the listing endpoint:
  `type=SKZZ`, `type=NPP` and an outright nonsense value all return identical
  results. The listing is therefore always complete, so any record type the
  portal adds later is picked up automatically rather than silently skipped.
  (`NPP` appears only in the portal's ordering code, never as a `report_type`.)
- Only Firefox is supported, on Linux, macOS and Windows. For other browsers,
  copy the `Cookie` header out of the developer tools into a file and pass
  `--cookie-file`, or set the `PZ_COOKIE` environment variable.
- If several Firefox profiles are logged in, the most recently used one wins.
  Profiles are never merged: mixing a logged-in profile with a logged-out one
  would produce a cookie header that authenticates as nobody.

### Tested on

Firefox ESR on Linux and Firefox on Windows, against a single account, in 2026.
On Windows the whole path has been exercised: reading the Firefox profile,
the `cookie.txt` route, a complete download, and the launcher's failure
branches. macOS is **not** tested - that profile location is implemented from
documentation, not from a working run.
Behaviour with multiple Firefox profiles, with very large numbers of reports,
and against the portal's WAF at speed is unverified - the 0.4s default delay is
a considered guess, not a measured safe rate. Treat this as v0.1 and check that
what you got matches what the portal shows you.

## Privacy

The script talks **only** to `portal.zdravlje.hr`. No telemetry, no third
parties. Everything stays on your disk.

Be careful what you share: `nalazi/` and `manifest.json` are your medical
records and metadata in plain text, and `~/.config/pz_cookie.txt` is valid
access to your account. `.gitignore` keeps them out of git - do not work around
it.

**When reporting bugs, do not paste portal responses.** They contain your health
data. The HTTP status and the endpoint name are enough.
