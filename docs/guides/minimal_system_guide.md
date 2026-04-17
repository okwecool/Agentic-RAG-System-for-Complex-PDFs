# 最小可运行系统指导文档

## 相关文档

- 总体开发计划：[`../development/development_plan.md`](../development/development_plan.md)
- API 与检索开发说明：[`../development/api_retrieval_development_notes.md`](../development/api_retrieval_development_notes.md)
- 前端设计文档：[`../development/frontend_design.md`](../development/frontend_design.md)
- 当前 RAG 缺口分析：[`../analysis/current_rag_gap_analysis.md`](../analysis/current_rag_gap_analysis.md)
- 页面模板分类与图表页分区设计：[`../analysis/page_template_classification_design.md`](../analysis/page_template_classification_design.md)

## 1. 文档目标

本文档用于说明当前项目**已经实现**的最小可运行系统，包括：

- PDF 解析与切块
- 索引构建与召回
- rerank 接入
- 问答生成
- API 对外服务
- 前端展示

这份文档不追求完整架构细节，而是强调：

- 当前系统到底已经做到什么程度
- 每一层代码入口在哪里
- 最小运行链路怎么走
- 当前默认参数是什么
- 后续要扩展时应从哪里进入

## 2. 当前系统总览

当前项目已经具备一条完整的最小化 RAG 主链：

```text
PDF 文件
  -> 解析与清洗
  -> 切块与落盘
  -> BM25 / 向量索引
  -> Hybrid Retrieval
  -> 可插拔 Reranker
  -> Context Packing
  -> LLM Answer Generation
  -> Citation / Evidence 返回
  -> CLI / API / Frontend 展示
```

当前可以把系统理解为：

- **主链已打通**
- **可本地运行**
- **可通过 API 和前端访问**
- **质量增强层仍在继续迭代**

## 3. 目录与模块入口

当前最关键的目录如下：

```text
src/
  api/           FastAPI 接口
  chunking/      切块逻辑
  config/        环境变量与路径配置
  generation/    问答生成与 citation
  indexing/      embedding / BM25 / FAISS / 索引构建
  ingestion/     PDF 扫描与处理主链
  parsing/       parser / cleaner / section builder / table extractor
  retrieval/     搜索、fusion、rerank、context packing
  frontend/      Gradio 前端

artifacts/       默认解析与切块产物
indexes/         默认索引缓存
scripts/         本地启动脚本
docs/            开发文档
```

## 4. 配置方式

当前系统主要通过项目根目录下的 `.env` 配置。

模板文件：

- [`.env.example`](../../.env.example)

### 4.1 常用配置项

#### 目录配置

- `DATA_DIR`
- `SOURCE_PDF_DIR`
- `ARTIFACTS_DIR`
- `PARSED_DIR`
- `CHUNKS_DIR`
- `MANIFESTS_DIR`
- `INDEXES_DIR`
- `RETRIEVAL_INDEX_DIR`

#### 模型配置

- `LOCAL_EMBEDDING_MODEL_DIR`
- `LOCAL_RERANKER_MODEL_DIR`
- `LLM_PROVIDER`
- `LLM_PROMPT_FAMILY`
- `DASHSCOPE_API_KEY`
- `DASHSCOPE_BASE_URL`
- `DASHSCOPE_MODEL`

#### 检索配置

- `QA_TOP_K`
- `FUSION_MODE`
- `FUSION_RRF_K`
- `FUSION_BM25_WEIGHT`
- `FUSION_VECTOR_WEIGHT`
- `RERANKER_PROVIDER`
- `RERANKER_TOP_N`
- `RERANKER_BATCH_SIZE`

#### 前端配置

- `FRONTEND_BACKEND_MODE`
- `FRONTEND_API_BASE_URL`
- `FRONTEND_HOST`
- `FRONTEND_PORT`
- `FRONTEND_TITLE`
- `FRONTEND_DEFAULT_TOP_K`

配置读取入口：

- [`../../src/config/settings.py`](../../src/config/settings.py)

## 5. PDF 解析流程

PDF ingestion 主链入口：

- [`../../src/ingestion/pipeline.py`](../../src/ingestion/pipeline.py)
- [`../../src/ingestion/run.py`](../../src/ingestion/run.py)

### 5.1 当前流程

```text
扫描 PDF
  -> PyMuPDF 解析页面与文本块
  -> cleaner 清洗与合并
  -> table extractor 抽取表格
  -> section builder 构建 section_path
  -> chunker 切块
  -> 写入 parsed / chunks / manifests
```

### 5.2 相关模块

- parser：[`../../src/parsing/pymupdf_parser.py`](../../src/parsing/pymupdf_parser.py)
- cleaner：[`../../src/parsing/cleaner.py`](../../src/parsing/cleaner.py)
- section builder：[`../../src/parsing/section_builder.py`](../../src/parsing/section_builder.py)
- table extractor：[`../../src/parsing/table_extractor.py`](../../src/parsing/table_extractor.py)

### 5.3 当前已实现的解析能力

- 基于 `PyMuPDF` 提取 page / block / bbox / text
- 基础 block 类型识别：
  - `heading`
  - `paragraph`
  - `list_item`
  - `table`
- 跨行正文合并
- 页眉页脚重复过滤
- 图表页短标签与噪声过滤
- source note / disclaimer / 伪表格过滤
- section_path 构建

### 5.4 当前仍未完全实现

- 真正的 `page template classification`
- 真正的 `block zoning`
- 明确的 `figure_caption / chart_label / source_note` 统一角色建模

## 6. 切块设置

切块逻辑入口：

- [`../../src/chunking/chunker.py`](../../src/chunking/chunker.py)
- [`../../src/chunking/rules.py`](../../src/chunking/rules.py)

### 6.1 当前切块策略

当前不是简单固定窗口，而是：

- 先按 `section_path + page_no` 聚合
- 再按字符长度控制 chunk 大小
- 对 `table` 块单独成 chunk
- 对跨 block 的续句做智能拼接

### 6.2 当前默认参数

- `target_size = 800`
- `overlap = 100`
- `min_chunk_size = 120`

说明：

- overlap 目前是字符级近似 overlap
- 不是 token-based overlap
- 也不是纯 sliding window

### 6.3 当前 chunk metadata

每个 chunk 会保留：

- `chunk_id`
- `doc_id`
- `page_no`
- `chunk_type`
- `section_path`
- `block_ids`
- `char_count`
- `text`

### 6.4 当前局限

- 图表标题仍可能混入正文 chunk
- 图表页 chunk 仍可能碎片化
- 还没有 parent-child chunking

## 7. 解析产物与切块产物

默认输出目录：

- parsed：`artifacts/parsed`
- chunks：`artifacts/chunks`
- manifests：`artifacts/manifests`

常见文件：

- `artifacts/parsed/doc_xxx.json`
- `artifacts/chunks/doc_xxx.json`
- `artifacts/manifests/ingestion_summary.json`

如果希望做全量新扫描，建议切换到新的 artifacts 目录，避免历史产物干扰。

## 8. 索引与召回设置

索引构建入口：

- [`../../src/indexing/index_builder.py`](../../src/indexing/index_builder.py)
- [`../../src/indexing/cli.py`](../../src/indexing/cli.py)

检索入口：

- [`../../src/retrieval/search_service.py`](../../src/retrieval/search_service.py)
- [`../../src/retrieval/cli.py`](../../src/retrieval/cli.py)

### 8.1 当前召回组成

当前召回由三层组成：

1. `BM25`
2. `vector retrieval`
3. `hybrid fusion`

### 8.2 BM25

实现位置：

- [`../../src/indexing/bm25_index.py`](../../src/indexing/bm25_index.py)

作用：

- 关键词召回
- 精确词面匹配

### 8.3 向量召回

实现位置：

- [`../../src/indexing/embeddings.py`](../../src/indexing/embeddings.py)
- [`../../src/indexing/vector_index.py`](../../src/indexing/vector_index.py)
- [`../../src/indexing/providers/sentence_transformer.py`](../../src/indexing/providers/sentence_transformer.py)
- [`../../src/indexing/providers/tfidf.py`](../../src/indexing/providers/tfidf.py)

当前支持：

- `sentence_transformer`
- `tfidf`

当前常用本地模型通过 `LOCAL_EMBEDDING_MODEL_DIR` 配置。

### 8.4 向量索引

当前已接入：

- `FAISS`

### 8.5 索引缓存

当前支持将索引持久化到：

- `RETRIEVAL_INDEX_DIR`

默认目录通常是：

- `indexes/retrieval_cache/...`

## 9. Hybrid Fusion 设置

实现位置：

- [`../../src/retrieval/hybrid_fusion.py`](../../src/retrieval/hybrid_fusion.py)

当前支持：

- `rrf`
- `weighted_rank`

### 9.1 当前默认设置

- `FUSION_MODE=rrf`
- `FUSION_RRF_K=60`
- `FUSION_BM25_WEIGHT=1.0`
- `FUSION_VECTOR_WEIGHT=1.0`

### 9.2 当前检索后处理

`SearchService` 还会在 fusion 后继续做：

- dedup
- result grouping / collapse
- 通用排序信号
- 目录型 chunk 降权
- 稀疏噪声 chunk 降权

相关实现：

- [`../../src/retrieval/search_service.py`](../../src/retrieval/search_service.py)
- [`../../src/retrieval/signals.py`](../../src/retrieval/signals.py)

## 10. Rerank 设置

实现位置：

- [`../../src/domain/protocols/reranker.py`](../../src/domain/protocols/reranker.py)
- [`../../src/retrieval/rerankers/noop.py`](../../src/retrieval/rerankers/noop.py)
- [`../../src/retrieval/rerankers/transformers_cross_encoder.py`](../../src/retrieval/rerankers/transformers_cross_encoder.py)

### 10.1 当前支持的 provider

- `noop`
- `local_transformers`

### 10.2 当前配置项

- `RERANKER_PROVIDER`
- `RERANKER_TOP_N`
- `RERANKER_BATCH_SIZE`
- `LOCAL_RERANKER_MODEL_DIR`

### 10.3 当前状态说明

reranker 框架已经接好，也已经支持本地模型接入，但从最近默认运行日志看，当前默认链路通常还是：

- `reranker = noop`

也就是说：

- **能力已接入**
- **默认质量闭环还未完全切换到真实 reranker**

## 11. 问答生成流程

入口：

- [`../../src/generation/qa_service.py`](../../src/generation/qa_service.py)

当前问答流程：

```text
query
  -> search
  -> context pack
  -> answer generate
  -> citation audit
  -> return answer / citations / evidence
```

### 11.1 相关模块

- answer generator：[`../../src/generation/answer_generator.py`](../../src/generation/answer_generator.py)
- citation auditor：[`../../src/generation/citation_auditor.py`](../../src/generation/citation_auditor.py)
- context packer：[`../../src/retrieval/context_packer.py`](../../src/retrieval/context_packer.py)

### 11.2 当前返回内容

当前问答结果会返回：

- `answer`
- `confidence`
- `model`
- `prompt_family`
- `embedding_backend`
- `retrieved_count`
- `citations`
- `evidence`

### 11.3 当前限制

- citation 仍偏基础
- 还不是 claim 级严格对齐
- context packing 还比较轻量

## 12. LLM 与 Prompt 设置

LLM provider 入口：

- [`../../src/generation/providers/openai_compatible.py`](../../src/generation/providers/openai_compatible.py)
- [`../../src/generation/providers/local_stub.py`](../../src/generation/providers/local_stub.py)

Prompt 入口：

- [`../../src/generation/prompts/chinese_generic.py`](../../src/generation/prompts/chinese_generic.py)
- [`../../src/generation/prompts/qwen.py`](../../src/generation/prompts/qwen.py)
- [`../../src/generation/prompts/factory.py`](../../src/generation/prompts/factory.py)

### 12.1 当前配置项

- `LLM_PROVIDER`
- `LLM_PROMPT_FAMILY`
- `DASHSCOPE_API_KEY`
- `DASHSCOPE_BASE_URL`
- `DASHSCOPE_MODEL`

### 12.2 当前默认逻辑

- 使用 OpenAI 兼容调用方式
- 默认走中文 prompt
- `qwen` 模型可自动切到对应 prompt family

## 13. API 对外服务

当前 API 入口：

- [`../../src/api/app.py`](../../src/api/app.py)
- [`../../src/api/routes/qa.py`](../../src/api/routes/qa.py)

### 13.1 当前接口

- `POST /api/qa/ask`

请求体：

```json
{
  "query": "Sora 2 有什么升级？",
  "top_k": 4,
  "tables_only": false
}
```

### 13.2 启动方式

启动入口：

- [`../../src/api/run.py`](../../src/api/run.py)

脚本：

- [`../../scripts/start_api.ps1`](../../scripts/start_api.ps1)
- [`../../scripts/smoke_test_api.ps1`](../../scripts/smoke_test_api.ps1)

## 14. CLI 使用链路

当前已经有三类 CLI：

### 14.1 ingestion

- [`../../src/ingestion/run.py`](../../src/ingestion/run.py)

### 14.2 indexing / retrieval

- [`../../src/indexing/cli.py`](../../src/indexing/cli.py)
- [`../../src/retrieval/cli.py`](../../src/retrieval/cli.py)

### 14.3 generation

- [`../../src/generation/cli.py`](../../src/generation/cli.py)
- [`../../scripts/ask.ps1`](../../scripts/ask.ps1)

这几条 CLI 链路适合本地调试和效果验证。

## 15. 前端展示

当前已经实现一版基础前端，采用 `Gradio`。

前端入口：

- [`../../src/frontend/app.py`](../../src/frontend/app.py)
- [`../../src/frontend/run.py`](../../src/frontend/run.py)

辅助模块：

- [`../../src/frontend/controller.py`](../../src/frontend/controller.py)
- [`../../src/frontend/state.py`](../../src/frontend/state.py)
- [`../../src/frontend/factory.py`](../../src/frontend/factory.py)
- [`../../src/frontend/clients/http_client.py`](../../src/frontend/clients/http_client.py)
- [`../../src/frontend/clients/inprocess_client.py`](../../src/frontend/clients/inprocess_client.py)

### 15.1 当前前端能力

- 单页聊天界面
- 提问与回答展示
- 简单 citation 展示
- evidence 预览
- 参数面板：
  - `top_k`
  - `tables_only`

### 15.2 当前后端模式

当前前端支持两种后端模式：

- `inprocess`
- `http`

配置项：

- `FRONTEND_BACKEND_MODE`
- `FRONTEND_API_BASE_URL`

### 15.3 当前前端边界

已实现：

- 基础聊天
- 基础引用溯源
- 轻量本地启动
- Hugging Face Spaces 友好路径预留

未实现：

- 真正多轮上下文传递
- session 持久化
- PDF 页面预览
- 文档内跳转高亮

## 16. 最小运行步骤

### 16.1 第一步：准备配置

复制并填写：

- [`.env.example`](../../.env.example)

至少需要保证：

- 索引目录可用
- embedding 模型目录可用
- LLM 接口配置可用

### 16.2 第二步：如有需要，先跑 ingestion

入口：

- [`../../src/ingestion/run.py`](../../src/ingestion/run.py)

### 16.3 第三步：构建索引

入口：

- [`../../src/indexing/cli.py`](../../src/indexing/cli.py)

### 16.4 第四步：用 CLI 验证问答链

入口：

- [`../../src/generation/cli.py`](../../src/generation/cli.py)

### 16.5 第五步：启动 API 或前端

API：

- [`../../src/api/run.py`](../../src/api/run.py)

前端：

- [`../../src/frontend/run.py`](../../src/frontend/run.py)
- [`../../scripts/start_frontend.ps1`](../../scripts/start_frontend.ps1)

## 17. 当前最值得注意的限制

当前系统已经可运行，但还存在这些明确边界：

1. 页面结构理解层还没真正补齐
- `page_profile / zone / block_role` 仍然主要停留在设计阶段

2. chunk 质量还在持续优化
- 图表标题、图例、标签区仍可能影响 chunk 质量

3. parent-child chunking 还没有实现

4. 图表 / 表格半结构化抽取还没有真正完成

5. reranker 还没有完全进入默认主流程闭环

6. citation 还没有做到 claim 级强校验

## 18. 当前最准确的状态判断

如果只用一句话总结当前系统：

**这是一个已经打通主链、具备 CLI / API / Frontend 的最小可运行 RAG 系统，但质量增强层仍未完全闭环。**

更具体地说：

- 能解析 PDF
- 能切块
- 能建索引
- 能检索
- 能回答
- 能返回引用
- 能通过前端访问

但还没有做到：

- 稳定利用复杂图表与表格信息
- 稳定保证高质量 chunk
- 稳定保证答案与证据严格对齐

## 19. 推荐阅读顺序

如果是第一次接手当前系统，建议按以下顺序阅读：

1. 本文档
2. [`../development/api_retrieval_development_notes.md`](../development/api_retrieval_development_notes.md)
3. [`../development/frontend_design.md`](../development/frontend_design.md)
4. [`../analysis/current_rag_gap_analysis.md`](../analysis/current_rag_gap_analysis.md)
5. [`../analysis/page_template_classification_design.md`](../analysis/page_template_classification_design.md)

## 20. 结论

当前项目已经完成了一个可运行的最小系统闭环：

- PDF ingestion
- chunking
- indexing
- retrieval
- rerank framework
- answer generation
- API
- frontend

因此后续工作重点不再是“把链路接起来”，而是：

- 提高页面理解能力
- 提高 chunk 质量
- 提高检索排序质量
- 提高结构化证据能力
- 提高 citation 可信度

一句话总结：

**当前系统已经可以作为最小可运行底座使用，下一阶段应重点投入质量增强，而不是重复搭建主链。**
