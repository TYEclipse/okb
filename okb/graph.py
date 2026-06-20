"""
OKB Graph Layer — 2-edge-connected knowledge graph.

Encapsulates the graph operations from graph_db.py as a reusable store.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from collections import defaultdict
from typing import TYPE_CHECKING

import networkx as nx

if TYPE_CHECKING:
    from .vector import VectorStore


class GraphStore:
    """NetworkX-backed graph store with incremental 2-edge-connectivity."""

    def __init__(self, graph_path: str, vector: "VectorStore | None" = None):
        self.graph_path = graph_path
        self._vector = vector
        self._G: nx.Graph | None = None
        self._node_meta: dict[str, dict] = {}

    @property
    def G(self) -> nx.Graph:
        if self._G is None:
            self._load()
        return self._G

    def _load(self):
        if os.path.exists(self.graph_path):
            with open(self.graph_path) as f:
                data = json.load(f)
            self._G = nx.node_link_graph(data)
        else:
            self._G = nx.Graph()

    def save(self):
        os.makedirs(os.path.dirname(self.graph_path), exist_ok=True)
        data = nx.node_link_data(self.G)
        with open(self.graph_path, "w") as f:
            json.dump(data, f, ensure_ascii=False)

    # ── Distance ─────────────────────────────────────────

    @staticmethod
    def cosine_distance(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        if na == 0 or nb == 0:
            return 1.0
        return 1.0 - dot / (na * nb)

    # ── Node CRUD ────────────────────────────────────────

    def add_node(self, oid: str, title: str = "", content: str = "", category: str = ""):
        if oid in self.G:
            return
        self.G.add_node(oid)
        self._node_meta[oid] = {"title": title, "category": category}

        if len(self.G) == 1:
            self.save()
            return

        # k-NN connect
        if self._vector:
            emb = self._vector.get_embedding(oid)
            if emb:
                existing = [n for n in self.G.nodes() if n != oid]
                all_embs = {eid: self._vector.get_embedding(eid) for eid in existing}
                all_embs = {k: v for k, v in all_embs.items() if v is not None}

                # Find 3 nearest neighbors
                neighbors = []
                for eid, eemb in all_embs.items():
                    d = self.cosine_distance(emb, eemb)
                    neighbors.append((eid, d))
                neighbors.sort(key=lambda x: x[1])

                for nid, dist in neighbors[:3]:
                    self.G.add_edge(oid, nid, weight=dist)

        # Ensure degree ≥ 2
        if self.G.degree(oid) < 2 and self._vector:
            emb = self._vector.get_embedding(oid)
            if emb:
                existing = [n for n in self.G.nodes() if n != oid and not self.G.has_edge(oid, n)]
                all_embs = {eid: self._vector.get_embedding(eid) for eid in existing}
                all_embs = {k: v for k, v in all_embs.items() if v is not None}
                neighbors = []
                for eid, eemb in all_embs.items():
                    neighbors.append((eid, self.cosine_distance(emb, eemb)))
                neighbors.sort(key=lambda x: x[1])
                for nid, dist in neighbors:
                    self.G.add_edge(oid, nid, weight=dist)
                    if self.G.degree(oid) >= 2:
                        break

        # Bridge repair
        self._fix_bridges()

        self.save()

    def remove_node(self, oid: str):
        if oid not in self.G:
            return
        neighbors = list(self.G.neighbors(oid))
        self.G.remove_node(oid)
        self._node_meta.pop(oid, None)

        # Repair orphaned nodes
        if self._vector:
            for n in neighbors:
                if n not in self.G:
                    continue
                if self.G.degree(n) < 2:
                    en = self._vector.get_embedding(n)
                    if en is None:
                        continue
                    existing = [x for x in self.G.nodes() if x != n and not self.G.has_edge(n, x)]
                    candidates = []
                    for x in existing:
                        ex = self._vector.get_embedding(x)
                        if ex is not None:
                            candidates.append((x, self.cosine_distance(en, ex)))
                    candidates.sort(key=lambda x: x[1])
                    for cid, dist in candidates:
                        self.G.add_edge(n, cid, weight=dist)
                        if self.G.degree(n) >= 2:
                            break

        self._fix_bridges()
        self.save()

    def merge_nodes(self, id1: str, id2: str) -> str:
        if id1 not in self.G or id2 not in self.G:
            return ""

        new_id = f"merged_{id1[:8]}_{id2[:8]}"
        m1 = self._node_meta.get(id1, {})
        m2 = self._node_meta.get(id2, {})

        all_neighbors = set()
        for n in list(self.G.neighbors(id1)) + list(self.G.neighbors(id2)):
            if n not in (id1, id2):
                all_neighbors.add(n)

        self.G.remove_node(id1)
        self.G.remove_node(id2)
        self._node_meta.pop(id1, None)
        self._node_meta.pop(id2, None)

        self.G.add_node(new_id)
        self._node_meta[new_id] = {"title": f"{m1.get('title','')} + {m2.get('title','')}",
                                   "category": m1.get("category", m2.get("category", ""))}

        for n in all_neighbors:
            if n in self.G:
                self.G.add_edge(new_id, n,
                    weight=self.G.get_edge_data(id1, n, {}).get("weight", 0.5) if id1 in self.G else 0.5)

        self._fix_bridges()
        self.save()
        return new_id

    def update_node_embedding(self, oid: str, new_content: str):
        """Placeholder for embedding update — actual re-embedding is vector layer's job."""
        pass

    # ── Build ────────────────────────────────────────────

    def build(self, k: int = 3, quiet: bool = False) -> dict:
        """Rebuild the full 2-edge-connected graph from vector store."""
        if self._vector is None:
            return {"error": "No vector store attached"}

        self._G = nx.Graph()
        self._node_meta = {}

        embs = self._vector.get_all_embeddings()
        metas = self._vector.get_all_metadatas()
        order = list(embs.keys())

        bridges_fixed = 0
        for idx, oid in enumerate(order):
            if oid not in embs:
                continue
            self._G.add_node(oid)
            self._node_meta[oid] = metas.get(oid, {})

            if len(self._G) == 1:
                if not quiet and (idx + 1) % 50 == 0:
                    print(f"  [{idx+1}/{len(order)}]", end=" ", flush=True)
                continue

            # k-NN
            emb = embs[oid]
            existing = [n for n in self.G.nodes() if n != oid]
            neighbors = []
            for eid in existing:
                if eid in embs:
                    neighbors.append((eid, self.cosine_distance(emb, embs[eid])))
            neighbors.sort(key=lambda x: x[1])
            for nid, dist in neighbors[:k]:
                self._G.add_edge(oid, nid, weight=dist)

            # Ensure degree ≥ 2
            if self.G.degree(oid) < 2 and len(neighbors) > k:
                for nid, dist in neighbors[k:]:
                    self._G.add_edge(oid, nid, weight=dist)
                    if self.G.degree(oid) >= 2:
                        break

            # Bridge fix
            bridges_fixed += self._fix_bridges()

            if not quiet and (idx + 1) % 50 == 0:
                print(f"  [{idx+1}/{len(order)}]", end=" ", flush=True)
            if not quiet:
                print(".", end="", flush=True)

        if not quiet:
            print(f"\n  {len(self.G)} nodes, {len(self.G.edges)} edges, {bridges_fixed} bridges fixed")

        self.save()
        return {"nodes": len(self.G), "edges": len(self.G.edges), "bridges_fixed": bridges_fixed}

    # ── Bridge Repair ───────────────────────────────────

    def _fix_bridges(self) -> int:
        """Fix all bridges in the graph. Returns number of bridges fixed."""
        bridges = list(nx.bridges(self.G))
        iterations = 0
        fixed = 0

        while bridges and iterations < 100:
            iterations += 1
            u, v = bridges[0]

            Gt = self.G.copy()
            Gt.remove_edge(u, v)
            cu = set(nx.node_connected_component(Gt, u))
            cv = set(self.G.nodes()) - cu

            if self._vector:
                best = None
                best_w = float('inf')
                for a in cu:
                    ea = self._vector.get_embedding(a)
                    if ea is None:
                        continue
                    for b in cv:
                        if self.G.has_edge(a, b):
                            continue
                        eb = self._vector.get_embedding(b)
                        if eb is None:
                            continue
                        w = self.cosine_distance(ea, eb)
                        if w < best_w:
                            best_w = w
                            best = (a, b, w)
                if best:
                    self.G.add_edge(best[0], best[1], weight=best[2])
                    fixed += 1

            bridges = list(nx.bridges(self.G))

        return fixed

    # ── Marginal Centrality ─────────────────────────────

    def marginal_centrality(self, query_text: str, top_n: int = 10) -> list[dict]:
        """Rank candidates by marginal betweenness centrality."""
        if self._vector is None:
            return []

        # Embed query
        try:
            q_emb = self._vector._embed([query_text])[0]
        except Exception:
            return []

        # Find k-NN in existing graph
        existing = list(self.G.nodes())
        all_embs = {}
        for nid in existing:
            e = self._vector.get_embedding(nid)
            if e is not None:
                all_embs[nid] = e

        neighbors = []
        for nid, nemb in all_embs.items():
            neighbors.append((nid, self.cosine_distance(q_emb, nemb)))
        neighbors.sort(key=lambda x: x[1])
        top_knn = neighbors[:3]

        # Build augmented graph with candidate
        G_test = self.G.copy()
        candidate_id = "candidate"
        G_test.add_node(candidate_id)
        for nid, dist in top_knn:
            G_test.add_edge(candidate_id, nid, weight=dist)

        # Betweenness centrality
        try:
            bc = nx.betweenness_centrality(G_test, weight="weight", normalized=True)
            mbc = bc.get(candidate_id, 0.0)
        except Exception:
            mbc = 0.0

        return [{
            "query": query_text,
            "mbc": round(mbc, 6),
            "neighbors": [(n, round(d, 4)) for n, d in top_knn],
        }]

    # ── Verify & Stats ──────────────────────────────────

    def verify(self) -> dict:
        result = {
            "nodes": len(self.G), "edges": len(self.G.edges),
            "connected": False, "bridges": 0, "min_degree": 0,
            "max_degree": 0, "avg_degree": 0.0, "isolated": [],
            "degree_1_nodes": [], "verified": False,
        }
        if len(self.G) == 0:
            return result
        result["connected"] = nx.is_connected(self.G)
        degrees = [d for _, d in self.G.degree()]
        result["min_degree"] = min(degrees) if degrees else 0
        result["max_degree"] = max(degrees) if degrees else 0
        result["avg_degree"] = sum(degrees) / len(degrees) if degrees else 0.0
        result["isolated"] = [n for n, d in self.G.degree() if d == 0]
        result["degree_1_nodes"] = [n for n, d in self.G.degree() if d == 1]
        try:
            result["bridges"] = len(list(nx.bridges(self.G)))
        except Exception:
            result["bridges"] = -1
        result["verified"] = (result["connected"] and result["bridges"] == 0
                              and len(result["isolated"]) == 0
                              and result["min_degree"] >= 2)
        return result

    def stats(self) -> dict:
        return self.verify()
