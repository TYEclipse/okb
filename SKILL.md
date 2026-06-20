---
name: open-knowledge-base
slug: open-knowledge-base
displayName: OKB — Open Knowledge Base
description: "Unified knowledge management for AI agents: ChromaDB vector search + NetworkX 2-edge-connected graph + OKF v1.0 compliance."
category: software-development
tags: [knowledge-graph, vector-search, ai-agent, okf, chromadb, networkx]
version: "1.0.0"
homepage: https://github.com/TYEclipse/okb
links:
  docs: https://github.com/TYEclipse/okb
  source: https://github.com/TYEclipse/okb
---

# OKB — Open Knowledge Base for AI Agents

> Vector + Graph + OKF — three layers, one API.

## Quickstart

```bash
# Install
pip install chromadb networkx pyyaml requests

# Clone
git clone https://github.com/TYEclipse/okb.git
cd okb

# Use
python3 -m okb.cli stats .
python3 -m okb.cli query . "your search query"
python3 -m okb.cli build . --k 3 --verify
```

```python
from okb import KnowledgeBase

kb = KnowledgeBase("~/my-knowledge-base")
kb.query("semantic search query")
kb.relevance("candidate concept description")
kb.stats()  # {'graph_nodes': N, 'graph_edges': M, 'graph_verified': True}
```

## Architecture

```
KnowledgeBase
  ├── .vector()  → VectorStore  (ChromaDB — semantic search & rerank)
  ├── .graph()   → GraphStore   (NetworkX — 2-edge-connected knowledge graph)
  └── .okf()     → OKFManifest  (YAML — OKF v1.0 compliance)
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `build` | Build 2-edge-connected graph from all indexed concepts |
| `query` | Semantic search with optional reranking |
| `relevance` | Marginal betweenness centrality for candidate concepts |
| `verify` | Self-check: connectivity, bridges, degree distribution |
| `stats` | Aggregate statistics across all layers |
| `export` | Export OKF-compliant bundle |
| `add` | Add a concept (index + graph node + OKF manifest) |

## OKF Bundle Structure

```
<root>/
├── okf.yaml           # Bundle manifest
└── concepts/           # One .md per concept
    ├── category-a/
    │   └── concept-1.md
    └── category-b/
        └── concept-2.md
```

## Requirements

- Python 3.10+
- `chromadb`, `networkx`, `pyyaml`, `requests`
- Embedding API (SiliconFlow or compatible OpenAI-format endpoint)
- Set `SILICONFLOW_API_KEY` environment variable (or pass via constructor)

## License

MIT

## References

- `references/privacy-audit.md` — Checklist for sanitizing secrets/PII before open-sourcing a knowledge base
