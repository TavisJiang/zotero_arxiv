from __future__ import annotations

import argparse
import sys

from .commands import cmd_generate, cmd_list, cmd_zotero_add, cmd_pick, cmd_zotero_add_from_md


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zotero_arxiv")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")

    sub = parser.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="Generate daily arXiv digest markdown + index")
    g.add_argument("--date", default=None, help="Date YYYY-MM-DD (defaults to today in configured timezone)")
    g.add_argument("--max-papers", type=int, default=None, help="Override output.max_papers (must be >= 10)")
    g.add_argument("--since-days", type=int, default=None, help="Override arxiv.since_days")
    g.add_argument("--temp", action="store_true", help="Generate a temporary report (not the regular daily one)")
    g.add_argument("--run-id", default=None, help="Optional run id/suffix for temp reports")
    g.set_defaults(func=cmd_generate)

    l = sub.add_parser("list", help="List papers in a generated daily index")
    l.add_argument("--date", required=True, help="Date YYYY-MM-DD")
    l.set_defaults(func=cmd_list)

    z = sub.add_parser("zotero-add", help="Import selected papers into Zotero")
    z.add_argument("--date", required=True, help="Date YYYY-MM-DD")
    z.add_argument("--ids", nargs="+", required=True, help="One or more numeric IDs from the daily list")
    z.set_defaults(func=cmd_zotero_add)

    pick_parser = sub.add_parser("pick", help="Interactively pick papers to import into Zotero")
    pick_parser.add_argument("--date", required=True, help="Date YYYY-MM-DD")
    pick_parser.set_defaults(func=cmd_pick)

    zm = sub.add_parser("zotero-add-from-md", help="Import all checked (- [x]) papers from markdown")
    zm.add_argument("--date", required=True, help="Date YYYY-MM-DD")
    zm.add_argument("--md-path", default=None, help="Path to markdown file (for temp/custom reports)")
    zm.add_argument("--index-path", default=None, help="Path to index json file (for temp/custom reports)")
    zm.set_defaults(func=cmd_zotero_add_from_md)

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = _build_parser()
    # Allow placing --config anywhere (before/after subcommand).
    # We do a lightweight pre-parse for --config, then let argparse parse normally.
    cfg = "config.yaml"
    if "--config" in argv:
        i = argv.index("--config")
        if i + 1 >= len(argv):
            print("Error: --config requires a value", file=sys.stderr)
            return 2
        cfg = argv[i + 1]
        argv = argv[:i] + argv[i + 2 :]

    args = parser.parse_args(argv)
    args.config = cfg

    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

