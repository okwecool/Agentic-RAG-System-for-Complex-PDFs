# 最小重构任务表

## 1. 目标

本任务表用于配合：

- `docs/development/minimal_refactor_evolution_plan.md`

将“最小重构并逐步朝设计演进”的方案，拆解为可执行任务。

---

## 2. P0 任务

## P0-1 修复 Conversation Resolver 的编码与规则可靠性

### 问题

- `ConversationResolverNode` 中存在中文规则编码污染
- 当前多轮补全存在偶然命中，不够稳定

### 涉及文件

- `src/graph/nodes/conversation_resolver.py`
- `tests/unit/test_graph_workflow.py`

### 目标

- 修正所有规则词、停用词、裁剪正则
- 补充稳定的中文 follow-up case 测试

### 完成标准

- 能稳定处理：
  - `那它今年呢？`
  - `这家公司最近怎么样？`
  - `那利润呢？`

---

## P0-2 明确 SupervisorNode 去留

### 问题

- `SupervisorNode` 当前职责极弱
- 会增加理解成本

### 涉及文件

- `src/graph/nodes/supervisor.py`
- `src/graph/workflow.py`

### 目标

二选一：

1. 删除 `SupervisorNode`
2. 或赋予其真正的调度职责

### 推荐

优先删除，并把必要逻辑并回 `QueryWorkflow`

### 完成标准

- graph 主入口清晰
- 不再保留名义抽象

---

## P0-3 收紧生产入口，限制 placeholder 静默兜底

### 问题

- 当前默认构造路径可能给出 placeholder 结果
- 容易掩盖 wiring 问题

### 涉及文件

- `src/graph/nodes/retrieval_strategist.py`
- `src/graph/nodes/synthesizer.py`
- `src/graph/nodes/citation_auditor.py`
- `src/graph/workflow.py`

### 目标

- 测试仍可注入 fake 依赖
- 真实运行入口缺依赖时显式失败

### 完成标准

- `from_settings()` 路径不再隐式生成 placeholder 结果
- 运行错误更早暴露

---

## 3. P1 任务

## P1-1 抽离公共 Response Builder

### 问题

- `QaService` 和 `AgenticQaService` 存在重复 citation/evidence/response 拼装逻辑

### 涉及文件

- `src/generation/qa_service.py`
- `src/generation/agentic_qa_service.py`
- 新增 `src/generation/response_builder.py`

### 目标

抽离：

- citation 构造
- evidence 序列化
- response payload assembly

### 完成标准

- 两个 service 不再保留重复的 `_build_citations` / `_serialize_evidence`
- 输出 schema 保持一致

---

## P1-2 让 QueryPlannerNode 真正消费会话状态

### 问题

- 目前 planner 仍主要围绕当前 query 规则规划

### 涉及文件

- `src/graph/nodes/query_planner.py`
- `src/domain/models/state.py`
- `src/domain/models/workflow_contracts.py`

### 目标

planner 读取：

- `resolved_user_query`
- `messages`
- `conversation_summary`
- `current_entities`

并输出更完整的 plan：

- `entity_scope`
- `time_scope`
- `carry_over_constraints`

### 完成标准

- planner 不再是“单轮 query 规则器”
- 多轮上下文开始进入 planning 逻辑

---

## P1-3 让 RetrievalStrategistNode 消费会话约束

### 问题

- retrieval 当前仍主要只读当前 query 和 top_k

### 涉及文件

- `src/graph/nodes/retrieval_strategist.py`
- `src/retrieval/search_service.py`

### 目标

支持使用 planner 输出中的：

- 主体约束
- 时间约束
- 继承的 topic / compare 约束

### 完成标准

- follow-up 问题能沿用上轮主体与时间范围
- retrieval 结果不再只依赖 query rewrite

---

## P1-4 让 failure/degrade 信息真正进入前端展示

### 问题

- 当前已经有 `failure_info / degradation_notes`
- 但前端只做了有限展示

### 涉及文件

- `src/frontend/controller.py`
- `src/frontend/app.py`

### 目标

前端更清晰展示：

- workflow status
- degraded reason
- failed stage

### 完成标准

- 用户能直接看到“为什么降级/失败”
- 不需要查看后端日志才能理解问题

---

## 4. P2 任务

## P2-1 让 GenericProfile 成为真实注入点

### 问题

- 当前 profile 体系存在感不足

### 涉及文件

- `src/profiles/*`
- `src/graph/nodes/query_planner.py`
- `src/graph/nodes/retrieval_strategist.py`
- `src/generation/*`

### 目标

让 `GenericProfile` 至少能参与：

- entity extract
- query expand
- filter build
- prompt context

### 完成标准

- profile 不再只是目录或概念
- 主链开始真正依赖 profile 接口

---

## P2-2 PDF Core 中继续推进页面结构信号接入

### 问题

- `page_profile / zone / content_role` 还没有完全成为主链质量信号

### 涉及文件

- `src/parsing/*`
- `src/chunking/*`
- `src/retrieval/*`

### 目标

让页面结构信号真正进入：

- chunking
- evidence typing
- retrieval ranking

### 完成标准

- mixed/chart-like/label-dense 页面不再大量污染正文证据

---

## P2-3 提升 citation 到 claim-aware 严格模式

### 问题

- 当前 citation audit 还是轻量版

### 涉及文件

- `src/generation/citation_auditor.py`
- `src/graph/nodes/citation_auditor.py`

### 目标

逐步做实：

- claim-support mapping
- unsupported span 检测
- 更严格 confidence 调整

### 完成标准

- citation 不只是“有引用”
- 而是“claim 被明确支撑”

---

## 5. 推荐执行顺序

推荐按下面顺序落地：

1. `P0-1`
2. `P0-2`
3. `P0-3`
4. `P1-1`
5. `P1-2`
6. `P1-3`
7. `P1-4`
8. `P2-1`
9. `P2-2`
10. `P2-3`

---

## 6. 本周优先建议

如果只做一轮短周期开发，建议优先：

1. 修 `ConversationResolverNode`
2. 去掉或做实 `SupervisorNode`
3. 抽 `response_builder`
4. 让 planner 读取会话状态

这四步做完之后，当前项目会明显从：

- “功能已经很多，但边界还松”

进入：

- “核心主链更加稳定，且更接近最初设计”
