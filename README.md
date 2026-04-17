# Agentic-RAG-System-for-Complex-PDFs

面向复杂 PDF 文档的通用 Agentic RAG 系统，当前已具备从 PDF 解析、切块、召回、问答到前端展示的最小可运行主链。

## 当前已实现

- PDF 解析、清洗、切块与产物落盘
- BM25 + 向量召回 + Hybrid Fusion
- 可插拔 reranker 架构
- CLI / API / Gradio Frontend 问答链路
- 基础 citation 与 evidence 返回

## 快速开始

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 配置环境变量

参考根目录下的 [`.env.example`](.env.example) 创建 `.env`。

3. 如需初始化本地向量库，先构建索引

```bash
python -m src.indexing.cli
```

如果已经准备好 `chunks` 产物并且 `.env` 中配置了：

- `CHUNKS_DIR`
- `RETRIEVAL_INDEX_DIR`
- `LOCAL_EMBEDDING_MODEL_DIR`

则会基于当前切块产物构建本地检索索引。

4. 启动前端

```bash
python -m src.frontend.run
```

或启动 API：

```bash
python -m src.api.run
```

## 文档入口

- 最小可运行系统说明：[`docs/guides/minimal_system_guide.md`](docs/guides/minimal_system_guide.md)
- 开发计划：[`docs/development/development_plan.md`](docs/development/development_plan.md)
- API / 检索说明：[`docs/development/api_retrieval_development_notes.md`](docs/development/api_retrieval_development_notes.md)
- 前端设计：[`docs/development/frontend_design.md`](docs/development/frontend_design.md)
- 当前缺口分析：[`docs/analysis/current_rag_gap_analysis.md`](docs/analysis/current_rag_gap_analysis.md)
