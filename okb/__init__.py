"""
OKB — Open Knowledge Base for AI Agents
========================================

A unified knowledge management system combining three layers:

  Vector Layer  — Semantic search & retrieval (ChromaDB + SiliconFlow)
  Graph Layer   — Structural knowledge graph (NetworkX, 2-edge-connected)
  OKF Layer     — Open Knowledge Format compliance (okf.md standard)

Usage::

    from okb import KnowledgeBase
    kb = KnowledgeBase("~/my-knowledge-base")

    kb.query("聚变能源 安全 事故")
    kb.graph().verify()
    kb.relevance("新的创作条目描述")
    kb.export_okf("./okf-bundle/")

OKF Bundle structure::

    <root>/
    ├── okf.yaml              # Bundle manifest
    └── concepts/              # Concept files (one per concept)

Architecture::

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
"""

from .vector import VectorStore
from .graph import GraphStore
from .okf import OKFManifest
from .core import KnowledgeBase

__version__ = "1.0.0"
__all__ = ["KnowledgeBase", "VectorStore", "GraphStore", "OKFManifest"]
