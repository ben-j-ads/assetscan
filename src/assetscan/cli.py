"""Command line: `assetscan serve` (the app), `assetscan scan file.csv`, `assetscan sample`."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .io import read_csv
from .scan import analyze
from .stats import n_for_margin


def _pct(text: str) -> float:
    text = text.strip()
    return float(text[:-1]) / 100 if text.endswith("%") else (float(text) / 100 if float(text) > 1 else float(text))


def render(result: dict) -> str:
    s = result["summary"]
    lines = [f"Distinctive asset scan: {s['assets']} assets, best is {s['best']} ({s['best_score']:.0f}/100)", ""]
    lines.append(f"{'asset':<24}{'score':>6}  {'fame':>6}  {'unique':>6}  {'conf':<6} grid")
    for r in result["assets"]:
        lines.append(f"{r['name'][:23]:<24}{r['score']:>6.0f}  {r['fame'] * 100:>5.0f}%  {r['uniqueness'] * 100:>5.0f}%  "
                     f"{r['confidence']:<6} {r['quadrant_label']} ({r['band']})")
    for r in result["assets"]:
        for n in r["notes"]:
            lines.append(f"  - {r['name']}: {n}")
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="assetscan", description="Score your brand's distinctive assets on fame and uniqueness.")
    p.add_argument("--version", action="version", version=f"assetscan {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    sv = sub.add_parser("serve", help="open the app in your browser")
    sv.add_argument("--port", type=int, default=8766)
    sv.add_argument("--no-browser", action="store_true")
    sc = sub.add_parser("scan", help="score assets from a csv")
    sc.add_argument("csv")
    sc.add_argument("--fame-cut", type=_pct, default=0.3)
    sc.add_argument("--uniq-cut", type=_pct, default=0.5)
    sc.add_argument("--json", action="store_true")
    pl = sub.add_parser("plan", help="how many respondents do I need?")
    pl.add_argument("--margin", type=_pct, default=0.05, help="± margin on fame, e.g. 5%%")
    args = p.parse_args(argv)

    try:
        if args.command == "serve":
            from .server import serve
            serve(args.port, not args.no_browser)
        elif args.command == "scan":
            res = analyze(read_csv(args.csv), args.fame_cut, args.uniq_cut)
            print(json.dumps(res, indent=2) if args.json else render(res))
        else:
            n = n_for_margin(args.margin)
            print(f"{n} respondents per asset for ±{args.margin * 100:.0f} points on fame at 95% confidence (worst case).\n"
                  "Uniqueness rests only on people who linked the asset to a brand, so if few do, you need more.")
    except (ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0
