"""
OKB Core — Unified Knowledge Base API
======================================

Usage::

    from okb import KnowledgeBase
    kb = KnowledgeBase("~/my-knowledge-base")

    # Query
    results = kb.query("聚变能源 安全 事故", top_k=5)

    # Graph
    print(kb.graph().stats())
    kb.graph().verify()

    # Marginal centrality
    ranked = kb.relevance("新的创作条目描述", top_n=10)

    # CRUD
    kb.add_concept(id, title, content, category)
    kb.remove_concept(id)
    kb.merge_concepts(id1, id2)

    # OKF Export
    kb.export_okf("./okf-bundle/")
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from .vector import VectorStore
from .graph import GraphStore
from .okf import OKFManifest

_OKB_VERSION = "1.0.0"

# ═══════════════════════════════════════════════════════════════
# Knowledge Base
# ═══════════════════════════════════════════════════════════════

class KnowledgeBase:
    """Unified knowledge base backed by Vector + Graph + OKF layers."""

    def __init__(self, root_dir: str | Path, embed_api_key: str = ""):
        self.root = Path(root_dir).expanduser().resolve()
        self.concepts_dir = self.root / "concepts"
        self.concepts_dir.mkdir(parents=True, exist_ok=True)

        self._vector: VectorStore | None = None
        self._graph: GraphStore | None = None
        self._okf: OKFManifest | None = None
        self._embed_key = embed_api_key or os.environ.get("SILICONFLOW_API_KEY", "")

    # ── Layer Access ──────────────────────────────────────

    def vector(self) -> VectorStore:
        if self._vector is None:
            # Use existing .chroma if present, otherwise .okb/chroma
            chroma_path = self.root / ".chroma"
            if not chroma_path.exists():
                chroma_path = self.root / ".okb" / "chroma"
            self._vector = VectorStore(
                chroma_dir=str(chroma_path),
                api_key=self._embed_key,
            )
        return self._vector

    def graph(self) -> GraphStore:
        if self._graph is None:
            # Use existing graph.json if present, otherwise .okb/graph.json
            graph_path = self.root / "graph.json"
            if not graph_path.exists():
                graph_path = self.root / ".okb" / "graph.json"
            self._graph = GraphStore(
                graph_path=str(graph_path),
                vector=self.vector(),
            )
        return self._graph

    def okf(self) -> OKFManifest:
        if self._okf is None:
            self._okf = OKFManifest(self.root)
        return self._okf

    # ── Query ─────────────────────────────────────────────

    def query(self, text: str, top_k: int = 10, use_rerank: bool = True) -> list[dict]:
        """Semantic search over all indexed concepts."""
        return self.vector().search(text, top_k=top_k, use_rerank=use_rerank)

    def relevance(self, text: str, top_n: int = 10) -> list[dict]:
        """Marginal centrality ranking for a candidate concept."""
        return self.graph().marginal_centrality(text, top_n=top_n)

    # ── CRUD ──────────────────────────────────────────────

    def add_concept(self, oid: str, title: str, content: str,
                    concept_type: str = "Concept",
                    category: str = "", tags: list[str] | None = None) -> dict:
        """
        Add a new concept to the knowledge base.

        Steps:
          1. Write OKF v0.1 compliant markdown file
          2. Index in vector store
          3. Add node to graph + maintain 2-edge-connectivity
          4. Update OKF manifest

        Args:
            oid: Stable concept identifier
            title: Human-readable name
            content: Markdown body
            concept_type: OKF v0.1 REQUIRED — asset/concept kind
            category: OKB extension — domain grouping
            tags: Cross-classification tags
        """
        # 1. OKF file
        filepath = self.okf().write_concept(oid, title, content,
                                            concept_type=concept_type,
                                            category=category, tags=tags)
        filepath_str = str(filepath.relative_to(self.root))

        # 2. Vector index
        doc_id = self.vector().index_concept(
            oid=oid,
            title=title,
            content=content,
            category=category if category else concept_type,
            path=filepath_str,
        )

        # 3. Graph
        self.graph().add_node(oid, title=title, content=content,
                              category=category if category else concept_type)

        # 4. Manifest
        self.okf().register(oid, title, concept_type=concept_type,
                            category=category, tags=tags)

        return {"id": oid, "doc_id": doc_id, "path": filepath_str}

    def remove_concept(self, oid: str) -> bool:
        """Remove a concept from all layers."""
        ok = True
        try:
            self.okf().unregister(oid)
        except Exception:
            ok = False
        try:
            self.vector().remove(oid)
        except Exception:
            ok = False
        try:
            self.graph().remove_node(oid)
        except Exception:
            ok = False
        return ok

    def merge_concepts(self, id1: str, id2: str) -> str:
        """Merge two concepts. Returns the new merged ID."""
        new_id = self.graph().merge_nodes(id1, id2)
        if new_id:
            self.vector().merge(id1, id2, new_id)
            self.okf().merge(id1, id2, new_id)
        return new_id

    def modify_concept(self, oid: str, new_content: str) -> dict:
        """Update a concept's content; re-index."""
        self.okf().update_concept(oid, new_content)
        self.vector().reindex(oid, new_content)
        self.graph().update_node_embedding(oid, new_content)
        return {"id": oid}

    # ── Build & Verify ───────────────────────────────────

    def build_graph(self, k: int = 3, quiet: bool = False) -> dict:
        """Build the full 2-edge-connected graph from all indexed concepts."""
        return self.graph().build(k=k, quiet=quiet)

    def verify(self) -> dict:
        """Self-check all layers."""
        return {
            "vector": self.vector().stats(),
            "graph": self.graph().verify(),
            "okf": self.okf().validate(),
        }

    # ── Export ────────────────────────────────────────────

    def export_okf(self, target_dir: str | Path) -> dict:
        """Export the knowledge base as an OKF-compliant bundle."""
        return self.okf().export_bundle(Path(target_dir))

    def stats(self) -> dict:
        """Aggregate statistics across all layers."""
        gs = self.graph().stats()
        vs = self.vector().stats()
        oks = self.okf().stats()
        return {
            "name": self.okf().manifest.get("name", self.root.name),
            "version": _OKB_VERSION,
            "concepts": oks.get("concepts", 0),
            "files": oks.get("files", 0),
            "vector_indexed": vs.get("concepts", 0),
            "graph_nodes": gs.get("nodes", 0),
            "graph_edges": gs.get("edges", 0),
            "graph_verified": gs.get("verified", False),
        }
