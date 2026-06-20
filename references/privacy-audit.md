# 隐私审计清单 (Privacy Audit Checklist)

开源知识库之前，逐项检查以下内容：

## 硬编码凭证 (P0 — 阻断)
- [ ] 无 API Key 硬编码（如 `api_key = "sk-xxx"`）
- [ ] 无 Token/Cookie/密码明文
- [ ] 所有凭证走环境变量或构造函数参数

## 个人身份信息 (P0 — 阻断)
- [ ] 无真实姓名（可用 GitHub ID 代替）
- [ ] 无邮箱地址
- [ ] 无手机号
- [ ] 无身份证/护照号

## 路径泄漏 (P1 — 重要)
- [ ] 无 `/home/<username>/` 类个人路径
- [ ] 无 Windows 个人路径（`C:\Users\...`）
- [ ] 无项目私有名称（用 `~/my-project/` 代替真实项目名）

## 内容泄漏 (P1 — 重要)
- [ ] 世界观/创作内容未打包进公开 repo
- [ ] ChromaDB 向量库（`.chroma/`）已加入 .gitignore
- [ ] 知识图谱数据（`graph.json`）已加入 .gitignore
- [ ] OKF 概念文件（`concepts/`）已加入 .gitignore

## 快速扫描命令

```bash
# 扫描当前目录所有 Python 文件
grep -rnE '(api[_-]?key|token|secret)\s*[:=]\s*["\'][A-Za-z0-9_-]{20,}' --include='*.py' .
grep -rnE '[\w\.-]+@[\w\.-]+\.\w+' --include='*.py' .
grep -rn '/home/' --include='*.py' .
grep -rn '1[3-9]\d{9}' --include='*.py' .
```
