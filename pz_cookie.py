#!/usr/bin/env python3
"""Extract the portal.zdravlje.hr Cookie header from a logged-in Firefox profile.

    python3 pz_cookie.py            print the Cookie header
    python3 pz_cookie.py --save     write it to the default cookie file

Also importable: get_cookie_header() returns the same string, which is how
pz_download.py picks up a fresh session without any manual copying.
"""
import argparse
import glob
import json
import os
import shutil
import sqlite3
import sys
import tempfile

WANT_HOST = "zdravlje.hr"
SESSION_COOKIE = "JSESSIONID_PZ"
PREFERRED = ["JSESSIONID_PZ", "subjectId", "subjectIdFormat", "session",
             "cookieconsent_status"]

DEFAULT_COOKIE_FILE = os.path.join(os.path.expanduser("~"), ".config", "pz_cookie.txt")


def profile_dirs():
    """Every Firefox profile directory on this machine, across platforms."""
    pats = [
        "~/.mozilla/firefox/*",                                 # Linux
        "~/snap/firefox/common/.mozilla/firefox/*",             # Linux, snap
        "~/.var/app/org.mozilla.firefox/.mozilla/firefox/*",    # Linux, flatpak
        "~/Library/Application Support/Firefox/Profiles/*",     # macOS
    ]
    out = [p for pat in pats for p in glob.glob(os.path.expanduser(pat))]
    appdata = os.environ.get("APPDATA")                         # Windows
    if appdata:
        out += glob.glob(os.path.join(appdata, "Mozilla", "Firefox", "Profiles", "*"))
    return sorted(p for p in out if os.path.isdir(p))


def read_sqlite(db):
    """Persistent cookies. Firefox holds a WAL lock, so work on a copy."""
    tmp = tempfile.mkdtemp()
    try:
        dst = os.path.join(tmp, "cookies.sqlite")
        shutil.copy2(db, dst)
        for side in ("-wal", "-shm"):
            if os.path.exists(db + side):
                shutil.copy2(db + side, dst + side)
        con = sqlite3.connect(dst)
        try:
            rows = con.execute(
                "SELECT name, value FROM moz_cookies WHERE host LIKE ?",
                (f"%{WANT_HOST}",)).fetchall()
        finally:
            con.close()
        return dict(rows)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def read_sessionstore(path):
    """Session cookies. JSESSIONID_PZ has no expiry, so Firefox keeps it in
    memory and never writes it to cookies.sqlite; it appears only here."""
    import lz4.block
    raw = open(path, "rb").read()
    if raw[:8] != b"mozLz40\0":
        return {}
    j = json.loads(lz4.block.decompress(raw[8:]))
    return {c["name"]: c["value"] for c in j.get("cookies", [])
            if WANT_HOST in (c.get("host") or "")}


def collect(verbose=False):
    """Cookies per profile, newest source winning *within* each profile.

    Profiles are kept separate on purpose: merging them would mix a logged-in
    profile with a logged-out one and produce a cookie header that authenticates
    as nobody. Returns [(mtime, profile_dir, cookies), ...].
    """
    have_lz4 = True
    try:
        import lz4.block  # noqa: F401
    except ImportError:
        have_lz4 = False
        print("# lz4 is not installed, so session cookies cannot be read.\n"
              "#   pip install lz4", file=sys.stderr)

    results = []
    for prof in profile_dirs():
        cookies, mtime = {}, 0.0
        db = os.path.join(prof, "cookies.sqlite")
        if os.path.exists(db):
            try:
                cookies.update(read_sqlite(db))
                mtime = max(mtime, os.path.getmtime(db))
            except Exception as e:
                if verbose:
                    print(f"# {db}: {e}", file=sys.stderr)
        if have_lz4:
            # Oldest first so the newest wins: recovery.baklz4 is a stale backup
            # of recovery.jsonlz4 and sorting by name would let it win.
            ss = glob.glob(os.path.join(prof, "sessionstore-backups", "recovery.*lz4"))
            for path in sorted(ss, key=os.path.getmtime):
                try:
                    found = read_sessionstore(path)
                except Exception as e:
                    if verbose:
                        print(f"# {path}: {e}", file=sys.stderr)
                    continue
                if found:
                    cookies.update(found)
                    mtime = max(mtime, os.path.getmtime(path))
        if cookies:
            results.append((mtime, prof, cookies))
    return results


def get_cookie_header(verbose=False):
    """Cookie header from the most recently active profile that is logged in."""
    profs = profile_dirs()
    if not profs:
        raise RuntimeError(
            "No Firefox profile directory found on this computer. If Firefox is "
            "installed somewhere unusual, or you use a different browser, save the "
            "cookie by hand into cookie.txt instead (see the README).")
    results = collect(verbose=verbose)
    if not results:
        raise RuntimeError(
            f"Firefox profiles were found ({len(profs)}), but none of them holds any "
            "portal.zdravlje.hr cookie. Log in to the portal with Firefox first, or "
            "save the cookie by hand into cookie.txt (see the README).")
    # Only a profile carrying the session cookie is actually logged in; among
    # those, the most recently written one is the live session.
    logged_in = [r for r in results if SESSION_COOKIE in r[2]]
    if not logged_in:
        raise RuntimeError(
            f"Found portal cookies but no {SESSION_COOKIE}, which means no Firefox "
            "profile is logged in right now. Log in to the portal and try again, or "
            "save the cookie by hand into cookie.txt (see the README).")
    mtime, prof, cookies = max(logged_in, key=lambda r: r[0])
    if verbose:
        print(f"# using profile {prof}", file=sys.stderr)
        if len(logged_in) > 1:
            print(f"# note: {len(logged_in)} profiles are logged in; used the newest",
                  file=sys.stderr)
    order = ([n for n in PREFERRED if n in cookies]
             + sorted(n for n in cookies if n not in PREFERRED))
    return "; ".join(f"{n}={cookies[n]}" for n in order)


def save(header, path):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n")
    try:
        os.chmod(path, 0o600)   # no effect on Windows, harmless there
    except OSError:
        pass
    return path


def main():
    ap = argparse.ArgumentParser(description="Extract the Portal zdravlja cookie from Firefox")
    ap.add_argument("--save", nargs="?", const=DEFAULT_COOKIE_FILE, metavar="PATH",
                    help=f"write to PATH instead of stdout (default {DEFAULT_COOKIE_FILE})")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    try:
        header = get_cookie_header(verbose=args.verbose)
    except RuntimeError as e:
        sys.exit(f"{e}")
    if args.save:
        print(f"saved to {save(header, args.save)}")
    else:
        print(header)


if __name__ == "__main__":
    main()
