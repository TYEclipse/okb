#!/usr/bin/env python3
"""OKB CLI — unified command-line interface for the Open Knowledge Base."""

import argparse
import json
import sys
from pathlib import Path

from okb import KnowledgeBase


def main():
    parser = argparse.ArgumentParser(description="OKB — Open Knowledge Base for AI Agents")
    sub = parser.add_subparsers(dest="cmd")

    # build
    p_build = sub.add_parser("build", help="Build 2-edge-connected graph from vector store")
    p_build.add_argument("root", nargs="?", default=".", help="Knowledge base root directory")
    p_build.add_argument("--k", type=int, default=3, help="k-NN neighbors")
    p_build.add_argument("--verify", action="store_true")
    p_build.add_argument("--quiet", action="store_true")

    # query
    p_q = sub.add_parser("query", help="Semantic search")
    p_q.add_argument("root", nargs="?", default=".")
    p_q.add_argument("text", help="Search query")
    p_q.add_argument("--top", type=int, default=10)
    p_q.add_argument("--json", action="store_true")

    # relevance
    p_rel = sub.add_parser("relevance", help="Marginal centrality ranking")
    p_rel.add_argument("root", nargs="?", default=".")
    p_rel.add_argument("text", help="Candidate concept description")
    p_rel.add_argument("--top", type=int, default=10)
    p_rel.add_argument("--json", action="store_true")

    # verify
    p_v = sub.add_parser("verify", help="Verify knowledge base")
    p_v.add_argument("root", nargs="?", default=".")

    # stats
    p_s = sub.add_parser("stats", help="Knowledge base statistics")
    p_s.add_argument("root", nargs="?", default=".")
    p_s.add_argument("--json", action="store_true")

    # export
    p_e = sub.add_parser("export", help="Export OKF bundle")
    p_e.add_argument("root", nargs="?", default=".")
    p_e.add_argument("target", help="Target directory")

    # add
    p_a = sub.add_parser("add", help="Add a concept")
    p_a.add_argument("root", nargs="?", default=".")
    p_a.add_argument("--id", required=True)
    p_a.add_argument("--title", required=True)
    p_a.add_argument("--content", required=True)
    p_a.add_argument("--category", default="")
    p_a.add_argument("--tags", default="")

    args = parser.parse_args()

    if not args.cmd:
        parser.print_help()
        return

    root = Path(args.root).expanduser().resolve()
    kb = KnowledgeBase(root)

    if args.cmd == "build":
        result = kb.build_graph(k=args.k, quiet=args.quiet)
        print(f"Built: {result['nodes']} nodes, {result['edges']} edges")
        if args.verify:
            v = kb.verify()
            ok = v["graph"]["verified"]
            print(f"Verify: {'✅ PASS' if ok else '❌ FAIL'} ({v['graph']['bridges']} bridges)")

    elif args.cmd == "query":
        results = kb.query(args.text, top_k=args.top)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for i, r in enumerate(results, 1):
                print(f"#{i} [{r.get('category','')}] {r.get('title','')}  ({r['score']:.4f})")

    elif args.cmd == "relevance":
        results = kb.relevance(args.text, top_n=args.top)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for r in results:
                print(f"MBC: {r['mbc']:.4f} — {r['query'][:60]}")
                for n in r.get("neighbors", []):
                    print(f"  └─ {n[0]} ({n[1]:.2f})")

    elif args.cmd == "verify":
        v = kb.verify()
        g = v["graph"]
        print(f"Nodes: {g['nodes']}  Edges: {g['edges']}")
        print(f"Connected: {'✅' if g['connected'] else '❌'}")
        print(f"Bridges: {g['bridges']}")
        print(f"Min/Max/Avg degree: {g['min_degree']}/{g['max_degree']}/{g['avg_degree']:.2f}")
        print(f"Result: {'✅ ALL CHECKS PASSED' if g['verified'] else '❌ FAILED'}")

    elif args.cmd == "stats":
        s = kb.stats()
        if args.json:
            print(json.dumps(s, ensure_ascii=False, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")

    elif args.cmd == "export":
        result = kb.export_okf(args.target)
        print(f"Exported {result['exported']} files to {result['target']}")

    elif args.cmd == "add":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []
        result = kb.add_concept(args.id, args.title, args.content, args.category, tags)
        print(f"Added: {result['id']} → {result['path']}")


if __name__ == "__main__":
    main()
