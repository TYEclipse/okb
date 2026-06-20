#!/usr/bin/env python3
"""OKB CLI — unified command-line interface for the Open Knowledge Base."""
import argparse, json, sys
from pathlib import Path

from okb import KnowledgeBase


def main():
    parser = argparse.ArgumentParser(description="OKB — Open Knowledge Base for AI Agents")
    sub = parser.add_subparsers(dest="cmd")

    # build
    p_build = sub.add_parser("build", help="Build 2-edge-connected graph from vector store")
    p_build.add_argument("root", nargs="?", default=".", help="Knowledge base root directory")
    p_build.add_argument("--k", type=int, default=3, help="k-NN neighbors (default: 3)")
    p_build.add_argument("--verify", action="store_true", help="Verify after build")
    p_build.add_argument("--quiet", action="store_true")

    # query
    p_q = sub.add_parser("query", help="Semantic search with reranking")
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
    p_v = sub.add_parser("verify", help="Verify knowledge base (all layers)")
    p_v.add_argument("root", nargs="?", default=".")

    # stats
    p_s = sub.add_parser("stats", help="Knowledge base statistics")
    p_s.add_argument("root", nargs="?", default=".")
    p_s.add_argument("--json", action="store_true")

    # export
    p_e = sub.add_parser("export", help="Export OKF v0.1 bundle")
    p_e.add_argument("root", nargs="?", default=".")
    p_e.add_argument("target", help="Target directory")

    # add
    p_a = sub.add_parser("add", help="Add a concept")
    p_a.add_argument("root", nargs="?", default=".")
    p_a.add_argument("--id", required=True, help="Stable concept identifier")
    p_a.add_argument("--title", required=True, help="Human-readable name")
    p_a.add_argument("--content", required=True, help="Markdown body text")
    p_a.add_argument("--type", default="Concept", dest="concept_type",
                     help="OKF v0.1 concept type (default: Concept)")
    p_a.add_argument("--category", default="", help="Domain grouping (OKB extension)")
    p_a.add_argument("--tags", default="", help="Comma-separated tags")

    # conformance (new)
    p_conf = sub.add_parser("conformance", help="Strict OKF v0.1 conformance check")
    p_conf.add_argument("root", nargs="?", default=".")
    p_conf.add_argument("--json", action="store_true")

    # generate-index (new)
    p_idx = sub.add_parser("generate-index", help="Generate OKF v0.1 index.md")
    p_idx.add_argument("root", nargs="?", default=".")
    p_idx.add_argument("--dir", default="concepts", help="Target directory (default: concepts)")

    # append-log (new)
    p_log = sub.add_parser("append-log", help="Append entry to OKF v0.1 log.md")
    p_log.add_argument("root", nargs="?", default=".")
    p_log.add_argument("entry", help="Log entry text (markdown)")
    p_log.add_argument("--dir", default=".", help="Directory relative to root (default: root)")

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
        print(f"Graph: {g['nodes']} nodes, {g['edges']} edges")
        print(f"Connected: {'✅' if g['connected'] else '❌'}")
        print(f"Bridges: {g['bridges']}")
        print(f"Min/Max/Avg degree: {g['min_degree']}/{g['max_degree']}/{g['avg_degree']:.2f}")
        print(f"Graph: {'✅ VERIFIED' if g['verified'] else '❌ FAILED'}")
        o = v["okf"]
        print(f"OKF: {o['concepts_registered']} registered, valid={o['valid']}")

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
        if result.get("index_generated"):
            print("  index.md generated")

    elif args.cmd == "add":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []
        result = kb.add_concept(args.id, args.title, args.content,
                                concept_type=getattr(args, 'concept_type', 'Concept'),
                                category=args.category, tags=tags)
        print(f"Added: {result['id']} → {result['path']}")

    elif args.cmd == "conformance":
        c = kb.okf().conformance()
        if args.json:
            del c["issues"]; del c["warnings"]  # keep summary only
            print(json.dumps(c, ensure_ascii=False, indent=2))
        else:
            print(f"OKF v{c['okf_version']} Conformance: "
                  f"{'✅ PASS' if c['conformant'] else '❌ FAIL'}")
            print(f"  Concepts: {c['valid_concepts']}/{c['total_concepts']} valid")
            for issue in c["issues"]:
                print(f"  ❌ {issue}")
            for warn in c["warnings"]:
                print(f"  ⚠️  {warn}")

    elif args.cmd == "generate-index":
        text = kb.okf().generate_index(args.dir)
        path = kb.root / args.dir / "index.md"
        print(f"Generated {path} ({len(text)} chars)")

    elif args.cmd == "append-log":
        path = kb.okf().append_log(args.entry, args.dir)
        print(f"Appended to {path}")


if __name__ == "__main__":
    main()
