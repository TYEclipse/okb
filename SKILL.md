---
name: open-knowledge-base
slug: open-knowledge-base
displayName: OKB — Open Knowledge Base
displayName_zh: OKB — AI 智能体开放知识库
version: "1.1.0"
homepage: https://github.com/TYEclipse/okb
homepage_zh: https://gitee.com/tyeclipse/okb
description: "Unified knowledge management for AI agents: ChromaDB vector search + NetworkX 2-edge-connected graph + OKF v1.0 compliance. Build, query, and maintain structured knowledge bases for digital gardens, worldbuilding, and RAG pipelines."
description_zh: "面向 AI 智能体的统一知识管理系统：ChromaDB 向量语义搜索 + NetworkX 双连通知识图谱 + OKF v1.0 标准合规。适用于数字花园、世界观构建、RAG 知识管线等场景。"
category: software-development
changelog: |
  v1.1.0: OKF v0.1 全合规 — type(必填)/timestamp/description/resource, index.md/log.md, conformance验证, CLI新增3命令
  v1.0.3: 修复 stats() vector_indexed 字段 key 错误 (count→concepts)；新增 references/reconstruction.md
  v1.0.2: 代码自包含（scripts/okb/）、全中文文档、FAQ/反模式/能力边界/错误处理指南、Gitee 镜像、触发决策表
  v1.0.0: 初始发布
---

# OKB — Open Knowledge Base for AI Agents

> 🧠 Vector + 🔗 Graph + 📋 OKF — three layers, one API.
> 🧠 向量语义搜索 + 🔗 双连通知识图谱 + 📋 OKF 标准 — 三层合一。

**中文用户 👉 直接从[快速上手](#快速上手中文版)开始。**

---

## When to Use / 适用场景

| ✅ 适合 | ❌ 不适合 |
|---------|----------|
| 构建 AI Agent 的结构化知识库 | 纯全文搜索（用 Elasticsearch） |
| 数字花园 / 个人 wiki 的知识管理层 | 只需要一个 markdown 文件夹（用 Obsidian） |
| 世界观构建的内容关联与检索 | 实时协作编辑（用 Wiki.js） |
| RAG 管线的知识图谱增强 | 超大规模图（>10万节点，考虑 Neo4j） |
| 需要 OKF 标准导出的知识管理 | 不需要结构化知识的简单问答 |

---

## Quickstart (English)

```bash
# 1. Install dependencies
pip install chromadb networkx pyyaml requests

# 2. Set your embedding API key
export SILICONFLOW_API_KEY="sk-..."

# 3. Run from the skill's bundled code
cd ~/.hermes/skills/open-knowledge-base
python3 -m scripts.okb.cli stats .
```

```python
from scripts.okb import KnowledgeBase

kb = KnowledgeBase("~/my-digital-garden")

# Add a concept
kb.add_concept("grav-tax", "Gravity Tax", "A progressive tax based on...", category="economics")

# Semantic search with reranking
results = kb.query("taxation in space colonies", top_k=5)

# Build 2-edge-connected knowledge graph
kb.build_graph(k=3)
kb.verify()  # {'graph': {'verified': True, 'bridges': 0}}

# Rank candidate concepts by marginal centrality
kb.relevance("Martian water rights dispute")

# Export as OKF-compliant bundle
kb.export_okf("./okf-export/")
```

---

## 快速上手（中文版）

```bash
# 1. 安装依赖（使用清华镜像加速）
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple chromadb networkx pyyaml requests

# 2. 设置硅基流动 API Key（国内可直接访问 api.siliconflow.cn）
export SILICONFLOW_API_KEY="sk-..."

# 3. 运行自检
python3 scripts/okb/cli.py stats .
```

### Python API

```python
from scripts.okb import KnowledgeBase

kb = KnowledgeBase("~/my-knowledge-base")

# 添加概念
kb.add_concept("grav-tax", "重力税", "一种基于天体表面重力加速度的累进税制...", category="经济学")

# 语义搜索（自动 rerank）
results = kb.query("太空殖民地的税收制度", top_k=5)
for r in results:
    print(f"[{r['category']}] {r['title']} (相关度: {r['score']:.4f})")

# 构建双连通知识图谱
kb.build_graph(k=3)

# 边际中心性排序 — 帮你决定下一个该写什么
kb.relevance("木卫二冰下海洋生命探测")

# 导出 OKF 格式
kb.export_okf("./okf-bundle/")
```

---

## Architecture / 架构

```
KnowledgeBase
  ├── .vector()  → VectorStore  (ChromaDB — 语义搜索 + Rerank)
  ├── .graph()   → GraphStore   (NetworkX — 2-边连通知识图谱)
  └── .okf()     → OKFManifest  (YAML — OKF v1.0 合规)
```

**三层各司其职：**
- **Vector 层**：存什么 → 找什么（语义理解）
- **Graph 层**：怎么关联 → 缺什么（结构推理）
- **OKF 层**：怎么导出 → 怎么合规（标准格式）

---

## CLI Commands / 命令行接口

### 触发决策表

| 我想做什么 | 用什么命令 | 示例 |
|-----------|-----------|------|
| 搜索已有概念 | `query` | `python3 scripts/okb/cli.py query . "聚变能源"` |
| 判断新想法是否值得写 | `relevance` | `python3 scripts/okb/cli.py relevance . "火星水资源争议"` |
| 构建/重建知识图谱 | `build` | `python3 scripts/okb/cli.py build . --k 3 --verify` |
| 检查知识库健康状态 | `verify` | `python3 scripts/okb/cli.py verify .` |
| 查看统计数据 | `stats` | `python3 scripts/okb/cli.py stats . --json` |
| 导出 OKF 格式 | `export` | `python3 scripts/okb/cli.py export . ./okf-out/` |
| 手动添加概念 | `add` | `python3 scripts/okb/cli.py add . --id "x" --title "X" --content "..."` |

### 完整命令参考

| Command | 说明 | 关键参数 |
|---------|------|---------|
| `build` | 从向量库重建 2-边连通图 | `--k 3` (k-NN), `--verify` (构建后自检) |
| `query` | 语义搜索（embedding → rerank） | `--top 10`, `--json` |
| `relevance` | 候选概念的边际介数中心性 | `--top 10`, `--json` |
| `verify` | 自检：连通性/桥/度分布 | — |
| `stats` | 全层聚合统计 | `--json` |
| `export` | 导出 OKF 合规包 | `<target_dir>` |
| `add` | 添加概念（索引+图节点+OKF） | `--id`, `--title`, `--content`, `--category` |

---

## 能力边界（重要！）

### 不适合的场景

1. **超大规模图（>10万节点）**: NetworkX 是纯 Python 内存图，超过这个量级考虑 Neo4j 或 ArangoDB
2. **纯全文搜索**: 如果你的需求只是 "grep 所有 markdown"，不需要向量搜索
3. **多人实时协作**: OKB 是本地优先的单人知识库，没有冲突解决机制
4. **非文本内容**: 目前只索引文本，不支持图片/音频的语义搜索
5. **零依赖部署**: 需要 ChromaDB + NetworkX + embedding API，不是单文件方案

### 适合的场景

- ✅ AI Agent 的长期记忆与知识检索
- ✅ 个人数字花园的结构化管理
- ✅ 世界观/设定集的交叉引用与一致性检查
- ✅ RAG 管线的知识图谱增强层
- ✅ 需要 OKF 标准导出的知识管理系统

---

## 错误处理指南

### 常见错误与解决方案

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `ModuleNotFoundError: No module named 'chromadb'` | 依赖未安装 | `pip install chromadb networkx pyyaml requests` |
| `ModuleNotFoundError: No module named 'numpy'` | 使用了系统 Python 而非 Hermes venv | 使用 `~/.hermes/hermes-agent/venv/bin/python3` 或先激活 venv |
| `requests.exceptions.ConnectionError` | 无法连接 embedding API | 检查 `SILICONFLOW_API_KEY`，确认 `api.siliconflow.cn` 可达 |
| `chromadb.errors.InvalidDimensionException` | 切换了 embedding 模型导致维度不匹配 | 删除 `.chroma/` 目录重新索引 |
| `graph.json not found` | 还未执行 `build` | 先运行 `build --k 3` 构建知识图谱 |
| graph 验证失败 (`bridges > 0`) | 某些节点语义孤立 | 尝试 `build --k 5` 增加邻居数，或检查向量质量 |
| `KeyError` 在 `vector.knn()` | 查询的节点不存在于向量库 | 先用 `stats` 确认节点存在 |

### 诊断命令

```bash
# 全面诊断
python3 scripts/okb/cli.py verify .

# 查看已索引概念数
python3 scripts/okb/cli.py stats . --json | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'概念: {d[\"concepts\"]}, 向量: {d[\"vector_indexed\"]}, 图节点: {d[\"graph_nodes\"]}')"

# 检查 API 连通性（需要 curl）
curl -s https://api.siliconflow.cn/v1/models -H "Authorization: Bearer $SILICONFLOW_API_KEY" | head -1
```

---

## 反模式 (Anti-Patterns) / 常见坑点

### ❌ 不要这样做

1. **直接用系统 Python 跑** — 如果你的环境中 `python3` 没有 numpy/networkx，会报 `ModuleNotFoundError`。请使用安装了依赖的 Python 环境。
2. **频繁全量 rebuild** — `build()` 是 O(n²) 操作（k-NN 距离计算），254 节点约需 30 秒。增量 `add_concept()` 更适合日常使用。
3. **忽略 verify 结果** — `build --verify` 不通过（bridges>0）说明知识图谱有结构缺陷，继续使用会导致边际中心性不可靠。
4. **在 ChromaDB 目录中手动删文件** — ChromaDB 使用 SQLite + 二进制索引，手工操作会损坏数据库。请通过 API 操作。
5. **忘记设置 SILICONFLOW_API_KEY** — 所有搜索/构建都需要 embedding API，不设置会静默失败或返回空结果。
6. **切换 embedding 模型后不重建** — 不同模型的向量维度和语义空间不同，混用会导致搜索结果异常。切换模型后删除 `.chroma/` 重新索引。

---

## FAQ

### Q: 我需要硅基流动账号吗？
A: 需要。去 [siliconflow.cn](https://siliconflow.cn) 注册，获取 API Key（免费额度足够个人使用）。硅基流动是国内可直连的服务。

### Q: 能用 OpenAI 的 embedding API 吗？
A: 可以。构造函数中传入自定义 `api_base`：`VectorStore(chroma_dir="...", api_key="sk-...", api_base="https://api.openai.com/v1", embed_model="text-embedding-3-small")`

### Q: 图节点的"边际中心性"是什么？
A: 对于候选新概念，计算它加入知识图谱后的介数中心性（betweenness centrality）。值越高，说明这个新概念能显著缩短图中其他节点间的最短路径——即"信息枢纽"潜力越大，创作优先级越高。

### Q: OKF 是什么？必须用吗？
A: Open Knowledge Format 是让 AI Agent 之间互通知识的标准格式。不强制使用，但如果你希望知识库能被其他 OKF 兼容工具读取，建议导出。详见 [okf.md](https://okf.md/)。

### Q: GitHub 访问慢怎么办？
A: 使用 Gitee 镜像：`git clone https://gitee.com/tyeclipse/okb.git`

### Q: 怎么为现有项目初始化知识库？
A: 
```bash
cd your-project/
python3 scripts/okb/cli.py build . --k 3 --verify
# 如果有已存在的 markdown 文件想批量导入：
# 参考 scripts/okb/cli.py 的 add 命令逐条导入
```

---

## OKF Bundle Structure / OKF 标准包结构

```
<root>/
├── okf.yaml           # 包清单（名称、版本、概念索引）
└── concepts/           # 每个概念一个 .md 文件
    ├── economics/
    │   └── gravity-tax.md
    └── astronomy/
        └── mars-colonies.md
```

每个概念文件使用 YAML 前置元数据：

```markdown
---
type: "WorldbuildingConcept"
id: "grav-tax"
title: "Gravity Tax"
description: "A progressive tax based on gravitational acceleration."
category: "economics"
resource: ""
tags: [taxation, space-law]
timestamp: "2026-06-20T00:00:00Z"
---
# Gravity Tax

A progressive tax based on...
```

---

## Requirements / 环境要求

- Python 3.10+
- `chromadb`, `networkx`, `pyyaml`, `requests`
- 硅基流动 API Key（或兼容 OpenAI 格式的 embedding 端点）
- 设置环境变量 `SILICONFLOW_API_KEY`

**国内用户推荐使用清华镜像加速安装：**
```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple chromadb networkx pyyaml requests
```

---

## 国内访问

| 资源 | 地址 |
|------|------|
| GitHub（主仓库） | https://github.com/TYEclipse/okb |
| Gitee（镜像，国内推荐） | https://gitee.com/tyeclipse/okb |
| 硅基流动 API（国内可直连） | https://api.siliconflow.cn/v1 |

---

## 重构已有知识库

如果已有散落的 .md 文件 + ChromaDB + graph.json，需要迁移到 OKF 格式：
→ 参考 `references/reconstruction.md`（轻量迁移，不重复索引）

## 技能维护（作者用）

Bug 修复后如何同步 GitHub / Gitee / SkillHub 三个平台：
→ 参考 `references/maintenance.md`（三平台同步流程 + 凭证管理）

## License / 协议

MIT © 2026 TYEclipse
