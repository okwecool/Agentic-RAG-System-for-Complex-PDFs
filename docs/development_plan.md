# Agentic RAG for Complex PDFs 开发计划

## 1. 文档目标

本文档用于将设计方案落地为可执行的开发计划，明确：

- 当前阶段的开发目标
- 模块拆解与职责边界
- 推荐的目录结构
- 每个阶段的交付物与验收标准
- 基于现有 `data/source_pdf` 中约 200 份 PDF 的实施顺序

当前项目仍处于早期阶段，仓库中尚未形成完整实现，因此开发策略应遵循：

1. 先完成通用 PDF RAG 闭环
2. 再引入 Agent 化查询流程
3. 最后做领域增强与 MCP 化扩展

---

## 2. 当前项目现状

### 2.1 已有内容

- `docs/generic_pdf_agentic_rag_design.md`
- `data/source_pdf/`：已放入约 200 份 PDF 样本
- `src/`：目前基本为空，尚未形成核心模块
- `tests/`：目前基本为空

### 2.2 当前判断

项目目前最适合采用“从 0 到 1”的方式推进，而不是在现阶段直接构建复杂 Agent 编排。  
短期内最重要的是把 200 份 PDF 转化为一个稳定的、可检索、可引用的知识底座。

---

## 3. 总体开发策略

### 3.1 开发主线

建议按照以下主线推进：

1. 定义统一数据模型
2. 跑通 PDF ingestion
3. 建立 chunk 与索引
4. 跑通混合检索
5. 输出带引用的答案
6. 建立基础评测
7. 接入 LangGraph 与 Agent Runtime
8. 引入 Domain Profile
9. 逐步 MCP 化

### 3.2 开发原则

- 优先完成通用能力，不在主链路中写死行业逻辑
- ingestion 流程优先采用确定性 workflow
- Agent 仅用于需要动态决策的查询流程
- 所有检索与回答结果都要保留可追溯引用
- 所有参数尽量配置化，避免后续重构成本过高

---

## 4. 推荐目录结构

建议将 `src/` 组织为如下结构：

```text
src/
  api/
    routes/
    schemas/

  config/
    settings.py

  domain/
    models/
      document.py
      chunk.py
      citation.py
      state.py
    protocols/
      parser.py
      chunker.py
      retriever.py
      reranker.py
      profile.py
      tool_executor.py

  ingestion/
    pipeline.py
    scanner.py
    tasks.py

  parsing/
    pymupdf_parser.py
    cleaner.py
    section_builder.py
    table_extractor.py

  chunking/
    chunker.py
    rules.py

  indexing/
    embeddings.py
    vector_index.py
    bm25_index.py
    index_builder.py

  retrieval/
    search_service.py
    hybrid_fusion.py
    rerank.py
    context_packer.py

  generation/
    answer_generator.py
    citation_auditor.py

  memory/
    thread_store.py
    summarizer.py

  profiles/
    base.py
    generic.py
    finance.py

  graph/
    nodes/
      supervisor.py
      query_planner.py
      retrieval_strategist.py
      synthesizer.py
      citation_auditor.py
    workflow.py

  storage/
    file_store.py
    metadata_store.py

  utils/
    logging.py
    ids.py
```

补充建议：

- `data/` 保持原始 PDF 输入来源
- 新增 `artifacts/` 保存中间解析结果、chunk 数据和调试输出
- 新增 `indexes/` 保存本地索引文件
- 新增 `eval/` 或 `datasets/` 保存评测样本

---

## 5. 核心数据模型拆解

第一阶段建议优先实现以下模型。

### 5.1 Document

职责：

- 表示一份 PDF 文档的统一结构化对象
- 承载通用 metadata 和领域 metadata

关键字段：

- `doc_id`
- `title`
- `source_file`
- `doc_type`
- `domain_profile`
- `pages`
- `chunks`
- `metadata`

### 5.2 Page

职责：

- 表示单页内容
- 保留页码和结构块

关键字段：

- `page_no`
- `blocks`
- `width`
- `height`

### 5.3 Block

职责：

- 表示页面中的最小结构块
- 作为 section 识别、chunk 切分和引用映射的基础

关键字段：

- `block_id`
- `type`
- `text`
- `bbox`
- `section_path`
- `table_html`
- `table_json`
- `source_span`

### 5.4 Chunk

职责：

- 检索和生成的基本单元

关键字段：

- `chunk_id`
- `doc_id`
- `page_no`
- `chunk_type`
- `text`
- `section_path`
- `metadata`

### 5.5 Citation

职责：

- 建立回答结论与原始证据的映射关系

关键字段：

- `claim`
- `doc_id`
- `page_no`
- `chunk_id`
- `excerpt`

### 5.6 ResearchState

职责：

- 查询流程中的共享状态
- 服务于多轮对话和 Agent Runtime

建议字段：

- `thread_id`
- `user_query`
- `normalized_query`
- `current_domain`
- `current_entities`
- `current_intent`
- `retrieval_plan`
- `retrieved_candidates`
- `selected_evidence`
- `draft_answer`
- `claims`
- `citation_map`
- `confidence`
- `conversation_summary`

---

## 6. 分阶段开发计划

## Phase 0：工程初始化

### 目标

建立基础工程骨架和统一数据模型，为后续实现提供稳定边界。

### 任务拆解

- 初始化 `src/` 目录结构
- 定义配置模块与环境变量读取方式
- 定义领域模型和协议接口
- 定义日志方案和 ID 生成规则
- 约定中间产物目录

### 交付物

- 基础项目结构
- `Document / Block / Chunk / Citation / ResearchState` 模型
- 配置文件模板

### 验收标准

- 可以正常导入项目模块
- 核心 schema 可被单测创建和序列化

---

## Phase 1：PDF Ingestion 闭环

### 目标

将 `data/source_pdf` 中的 PDF 批量转换为结构化文档对象和中间产物。

### 任务拆解

#### 1. 文件扫描

- 扫描 `data/source_pdf`
- 建立文档注册表
- 生成 `doc_id`
- 计算 `file_hash`

#### 2. PDF 解析

- 采用 `PyMuPDF` 解析文本块、页码、bbox
- 提取标题、段落、列表等基础 block
- 预留表格抽取接口

#### 3. 清洗与标准化

- 去除空白块和无效字符
- 清洗页眉页脚噪声
- 标准化文本与换行

#### 4. section 构建

- 基于标题层级或版式线索构建 `section_path`
- 为后续 chunk 切分提供结构信息

#### 5. 中间结果落盘

- 将结构化解析结果输出到 `artifacts/parsed/`
- 支持逐文档调试和重跑

### 交付物

- `scanner.py`
- `pymupdf_parser.py`
- `cleaner.py`
- `section_builder.py`
- `pipeline.py`

### 验收标准

- 至少 90% 以上 PDF 能完成基础解析
- 每份文档都能输出结构化 JSON
- JSON 中包含页码、文本块、bbox、section_path

---

## Phase 2：Chunk 与索引

### 目标

将解析结果切分为可检索 chunk，并建立 BM25 与向量索引。

### 任务拆解

#### 1. chunk 规则实现

- 按 section 感知切分
- 保留小范围 overlap
- 表格单独成 chunk
- 图表标题可单独成 chunk

#### 2. metadata 补充

- 写入 `doc_id`
- 写入 `page_no`
- 写入 `section_path`
- 写入 `chunk_type`

#### 3. 向量索引

- 接入 embedding 模型
- 用 `FAISS` 建立本地向量索引

#### 4. BM25 索引

- 为 chunk 文本建立关键词检索索引

#### 5. 索引管理

- 支持增量构建
- 支持索引持久化与加载

### 交付物

- `chunker.py`
- `embeddings.py`
- `vector_index.py`
- `bm25_index.py`
- `index_builder.py`

### 验收标准

- 可对任意文档 chunk 进行索引构建
- 可返回包含 metadata 的 chunk 检索结果
- 支持关键词检索和向量检索

---

## Phase 3：混合检索与基础问答

### 目标

建立最小可用问答闭环，支持带引用输出。

### 任务拆解

#### 1. 检索服务

- 实现 `search_chunks`
- 实现可选 `search_tables`
- 合并 BM25 与向量检索结果

#### 2. 融合与重排

- 实现 hybrid fusion
- 接入 reranker
- 输出 top-n evidence

#### 3. 上下文打包

- 控制上下文长度
- 保留必要 metadata 和来源信息

#### 4. 答案生成

- 基于 evidence 生成回答
- 输出引用信息

#### 5. 引用审计

- 检查 claim 是否存在支持 chunk
- 过滤明显无证据支撑的内容

### 交付物

- `search_service.py`
- `hybrid_fusion.py`
- `rerank.py`
- `context_packer.py`
- `answer_generator.py`
- `citation_auditor.py`

### 验收标准

- 输入问题后可返回答案
- 答案中附带页码或 chunk 来源
- 对明显无关问题能够给出低置信度或证据不足提示

---

## Phase 4：评测与数据驱动修正

### 目标

基于现有 200 份 PDF 建立第一版评测机制，驱动检索质量提升。

### 任务拆解

#### 1. 样本集构建

- 从 200 份 PDF 中抽样
- 设计代表性问题
- 标注期望文档、页码或 chunk

#### 2. 评测指标

- 解析成功率
- Recall@k
- MRR
- nDCG
- 正确页码命中率
- 引用准确率

#### 3. 误差分析

- 分析解析失败原因
- 分析检索误命中原因
- 分析引用不一致原因

#### 4. 参数调优

- chunk size
- overlap
- BM25 top_k
- vector top_k
- rerank top_n

### 交付物

- 评测样本文件
- 评测脚本
- 第一版误差分析报告

### 验收标准

- 可以批量跑评测
- 可以输出检索与引用指标
- 能明确下一轮优化优先项

---

## Phase 5：Agent Runtime

### 目标

将查询流程升级为有状态的 Agent 工作流，但不改变 ingestion 主链路。

### 任务拆解

#### 1. LangGraph 接入

- 定义图状态
- 定义节点输入输出
- 建立主工作流

#### 2. 角色落地

- `Supervisor`
- `Query Planner`
- `Retrieval Strategist`
- `Synthesizer`
- `Citation Auditor`

#### 3. 多轮会话

- 使用 `ResearchState`
- 支持 thread 级上下文延续
- 支持追问场景

#### 4. 失败分支与降级

- 无法识别领域时回退到 `generic`
- 检索不足时自动放宽条件
- 引用不足时输出保守答案

### 交付物

- `graph/workflow.py`
- `graph/nodes/*.py`
- `memory/thread_store.py`

### 验收标准

- 查询流程可通过 LangGraph 跑通
- 支持基础多轮对话
- 能基于状态做策略调整

---

## Phase 6：Domain Profile

### 目标

在不破坏通用架构的前提下引入领域增强能力。

### 任务拆解

#### 1. Generic Profile

- 通用实体提取
- 通用 query expansion
- 通用过滤器与提示词模板

#### 2. Finance Profile

- 公司、ticker、机构等字段提取
- 金融别名扩展
- 报告类型识别
- 金融指标相关检索增强

#### 3. Profile 选择策略

- 文档级 detect
- 查询级 domain 判断

### 交付物

- `profiles/base.py`
- `profiles/generic.py`
- `profiles/finance.py`

### 验收标准

- 默认可以使用 `generic`
- 对金融 PDF 能启用增强检索逻辑
- profile 切换不需要改动主链路

---

## Phase 7：MCP 化与服务化

### 目标

将内部能力以统一工具接口对外暴露，提升复用性与扩展性。

### 任务拆解

- 定义统一 `ToolExecutor`
- 将搜索能力映射为工具
- 将文档与页面映射为资源
- 将引用解析能力封装为独立接口
- 逐步演化为 MCP server

### 交付物

- 工具适配层
- MCP adapter
- 搜索与引用相关工具

### 验收标准

- 能通过统一工具接口访问搜索与文档资源
- 核心能力可从主应用中解耦

---

## 7. 基于 200 份 PDF 的具体实施建议

### 7.1 第一周重点

第一周不建议追求 UI、复杂会话或 MCP，而应聚焦底层数据质量。

建议第一周完成：

- 核心 schema
- PDF 批量扫描
- PDF 解析与结构化落盘
- chunk 切分
- 向量索引与 BM25 基础实现

### 7.2 第二周重点

建议第二周完成：

- 混合检索
- 基础问答
- 引用输出
- 第一版评测集
- 参数调优

### 7.3 第三周重点

建议第三周完成：

- LangGraph 工作流
- 多 Agent 查询编排
- 多轮状态

### 7.4 第四周重点

建议第四周完成：

- `generic profile`
- 根据样本分布判断是否优先实现 `finance profile`
- 形成第一版稳定 demo

---

## 8. 开发任务清单

以下任务可以直接作为 backlog 使用。

### P0：必须优先完成

- 定义统一 schema
- 建立 PDF 扫描与注册逻辑
- 实现 PyMuPDF 解析器
- 实现 block 清洗与 section 构建
- 实现 chunk 切分
- 实现 FAISS 向量索引
- 实现 BM25 索引
- 实现混合检索服务
- 实现基础回答生成
- 实现引用映射

### P1：闭环后立即跟进

- 建立评测样本集
- 建立自动评测脚本
- 引入 reranker
- 优化表格处理
- 支持多轮会话上下文
- 接入 LangGraph

### P2：后续增强

- `finance profile`
- 表格专项检索
- OCR 与复杂版面增强
- MCP adapter
- 外部数据源接入

---

## 9. 验收标准总表

### MVP 验收标准

满足以下条件可视为第一版 MVP 完成：

- 能批量处理 `data/source_pdf` 中的 PDF
- 能输出结构化解析结果
- 能建立 chunk 与索引
- 能基于问题完成混合检索
- 能生成带引用的答案
- 能对证据不足场景进行降级提示

### Agent 阶段验收标准

- 查询流程由 LangGraph 编排
- 支持基本追问
- 能进行检索策略调整
- 能输出更稳定的 claim-citation 对齐结果

### Profile 阶段验收标准

- `generic profile` 默认可用
- 至少一个领域 profile 可用
- profile 能增强检索，不破坏主流程

---

## 10. 风险与注意事项

### 10.1 当前最大风险

- PDF 解析质量不稳定
- chunk 粒度不合适导致检索效果差
- 表格内容在 MVP 阶段可能命中不足
- 过早引入 Agent 导致排障成本变高

### 10.2 应对策略

- 先保留完整中间产物，方便回放
- 先做少量高质量评测样本，不盲目扩大范围
- 先把 retrieval 和 citation 做稳，再升级 Agent
- profile 采用可插拔方式，避免侵入主流程

---

## 11. 推荐的最近执行顺序

建议严格按照以下顺序开始实现：

1. 建立 `src` 目录结构
2. 定义 schema 与协议接口
3. 完成 PDF 解析 pipeline
4. 完成 chunk 生成
5. 完成 FAISS 与 BM25 索引
6. 完成 hybrid retrieval
7. 完成基础问答与 citation
8. 建立评测样本与调优机制
9. 接入 LangGraph
10. 引入 profile

---

## 12. 结论

当前最合理的落地路径，不是直接做“复杂多 Agent 系统”，而是先把 200 份 PDF 转化为高质量、可检索、可引用的数据底座。  
只要 Phase 1 到 Phase 3 走稳，这个项目就已经具备真实可用的第一版价值。之后再接入 Agent Runtime、领域增强和 MCP，会顺很多，也更容易评估每一步改动是否真的提升了系统质量。
