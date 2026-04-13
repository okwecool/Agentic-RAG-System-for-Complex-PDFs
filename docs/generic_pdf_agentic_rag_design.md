# 通用 PDF Agentic RAG 系统设计方案（支持金融等领域扩展）

## 1. 项目定位

本项目定位为一个**面向复杂 PDF 文档的通用 Agentic RAG 系统**。系统核心目标不是面向某一个固定行业，而是围绕 PDF 文档的通用处理能力构建一套可扩展底座，并通过领域配置或插件机制，逐步扩展到金融、法律、科研、制造、医药等不同场景。

系统需要同时具备以下能力：

- 支持复杂 PDF 文档导入、解析、切块与索引
- 支持关键词检索、向量检索、混合检索与重排序
- 支持引用溯源、页码定位与证据校验
- 支持多轮对话与任务连续性
- 支持 Agent 化查询流程
- 支持通过 MCP 和模块化机制持续扩展
- 支持通过 Domain Profile 适配不同领域

该系统不将行业能力写死在主流程中，而是采用：

> **通用 PDF Core + Agent Runtime + Domain Profile + MCP Tooling**

的整体思路。

---

## 2. 设计目标

### 2.1 第一阶段目标

第一阶段优先实现通用 PDF 问答闭环，确保系统能够：

- 导入 PDF 文档
- 提取正文、标题、页码、表格等基础信息
- 建立 chunk 索引
- 支持 BM25 + 向量混合检索
- 支持答案生成与引用
- 支持基础多轮对话
- 支持 Agent 化查询流程
- 支持领域增强接口

### 2.2 中长期目标

在初版闭环基础上，逐步扩展：

- 更强的版面解析与表格处理
- 更强的跨文档分析
- 领域实体识别与元数据增强
- 外部工具与数据库接入
- MCP Server 化
- 任务型研究助手能力
- 可观测性、评测与回归体系

---

## 3. 核心设计原则

### 3.1 通用底座优先

所有能力优先围绕“复杂 PDF 的共性处理问题”设计，包括：

- 页面解析
- 文本结构化
- chunk 切分
- 混合检索
- 引用校验
- 多轮状态管理

### 3.2 领域增强后置

行业差异不写死在主流程里，而通过 Domain Profile 注入：

- 元数据抽取规则
- 别名词典
- 过滤条件
- Prompt 模板
- 输出模板
- 检索增强策略

### 3.3 Agent 只用于需要动态决策的部分

文档导入、解析、入库等强确定性步骤仍采用普通 workflow。  
问题理解、策略检索、证据归纳、引用审校等需要动态判断的步骤采用 Agent 化设计。

### 3.4 模块解耦

核心能力通过统一接口抽象，不与具体技术栈强绑定，便于替换：

- Parser
- Chunker
- Embedder
- VectorStore
- Retriever
- Reranker
- ChatModel
- MemoryStore
- ToolAdapter
- DomainProfile

### 3.5 先模块化，后协议化

第一阶段先在系统内部完成模块化。  
当某些模块需要跨进程复用、远程调用或独立演进时，再逐步 MCP 化。

---

## 4. 系统总体架构

整体架构分为四层：

1. **PDF Core**
2. **Agent Runtime**
3. **Domain Profiles**
4. **MCP / Tooling Layer**

### 4.1 架构图

```text
用户 / Chat UI
    |
    v
API Layer (FastAPI)
    |
    v
Agent Runtime (LangGraph)
    |
    +--> Supervisor
    +--> Query Planner
    +--> Retrieval Strategist
    +--> Synthesizer
    +--> Citation Auditor
    |
    v
PDF Core
    |
    +--> Loader
    +--> Parser
    +--> Cleaner
    +--> Chunker
    +--> Embedder
    +--> Indexer
    |
    v
Storage & Search Layer
    |
    +--> Metadata DB
    +--> Vector Index
    +--> BM25 Index
    +--> File Storage
    +--> Memory Store
    |
    v
Domain Profiles / MCP Tools
    |
    +--> Generic Profile
    +--> Finance Profile
    +--> Legal Profile
    +--> Research Profile
```

---

## 5. 四层架构说明

## 5.1 PDF Core

PDF Core 是整个系统的底座，负责处理所有 PDF 文档的通用问题。

主要职责包括：

- PDF 导入与文件管理
- 页面级解析
- 文本块抽取
- 表格抽取
- 标题层级识别
- section path 构建
- 文本清洗
- chunk 切分
- embedding 生成
- 索引入库

这一层不依赖具体行业。

### PDF Core 输出目标

输出一份统一的结构化文档对象，供上层检索与 Agent 使用。

示例：

```json
{
  "doc_id": "doc_001",
  "title": "示例 PDF",
  "doc_type": "report",
  "domain_profile": "generic",
  "pages": [
    {
      "page_no": 1,
      "blocks": [
        {
          "block_id": "b1",
          "type": "heading",
          "text": "1. Introduction",
          "bbox": [0, 0, 100, 20],
          "section_path": ["1. Introduction"]
        },
        {
          "block_id": "b2",
          "type": "paragraph",
          "text": "This is a paragraph...",
          "bbox": [0, 25, 100, 80],
          "section_path": ["1. Introduction"]
        }
      ]
    }
  ],
  "chunks": [
    {
      "chunk_id": "c1",
      "text": "This is a paragraph...",
      "page_no": 1,
      "section_path": ["1. Introduction"],
      "metadata": {
        "language": "en"
      }
    }
  ]
}
```

---

## 5.2 Agent Runtime

Agent Runtime 是系统的智能执行层。  
它基于 LangGraph 组织成有状态图流程，用于处理动态查询任务、多轮对话和多步骤推理。

这一层的核心思想是：

- 用确定性 workflow 处理稳定流程
- 用 Agent 处理需要动态决策的步骤
- 用共享状态维护会话与研究任务上下文

推荐采用：

> **Supervisor + 4 个 Specialist**

的结构。

---

## 5.3 Domain Profiles

Domain Profile 用于承载领域差异。  
它并不改变系统的主架构，而是在特定节点增强系统能力。

每个 Domain Profile 可以定义：

- 文档类型识别规则
- 元数据抽取规则
- 实体识别规则
- 别名词典
- 专有过滤字段
- 检索增强策略
- 专属 Prompt 模板
- 输出模板
- 评测集与规则

初期建议提供两个 profile：

- `generic`
- `finance`

后续扩展：

- `legal`
- `research`
- `policy`
- `manual`

---

## 5.4 MCP / Tooling Layer

MCP 层用于将系统内部能力逐步抽象成标准工具与资源，以支持：

- 模块独立演进
- 远程工具调用
- 外部系统接入
- 统一资源访问
- 更强的 Agent 工具生态

初版不要求所有模块 MCP 化，但需要预留统一工具接口和资源接口。

---

## 6. 通用文档数据模型

为支持跨领域扩展，系统需要采用通用文档模型，而不是一开始绑定金融字段。

## 6.1 Document 对象

```json
{
  "doc_id": "xxx",
  "title": "xxx",
  "doc_type": "report|contract|paper|manual|policy|other",
  "source_file": "xxx.pdf",
  "domain_profile": "generic|finance|legal|research",
  "pages": [],
  "chunks": [],
  "metadata": {
    "generic": {},
    "domain": {}
  }
}
```

## 6.2 Metadata 分层

### generic metadata

适用于所有 PDF：

- author
- publish_date
- language
- publisher
- file_name
- file_hash
- page_count
- document_category

### domain metadata

由特定 profile 增强：

#### finance
- company
- ticker
- broker
- report_type
- sector
- analyst
- rating
- metrics

#### legal
- contract_parties
- effective_date
- jurisdiction
- clauses
- obligations

#### research
- authors
- institution
- methods
- datasets
- metrics
- conclusions

---

## 7. 模块划分

建议项目目录：

```text
app/
├── api/                    # API 路由层
├── graph/                  # LangGraph 主图与子图
├── ingestion/              # PDF 导入链路
├── parsing/                # parser / cleaner / layout logic
├── retrieval/              # 检索与重排
├── generation/             # 回答生成与引用构建
├── memory/                 # 会话记忆与任务状态
├── profiles/               # Domain Profiles
├── tools/                  # 内部工具抽象
├── mcp/                    # MCP adapter / server
├── storage/                # db / vector / file / cache 适配
├── domain/                 # schema / entity / protocol
├── eval/                   # 评测与回归
└── config/                 # 配置
```

---

## 8. 技术选型建议

## 8.1 后端与编排

- **FastAPI**：API 层
- **LangGraph**：Agent Runtime 与状态图编排

## 8.2 PDF 处理

MVP 阶段建议：

- **PyMuPDF**：文本、页码、块提取
- **pdfplumber**：表格辅助抽取

后续可扩展：

- **Docling**
- OCR 组件
- 版面分析模型

## 8.3 检索层

### 最小实现集
- 向量检索：FAISS
- 关键词检索：BM25
- 重排序：Cross-Encoder / BGE Reranker

### 可扩展版本
- 向量检索：Qdrant
- 检索引擎：Elasticsearch / OpenSearch

## 8.4 存储层

- **PostgreSQL**：元数据、任务状态、会话、评测集
- **Redis**：缓存与短期会话
- **本地文件系统 / MinIO / S3**：原始 PDF 与中间产物

## 8.5 模型层

- Embedding 模型：支持中英混合检索的语义模型
- Reranker 模型：cross-encoder 类
- Generation 模型：Qwen / DeepSeek / OpenAI 兼容模型

---

## 9. 通用 PDF Core 设计

## 9.1 导入链路

导入链路保持确定性 workflow，不做 agent 化。

流程如下：

```text
upload_pdf
  -> validate_file
  -> parse_pdf
  -> clean_blocks
  -> build_sections
  -> chunk_document
  -> enrich_metadata
  -> embed_chunks
  -> build_indexes
  -> save_metadata
```

## 9.2 解析层设计

解析层至少要保留以下结构：

- page_no
- block_id
- block_type
- text
- bbox
- section_path
- table_html / table_json
- source_span

不绑定行业字段。

## 9.3 chunk 设计

通用 chunk 规则建议：

- 按 section 感知切分
- 表格单独成 chunk
- 图表标题单独成 chunk
- 保留页码与章节路径
- 支持小范围 overlap
- 允许 profile 注入额外切块规则

---

## 10. Agent Runtime 设计

系统采用：

> **Supervisor + 4 个 Specialist**

## 10.1 角色总览

### Supervisor
负责总控、路由、状态管理与最终答复。

### Query Planner
负责将用户问题转换成结构化任务与检索计划。

### Retrieval Strategist
负责动态选择检索策略并调用检索工具。

### Synthesizer
负责归纳证据、整合多文档信息、形成答案草稿。

### Citation Auditor
负责校验结论与证据的一致性，生成引用映射。

---

## 11. 共享状态设计

建议定义统一状态对象 `ResearchState`：

```python
class ResearchState(TypedDict):
    thread_id: str
    user_query: str
    normalized_query: str

    current_domain: str
    current_entities: dict
    current_time_range: dict
    current_intent: str

    retrieval_plan: dict
    retrieved_candidates: list
    selected_evidence: list

    draft_answer: str
    claims: list
    citation_map: list

    confidence: str
    next_action: str
    conversation_summary: str
```

关键字段说明：

- `current_domain`：当前启用的 profile
- `current_entities`：当前焦点实体
- `retrieval_plan`：本轮检索策略
- `selected_evidence`：最终采用的证据
- `claims`：待校验结论集合
- `citation_map`：引用映射
- `conversation_summary`：会话压缩摘要

---

## 12. 5 个角色详细设计

## 12.1 Supervisor

Supervisor 是系统唯一直接面对用户的 Agent。

职责包括：

- 读取 thread state
- 判断是否为追问
- 决定启用的 Domain Profile
- 调用 Specialist
- 控制输入输出边界
- 汇总结果
- 更新状态
- 处理失败与降级

适合处理：

- 指代继承
- 任务连续性
- 答案风格控制
- 结果汇总

---

## 12.2 Query Planner

Query Planner 不回答问题，只产出结构化任务计划。

输出内容包括：

- 问题类型
- 目标实体
- 时间范围
- 文档约束
- query variants
- 是否需要表格或原文
- 是否需要对比分析

示例输出：

```json
{
  "intent": "summarize",
  "entities": {
    "topics": ["pricing strategy"]
  },
  "time_range": {
    "start": null,
    "end": null
  },
  "doc_constraints": {
    "doc_types": ["report", "manual"]
  },
  "search_plan": {
    "query_variants": [
      "pricing strategy summary",
      "pricing strategy explanation"
    ],
    "must_have_terms": ["pricing"],
    "need_tables": false
  }
}
```

---

## 12.3 Retrieval Strategist

Retrieval Strategist 负责决定：

- 用哪种检索方式
- 是否加 filter
- 是否扩展别名
- 是否进行二次检索
- 是否触发表格专项搜索
- top_k 设置

它不直接输出最终答案，而输出候选证据集。

建议工具：

- `search_reports`
- `search_chunks`
- `search_tables`
- `get_report_metadata`
- `expand_aliases`
- `load_profile_filters`

---

## 12.4 Synthesizer

Synthesizer 的职责是：

- 基于证据构造答案草稿
- 处理跨文档汇总
- 对比不同文档或来源
- 区分共识与分歧
- 输出结构化 claim 列表

输出示例：

```json
{
  "draft_answer": "...",
  "claims": [
    {
      "claim": "...",
      "supporting_chunk_ids": ["c1", "c2"]
    }
  ],
  "confidence": "medium"
}
```

---

## 12.5 Citation Auditor

Citation Auditor 负责：

- 检查每条 claim 是否有证据支持
- 检查 claim 与 chunk 是否匹配
- 检查页码与文档映射
- 删除或降级 unsupported claim
- 生成最终引用映射

输出示例：

```json
{
  "verified_claims": [
    {
      "claim": "...",
      "chunk_ids": ["c1"]
    }
  ],
  "unsupported_claims": [],
  "citation_map": [
    {
      "claim": "...",
      "doc_id": "doc_1",
      "page_no": 5,
      "chunk_id": "c1"
    }
  ],
  "final_confidence": "high"
}
```

---

## 13. 主流程设计

## 13.1 问答主流程

```text
receive_query
  -> load_thread_state
  -> select_domain_profile
  -> query_planner
  -> retrieval_strategist
  -> synthesize_answer
  -> audit_citations
  -> finalize_answer
  -> update_memory
```

## 13.2 多轮追问处理

追问时不直接依赖长对话历史，而依赖 thread state：

- 当前实体
- 当前文档集合
- 当前时间范围
- 当前研究任务摘要

例如：

- 第 1 轮：请总结这个 PDF 的主要观点
- 第 2 轮：那它的风险点呢？

系统应自动继承“这个 PDF”与“上一轮总结任务”。

---

## 14. Domain Profile 设计

## 14.1 Domain Profile 接口

```python
class DomainProfile(Protocol):
    name: str

    def detect(self, document) -> bool: ...
    def enrich_metadata(self, document) -> dict: ...
    def extract_entities(self, text: str) -> dict: ...
    def expand_query(self, query: str, state: dict) -> list[str]: ...
    def build_filters(self, plan: dict) -> dict: ...
    def build_prompt_context(self) -> dict: ...
```

## 14.2 Generic Profile

默认 profile，适用于所有 PDF。

能力包括：

- 通用实体抽取
- 通用 query expansion
- 通用输出模板
- 通用 metadata

## 14.3 Finance Profile

首个领域增强包，提供：

- 公司 / ticker / 券商 / 行业 抽取
- 金融别名扩展
- 报告类型识别
- 财务指标关键词增强
- 金融问答模板
- 金融对比分析模板

## 14.4 Legal / Research Profile

后续可按相同方式新增，无需改动系统主框架。

---

## 15. 检索层设计

## 15.1 通用检索主链路

```text
query analysis
  -> keyword retrieval
  -> vector retrieval
  -> hybrid fusion
  -> rerank
  -> context packing
  -> evidence set
```

## 15.2 可配置项

所有以下内容都应配置化：

- chunk size
- overlap
- BM25 top_k
- vector top_k
- rerank top_n
- fusion strategy
- domain filters
- profile query expansion

## 15.3 表格专项检索

对复杂 PDF，表格往往承载关键信息。  
因此建议表格：

- 单独成 chunk
- 单独建索引字段
- 允许 Specialist 显式调用 `search_tables`

---

## 16. MCP 设计

## 16.1 初期策略

MCP 不作为 MVP 的前置依赖，但需要预留统一适配层。

### 内部统一工具接口

```python
class ToolExecutor(Protocol):
    def name(self) -> str: ...
    def description(self) -> str: ...
    def invoke(self, arguments: dict) -> dict: ...
```

### MCP Adapter

将内部工具映射成 MCP tools / resources / prompts。

---

## 16.2 推荐 MCP 工具拆分

### Document Search MCP

- `search_reports`
- `search_chunks`
- `search_tables`
- `get_chunk_by_id`
- `get_report_metadata`

### Document Resource MCP

- `report://{doc_id}`
- `page://{doc_id}/{page_no}`
- `chunk://{chunk_id}`

### Citation MCP

- `resolve_citation`
- `get_source_excerpt`
- `get_page_snapshot`

### Domain Enrichment MCP

- `extract_domain_entities`
- `expand_domain_aliases`
- `load_domain_schema`

---

## 17. 数据库设计建议

## 17.1 report 表

- report_id
- title
- doc_type
- domain_profile
- source_path
- publish_date
- parse_status
- metadata_json

## 17.2 chunk 表

- chunk_id
- report_id
- page_no
- section_path
- chunk_type
- text
- metadata_json

## 17.3 conversation 表

- conversation_id
- user_id
- current_domain
- created_at

## 17.4 message 表

- message_id
- conversation_id
- role
- content
- extracted_entities
- created_at

## 17.5 eval_case 表

- case_id
- domain_profile
- query
- expected_answer
- expected_chunks
- tags

---

## 18. 失败分支与降级策略

## 18.1 文档解析失败

- 标记 parse_status
- 回退到简单文本抽取
- 保留原始页码信息

## 18.2 Query Planner 无法识别领域

- 回退到 generic profile

## 18.3 Retrieval 结果不足

- 放宽 filter
- 扩大时间范围
- 切换 hybrid 检索
- 返回低置信度提示

## 18.4 Citation Auditor 否决过多 claim

- 输出保守版答案
- 明确指出证据不足部分

---

## 19. 评测体系设计

评测不应只做单一答案打分，而应分层进行。

## 19.1 检索评测

- Recall@k
- MRR
- nDCG
- 正确页码命中率
- 正确文档命中率

## 19.2 回答评测

- 是否回答了问题
- 是否引用正确
- 是否存在 unsupported claim
- 是否遗漏关键信息
- 是否有跨文档归纳错误

## 19.3 Domain Profile 评测

针对不同 profile 单独评测：

- generic 文档问答
- finance 报告问答
- legal 合同问答
- research 论文问答

---

## 20. 分阶段落地路线

## Phase 1：通用闭环 MVP

- PDF 导入
- 通用解析
- chunk
- FAISS + BM25
- 混合检索
- rerank
- 基础问答
- 引用输出
- generic profile
- 基础多轮状态

## Phase 2：Agent 化查询层

- Supervisor
- Query Planner
- Retrieval Strategist
- Synthesizer
- Citation Auditor
- LangGraph 状态图
- thread state 持久化

## Phase 3：领域增强

- finance profile
- 领域元数据抽取
- 别名扩展
- 金融问答模板
- 金融对比分析

## Phase 4：MCP 化与服务化

- search tools MCP 化
- citation tools MCP 化
- domain tools MCP 化
- profile 独立演进
- 支持外部工具接入

## Phase 5：高级能力

- OCR / layout 增强
- 图表理解
- 外部数据库查询
- 任务型研究助手
- 自动评测与回归

---

## 21. 推荐的最小落地顺序

建议严格按以下顺序推进：

1. 先定义通用文档 schema
2. 完成 PDF Core 的解析与 chunk
3. 接向量检索与 BM25
4. 完成混合检索与 rerank
5. 完成基础问答与引用
6. 接入 LangGraph 状态图
7. 引入 Supervisor + 4 个 Specialist
8. 实现 generic profile
9. 实现 finance profile
10. 增加 MCP adapter

---

## 22. 总结

本项目应设计为一个**面向复杂 PDF 文档的通用 Agentic RAG 系统**，而不是一个只服务于单一行业的垂直 demo。系统底座围绕 PDF 文档的共性处理能力展开，通过 PDF Core 提供解析、切块、索引、检索和引用能力；通过 Agent Runtime 提供多轮、有状态、可规划的查询处理能力；通过 Domain Profile 机制实现领域增强；通过 MCP 机制支持模块独立演进和外部能力接入。整体架构遵循“通用底座优先、领域增强后置、Agent 用于动态决策、模块先本地解耦后协议化”的路线，兼顾第一阶段最小闭环落地和后续跨领域扩展能力。
