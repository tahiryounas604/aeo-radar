"""CLI: init / brand / import / analyze / report / score / query"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .analysis import analyze_answers
from .importer import import_file
from .models import Brand, Competitor
from .provider import OpenAICompatibleProvider
from .report import render_json, render_markdown
from .storage import Store

DEFAULT_DB = "aeo-radar.db"


def _store(args) -> Store:
    store = Store(args.db)
    store.init()
    return store


def _parse_competitors(raw: str) -> list[Competitor]:
    """Format: 'Name:alias1|alias2;Other:o1' — aliases optional."""
    out: list[Competitor] = []
    if not raw:
        return out
    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" in chunk:
            name, alias_part = chunk.split(":", 1)
            aliases = [a.strip() for a in alias_part.split("|") if a.strip()]
        else:
            name, aliases = chunk, []
        out.append(Competitor(name=name.strip(), aliases=aliases))
    return out


def _split_csv(raw: str) -> list[str]:
    return [x.strip() for x in (raw or "").split(",") if x.strip()]


def cmd_init(args) -> int:
    with _store(args):
        pass
    print(f"Initialized database at {args.db}")
    return 0


def cmd_brand(args) -> int:
    store = _store(args)
    try:
        if args.brand_cmd == "add":
            brand = Brand(
                name=args.name,
                aliases=_split_csv(args.aliases or ""),
                competitors=_parse_competitors(args.competitors or ""),
                prompts=_split_csv(args.prompts or ""),
            )
            store.add_brand(brand)
            print(f"Brand saved: {brand.name} (aliases={brand.aliases}, "
                  f"competitors={[c.name for c in brand.competitors]}, prompts={len(brand.prompts)})")
            return 0
        if args.brand_cmd == "list":
            brands = store.list_brands()
            if not brands:
                print("No brands yet.")
            for b in brands:
                print(f"- {b.name} aliases={b.aliases} competitors={[c.name for c in b.competitors]} prompts={len(b.prompts)}")
            return 0
        if args.brand_cmd == "show":
            b = store.get_brand(args.name)
            if b is None:
                print(f"Brand not found: {args.name}", file=sys.stderr)
                return 1
            print(json.dumps(b.to_dict(), indent=2))
            return 0
    finally:
        store.close()
    return 2


def cmd_import(args) -> int:
    store = _store(args)
    try:
        if store.get_brand(args.brand) is None:
            print(f"Brand not found: {args.brand} (create it with: brand add)", file=sys.stderr)
            return 1
        answers = import_file(args.file, default_prompt=args.prompt or "", default_engine=args.engine or "unknown")
        n = store.add_answers(args.brand, answers)
        print(f"Imported {n} answer(s) for brand '{args.brand}' from {args.file}")
        return 0
    finally:
        store.close()


def _run_analysis(store: Store, brand_name: str):
    brand = store.get_brand(brand_name)
    if brand is None:
        return None, None
    answers = store.list_answers(brand_name)
    result = analyze_answers(brand, answers)
    store.save_run(result)
    return brand, result


def cmd_analyze(args) -> int:
    store = _store(args)
    try:
        _brand, result = _run_analysis(store, args.brand)
        if result is None:
            print(f"Brand not found: {args.brand}", file=sys.stderr)
            return 1
        print(f"Analysed {result.total_answers} answer(s) for '{result.brand_name}'")
        print(f"Overall visibility score: {result.overall_score}")
        print(f"Mentioned: {result.mentioned_answers}/{result.total_answers} (rate {result.mention_rate})")
        print(f"Share of voice: {result.share_of_voice}")
        return 0
    finally:
        store.close()


def cmd_report(args) -> int:
    store = _store(args)
    try:
        latest = store.latest_result(args.brand)
        if latest is None:
            _b, result = _run_analysis(store, args.brand)
            if result is None:
                print(f"Brand not found: {args.brand}", file=sys.stderr)
                return 1
            latest = result.to_dict()
        content = render_json(latest) if args.format == "json" else render_markdown(latest)
        if args.output:
            Path(args.output).write_text(content, encoding="utf-8")
            print(f"Report written to {args.output}")
        else:
            print(content)
        return 0
    finally:
        store.close()


def cmd_score(args) -> int:
    store = _store(args)
    try:
        history = store.score_history(args.brand)
        if not history:
            print(f"No analysis runs yet for '{args.brand}'. Run: analyze --brand {args.brand}")
            return 0
        for h in history:
            print(f"run {h['run_id']}  {h['created_at']}  score={h['overall_score']}")
        print(f"Latest score: {history[-1]['overall_score']}")
        if len(history) >= 2:
            delta = round(history[-1]["overall_score"] - history[-2]["overall_score"], 2)
            print(f"Trend (vs previous run): {delta:+}")
        return 0
    finally:
        store.close()


def cmd_query(args) -> int:
    """Optional live query — requires the user's own API key in env."""
    provider = OpenAICompatibleProvider(model=args.model)
    text = provider.query(args.prompt)
    print(text)
    if args.brand:
        store = _store(args)
        try:
            from .models import Answer
            store.add_answers(args.brand, [Answer(prompt=args.prompt, engine=args.engine or provider.model, text=text)])
            print(f"[saved answer for brand '{args.brand}']", file=sys.stderr)
        finally:
            store.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aeo-radar", description="AI Search Visibility Tracker (offline-first)")
    p.add_argument("--db", default=DEFAULT_DB, help="SQLite database path")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init").set_defaults(func=cmd_init)

    bp = sub.add_parser("brand")
    bsub = bp.add_subparsers(dest="brand_cmd", required=True)
    add = bsub.add_parser("add")
    add.add_argument("--name", required=True)
    add.add_argument("--aliases", default="")
    add.add_argument("--competitors", default="", help="'Name:a1|a2;Other:o1'")
    add.add_argument("--prompts", default="")
    add.set_defaults(func=cmd_brand)
    bsub.add_parser("list").set_defaults(func=cmd_brand)
    show = bsub.add_parser("show")
    show.add_argument("--name", required=True)
    show.set_defaults(func=cmd_brand)

    ip = sub.add_parser("import")
    ip.add_argument("--brand", required=True)
    ip.add_argument("--file", required=True)
    ip.add_argument("--engine", default="unknown")
    ip.add_argument("--prompt", default="")
    ip.set_defaults(func=cmd_import)

    ap = sub.add_parser("analyze")
    ap.add_argument("--brand", required=True)
    ap.set_defaults(func=cmd_analyze)

    rp = sub.add_parser("report")
    rp.add_argument("--brand", required=True)
    rp.add_argument("--format", choices=["md", "json"], default="md")
    rp.add_argument("--output", default="")
    rp.set_defaults(func=cmd_report)

    sp = sub.add_parser("score")
    sp.add_argument("--brand", required=True)
    sp.set_defaults(func=cmd_score)

    qp = sub.add_parser("query")
    qp.add_argument("--prompt", required=True)
    qp.add_argument("--brand", default="")
    qp.add_argument("--engine", default="")
    qp.add_argument("--model", default=None)
    qp.set_defaults(func=cmd_query)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
