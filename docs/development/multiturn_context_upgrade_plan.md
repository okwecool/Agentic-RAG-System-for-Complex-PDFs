# 多轮上下文对话升级方案

## 1. 当前状态

当前系统已经具备一版轻量多轮能力，但还不能算真正完整的上下文对话。

已具备的能力：

- `session_id` 已经可以在前后端与 agentic service 之间透传
- 服务端已有内存版 `session store`
- 会话状态中已经保存最近若干轮 `messages`
- 已有 `conversation_summary`
- graph 中已接入 `conversation_resolver`
- 简单追问场景下，可把类似“那它今年呢？”补全为更完整的问题

当前的主要局限：

- planner 还没有深度消费完整对话历史
- `conversation_resolver` 仍然是轻量规则版
- retrieval 还没有真正继承上一轮的主体、时间、约束
- synthesis 仍然主要按当前轮证据回答
- 当前 `session store` 是内存版，服务重启后会丢失

因此，当前系统更准确的定位是：

> 带会话状态的单轮问答 + 轻量上下文补全

而不是成熟的上下文对话 agent。

## 2. 总体目标

升级目标不是简单“保存更多历史消息”，而是把多轮上下文真正接入以下链路：

- 会话理解
- query planning
- retrieval strategy
- answer synthesis
- citation alignment

最终希望达到：

- 系统能理解承接式追问
- 系统能继承上一轮主体、时间、约束
- 系统能处理简单比较与省略表达
- 回答体现对话连续性，而不是多个单轮回答的拼接

## 3. 分阶段实现方案

### Phase 1：让会话状态真正进入工作流

目标：

- 历史不只是被存储，而是成为 workflow 的正式输入

本阶段重点：

- 稳定 `ResearchState` 中与会话相关的字段
- 统一 `session store` 中的持久化状态结构
- 让 planner 能读取最近轮次消息与摘要

建议补充或稳定的字段：

- `session_id`
- `turn_index`
- `messages`
- `conversation_summary`
- `resolved_user_query`
- `conversation_entities`
- `conversation_constraints`
- `last_user_intent`

实现重点：

- 让 `QueryPlannerNode` 不再只依赖 `user_query`
- planner 同时读取：
  - `resolved_user_query`
  - `conversation_summary`
  - 最近 1~3 轮消息

阶段完成标准：

- planner 的输入已经具备会话上下文
- 历史消息和摘要对 planning 开始生效

### Phase 2：把 conversation resolver 升级为会话理解器

目标：

- 让系统更稳定地处理追问、省略、指代与延续性表达

本阶段重点：

- 将当前轻量规则版 `conversation_resolver` 升级为更清晰的会话理解模块

建议职责：

- 指代消解
  - 例如：`它`、`这家公司`、`前面那个`
- 省略补全
  - 例如：`那今年呢？`、`利润呢？`
- 比较承接
  - 例如：`那和英特尔比呢？`
- 约束延续
  - 例如：`还是只看 2025 年`

建议输出：

- `resolved_user_query`
- `resolved_entities`
- `conversation_constraints`
- `dialogue_act`

其中 `dialogue_act` 可先从以下几类开始：

- `new_topic`
- `follow_up`
- `compare`
- `clarification`

阶段完成标准：

- 当前轮 query 能稳定改写为可检索、可规划的问题
- 简单代词、省略、延续性追问明显改善

### Phase 3：让 planning 与 retrieval 真正上下文化

目标：

- 不只是改写 query，而是让 retrieval strategy 感知会话上下文

本阶段重点：

- planner 输出 richer retrieval plan
- retrieval 继承上一轮主体、时间和约束
- retrieval ranking / filtering 消费对话上下文

建议扩展 `retrieval_plan`：

- `query_focus`
- `carry_over_constraints`
- `comparison_targets`
- `time_scope`
- `entity_scope`
- `dialogue_act`

建议实现：

- 当前轮未显式指定主体时，默认继承上一轮主体
- 当前轮未显式指定时间范围时，默认继承上一轮时间约束
- 对比较类问题，优先检索多个主体共同出现或相近主题的证据

阶段完成标准：

- 多轮提升不只体现在 query rewrite 上
- retrieval 的策略和排序开始真正受历史影响

### Phase 4：让 answer synthesis 成为真正的对话生成

目标：

- 回答不仅要正确，还要体现上下文连续性

本阶段重点：

- synthesis 输入加入会话上下文
- prompt 区分新问题、追问、比较、澄清
- 回答层体现前后轮连续性

建议做法：

- synthesizer 读取：
  - `resolved_user_query`
  - `conversation_summary`
  - `dialogue_act`
  - `conversation_constraints`
- prompt 增加对 follow-up / compare 的专门要求
- 回答中在必要时显式承接上文，例如：
  - `延续你上一轮关于英伟达的提问`
  - `在你刚才限定 2025 年的前提下`

阶段完成标准：

- 回答看起来是连续对话，而不是多个孤立单轮输出

## 4. 推荐实施顺序

建议按以下顺序推进：

1. Phase 1
2. Phase 2
3. Phase 3
4. Phase 4

原因：

- 没有 Phase 1，会话上下文无法稳定进入主链
- 没有 Phase 2，多轮只停留在脆弱的规则补全
- 没有 Phase 3，retrieval 仍然是单轮思维
- 没有 Phase 4，最终回答仍然不像真正对话

## 5. 每阶段的 MVP 建议

为避免一次性改动过大，建议每阶段都先交付一个最小可用版本。

### Phase 1 MVP

- planner 读取最近 2 轮消息和会话摘要

### Phase 2 MVP

- resolver 稳定处理：
  - `它`
  - `这家公司`
  - `那今年呢`

### Phase 3 MVP

- retrieval 能继承主体和时间约束

### Phase 4 MVP

- 回答里体现 follow-up continuity

## 6. 与当前架构的关系

当前这套升级方案默认基于项目现有的自研 agentic 状态机推进，不要求立即接入 LangChain 或 LangGraph。

现有基础已经具备：

- `ResearchState`
- `Router`
- `QueryWorkflow`
- `AgenticQaService`
- `conversation_resolver`
- `session store`

因此，当前更推荐：

- 先在现有状态机上把多轮能力做实
- 等状态模型和节点边界稳定后，再评估是否需要迁移到更重的图编排框架

## 7. 当前最值得优先做的工作

如果按当前项目状态继续推进，优先级最高的是：

1. 继续强化 `conversation_resolver`
2. 让 `QueryPlannerNode` 真正消费历史消息与摘要
3. 让 retrieval 继承主体与时间约束

也就是说：

> 下一阶段最值得做的是 Phase 1 + Phase 2 的结合版

这样能最快从“有 session”升级到“真正开始理解上一轮”。

## 8. 相关文档

- [Agentic Workflow Design](./agentic_workflow_design.md)
- [Frontend Design](./frontend_design.md)
- [Development Plan](./development_plan.md)
