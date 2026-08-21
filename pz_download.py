#!/usr/bin/env python3
"""
Download every lab result (labreports) and specialist finding (medicalreports/SKZZ)
PDF from Portal zdravlja, using a session cookie copied out of a logged-in browser.

Usage:
    export PZ_COOKIE="$(cat ~/.config/pz_cookie.txt)"
    ./pz_download.py --probe            # check the cookie is alive, print counts
    ./pz_download.py                    # download everything into ./nalazi/
"""
import argparse
import base64
import json
import os
import re
import sys
import time
import unicodedata

import requests

BASE = "https://portal.zdravlje.hr/portalzdravlja"
API = BASE + "/api/rest"
REFERER_LAB = BASE + "/web/laboratorijski-nalazi"
REFERER_SKZZ = BASE + "/web/specijalisticki-nalazi"

# The Angular app POSTs its own HttpHeaders object as the body of the lab
# attachment call. Harmless, but replicated so the request is byte-identical.
ANGULAR_BODY = {"headers": {"normalizedNames": {}, "lazyUpdate": None}, "withCredentials": True}

# The SKZZ list endpoint was not in the capture; these are tried in order.
SKZZ_LIST_CANDIDATES = [
    ("medicalreports/getmedicalreports", {"type": "SKZZ"}),
    ("medicalreports/getreports", {"type": "SKZZ"}),
    ("medicalreports/getlist", {"type": "SKZZ"}),
    ("medicalreports/list", {"type": "SKZZ"}),
]


class SessionExpired(RuntimeError):
    pass


EXIT_ERROR = 1
EXIT_AUTH = 2      # cookie or session problem: the user can fix this themselves


def die(msg, code=EXIT_ERROR):
    print(msg, file=sys.stderr)
    sys.exit(code)


def slug(s, maxlen=60):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s[:maxlen] or "nn"


class Portal:
    def __init__(self, cookie, delay=0.4, verbose=True):
        self.s = requests.Session()
        self.s.headers.update({
            "Cookie": cookie.strip(),
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "hr,en-US;q=0.7,en;q=0.3",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Origin": "https://portal.zdravlje.hr",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        })
        self.delay = delay
        self.verbose = verbose

    def call(self, path, params=None, method="GET", referer=REFERER_LAB, json_body=None):
        url = f"{API}/{path}"
        r = self.s.request(method, url, params=params, headers={"Referer": referer},
                           json=json_body, allow_redirects=False, timeout=60)
        time.sleep(self.delay)
        if r.status_code in (301, 302, 303, 307):
            raise SessionExpired(f"{path} redirected to {r.headers.get('Location','?')} - cookie is dead, log in again")
        if r.status_code in (401, 403):
            raise SessionExpired(f"{path} -> HTTP {r.status_code} - cookie is dead, log in again")
        ctype = r.headers.get("Content-Type", "")
        if "json" not in ctype:
            # An HTML 200 is the SPA shell served after a logout; an HTML 404/500
            # is just a wrong path, which must not abort the whole run.
            if "html" in ctype and r.status_code == 200:
                raise SessionExpired(f"{path} returned the login page - cookie is dead")
            raise RuntimeError(f"{path} -> HTTP {r.status_code} {ctype}: {r.text[:200]}")
        r.raise_for_status()
        return r.json()

    # ---------- listings ----------

    def lab_list(self, active=True, page_size=50):
        out, seen, page = [], set(), 1
        while True:
            j = self.call("labreports/getlabreports",
                          {"pageSize": page_size, "pageNumber": page, "active": str(active).lower()})
            rows = j.get("data", [])
            new = [r for r in rows if r.get("id") not in seen]
            seen.update(r.get("id") for r in rows)
            out.extend(new)
            total = j.get("totalElements", len(out))
            if self.verbose:
                print(f"  lab list (active={active}): page {page}, {len(out)}/{total}")
            if rows and not new:
                # This API is known to ignore query parameters it does not like
                # (see `type`). If it ignores pageNumber too, every page repeats
                # and counting rows would look like success while losing records.
                print(f"  ! page {page} repeated earlier records: the server may be "
                      f"ignoring pageNumber. Got {len(out)} of {total}.", file=sys.stderr)
                break
            if len(out) >= total or not rows:
                break
            page += 1
        return out

    def skzz_list(self, active=True, page_size=50):
        """The SKZZ list path was not in the Burp capture, so probe the candidates."""
        last_err = None
        for path, extra in SKZZ_LIST_CANDIDATES:
            try:
                params = {"pageSize": page_size, "pageNumber": 1, "active": str(active).lower(), **extra}
                j = self.call(path, params, referer=REFERER_SKZZ)
            except SessionExpired:
                raise
            except Exception as e:
                last_err = e
                continue
            if self.verbose:
                print(f"  SKZZ list endpoint: {path}")
            out = list(j.get("data", j if isinstance(j, list) else []))
            seen = {r.get("id") for r in out}
            total = j.get("totalElements", len(out)) if isinstance(j, dict) else len(out)
            page = 2
            while len(out) < total:
                params["pageNumber"] = page
                j = self.call(path, params, referer=REFERER_SKZZ)
                rows = j.get("data", []) if isinstance(j, dict) else j
                if not rows:
                    break
                new = [r for r in rows if r.get("id") not in seen]
                seen.update(r.get("id") for r in rows)
                if not new:
                    print(f"  ! page {page} repeated earlier records: the server may be "
                          f"ignoring pageNumber. Got {len(out)} of {total}.", file=sys.stderr)
                    break
                out.extend(new)
                if self.verbose:
                    print(f"  SKZZ list: page {page}, {len(out)}/{total}")
                page += 1
            return out, path
        print(f"  !! could not find the SKZZ list endpoint (last error: {last_err})", file=sys.stderr)
        print("     Open /web/specijalisticki-nalazi with Burp running, read the real path,", file=sys.stderr)
        print("     and add it to SKZZ_LIST_CANDIDATES.", file=sys.stderr)
        return [], None

    # ---------- attachments ----------

    def lab_attachments(self, report_id):
        return self.call("labreports/getattachments", {"report_id": report_id})

    def lab_attachment(self, attachment_id):
        return self.call("labreports/getattachment", {"attachment_id": attachment_id},
                         method="POST", json_body=ANGULAR_BODY)

    def skzz_attachments(self, report_id):
        return self.call("medicalreports/getattachments", {"report_id": report_id, "type": "SKZZ"},
                         referer=REFERER_SKZZ)

    def skzz_attachment(self, attachment_id):
        return self.call("medicalreports/getattachment", {"attachment_id": attachment_id, "type": "SKZZ"},
                         referer=REFERER_SKZZ)


EXT = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png",
       "text/html": "html", "text/plain": "txt", "application/xml": "xml"}


def save_attachment(payload, outdir, stem):
    if payload.get("encoding", "").upper() != "B64":
        raise RuntimeError(f"unexpected encoding {payload.get('encoding')!r}")
    blob = base64.b64decode(payload["attachment"])
    ext = EXT.get(payload.get("mime_type", ""), "bin")
    path = os.path.join(outdir, f"{stem}.{ext}")
    with open(path, "wb") as f:
        f.write(blob)
    return path, len(blob)


def harvest(p, kind, rows, list_atts, get_att, outdir, manifest):
    os.makedirs(outdir, exist_ok=True)
    n_new = n_skip = 0
    for row in rows:
        rid = row.get("id")
        date = (row.get("datum") or "0000-00-00")[:10]
        stem_base = f"{date}_{slug(row.get('ustanova') or row.get('naslov_nalaza'), 40)}_r{rid}"
        try:
            atts = list_atts(rid)
        except SessionExpired:
            raise
        except Exception as e:
            print(f"  ! {kind} {rid}: attachment list failed: {e}", file=sys.stderr)
            continue
        if not atts:
            # Normal for report_type HOSP: the portal holds no document for those.
            rt = row.get("report_type") or "?"
            print(f"  - {kind} {rid} ({date}, {rt}): no attachment")
        for a in atts:
            aid = a.get("id")
            stem = f"{stem_base}_a{aid}"
            existing = [f for f in os.listdir(outdir) if f.startswith(stem + ".")]
            if existing:
                n_skip += 1
                continue
            try:
                payload = get_att(aid)
                path, size = save_attachment(payload, outdir, stem)
            except SessionExpired:
                raise
            except Exception as e:
                print(f"  ! {kind} {rid}/{aid}: {e}", file=sys.stderr)
                continue
            n_new += 1
            print(f"  + {os.path.basename(path)} ({size//1024} KB)")
        manifest.append({"kind": kind, "report": row, "attachments": atts})
    return n_new, n_skip


COOKIE_HOST = "zdravlje.hr"


def clean_cookie_text(text):
    """Accept whatever someone actually puts in a cookie file.

    In practice that is one of: a Netscape cookies.txt exported by a browser
    extension, the bare cookie string, a full `Cookie: ...` header line, or the
    whole request-header block copied out of devtools.
    """
    raw = [ln for ln in text.splitlines() if ln.strip()]

    # Netscape cookies.txt: domain, flag, path, secure, expiry, name, value,
    # tab separated. Exporters mark HttpOnly entries with a #HttpOnly_ prefix,
    # and JSESSIONID_PZ is HttpOnly, so those lines must be kept rather than
    # discarded as comments.
    netscape = {}
    for ln in raw:
        if ln.startswith("#HttpOnly_"):
            ln = ln[len("#HttpOnly_"):]
        elif ln.lstrip().startswith("#"):
            continue
        parts = ln.split("\t")
        if len(parts) >= 7 and COOKIE_HOST in parts[0]:
            netscape[parts[5].strip()] = parts[6].strip()
    if netscape:
        return "; ".join(f"{k}={v}" for k, v in netscape.items())

    lines = [ln.strip() for ln in raw]
    for ln in lines:
        if ln.lower().startswith("cookie:"):
            return ln.split(":", 1)[1].strip()
    return " ".join(lines).strip()


def resolve_cookie(args):
    """Find a session cookie: explicit file, then $PZ_COOKIE, then Firefox itself.

    Reading Firefox directly is the default because a cookie file goes stale the
    moment the session rotates, and a stale file fails as an opaque 401 rather
    than as "you are not logged in".
    """
    if args.cookie_file:
        if not os.path.exists(args.cookie_file):
            die(f"No such cookie file: {args.cookie_file}", EXIT_AUTH)
        cookie = clean_cookie_text(open(args.cookie_file, encoding="utf-8-sig").read())
        source = args.cookie_file
    elif os.environ.get("PZ_COOKIE", "").strip():
        cookie = clean_cookie_text(os.environ["PZ_COOKIE"])
        source = "$PZ_COOKIE"
    else:
        try:
            import pz_cookie
        except ImportError:
            die("pz_cookie.py must sit next to this script, or pass --cookie-file.")
        try:
            cookie = pz_cookie.get_cookie_header()
        except RuntimeError as e:
            die(f"{e}\n\nAlready logged in? Then pass --cookie-file, or set $PZ_COOKIE "
                f"to the Cookie header copied from your browser's developer tools.", EXIT_AUTH)
        source = "Firefox"
    if "JSESSIONID_PZ" not in cookie:
        print(f"warning: cookie from {source} has no JSESSIONID_PZ, so it will "
              f"probably not authenticate", file=sys.stderr)
    else:
        print(f"cookie source: {source}")
    return cookie


def main():
    # Windows consoles default to a legacy codepage that cannot encode Croatian
    # characters, which turns any diacritic in the output into a crash.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(description="Bulk-download Portal zdravlja nalazi")
    ap.add_argument("-o", "--outdir", default="nalazi",
                    help="where to save the PDFs (default: nalazi)")
    ap.add_argument("--cookie-file", default=None,
                    help="read the Cookie header from this file instead of reading "
                         "the live session straight out of Firefox")
    ap.add_argument("--delay", type=float, default=0.4, help="seconds between requests")
    ap.add_argument("--active", choices=["true", "false", "both"], default="true",
                    help="which listing to request; the server appears to ignore this")
    ap.add_argument("--only", choices=["lab", "skzz"], help="restrict to one category")
    ap.add_argument("--probe", action="store_true", help="just verify the session and print counts")
    args = ap.parse_args()

    cookie = resolve_cookie(args)

    p = Portal(cookie, delay=args.delay)
    actives = [True, False] if args.active == "both" else [args.active == "true"]

    try:
        who = p.call("confperson/")
        name = who.get("ime") or who.get("firstName") or ""
        print(f"session OK{(' - ' + str(name)) if name else ''}")

        lab_rows, skzz_rows = [], []
        if args.only != "skzz":
            for act in actives:
                lab_rows += p.lab_list(active=act)
        if args.only != "lab":
            for act in actives:
                rows, _ = p.skzz_list(active=act)
                skzz_rows += rows

        # de-duplicate on id, active=true/false lists can overlap
        lab_rows = list({r["id"]: r for r in lab_rows}.values())
        skzz_rows = list({r["id"]: r for r in skzz_rows}.values())
        print(f"lab reports: {len(lab_rows)}   specialist (SKZZ): {len(skzz_rows)}")
        if args.probe:
            return

        manifest = []
        new_files = skipped = 0
        os.makedirs(args.outdir, exist_ok=True)
        if lab_rows:
            print("laboratorijski nalazi:")
            a, b = harvest(p, "lab", lab_rows, p.lab_attachments, p.lab_attachment,
                           os.path.join(args.outdir, "laboratorijski"), manifest)
            new_files += a; skipped += b
        if skzz_rows:
            print("specijalisticki nalazi:")
            a, b = harvest(p, "skzz", skzz_rows, p.skzz_attachments, p.skzz_attachment,
                           os.path.join(args.outdir, "specijalisticki"), manifest)
            new_files += a; skipped += b

        # The PDFs are the point. A manifest problem must not be reported as if
        # the whole download failed, which is exactly what it used to look like.
        try:
            with open(os.path.join(args.outdir, "manifest.json"), "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=1)
            note = "manifest.json written"
        except (OSError, UnicodeError) as e:
            note = f"manifest.json could NOT be written: {e}"
            print(f"warning: {note}", file=sys.stderr)
        print(f"\ndone -> {args.outdir}/")
        print(f"  {new_files} new file(s), {skipped} already present, {note}")

    except SessionExpired as e:
        die(f"\nSESSION EXPIRED: {e}\nRe-login in the browser, copy a fresh Cookie header, rerun "
            f"(already-downloaded files are skipped).", EXIT_AUTH)


if __name__ == "__main__":
    try:
        main()
    finally:
        # A double-clicked .exe closes its console the instant it returns, which
        # would hide both the summary and any error. sys.exit raises SystemExit,
        # so finally still runs on the failure paths.
        if getattr(sys, "frozen", False):
            try:
                input("\nPritisnite Enter za izlaz / press Enter to exit...")
            except (EOFError, KeyboardInterrupt):
                pass
