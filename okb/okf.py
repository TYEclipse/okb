"""
OKB OKF Layer — Open Knowledge Format compliance.

Implements Google's OKF v0.1 standard for AI-agent-readable knowledge bundles.

Spec: https://okf.md/

OKF Bundle structure::

    <root>/
    ├── okf.yaml              # Bundle manifest
    └── concepts/              # Concept files (one per concept)
        ├── category-a/
        │   └── concept-1.md
        └── category-b/
            └── concept-2.md

Each concept file::

    ---
    okf: "1.0"
    id: "concept-1"
    title: "Concept Title"
    category: "category-a"
    tags: [tag1, tag2]
    created: "2026-06-20"
    ---
    # Concept Title

    Concept content in markdown...
"""

from __future__ import annotations

import os
import shutil
import yaml
from datetime import datetime
from pathlib import Path


class OKFManifest:
    """OKF bundle manifest and concept file manager."""

    def __init__(self, root_dir: Path):
        self.root = root_dir
        self.manifest_path = self.root / "okf.yaml"
        self.concepts_dir = self.root / "concepts"
        self.manifest: dict = self._load_manifest()

    def _load_manifest(self) -> dict:
        if self.manifest_path.exists():
            with open(self.manifest_path) as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}
        data.setdefault("okf", "1.0")
        data.setdefault("name", self.root.name)
        if data.get("concepts") is None:
            data["concepts"] = {}
        return data

    def _save_manifest(self):
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, "w") as f:
            yaml.dump(self.manifest, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # ── Concept File I/O ──────────────────────────────────

    def write_concept(self, oid: str, title: str, content: str,
                      category: str = "", tags: list[str] | None = None) -> Path:
        """Write an OKF-compliant concept markdown file."""
        cat_dir = self.concepts_dir / (category or "general")
        cat_dir.mkdir(parents=True, exist_ok=True)

        safe_name = oid.replace("/", "-").replace(" ", "-")[:64]
        filepath = cat_dir / f"{safe_name}.md"

        frontmatter = {
            "okf": "1.0",
            "id": oid,
            "title": title,
            "category": category or "general",
            "tags": tags or [],
            "created": datetime.now().strftime("%Y-%m-%d"),
        }

        yaml_str = yaml.dump(frontmatter, default_flow_style=False,
                             allow_unicode=True, sort_keys=False).strip()

        body = f"---\n{yaml_str}\n---\n\n# {title}\n\n{content}\n"
        filepath.write_text(body, encoding="utf-8")
        return filepath

    def read_concept(self, oid: str) -> dict | None:
        """Read a concept file and return parsed frontmatter + content."""
        info = self.manifest.get("concepts", {}).get(oid, {})
        filepath = info.get("path", "")
        if not filepath:
            return None
        full_path = self.root / filepath
        if not full_path.exists():
            return None
        text = full_path.read_text(encoding="utf-8")
        return self._parse_concept_file(text)

    def _parse_concept_file(self, text: str) -> dict:
        """Parse YAML frontmatter + markdown body."""
        if not text.startswith("---"):
            return {"content": text}
        parts = text.split("---", 2)
        if len(parts) < 3:
            return {"content": text}
        try:
            fm = yaml.safe_load(parts[1])
        except yaml.YAMLError:
            fm = {}
        if not isinstance(fm, dict):
            fm = {}
        return {"frontmatter": fm, "content": parts[2].strip()}

    def update_concept(self, oid: str, new_content: str) -> bool:
        """Update a concept's content (preserves frontmatter)."""
        info = self.manifest.get("concepts", {}).get(oid, {})
        filepath = info.get("path", "")
        if not filepath:
            return False
        full_path = self.root / filepath
        if not full_path.exists():
            return False
        text = full_path.read_text(encoding="utf-8")
        parsed = self._parse_concept_file(text)
        fm = parsed.get("frontmatter", {})
        title = fm.get("title", oid)
        return self.write_concept(oid, title, new_content,
                                  fm.get("category", ""), fm.get("tags", [])) is not None

    # ── Register / Unregister ─────────────────────────────

    def register(self, oid: str, title: str, category: str = "",
                 tags: list[str] | None = None) -> dict:
        """Register a concept in the manifest."""
        if "concepts" not in self.manifest:
            self.manifest["concepts"] = {}

        cat_dir = category or "general"
        safe_name = oid.replace("/", "-").replace(" ", "-")[:64]
        rel_path = f"concepts/{cat_dir}/{safe_name}.md"

        self.manifest["concepts"][oid] = {
            "title": title,
            "category": category or "general",
            "path": rel_path,
            "tags": tags or [],
        }
        self._save_manifest()
        return self.manifest["concepts"][oid]

    def unregister(self, oid: str):
        """Remove a concept from the manifest."""
        self.manifest.get("concepts", {}).pop(oid, None)
        self._save_manifest()

    def merge(self, id1: str, id2: str, new_id: str):
        """Merge two concepts in the manifest."""
        m1 = self.manifest.get("concepts", {}).pop(id1, {})
        m2 = self.manifest.get("concepts", {}).pop(id2, {})
        self.manifest["concepts"][new_id] = {
            "title": f"{m1.get('title','')} + {m2.get('title','')}",
            "category": m1.get("category", m2.get("category", "general")),
            "tags": list(set((m1.get("tags") or []) + (m2.get("tags") or []))),
            "merged_from": [id1, id2],
        }
        self._save_manifest()

    # ── Validate ──────────────────────────────────────────

    def validate(self) -> dict:
        """Validate the OKF bundle."""
        issues = []
        if not self.manifest_path.exists():
            issues.append("okf.yaml not found")
        if not self.concepts_dir.exists():
            issues.append("concepts/ directory not found")
        if "okf" not in self.manifest:
            issues.append("okf version not specified")

        count = len(self.manifest.get("concepts", {}))
        for oid, info in self.manifest.get("concepts", {}).items():
            filepath = self.root / info.get("path", "")
            if not filepath.exists():
                issues.append(f"concept file missing: {info.get('path', oid)}")

        return {"valid": len(issues) == 0, "issues": issues, "concepts_registered": count}

    # ── Export ────────────────────────────────────────────

    def export_bundle(self, target_dir: Path) -> dict:
        """Export the full OKF bundle to a target directory."""
        target_dir.mkdir(parents=True, exist_ok=True)

        # Copy okf.yaml
        if self.manifest_path.exists():
            shutil.copy2(self.manifest_path, target_dir / "okf.yaml")

        # Copy all concept files
        count = 0
        for oid, info in self.manifest.get("concepts", {}).items():
            src = self.root / info.get("path", "")
            if src.exists():
                dst = target_dir / info.get("path", "")
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                count += 1

        return {"exported": count, "target": str(target_dir), "manifest_copied": self.manifest_path.exists()}

    # ── Stats ─────────────────────────────────────────────

    def stats(self) -> dict:
        concepts = self.manifest.get("concepts", {})
        files_exist = 0
        for info in concepts.values():
            if (self.root / info.get("path", "")).exists():
                files_exist += 1
        categories = {}
        for info in concepts.values():
            cat = info.get("category", "general")
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "concepts": len(concepts),
            "files": files_exist,
            "categories": categories,
            "okf_version": self.manifest.get("okf", "unknown"),
        }
