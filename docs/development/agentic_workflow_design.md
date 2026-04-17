# Agentic 工作流设计与实现路书

## 相关文档

- 开发计划：[`development_plan.md`](development_plan.md)
- API 与检索开发说明：[`api_retrieval_development_notes.md`](api_retrieval_development_notes.md)
- 最小可运行系统说明：[`../guides/minimal_system_guide.md`](../guides/minimal_system_guide.md)
- 当前 RAG 缺口分析：[`../analysis/current_rag_gap_analysis.md`](../analysis/current_rag_gap_analysis.md)
- 页面模板分类与图表页分区设计：[`../analysis/page_template_classification_design.md`](../analysis/page_template_classification_design.md)

## 1. 文档目标

本文档用于定义当前项目进入 agentic 阶段时的第一版设计方案，并给出一条可直接落代码的实现路书。

当前重点不是一次性做完整多智能体系统，而是先建立：

1. 一个**可解释、可测试、可扩展**的工作流框架
2. 一个独立的**路由模块**
3. 一套面向 document / block / chunk 的**类型标注体系**
4. 一个能够把现有 retrieval / generation 主链纳入编排的轻量 agentic runtime

一句话目标：

**先把“怎么路由”和“当前证据是什么”这两件事做清楚，再逐步扩展成真正的 agentic 工作流。**

## 2. 当前基础与问题

### 2.1 当前已经具备的基础

项目已经有以下主链能力：

- PDF ingestion
- parser / cleaner / section builder / chunker
- BM25 + vector + hybrid retrieval
- 可插拔 reranker
- 问答生成
- citation / evidence 返回
- CLI / API / Frontend

同时，`graph` 目录下已经有骨架：

- [`../../src/graph/workflow.py`](../../src/graph/workflow.py)
- [`../../src/graph/nodes/supervisor.py`](../../src/graph/nodes/supervisor.py)
- [`../../src/graph/nodes/query_planner.py`](../../src/graph/nodes/query_planner.py)
- [`../../src/graph/nodes/retrieval_strategist.py`](../../src/graph/nodes/retrieval_strategist.py)
- [`../../src/graph/nodes/synthesizer.py`](../../src/graph/nodes/synthesizer.py)
- [`../../src/graph/nodes/citation_auditor.py`](../../src/graph/nodes/citation_auditor.py)

以及一份已有的共享状态定义：

- [`../../src/domain/models/state.py`](../../src/domain/models/state.py)

### 2.2 当前还缺少什么

当前 `graph` 层仍然是 placeholder，缺少：

- 显式路由决策
- workflow 状态机
- node 间跳转规则
- 结构化路由决策对象
- 证据类型建模
- agentic 调试与日志语义

当前系统虽然已经能“检索 + 回答”，但还没有真正做到：

- 根据问题动态决定下一步
- 根据证据质量动态重试
- 根据证据类型决定后续分支

## 3. 设计原则

### 3.1 先做显式状态机，不做黑盒编排

第一版 agentic 工作流建议优先使用：

- 显式状态
- 显式路由
- 显式节点边界

而不是让 LLM 直接决定整个流程。

原因：

- 更可控
- 更可测试
- 更容易调试
- 更适合当前项目阶段

### 3.2 Router 只负责决策，不负责执行

路由模块应只回答：

- 下一步应该去哪个 node
- 为什么去
- 是否继续

它不应该直接执行业务逻辑。

### 3.3 节点只负责本职工作

建议边界如下：

- `query_planner`：理解问题并形成计划
- `retrieval_strategist`：组织检索与候选生成
- `synthesizer`：基于证据组织答案
- `citation_auditor`：检查引用与答案关系
- `router`：决定下一步去哪里

### 3.4 类型标注优先于复杂智能调度

如果不先回答“当前证据是什么类型”，后续 router、retrieval、rerank、frontend 都只能看到一堆无差别的 chunk。

因此：

**类型标注不是附属优化，而是 agentic 路由的重要前置基础。**

## 4. 总体架构

推荐的第一版结构如下：

```text
User Query
  -> Supervisor
  -> Router
  -> Query Planner
  -> Router
  -> Retrieval Strategist
  -> Router
  -> Synthesizer
  -> Router
  -> Citation Auditor
  -> Router
  -> Finish
```

其中允许出现回路：

- `retrieval -> retrieval`
- `synthesizer -> retrieval`
- `citation_auditor -> retrieval`
- `citation_auditor -> synthesizer`

## 5. 路由模块设计

## 5.1 路由模块职责

Router 的职责是根据当前 `ResearchState` 决定：

- `next_node`
- `reason`
- `route_type`
- `should_continue`

它不负责：

- 调用外部模型
- 检索
- 生成答案
- 写 citation

## 5.2 推荐新增模块

建议第一版新增：

```text
src/graph/router.py
src/graph/route_rules.py
src/domain/models/routing.py
```

### `routing.py`

定义：

- 路由节点枚举
- `RouteDecision`

### `router.py`

定义：

- `Router`
- `decide(state) -> RouteDecision`

### `route_rules.py`

定义：

- 纯规则函数
- 状态判断函数
- 是否证据充分等判断逻辑

## 5.3 推荐的 `RouteDecision`

建议设计为：

```python
{
    "next_node": "retrieval_strategist",
    "reason": "missing_evidence",
    "route_type": "retrieve_then_synthesize",
    "should_continue": True
}
```

建议字段：

- `next_node`
- `reason`
- `route_type`
- `should_continue`

必要时可扩展：

- `debug_signals`
- `retry_count`
- `priority`

## 5.4 第一版应覆盖的路由分支

建议第一版先覆盖以下最小分支：

### `plan`

条件：

- 没有 `current_intent`
- 没有 `retrieval_plan`

动作：

- 路由到 `query_planner`

### `retrieve`

条件：

- 已有意图 / 计划
- 还没有候选证据

动作：

- 路由到 `retrieval_strategist`

### `refine_retrieve`

条件：

- 有候选证据
- 但证据质量不足

动作：

- 再次进入 `retrieval_strategist`

### `synthesize`

条件：

- 已经有足够证据
- 尚未生成草稿答案

动作：

- 路由到 `synthesizer`

### `audit`

条件：

- 已有 `draft_answer`
- 需要做 citation / claim 审查

动作：

- 路由到 `citation_auditor`

### `finish`

条件：

- 已有答案
- 已有 citation 审查结果

动作：

- 结束 workflow

## 5.5 第一版路由依据

第一版建议只用通用状态信号判断：

- `current_intent`
- `retrieval_plan`
- `retrieved_candidates`
- `selected_evidence`
- `draft_answer`
- `claims`
- `citation_map`
- `confidence`
- `next_action`

不要在 router 里引入：

- 行业词典
- 公司名硬编码
- 财务指标硬编码

这些应属于：

- profile 层
- planner 层
- retrieval / rerank 特征层

## 6. 类型标注设计

## 6.1 为什么要做类型标注

当前项目的数据来源已经不是单一正文，而是混合了：

- 正文段落
- 标题
- 表格
- 图表标题
- 图例 / 轴标签
- source note
- 页眉页脚
- 封面元信息
- 目录型内容

如果不做类型标注，会导致：

- router 不知道当前证据是否有效
- retrieval 无法按结构角色调权
- reranker 缺少结构特征
- frontend 无法有区分地展示证据

## 6.2 建议分三层类型

### A. 文档级 `document_source_type`

描述整份文档的来源性质，例如：

- `research_report`
- `company_announcement`
- `presentation`
- `manual`
- `mixed_pdf`
- `unknown`

### B. block/page 级 `content_role`

描述页面元素角色，例如：

- `narrative_paragraph`
- `heading`
- `list_item`
- `table`
- `table_caption`
- `figure_caption`
- `chart_label`
- `source_note`
- `header`
- `footer`
- `cover_meta`
- `toc_entry`
- `sidebar_note`

### C. chunk 级 `evidence_type`

描述检索证据类型，例如：

- `narrative_evidence`
- `table_evidence`
- `chart_evidence`
- `caption_evidence`
- `navigational_evidence`
- `metadata_evidence`
- `low_value_evidence`

## 6.3 推荐的最小实现字段

### 文档级

建议在 `Document.metadata` 增加：

- `document_source_type`
- `source_collection`
- `document_profile`

### block 级

建议在 block metadata 增加：

- `page_profile`
- `zone`
- `content_role`
- `role_confidence`

### chunk 级

建议在 chunk metadata 增加：

- `evidence_type`
- `source_roles`
- `source_zones`
- `source_page_profile`
- `evidence_quality_hint`

## 6.4 类型标注与路由的关系

这套标注会直接帮助 router：

1. 判断证据是否“有”且“有用”
2. 区分叙述性证据与低价值导航证据
3. 区分是否应该继续检索
4. 区分是否可以进入 synthesis

例如：

- 只有 `caption_evidence` / `chart_label`，不应视为充分证据
- 已有多个 `narrative_evidence` / `table_evidence`，可以进入 synthesis

## 7. 状态模型建议

当前已有：

- [`../../src/domain/models/state.py`](../../src/domain/models/state.py)

建议下一步扩展字段，至少补：

- `route_decision`
- `workflow_status`
- `document_source_types`
- `candidate_evidence_types`
- `selected_evidence_types`
- `retry_count`
- `max_retry_count`

例如：

```python
class ResearchState(TypedDict, total=False):
    ...
    route_decision: dict[str, Any]
    workflow_status: str
    candidate_evidence_types: list[str]
    selected_evidence_types: list[str]
    retry_count: int
    max_retry_count: int
```

## 8. 节点边界建议

## 8.1 SupervisorNode

职责：

- 启动 workflow
- 调用 router
- 记录路由结果

不做：

- 检索
- synthesis
- audit

## 8.2 QueryPlannerNode

职责：

- 理解 query
- 规范化问题
- 填充：
  - `normalized_query`
  - `current_intent`
  - `current_entities`
  - `current_time_range`
  - `retrieval_plan`

## 8.3 RetrievalStrategistNode

职责：

- 调用现有 `SearchService`
- 形成 `retrieved_candidates`
- 选择 `selected_evidence`
- 汇总证据类型特征

## 8.4 SynthesizerNode

职责：

- 使用 `selected_evidence`
- 调用现有 generation 主链
- 形成：
  - `draft_answer`
  - `claims`
  - `confidence`

## 8.5 CitationAuditorNode

职责：

- 校验 draft answer / claims / evidence
- 输出：
  - `citation_map`
  - `confidence`
  - 必要时要求回退到 retrieval 或 synthesis

## 9. Workflow 设计

当前 `workflow.py` 还是 placeholder，建议第一版实现成一个显式循环：

```text
while should_continue:
  1. router 决定 next_node
  2. 执行对应 node
  3. 更新 state
  4. 继续 router
```

建议控制：

- 最大循环步数
- 最大重试次数
- 每一步日志输出

建议输出调试信息：

- 当前 node
- route decision
- reason
- selected evidence count
- selected evidence types

## 10. 与现有 retrieval / generation 的接法

当前不建议重写 retrieval / generation 主链，而是做“包裹式接入”。

### retrieval

复用：

- [`../../src/retrieval/search_service.py`](../../src/retrieval/search_service.py)

让 `RetrievalStrategistNode` 调用它。

### generation

复用：

- [`../../src/generation/qa_service.py`](../../src/generation/qa_service.py)

但建议逐步拆出“检索后半链”能力，或者至少让 synthesize / audit 节点可以分别调用：

- `AnswerGenerator`
- `CitationAuditor`

## 11. 第一版不建议做的事

当前不建议一开始就做：

1. LLM 直接决定整个 workflow
2. 动态任意 DAG 编排
3. 把领域 profile 直接塞进 router
4. 一开始就实现完整多 agent 并发
5. 在 router 中加入大量业务词典

这些会让第一版变得难测、难控、难调试。

## 12. 代码实现路书

下面是建议的分阶段落地顺序。

## Phase 0：补数据结构

目标：

- 为 agentic runtime 建好基础类型与状态结构

建议改动：

1. 新增 `src/domain/models/routing.py`
2. 扩展 `src/domain/models/state.py`
3. 在 `Document / Chunk metadata` 中预留类型字段

交付物：

- `RouteDecision`
- 扩展版 `ResearchState`
- chunk 级 `evidence_type` 预留位

## Phase 1：实现轻量 Router

目标：

- 基于显式规则返回下一步路由决策

建议新增：

- `src/graph/router.py`
- `src/graph/route_rules.py`

交付物：

- `Router.decide(state)`
- 最小规则集：
  - `plan`
  - `retrieve`
  - `synthesize`
  - `audit`
  - `finish`

测试重点：

- 空 state 如何路由
- 证据不足如何回到 retrieval
- 有答案但无 citation 如何进入 audit

## Phase 2：让 Workflow 跑起来

目标：

- 将当前 placeholder workflow 变成可执行工作流

建议改动：

- `src/graph/workflow.py`
- `src/graph/nodes/supervisor.py`

交付物：

- 显式循环式 workflow
- 最大步数保护
- route decision 写回 state

## Phase 3：让节点消费现有主链

目标：

- 把现有 retrieval / generation 主链接入 graph

建议改动：

- `src/graph/nodes/query_planner.py`
- `src/graph/nodes/retrieval_strategist.py`
- `src/graph/nodes/synthesizer.py`
- `src/graph/nodes/citation_auditor.py`

交付物：

- planner 能写 retrieval_plan
- retrieval strategist 能调用 SearchService
- synthesizer 能调用 answer generation
- citation auditor 能调用 citation 校验

## Phase 4：补类型标注第一版

目标：

- 让 router 和 retrieval 能消费 chunk 类型

建议改动：

- parser / chunker metadata
- retrieval candidate serialization
- state 中 evidence type 统计

交付物：

- 最小 `content_role / evidence_type`
- `selected_evidence_types`
- 基于类型的 router 判断

## Phase 5：观测与调试

目标：

- 让 agentic workflow 可解释、可排查

建议补：

- workflow 日志
- route decision 日志
- node 输入输出摘要
- 简单 CLI / API 调试输出

## 13. 推荐的近期实现顺序

如果只看当前分支最合理的推进顺序，我建议：

1. `RouteDecision + ResearchState` 扩展
2. `Router` 实现
3. `QueryWorkflow` 显式状态机化
4. `RetrievalStrategistNode` 接现有 SearchService
5. `SynthesizerNode` / `CitationAuditorNode` 接现有 generation 主链
6. 补第一版 `content_role / evidence_type`

## 14. 当前结论

当前开始做 agentic，最合理的切入点就是：

- 先做轻量路由
- 同时建立类型标注体系

这样做的价值在于：

- 不会推翻现有 retrieval / generation 主链
- 能快速把 placeholder graph 变成真正可运行的 workflow
- 为后续复杂路由、多轮对话、session、domain profile、结构化证据消费打基础

一句话总结：

**第一版 agentic 不应该从“多写几个 agent”开始，而应该从“显式路由 + 类型标注 + 可执行状态机”开始。**
