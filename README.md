# OKB — Open Knowledge Base for AI Agents

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![OKF v1.0](https://img.shields.io/badge/OKF-v1.0-green)](https://okf.md/)

> **Vector + Graph + OKF** — a unified knowledge management system for AI agents.

OKB combines three layers into one Python API:

- 🧠 **Vector Layer** — ChromaDB semantic search with SiliconFlow embedding + reranking
- 🔗 **Graph Layer** — NetworkX 2-edge-connected knowledge graph with marginal centrality
- 📋 **OKF Layer** — [Open Knowledge Format](https://okf.md/) v1.0 compliance (YAML manifest + concept files)

## Why OKB?

Most knowledge bases are either pure vector stores (fast search, no structure) or pure graphs (rich structure, no semantic search). OKB gives you both — plus OKF compliance for interoperability between AI agents.

| Feature | ChromaDB alone | NetworkX alone | **OKB** |
|---------|:---:|:---:|:---:|
| Semantic search | ✅ | ❌ | ✅ |
| Reranking | ✅ | ❌ | ✅ |
| Graph structure | ❌ | ✅ | ✅ |
| 2-edge-connectivity guarantee | ❌ | ❌ | ✅ |
| Marginal centrality ranking | ❌ | ❌ | ✅ |
| OKF export | ❌ | ❌ | ✅ |
| CRUD across all layers | ❌ | ❌ | ✅ |

## Quickstart

```bash
pip install chromadb networkx pyyaml requests
export SILICONFLOW_API_KEY="sk-..."
```

```python
from okb import KnowledgeBase

kb = KnowledgeBase("~/my-digital-garden")

# Add concepts
kb.add_concept("grav-tax", "Gravity Tax", "A progressive tax based on...", category="economics")

# Search
results = kb.query("taxation in space colonies")  # reranked top-10

# Build graph
kb.build_graph(k=3)  # 2-edge-connected, 0 bridges

# Rank candidates by marginal centrality
kb.relevance("Martian water rights dispute")

# Export as OKF bundle
kb.export_okf("./okf-export/")
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│                KnowledgeBase                     │
│  .query() .graph() .relevance() .verify()       │
│  .add_concept() .remove_concept() .merge()      │
│  .export_okf()                                  │
└────────┬────────────┬──────────────┬────────────┘
         │            │              │
┌────────▼────┐ ┌─────▼──────┐ ┌─────▼──────┐
│  VectorStore│ │  GraphStore│ │  OKFManifest│
│  (ChromaDB) │ │  (NetworkX)│ │  (YAML)     │
└─────────────┘ └────────────┘ └────────────┘
```

## CLI

```bash
# Semantic search
python3 -m okb.cli query . "聚变能源 安全" --top 5

# Marginal centrality
python3 -m okb.cli relevance . "木卫二冰下海洋生命探测"

# Build & verify
python3 -m okb.cli build . --k 3 --verify

# Stats
python3 -m okb.cli stats . --json

# Export OKF bundle
python3 -m okb.cli export . ./okf-export/
```

## Graph Guarantees

The `build()` algorithm ensures:

1. **2-edge-connected** — every node has at least 2 disjoint paths to the rest of the graph (no bridges)
2. **Min degree ≥ 2** — every node is in at least one cycle
3. **Incremental** — nodes can be added one at a time without full rebuild

Bridges are detected and repaired automatically using semantic nearest-neighbor edge addition.

## OKF Compliance

OKB follows the [Open Knowledge Format v1.0](https://okf.md/) spec:

```
<root>/
├── okf.yaml              # Bundle manifest (name, version, concept index)
└── concepts/              # One .md file per concept with YAML frontmatter
    ├── astronomy/
    │   └── mars-colonies.md
    └── economics/
        └── gravity-tax.md
```

Each concept file uses YAML frontmatter:

```markdown
---
okf: "1.0"
id: "grav-tax"
title: "Gravity Tax"
category: "economics"
tags: [taxation, space-law]
created: "2026-06-20"
---
# Gravity Tax

A progressive tax based on...
```

## Requirements

- Python 3.10+
- `chromadb`, `networkx`, `pyyaml`, `requests`
- Embedding API key (SiliconFlow or any OpenAI-compatible endpoint)
- Set `SILICONFLOW_API_KEY` (or pass `embed_api_key` to constructor)

## License

MIT © 2026 [TYEclipse](https://github.com/TYEclipse)
