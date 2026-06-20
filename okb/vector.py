"""
OKB Vector Layer — Semantic search via ChromaDB + SiliconFlow embeddings.

Encapsulates the vector operations from queue_db.py as a reusable store.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

import chromadb
import requests
from chromadb.config import Settings


class VectorStore:
    """ChromaDB-backed vector store with embedding + reranking."""

    def __init__(self, chroma_dir: str, api_key: str,
                 embed_model: str = "Qwen/Qwen3-Embedding-0.6B",
                 rerank_model: str = "Qwen/Qwen3-Reranker-0.6B",
                 api_base: str = "https://api.siliconflow.cn/v1"):
        self.chroma_dir = chroma_dir
        self.api_key = api_key
        self.embed_model = embed_model
        self.rerank_model = rerank_model
        self.api_base = api_base
        self._client: chromadb.PersistentClient | None = None

    @property
    def client(self) -> chromadb.PersistentClient:
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=self.chroma_dir,
                settings=Settings(anonymized_telemetry=False),
            )
        return self._client

    def _embed(self, texts: list[str]) -> list[list[float]]:
        resp = requests.post(
            f"{self.api_base}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.embed_model, "input": texts},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return [d["embedding"] for d in sorted(data["data"], key=lambda x: x["index"])]

    def _rerank(self, query: str, docs: list[str], top_n: int = 10) -> list[tuple[int, float]]:
        resp = requests.post(
            f"{self.api_base}/rerank",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.rerank_model, "query": query, "documents": docs, "top_n": top_n},
            timeout=30,
        )
        resp.raise_for_status()
        return [(r["index"], r["relevance_score"]) for r in resp.json()["results"]]

    # ── Collections ───────────────────────────────────────

    def concepts(self):
        return self.client.get_or_create_collection(
            name="content_index", metadata={"hnsw:space": "cosine"})

    def queue(self):
        return self.client.get_or_create_collection(
            name="queue_entries", metadata={"hnsw:space": "cosine"})

    # ── Concept CRUD ──────────────────────────────────────

    def index_concept(self, oid: str, title: str, content: str,
                      category: str = "", path: str = "") -> str:
        """Index a concept. Returns the doc_id."""
        col = self.concepts()
        doc_id = hashlib.md5(oid.encode()).hexdigest()[:16]

        # Remove old if exists
        try:
            col.delete(ids=[doc_id])
        except Exception:
            pass

        composite = f"[{category}] {title}: {content[:500]}"
        emb = self._embed([composite])
        col.add(
            ids=[doc_id],
            documents=[composite],
            embeddings=emb,
            metadatas=[{"oid": oid, "title": title, "category": category, "path": path}],
        )
        return doc_id

    def reindex(self, oid: str, new_content: str) -> None:
        """Re-index after content modification."""
        col = self.concepts()
        doc_id = hashlib.md5(oid.encode()).hexdigest()[:16]
        try:
            results = col.get(ids=[doc_id])
            if results["metadatas"]:
                meta = results["metadatas"][0]
                composite = f"[{meta.get('category','')}] {meta.get('title','')}: {new_content[:500]}"
                emb = self._embed([composite])
                col.update(ids=[doc_id], documents=[composite], embeddings=emb)
        except Exception:
            pass

    def remove(self, oid: str) -> None:
        doc_id = hashlib.md5(oid.encode()).hexdigest()[:16]
        try:
            self.concepts().delete(ids=[doc_id])
        except Exception:
            pass

    def merge(self, id1: str, id2: str, new_id: str) -> None:
        self.remove(id1)
        self.remove(id2)

    # ── Search ───────────────────────────────────────────

    def search(self, query: str, top_k: int = 10, use_rerank: bool = True) -> list[dict]:
        """Two-stage semantic search: embed → rerank."""
        col = self.concepts()
        if col.count() == 0:
            return []

        q_emb = self._embed([query])
        n_retrieve = min(50, col.count())
        results = col.query(query_embeddings=q_emb, n_results=n_retrieve)

        if not results["ids"] or not results["ids"][0]:
            return []

        ids = results["ids"][0]
        docs = results["documents"][0]
        metas = results["metadatas"][0]

        if use_rerank and n_retrieve > top_k:
            ranked = self._rerank(query, docs, top_n=top_k)
            out = []
            for idx, score in ranked:
                m = metas[idx]
                out.append({"oid": m.get("oid", ids[idx]), "title": m.get("title", ""),
                           "category": m.get("category", ""), "score": score})
            return out
        else:
            distances = results.get("distances", [[]])[0]
            out = []
            for i in range(min(top_k, len(ids))):
                m = metas[i]
                out.append({"oid": m.get("oid", ids[i]), "title": m.get("title", ""),
                           "category": m.get("category", ""),
                           "score": 1.0 - min(distances[i], 1.0)})
            return out

    # ── Queue Management ─────────────────────────────────

    def queue_add(self, desc: str, category: str, op: str = "增加",
                  target: str = "", refs: str = "") -> str:
        col = self.queue()
        qid = hashlib.md5(desc.encode()).hexdigest()[:16]
        emb = self._embed([desc])
        col.upsert(
            ids=[qid],
            documents=[desc],
            embeddings=emb,
            metadatas=[{"category": category, "op": op, "target": target, "refs": refs}],
        )
        return qid

    def queue_remove(self, qid: str) -> None:
        try:
            self.queue().delete(ids=[qid])
        except Exception:
            pass

    def queue_search(self, query: str, top_k: int = 10) -> list[dict]:
        col = self.queue()
        if col.count() == 0:
            return []
        q_emb = self._embed([query])
        results = col.query(query_embeddings=q_emb, n_results=min(top_k, col.count()))
        if not results["ids"] or not results["ids"][0]:
            return []
        out = []
        for i in range(len(results["ids"][0])):
            m = results["metadatas"][0][i]
            out.append({"id": results["ids"][0][i], "desc": results["documents"][0][i],
                       "category": m.get("category", ""), "op": m.get("op", ""),
                       "target": m.get("target", "")})
        return out

    # ── Stats ────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            "concepts": self.concepts().count(),
            "queue": self.queue().count(),
        }

    def get_all_embeddings(self) -> dict[str, list[float]]:
        col = self.concepts()
        if col.count() == 0:
            return {}
        results = col.get(limit=col.count(), include=["embeddings"])
        if not results["ids"]:
            return {}
        emb_dict = {}
        emb_raw = results.get("embeddings")
        if emb_raw is not None:
            for rid, emb in zip(results["ids"], emb_raw):
                meta = results["metadatas"][results["ids"].index(rid)] if results.get("metadatas") else {}
                oid = meta.get("oid", rid) if meta else rid
                emb_dict[oid] = list(emb)
        return emb_dict

    def get_all_metadatas(self) -> dict[str, dict]:
        col = self.concepts()
        if col.count() == 0:
            return {}
        results = col.get(limit=col.count(), include=["metadatas", "documents"])
        if not results["ids"]:
            return {}
        meta = {}
        for rid, m, doc in zip(results["ids"], results["metadatas"] or [], results["documents"] or []):
            oid = m.get("oid", rid)
            meta[oid] = {"title": m.get("title", ""), "category": m.get("category", ""),
                        "path": m.get("path", ""), "preview": doc[:200] if doc else ""}
        return meta

    def get_embedding(self, oid: str) -> list[float] | None:
        doc_id = hashlib.md5(oid.encode()).hexdigest()[:16]
        col = self.concepts()
        try:
            results = col.get(ids=[doc_id], include=["embeddings"])
            if results["embeddings"] is not None and len(results["embeddings"]) > 0:
                return list(results["embeddings"][0])
        except Exception:
            pass
        return None

    def knn(self, oid: str, k: int = 3, exclude: set[str] | None = None) -> list[tuple[str, float]]:
        """Find k nearest neighbors for a given concept ID."""
        emb = self.get_embedding(oid)
        if emb is None:
            return []
        col = self.concepts()
        if col.count() == 0:
            return []
        results = col.query(query_embeddings=[emb], n_results=min(k + (len(exclude or set())), col.count()))
        if not results["ids"] or not results["ids"][0]:
            return []
        out = []
        exclude = exclude or set()
        for rid, dist in zip(results["ids"][0], results.get("distances", [[]])[0]):
            meta_idx = results["ids"][0].index(rid)
            oid_val = results["metadatas"][0][meta_idx].get("oid", rid) if results.get("metadatas") else rid
            if oid_val not in exclude:
                out.append((oid_val, dist))
            if len(out) >= k:
                break
        return out
