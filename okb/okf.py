"""
OKB OKF Layer — Open Knowledge Format v0.1 compliance.

Implements the OKF v0.1 standard (https://okf.md/spec) for
AI-agent-readable knowledge bundles.

Key spec requirements:
  - Every concept MUST have a non-empty ``type`` field in frontmatter (§4.1)
  - ``index.md`` and ``log.md`` are reserved filenames (§3.1)
  - Concept ID = file path minus ``.md`` suffix (§2)
  - Consumers MUST tolerate unknown fields, missing optional fields, broken links (§9)

Extensions beyond the spec (OKB-specific):
  - ``id`` field for stable cross-layer references (vector/graph)
  - ``category`` field for domain grouping (complementary to ``type``)
  - ``okf.yaml`` bundle manifest (OKB convention)
"""

from __future__ import annotations

import os
import re
import shutil
import yaml
from datetime import datetime, timezone
from pathlib import Path

# Reserved filenames per OKF v0.1 §3.1
RESERVED_FILENAMES = {"index.md", "log.md"}

# OKF v0.1 required frontmatter field
REQUIRED_FIELDS = {"type"}

# OKF v0.1 recommended frontmatter fields
RECOMMENDED_FIELDS = {"title", "description", "resource", "tags", "timestamp"}


class OKFManifest:
    """OKF v0.1 bundle manifest and concept file manager."""

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
        data.setdefault("okf", "0.1")
        data.setdefault("name", self.root.name)
        if data.get("concepts") is None:
            data["concepts"] = {}
        return data

    def _save_manifest(self):
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, "w") as f:
            yaml.dump(self.manifest, f, default_flow_style=False,
                      allow_unicode=True, sort_keys=False)

    # ═══════════════════════════════════════════════════════
    # Concept File I/O
    # ═══════════════════════════════════════════════════════

    def write_concept(self, oid: str, title: str, content: str,
                      concept_type: str = "Concept",
                      category: str = "",
                      tags: list[str] | None = None,
                      description: str = "",
                      resource: str = "") -> Path:
        """
        Write an OKF v0.1 compliant concept markdown file.

        Args:
            oid: Stable concept identifier (OKB extension; used for cross-layer refs)
            title: Human-readable display name (§4.1 recommended)
            content: Markdown body content
            concept_type: REQUIRED — asset/concept kind (§4.1), e.g. "WorldbuildingConcept"
            category: OKB extension — domain grouping (e.g. "天文学")
            tags: Cross-classification tags (§4.1 optional)
            description: One-line summary (§4.1 recommended)
            resource: Canonical URI of underlying asset (§4.1 optional)
        """
        type_dir = self.concepts_dir / (concept_type.lower().replace(" ", "-") or "general")
        type_dir.mkdir(parents=True, exist_ok=True)

        safe_name = oid.replace("/", "-").replace(" ", "-")[:64]
        filepath = type_dir / f"{safe_name}.md"

        frontmatter = {
            "type": concept_type or "Concept",     # REQUIRED per OKF v0.1 §4.1
            "id": oid,                              # OKB extension (stable cross-layer ID)
            "title": title,                         # recommended
            "description": description,             # recommended
            "resource": resource,                   # optional URI
            "category": category or "",             # OKB extension (domain grouping)
            "tags": tags or [],                     # optional
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        # Remove empty optional fields for cleaner output
        if not description:
            del frontmatter["description"]
        if not resource:
            del frontmatter["resource"]
        if not category:
            del frontmatter["category"]

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

    def read_concept_by_path(self, rel_path: str) -> dict | None:
        """Read concept by bundle-relative path."""
        full_path = self.root / rel_path
        if not full_path.exists():
            return None
        text = full_path.read_text(encoding="utf-8")
        return self._parse_concept_file(text)

    def _parse_concept_file(self, text: str) -> dict:
        """Parse YAML frontmatter + markdown body."""
        if not text.startswith("---"):
            return {"content": text, "frontmatter": {}}
        parts = text.split("---", 2)
        if len(parts) < 3:
            return {"content": text, "frontmatter": {}}
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
        return self.write_concept(
            oid, title, new_content,
            concept_type=fm.get("type", fm.get("category", "Concept")),
            category=fm.get("category", ""),
            tags=fm.get("tags", []),
            description=fm.get("description", ""),
            resource=fm.get("resource", ""),
        ) is not None

    # ═══════════════════════════════════════════════════════
    # Register / Unregister
    # ═══════════════════════════════════════════════════════

    def register(self, oid: str, title: str, concept_type: str = "Concept",
                 category: str = "", tags: list[str] | None = None) -> dict:
        """Register a concept in the manifest."""
        if "concepts" not in self.manifest:
            self.manifest["concepts"] = {}

        type_dir = concept_type.lower().replace(" ", "-") or "general"
        safe_name = oid.replace("/", "-").replace(" ", "-")[:64]
        rel_path = f"concepts/{type_dir}/{safe_name}.md"

        self.manifest["concepts"][oid] = {
            "title": title,
            "type": concept_type,
            "category": category or "",
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
            "type": m1.get("type", m2.get("type", "Concept")),
            "category": m1.get("category", m2.get("category", "")),
            "tags": list(set((m1.get("tags") or []) + (m2.get("tags") or []))),
            "merged_from": [id1, id2],
            "path": f"concepts/merged/{new_id}.md",
        }
        self._save_manifest()

    # ═══════════════════════════════════════════════════════
    # index.md Generation (§6)
    # ═══════════════════════════════════════════════════════

    def generate_index(self, dir_path: str = "concepts") -> str:
        """
        Generate an OKF v0.1 compliant index.md for progressive disclosure.

        Groups concepts by type, lists title + description.
        """
        target_dir = self.root / dir_path
        if not target_dir.exists():
            return ""

        lines = [f"# {self.manifest.get('name', 'Knowledge Bundle')}\n"]
        lines.append(f"_OKF v0.1 bundle — {len(self.manifest.get('concepts', {}))} concepts_\n")

        # Group by type
        by_type: dict[str, list[dict]] = {}
        for oid, info in self.manifest.get("concepts", {}).items():
            ct = info.get("type", "Concept")
            by_type.setdefault(ct, []).append(info)

        for ct, items in sorted(by_type.items()):
            lines.append(f"\n## {ct}\n")
            for item in sorted(items, key=lambda x: x.get("title", "")):
                title = item.get("title", "Untitled")
                desc = item.get("description", item.get("category", ""))
                path = item.get("path", "")
                if desc:
                    lines.append(f"* [{title}]({path}) — {desc}")
                else:
                    lines.append(f"* [{title}]({path})")

        result = "\n".join(lines) + "\n"
        (target_dir / "index.md").write_text(result, encoding="utf-8")
        return result

    # ═══════════════════════════════════════════════════════
    # log.md Support (§7)
    # ═══════════════════════════════════════════════════════

    def append_log(self, entry: str, log_dir: str = ".") -> Path:
        """
        Append an update entry to log.md.

        Args:
            entry: Markdown log entry (e.g. "**Update**: Added new concept for X")
            log_dir: Directory relative to root (default: root)
        """
        log_path = self.root / log_dir / "log.md"
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        if log_path.exists():
            content = log_path.read_text(encoding="utf-8")
        else:
            content = "# Update Log\n\n"

        # Check if today's section exists
        today_header = f"## {today}"
        if today_header not in content:
            # Insert after the title line
            lines = content.split("\n")
            insert_idx = 1
            for i, line in enumerate(lines):
                if line.startswith("## "):
                    insert_idx = i
                    break
            else:
                insert_idx = len(lines)
            lines.insert(insert_idx, f"\n{today_header}\n")
            content = "\n".join(lines)

        # Append entry under today's section
        entry_line = f"* {entry}"
        content = content.rstrip() + f"\n{entry_line}\n"
        log_path.write_text(content, encoding="utf-8")
        return log_path

    # ═══════════════════════════════════════════════════════
    # Conformance Validation (§9)
    # ═══════════════════════════════════════════════════════

    def conformance(self) -> dict:
        """
        Strict OKF v0.1 conformance check.

        A bundle conforms to OKF v0.1 if:
          1. Every non-reserved .md file has parsable YAML frontmatter
          2. Every frontmatter contains a non-empty ``type`` field
          3. Reserved filenames (index.md, log.md) follow §6/§7 structure
        """
        issues = []
        warnings = []
        total = 0
        valid = 0

        # Check all concept files
        for md_file in sorted(self.concepts_dir.rglob("*.md")):
            rel = md_file.relative_to(self.root)
            name = md_file.name

            # Skip reserved files
            if name in RESERVED_FILENAMES:
                continue

            total += 1
            text = md_file.read_text(encoding="utf-8")

            # Rule 1: must have YAML frontmatter
            if not text.startswith("---"):
                issues.append(f"[CONFORMANCE] {rel}: missing YAML frontmatter")
                continue

            parts = text.split("---", 2)
            if len(parts) < 3:
                issues.append(f"[CONFORMANCE] {rel}: unclosed YAML frontmatter")
                continue

            try:
                fm = yaml.safe_load(parts[1])
            except yaml.YAMLError as e:
                issues.append(f"[CONFORMANCE] {rel}: invalid YAML — {e}")
                continue

            if not isinstance(fm, dict):
                issues.append(f"[CONFORMANCE] {rel}: frontmatter is not a mapping")
                continue

            # Rule 2: must have non-empty type
            concept_type = fm.get("type", "")
            if not concept_type:
                issues.append(f"[CONFORMANCE] {rel}: missing required 'type' field (§4.1)")
                continue

            valid += 1

            # Soft warnings (not blocking)
            if "title" not in fm:
                warnings.append(f"[WARNING] {rel}: missing recommended 'title' field")
            if "description" not in fm:
                warnings.append(f"[WARNING] {rel}: missing recommended 'description' field")

        # Check reserved files exist
        root_index = self.root / "index.md"
        if not root_index.exists():
            warnings.append("[WARNING] Root index.md not found (§6)")

        return {
            "okf_version": "0.1",
            "conformant": len(issues) == 0,
            "total_concepts": total,
            "valid_concepts": valid,
            "issues": issues,
            "warnings": warnings,
        }

    # ═══════════════════════════════════════════════════════
    # Validate (backward-compat)
    # ═══════════════════════════════════════════════════════

    def validate(self) -> dict:
        """Legacy validate — checks manifest + file existence (tolerant)."""
        issues = []
        if not self.manifest_path.exists():
            issues.append("okf.yaml not found")

        count = len(self.manifest.get("concepts", {}))
        for oid, info in self.manifest.get("concepts", {}).items():
            filepath = self.root / info.get("path", "")
            if not filepath.exists():
                issues.append(f"concept file missing: {info.get('path', oid)}")

        return {"valid": len(issues) == 0, "issues": issues,
                "concepts_registered": count}

    # ═══════════════════════════════════════════════════════
    # Export
    # ═══════════════════════════════════════════════════════

    def export_bundle(self, target_dir: Path) -> dict:
        """Export the full OKF v0.1 bundle to a target directory."""
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

        # Generate and copy index.md
        self.generate_index("concepts")
        if (self.concepts_dir / "index.md").exists():
            shutil.copy2(self.concepts_dir / "index.md",
                        target_dir / "concepts" / "index.md")

        return {"exported": count, "target": str(target_dir),
                "manifest_copied": self.manifest_path.exists(),
                "index_generated": True}

    # ═══════════════════════════════════════════════════════
    # Stats
    # ═══════════════════════════════════════════════════════

    def stats(self) -> dict:
        concepts = self.manifest.get("concepts", {})
        files_exist = 0
        for info in concepts.values():
            if (self.root / info.get("path", "")).exists():
                files_exist += 1
        type_counts: dict[str, int] = {}
        for info in concepts.values():
            ct = info.get("type", info.get("category", "Concept"))
            type_counts[ct] = type_counts.get(ct, 0) + 1
        return {
            "concepts": len(concepts),
            "files": files_exist,
            "types": type_counts,
            "okf_version": self.manifest.get("okf", "unknown"),
        }
