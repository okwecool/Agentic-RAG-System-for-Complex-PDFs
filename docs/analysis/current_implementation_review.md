# 当前实现审查与收敛建议

## 1. 背景

本文档用于从“实现是否偏离、是否存在代码冗余、是否存在无效实现”三个维度，对当前项目状态做一次收敛性审查。

目标不是重复已有设计文档，而是回答以下问题：

- 当前实现是否已经明显偏离最初设计目标
- 当前代码里是否存在可见的重复实现
- 当前有哪些能力只是“看起来有”，但实际上还没有形成可靠生产能力
- 后续应该优先从哪些方面继续收敛

---

## 2. 总体判断

当前项目没有出现方向性跑偏，主线仍然围绕：

- PDF 解析与切块
- 混合检索与 rerank
- 生成与引用
- agentic workflow
- 前端/API/多轮能力

展开。

但当前实现确实存在比较明显的“先铺功能、后收边界”的现象，主要表现在：

1. 一部分模块已经可用，但还没有形成真正稳定的生产契约
2. 一部分能力已经写入 state 或写入存储，但还没有被后续节点真正消费
3. 一部分 placeholder/兼容分支仍然停留在主链里，容易掩盖 wiring 问题
4. 一部分服务层已经开始出现重复实现，后续有漂移风险

一句话概括：

**当前系统已经有了“可运行主链”，但部分实现仍处在“可演示、未完全收敛”的阶段。**

---

## 3. 主要偏离点

### 3.1 Agent Runtime 与最初设计存在实现路径偏离

最初设计强调的是更完整的 agent runtime / graph orchestration 层，而当前实际实现是：

- 基于 `ResearchState`
- 基于显式 `Router`
- 基于 `QueryWorkflow`
- 手工循环 dispatch 各节点

对应代码：

- `src/graph/workflow.py`
- `src/graph/router.py`

这种实现方式本身没有问题，优点是：

- 可解释
- 易测试
- 易逐步演进

但需要注意，它与“更重的图编排框架式设计”并不完全一致。后续如果继续扩展更多节点、失败恢复、人工介入、多 agent 协作，就需要重新评估当前 workflow 结构是否还能保持简单。

当前判断：

- **这是实现路径偏离，但不是错误偏离**
- 当前阶段仍然是合理取舍

### 3.2 多轮对话已经有 session，但还不是完整上下文对话

当前已经实现：

- `session_id`
- `messages`
- `conversation_summary`
- `current_entities`
- `ConversationResolverNode`
- `FileThreadStore`

对应代码：

- `src/generation/agentic_qa_service.py`
- `src/memory/thread_store.py`
- `src/memory/summarizer.py`
- `src/graph/nodes/conversation_resolver.py`

但当前真正使用这些会话信息的，基本只有 `ConversationResolverNode`。

`QueryPlannerNode` 仍然主要依据当前 query 做规则规划，`RetrievalStrategistNode` 也没有真正继承历史约束。

这意味着当前更准确的状态是：

**带有持久化 session 的单轮问答 + 轻量 query rewrite**

而不是：

**真正上下文感知的多轮对话系统**

---

## 4. 明显的代码冗余

### 4.1 `QaService` 和 `AgenticQaService` 存在重复的响应拼装逻辑

当前两处都实现了：

- citation 构造
- evidence 序列化
- 返回结果组装

对应代码：

- `src/generation/qa_service.py`
- `src/generation/agentic_qa_service.py`

重复点包括：

- `_build_citations`
- `_serialize_evidence`
- 返回字段拼接方式

当前风险：

- 现在两边仍然基本一致
- 后续如果 citation schema、evidence schema、前端展示字段继续演进，很容易出现两套逻辑漂移

建议：

- 抽一层公共 response serializer
- 或至少抽成共享 helper

### 4.2 `SupervisorNode` 当前几乎没有独立价值

当前 `SupervisorNode` 只做：

- 写入 `route_decision`
- 写入 `next_action`
- 保证 `workflow_status=running`

对应代码：

- `src/graph/nodes/supervisor.py`

但真正的：

- 节点分发
- trace 记录
- finish 状态处理
- 降级/失败结束

都在 `src/graph/workflow.py` 中完成。

所以当前 `SupervisorNode` 更像一个“名义存在的层”，而不是真正有价值的调度节点。

建议二选一：

1. 把它做实，承担更明确的 orchestration 职责
2. 直接删掉，把职责并回 workflow

---

## 5. 无效实现或低效实现

### 5.1 `ConversationResolverNode` 存在编码污染，规则不可靠

当前最明显的问题之一，是：

- `src/graph/nodes/conversation_resolver.py`

里面大量中文规则词、停用词、裁剪正则都出现了编码污染。

表现包括：

- `_needs_resolution()` 中的上下文触发词异常
- `_inject_anchor_entity()` 中的前缀词异常
- `_looks_like_entity()` 中的停用词异常
- `_trim_entity_candidate()` 中的正则模式异常

这意味着当前 resolver 虽然在某些 case 里能工作，但有相当一部分成功，实际上来自：

- 回退逻辑
- 实体抽取碰巧命中

而不是稳定可靠的中文规则匹配。

这是当前最典型的：

**“实现存在，但可靠性不足”**

### 5.2 `conversation_summary` 目前更多是展示字段，而不是决策输入

当前 `conversation_summary` 已经被：

- 持久化
- 返回给前端
- 前端展示

但它并没有真正进入：

- planner 的意图判断
- retrieval 的约束继承
- synthesis 的回答组织

因此当前它的真实定位更接近：

- 会话摘要展示
- 为后续升级预留

而不是已经形成生产价值的上下文驱动信号。

### 5.3 Placeholder 分支仍然在主链中保留，容易掩盖 wiring 问题

当前多个节点仍然保留了“没有真实依赖时自动返回 placeholder 结果”的逻辑，例如：

- `src/graph/nodes/retrieval_strategist.py`
- `src/graph/nodes/synthesizer.py`
- `src/graph/nodes/citation_auditor.py`

这对单元测试或局部开发是方便的，但问题在于：

- 如果某条入口误用了默认构造，而不是 `from_settings()`
- 系统不会立刻 fail fast
- 而是生成一套“看起来能跑”的假结果

这会让真实问题更难定位。

建议：

- 测试场景保留 placeholder 注入能力
- 真实运行入口尽量走严格构造
- 对生产入口缺少依赖的情况，优先显式失败，而不是静默补假数据

---

## 6. 当前哪些能力是“半完成态”

以下能力已经存在，但还没有完全形成稳定闭环：

### 6.1 多轮上下文理解

已完成：

- session 持久化
- 消息保存
- 摘要保存
- resolver 节点

未完成：

- planner 消费历史消息和摘要
- retrieval 继承历史约束
- synthesis 感知 follow-up 语义

### 6.2 失败/降级契约

已完成：

- `planner_result`
- `retrieval_result`
- `audit_result`
- `failure_info`
- `degradation_notes`
- `workflow_status=completed/degraded/failed`

未完成：

- 前端更完整展示这些失败/降级信息
- API 层对外更明确的错误分类
- 更细粒度的恢复/重试策略

### 6.3 citation 严格度

已完成：

- unsupported claim 初步识别
- 审计节点可把 unsupported 写回 state

未完成：

- claim 级严格支撑映射
- answer span 到证据 span 的细粒度绑定

---

## 7. 建议的收敛顺序

### P0：修掉不稳定基础

1. 修复 `ConversationResolverNode` 中的编码污染与规则异常
2. 明确生产入口和测试入口的差异，减少 placeholder 静默兜底

### P1：收紧状态与服务边界

1. 让 `conversation_summary / messages / current_entities` 真正进入 planner
2. 让 retrieval 支持继承历史主体、时间等约束
3. 抽取 `QaService / AgenticQaService` 的公共 response serializer

### P1：收掉无效抽象

1. 评估 `SupervisorNode` 去留
2. 如果短期不做实，建议删除

### P2：把“半完成态”能力做实

1. 多轮上下文从 resolver-only 升级为 planner/retrieval-aware
2. citation 从轻量审计升级为更严格 claim 对齐
3. failure/degrade 信息前端化与产品化

---

## 8. 结论

当前项目的主要问题不是“方向错误”，而是：

**有一部分能力已经铺开，但还没有完全收口。**

更具体地说：

- 没有明显的架构性跑偏
- 但存在实现路径偏离
- 存在服务层重复实现
- 存在少量名义抽象和低效占位
- 存在“已经写进 state/存储，但还没有真正被后续流程消费”的半完成态能力

因此后续最值得做的工作，不是继续扩入口，而是：

1. 修 resolver 的可靠性
2. 把多轮上下文真正接入 planner/retrieval
3. 收掉重复的 response 组装
4. 明确 placeholder 和生产运行路径的边界
5. 清理无效抽象

只有这些收口之后，当前 agentic 主链才会从“可运行”进一步走向“可长期维护”。
