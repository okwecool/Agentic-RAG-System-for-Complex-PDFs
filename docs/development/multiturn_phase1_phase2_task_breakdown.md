# 多轮上下文升级：Phase 1 + Phase 2 代码任务拆解

## 1. 文档目的

这份文档用于把“轻量多轮升级到真正上下文对话”的前两个阶段拆成可执行的代码任务。

对应上游设计文档：

- [多轮上下文对话升级方案](./multiturn_context_upgrade_plan.md)

本拆解聚焦：

- Phase 1：让会话状态真正进入工作流
- Phase 2：把 `conversation_resolver` 升级为会话理解器

## 2. 当前代码基线

当前已经具备的基础：

- `session_id` 已经可以在前后端与 agentic service 之间透传
- `AgenticQaService` 已接内存版 `thread_store`
- `ResearchState` 已经包含：
  - `session_id`
  - `turn_index`
  - `messages`
  - `conversation_summary`
  - `resolved_user_query`
- graph 中已经接入 `conversation_resolver`
- 当前可以处理简单追问，例如：
  - `那它今年呢？`

当前还不足的点：

- planner 对会话历史的消费仍然偏弱
- `conversation_resolver` 还是轻量规则版
- 实体提取、约束继承、追问分类还不够明确

## 3. 总体实施原则

本阶段开发遵循以下原则：

- 不引入领域硬编码
- 优先增强通用会话信号
- 保持现有自研状态机结构稳定
- 不急于引入 LangChain / LangGraph
- 每一步都要能单独测试和回归

## 4. Phase 1 代码任务：会话状态正式入链

### 4.1 目标

让会话状态不只是“被保存”，而是成为 planner 和 workflow 的正式输入。

### 4.2 模块拆解

#### Task 1：稳定 `ResearchState` 的会话字段

文件：

- `src/domain/models/state.py`

目标：

- 统一会话态字段定义
- 避免不同节点各自临时拼字段

建议字段：

- `session_id`
- `turn_index`
- `messages`
- `conversation_summary`
- `resolved_user_query`
- `current_entities`
- `conversation_constraints`
- `last_user_intent`

验收标准：

- workflow / node / service 层不再自行发明会话字段

#### Task 2：稳定 `thread_store` 的持久化结构

文件：

- `src/memory/thread_store.py`
- `src/memory/summarizer.py`

目标：

- 明确单个 session 的存储结构
- 保证重入同一个 session 时状态可复用

最小结构建议：

- `session_id`
- `turn_index`
- `messages`
- `conversation_summary`
- `current_entities`
- `current_domain`

验收标准：

- 同一 `session_id` 连续请求时，服务端能读回历史状态

#### Task 3：让 `AgenticQaService` 统一管理会话载入与回写

文件：

- `src/generation/agentic_qa_service.py`

目标：

- 会话加载、初始 state 组装、会话回写由 service 统一负责

需要完成：

- 根据 `session_id` 取回历史状态
- 生成本轮 `initial_state`
- workflow 结束后回写：
  - `messages`
  - `conversation_summary`
  - `current_entities`
  - `turn_index`

验收标准：

- 对同一个 `session_id` 连续调用，两轮之间状态连续

#### Task 4：把 `messages / summary` 明确接到 planner 输入

文件：

- `src/graph/nodes/query_planner.py`

目标：

- planner 不再只看 `user_query`
- 开始同时消费：
  - `resolved_user_query`
  - `conversation_summary`
  - 最近 1~3 轮 `messages`

第一版最低要求：

- planner 至少能根据：
  - 是否是 follow-up
  - 是否已有 conversation anchor
  来调整 `intent` 或 `retrieval_plan`

验收标准：

- planner 的日志里能看到它开始使用会话态输入

### 4.3 Phase 1 推荐测试

建议新增测试：

- `session_id` 连续两轮请求能正确累积 `messages`
- `turn_index` 递增
- `conversation_summary` 在第二轮后非空
- planner 在有 `resolved_user_query` 时优先使用补全后的 query

## 5. Phase 2 代码任务：conversation resolver 升级

### 5.1 目标

让 resolver 从“简单替换器”升级为“轻量会话理解器”。

### 5.2 模块拆解

#### Task 5：稳定 `conversation_resolver` 的输入输出契约

文件：

- `src/graph/nodes/conversation_resolver.py`

目标：

- 明确 resolver 的职责边界

建议输入：

- `user_query`
- `messages`
- `conversation_summary`
- `current_entities`

建议输出：

- `resolved_user_query`
- `current_entities`
- `conversation_constraints`
- `next_action`

验收标准：

- resolver 输出可被 planner 直接消费

#### Task 6：增强实体锚点解析

文件：

- `src/graph/nodes/conversation_resolver.py`

目标：

- 更稳定地从历史轮次中找到当前追问的主体锚点

建议能力：

- 优先使用：
  - `last_entity`
  - `conversation_anchor`
- 若无显式锚点，则回看最近消息中的高显著实体

需避免的问题：

- 把整句误识别为实体
- 把“近期发展势头”“商业信息”这种描述性短语当主体

验收标准：

- 类似“那它今年呢？”能稳定补成“英伟达今年呢？”

#### Task 7：增加 `dialogue_act` 判定

文件：

- `src/graph/nodes/conversation_resolver.py`
- 或后续可拆成单独模块

目标：

- 让系统知道这一轮是：
  - 新问题
  - 追问
  - 比较
  - 澄清

建议第一版类别：

- `new_topic`
- `follow_up`
- `compare`
- `clarification`

建议判断信号：

- 是否使用代词
- 是否继承上一轮主体
- 是否出现比较词：
  - `对比`
  - `和...比`
  - `相比`

验收标准：

- resolver 能在日志和 state 中写出 `dialogue_act`

#### Task 8：增加会话约束抽取

文件：

- `src/graph/nodes/conversation_resolver.py`
- 后续可拆为 `conversation_constraints.py`

目标：

- 从当前轮或历史轮提取并延续约束

约束类型建议：

- `entity_scope`
- `time_scope`
- `region_scope`
- `metric_scope`

第一版不追求复杂，只做基础延续：

- 当前轮没说主体，则沿用上一轮主体
- 当前轮没说年份，但上一轮说了，则可记录为候选继承约束

验收标准：

- state 中开始出现结构化的 `conversation_constraints`

#### Task 9：把 resolver 输出接入 planner

文件：

- `src/graph/nodes/query_planner.py`
- `src/graph/workflow.py`

目标：

- planner 接收 resolver 的：
  - `resolved_user_query`
  - `dialogue_act`
  - `conversation_constraints`

planner 第一版需要做的事情：

- follow-up 问题优先继承主体约束
- compare 问题优先设为更高复杂度
- 有时间约束时写入 `retrieval_plan.time_terms`

验收标准：

- planning 输出开始体现会话上下文带来的差异

### 5.3 Phase 2 推荐测试

建议新增测试：

- 指代补全：
  - `那它今年呢？`
  - `这家公司最近怎么样？`
- 比较补全：
  - `那和英特尔比呢？`
- 省略补全：
  - `利润呢？`
- `dialogue_act` 分类正确
- `conversation_constraints` 能被写入 state

## 6. 推荐开发顺序

建议按下面顺序开发：

1. Task 1
2. Task 2
3. Task 3
4. Task 5
5. Task 6
6. Task 9
7. Task 7
8. Task 8
9. 补测试与日志

原因：

- 先把会话态稳定下来，再增强 resolver
- resolver 增强后，优先让 planner 真正消费
- `dialogue_act` 和约束抽取可以在基础链路稳定后继续丰富

## 7. 第一批建议直接落地的任务

如果只做第一批最有价值的任务，建议优先：

- Task 2：稳定 `thread_store`
- Task 3：统一 `AgenticQaService` 会话管理
- Task 6：增强实体锚点解析
- Task 9：让 planner 真正消费 `resolved_user_query`

这一批做完以后，系统会从：

> 有 session + 能做一点规则补全

升级到：

> 真正开始利用上一轮上下文进行 planning

## 8. 后续衔接

当 Phase 1 + Phase 2 稳定之后，可以自然衔接到：

- Phase 3：上下文化 retrieval
- Phase 4：上下文化 synthesis

对应主文档见：

- [多轮上下文对话升级方案](./multiturn_context_upgrade_plan.md)
