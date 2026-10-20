import argparse
import json
import os
import sys

from . import __version__, check, credits_markdown, scan, write_manifest


def main(argv=None):
    ap = argparse.ArgumentParser(prog="rights-preflight", description="Rights gate for creative assets.")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("scan", help="list media files and write rights-manifest.json")
    p.add_argument("dir")
    p.add_argument("-o", "--output", help="manifest path (default: <dir>/rights-manifest.json)")
    p = sub.add_parser("check", help="fail on missing or conflicting rights")
    p.add_argument("dir")
    p.add_argument("--commercial", action="store_true", help="also fail on non-commercial licenses")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p = sub.add_parser("credits", help="write CREDITS.md grouped by license")
    p.add_argument("dir")
    p.add_argument("-o", "--output", help="output path (default: <dir>/CREDITS.md)")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.dir):
        print("rights-preflight: not a directory: " + args.dir, file=sys.stderr)
        return 2
    try:
        files = scan(args.dir)
    except ValueError as e:
        print("rights-preflight: " + str(e), file=sys.stderr)
        return 2

    if args.cmd == "scan":
        out = args.output or os.path.join(args.dir, "rights-manifest.json")
        write_manifest(files, out)
        for f in files:
            print("%-6s %10d  %-20s %s" % (f["type"], f["size"], f["rights"]["license_id"] or "-", f["path"]))
        print("%d media files -> %s" % (len(files), out))
        return 0

    if args.cmd == "credits":
        out = args.output or os.path.join(args.dir, "CREDITS.md")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(credits_markdown(files))
        print("wrote " + out)
        return 0

    problems = check(files, commercial=args.commercial)
    if args.json:
        print(json.dumps({"ok": not problems, "commercial": args.commercial, "files": len(files),
                          "problems": problems}, indent=2, ensure_ascii=False))
    else:
        for p in problems:
            print("%s: %s: %s" % (p["path"], p["code"], p["message"]))
        bad = len({p["path"] for p in problems})
        print("%d problems in %d of %d files" % (len(problems), bad, len(files)) if problems
              else "OK: %d files checked" % len(files))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
