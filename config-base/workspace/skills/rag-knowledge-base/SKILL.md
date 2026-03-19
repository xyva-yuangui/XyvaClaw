# RAG Knowledge Base

本地 RAG 知识库系统，支持文档解析、向量存储、混合检索和增强生成。

## 功能

- **文档解析**：PDF / Word / Excel / Markdown / 纯文本
- **智能分块**：递归字符分割，保留语义完整性
- **向量存储**：ChromaDB 本地持久化
- **混合检索**：向量语义检索 + 关键词 BM25
- **Embedding**：DashScope text-embedding-v3（通义千问）
- **CLI 管理**：add / remove / list / query / stats

## 使用方式

```bash
# 添加文档到知识库
python3 scripts/kb_manager.py add /path/to/document.pdf --collection default

# 添加整个目录
python3 scripts/kb_manager.py add /path/to/docs/ --collection project-docs

# 查询知识库
python3 scripts/kb_manager.py query "什么是 OpenClaw 的架构？" --top-k 5

# 列出所有 collection
python3 scripts/kb_manager.py list

# 查看统计
python3 scripts/kb_manager.py stats

# 删除文档
python3 scripts/kb_manager.py remove --source /path/to/document.pdf

# 导出检索结果为上下文（供 LLM 使用）
python3 scripts/kb_manager.py context "用户问题" --max-tokens 4000
```

## 配置

环境变量 `DASHSCOPE_API_KEY` 用于 embedding 模型调用。
数据存储在 `~/.openclaw/data/chromadb/`。
