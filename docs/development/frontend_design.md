# 前端设计文档

## 相关文档

- 开发计划：[`development_plan.md`](development_plan.md)
- API 与检索开发说明：[`api_retrieval_development_notes.md`](api_retrieval_development_notes.md)
- 当前最小化 RAG 缺口分析：[`../analysis/current_rag_gap_analysis.md`](../analysis/current_rag_gap_analysis.md)
- 页面模板分类与图表页分区设计：[`../analysis/page_template_classification_design.md`](../analysis/page_template_classification_design.md)

## 1. 背景与目标

当前项目已经具备：

- 本地索引与检索能力
- CLI 问答链路
- FastAPI 问答接口
- 基础 citation 与 evidence 返回

下一步需要补一个**基础前端**，用于把已有问答能力以更直观的方式提供出来，并为后续增强留出空间。

本阶段前端的核心目标不是追求复杂交互，而是先搭一条稳定、轻量、可部署的展示链路。

## 2. 需求分析

用户提出的约束可以拆成四点：

### 2.1 本地轻量启动

要求前端能在本地快速跑起来，尽量减少额外工程复杂度。

这意味着前端不适合一开始就采用：

- 需要 Node.js 工具链的大型 SPA 工程
- 需要单独前后端构建与代理配置的复杂方案

更适合：

- Python 原生即可启动
- 与现有 FastAPI / Python 服务兼容
- 开发、调试、演示成本较低

### 2.2 基础问答能力

第一版前端至少需要支持：

- 展示聊天窗口
- 输入问题
- 获取回答
- 展示简单引用溯源

这里的“简单引用溯源”建议定义为：

- 回答正文
- 引用列表
- 每条引用展示 `doc_id / page_no / excerpt`

暂时不要求：

- claim 级高亮对齐
- 文档内定位跳转
- PDF 页面预览

### 2.3 Hugging Face Spaces 兼容

后续可能部署到 Hugging Face Spaces，因此前端方案需要天然适配：

- Python 运行环境
- 容器或 Space 启动脚本简单
- 尽量少依赖系统级前端构建链

### 2.4 预留后续扩展能力

当前前端虽然只做基础版，但必须为后续能力预留结构空间，包括：

- 多轮对话
- session 管理
- 展示层优化
- 参数面板
- 可切换后端模式
- 结果结构增强

## 3. 设计原则

### 3.1 先做可运行的前端壳

第一阶段优先建立：

- 清晰的页面结构
- 与现有 API 的稳定对接
- 可扩展的前端状态模型

而不是一开始就追求复杂 UI。

### 3.2 前端层不直接绑定具体模型或具体提供商

前端只消费统一问答接口，不应关心：

- 是哪个 LLM provider
- 是哪个 embedding 模型
- 是否启用了 reranker

这些信息可以作为调试信息展示，但不应成为前端逻辑耦合点。

### 3.3 优先兼容 Python 生态与 Spaces

本阶段前端应优先选用：

- Python 原生可运行
- Hugging Face Spaces 原生友好
- 无需额外 Node 构建链

### 3.4 为后续替换前端技术栈预留边界

虽然第一版推荐采用轻量方案，但整体结构上要预留：

- 后续替换成 React / Next.js / Vue 前端
- 保持 API 与 UI 解耦

因此应显式区分：

- UI 层
- 前端控制层
- 后端调用适配层

## 4. 技术路线建议

## 4.1 推荐方案：Gradio 作为第一版前端

综合当前约束，第一版最推荐使用 **Gradio**。

原因：

1. 本地启动轻量
- 只需 Python 依赖
- 无需 Node.js 构建

2. Hugging Face Spaces 兼容性最好
- Gradio 是 Hugging Face Spaces 的原生友好方案之一
- 部署门槛低

3. 非常适合作为 RAG Demo 与 MVP 前端
- 能快速搭聊天界面
- 能方便展示 citation、accordion、侧栏参数

4. 可以先把工程重心放在 RAG 质量上
- 避免前期时间被前端工程化吞掉

## 4.2 为什么不推荐第一版直接上 React / Vue

React / Vue 并不是不能做，而是不适合作为当前阶段的第一优先级。

主要原因：

- 本地启动链路更重
- 需要额外维护构建工具链
- Hugging Face Spaces 部署路径更复杂
- 当前项目的核心瓶颈不在前端技术复杂度，而在 RAG 质量

因此更合理的策略是：

- 第一版先用 Gradio 建立轻量前端
- 后续如果产品化需求增强，再考虑迁移到更完整的 Web 前端

## 5. 总体架构设计

推荐采用三层结构：

```text
Gradio UI
  -> Frontend Controller
  -> QA Client Adapter
  -> Existing FastAPI API / In-process QaService
```

### 5.1 UI 层

负责：

- 聊天消息展示
- 用户输入
- 参数面板
- 引用与证据展示

不负责：

- 检索逻辑
- 会话持久化逻辑
- 模型调用逻辑

### 5.2 Frontend Controller

负责：

- 组织页面状态
- 收集用户输入
- 调用后端适配层
- 把返回结果转换为 UI 需要的展示结构

它是前端的编排层。

### 5.3 QA Client Adapter

建议抽象一层统一客户端接口，例如：

- `QaClient`
  - `ask(query, top_k, tables_only, session_id=None) -> QaUiResult`

第一版可准备两种实现：

1. `HttpQaClient`
- 调用现有 FastAPI `POST /qa/ask`

2. `InProcessQaClient`
- 在同一 Python 进程内直接调用 `QaService`

这样做的价值是：

- 本地开发可以不强依赖单独启动 API
- Spaces 部署时可以根据资源与部署方式切换
- 后续如果前端独立部署，也只需要保留 HTTP client

## 6. 与现有后端的接口对接

当前已存在接口：

- `POST /qa/ask`

请求体：

```json
{
  "query": "Sora 2 有什么升级？",
  "top_k": 4,
  "tables_only": false
}
```

响应体当前包含：

- `query`
- `answer`
- `confidence`
- `model`
- `prompt_family`
- `embedding_backend`
- `retrieved_count`
- `citations`
- `evidence`

因此前端第一版不需要增加新接口，就可以直接接入现有链路。

## 7. 页面结构设计

第一版页面建议采用**单页双栏布局**。

### 7.1 左侧：聊天主区域

包含：

- 标题栏
- 对话历史
- 输入框
- 提问按钮

回答消息建议展示：

- 回答正文
- 置信度
- 可折叠的引用列表

### 7.2 右侧：证据与参数面板

包含：

- 本次查询参数
  - `top_k`
  - `tables_only`
- 检索摘要
  - `retrieved_count`
  - `model`
  - `embedding_backend`
- 引用列表
- evidence 预览

这种结构的好处是：

- 主聊天区保持简洁
- 调试信息不打断阅读
- 后续继续扩展比较方便

### 7.3 移动端 / 窄屏策略

在窄屏下建议自动退化为上下结构：

- 上方聊天区
- 下方折叠式 citation / evidence 区

## 8. 首版交互设计

第一版建议只支持**单轮提问 + 历史展示**，但前端内部状态设计成可扩展。

### 8.1 用户提问流程

1. 用户输入问题
2. 点击发送
3. UI 进入 loading 状态
4. 调用 `QaClient.ask`
5. 展示回答
6. 展示引用
7. 展示 evidence 预览

### 8.2 回答展示方式

每条 assistant 消息建议包含：

- `answer`
- `confidence`
- `citations`

其中 citation 可简化为：

- 文档 ID
- 页码
- chunk ID
- 摘录

### 8.3 错误处理

第一版应至少处理：

- API 不可达
- 检索索引缺失
- 模型调用失败
- 超时

前端不需要暴露完整 traceback，只需给出明确可读提示。

## 9. 会话与状态设计

虽然第一版不强制实现完整 session 管理，但状态结构应先设计好。

建议前端内部维护：

```json
{
  "session_id": "optional",
  "messages": [
    {
      "role": "user",
      "content": "..."
    },
    {
      "role": "assistant",
      "content": "...",
      "citations": [],
      "metadata": {}
    }
  ],
  "query_options": {
    "top_k": 4,
    "tables_only": false
  }
}
```

### 9.1 第一版如何使用

第一版可以：

- 只在前端内存里保存消息列表
- 不真正传递 `session_id` 给后端

### 9.2 后续扩展方式

后续可逐步扩展为：

- 本地 session 列表
- 浏览器级持久化
- 服务端 session 存储
- 多轮对话上下文传递

## 10. Hugging Face Spaces 兼容设计

这是本方案必须考虑的重点。

### 10.1 推荐部署模式

对 Spaces 来说，第一版最推荐：

- 使用 Gradio
- 同进程直接调用 `QaService` 或通过本地 HTTP 调用现有 API

两种方式里，更推荐优先支持：

1. **In-process 模式**
- 结构简单
- 少一个 HTTP 层
- 更适合 Spaces 单应用部署

2. **HTTP 模式**
- 更接近本地开发与未来分离式部署

因此建议前端设计时支持：

- `FRONTEND_BACKEND_MODE=inprocess|http`

### 10.2 对 Spaces 的具体兼容要求

前端设计应避免依赖：

- 本地绝对路径展示
- 需要浏览器本地文件系统能力的功能
- 复杂反向代理配置

同时建议配置项全部环境变量化，例如：

- `FRONTEND_BACKEND_MODE`
- `FRONTEND_API_BASE_URL`
- `FRONTEND_HOST`
- `FRONTEND_PORT`

### 10.3 对资源占用的考虑

如果后续在 Spaces 上部署，需要注意：

- 首次加载 embedding / reranker / 索引会较慢
- 前端不要在页面加载时主动触发重计算
- 前端应尽量按需请求

## 11. 建议的代码组织

建议新增前端目录：

```text
src/frontend/
  app.py
  controller.py
  state.py
  clients/
    base.py
    http_client.py
    inprocess_client.py
  components/
    chat.py
    citations.py
    settings.py
```

### 11.1 `app.py`

前端入口，负责：

- 构建 Gradio app
- 注册页面布局
- 启动本地服务

### 11.2 `controller.py`

负责：

- 输入处理
- 调用客户端
- 组装 UI 输出

### 11.3 `state.py`

负责：

- 定义前端会话状态
- 规范消息结构

### 11.4 `clients/`

负责：

- 封装后端调用方式
- 实现 `QaClient` 抽象

### 11.5 `components/`

负责：

- UI 子组件
- 聊天区
- 引用区
- 参数区

## 12. 配置设计建议

建议新增以下环境变量：

- `FRONTEND_ENABLED`
- `FRONTEND_BACKEND_MODE`
- `FRONTEND_API_BASE_URL`
- `FRONTEND_HOST`
- `FRONTEND_PORT`
- `FRONTEND_TITLE`
- `FRONTEND_DEFAULT_TOP_K`

说明：

- `FRONTEND_BACKEND_MODE=http` 时调用 FastAPI
- `FRONTEND_BACKEND_MODE=inprocess` 时直接调用 `QaService`

## 13. 分阶段落地建议

### Phase 1：基础前端壳

交付目标：

- Gradio 单页应用
- 能提问
- 能拿回答
- 能展示 citation
- 能本地启动

### Phase 2：补证据面板与参数面板

交付目标：

- evidence 展示
- `top_k` / `tables_only` 配置
- 调试信息展示

### Phase 3：多轮与 session

交付目标：

- 前端消息历史
- 多轮对话展示
- session_id 预留

### Phase 4：体验增强

交付目标：

- 更好的消息样式
- 引用折叠
- 文档卡片
- 错误提示优化

## 14. 当前阶段最推荐的实现边界

为了控制复杂度，第一版前端建议明确边界：

应该做：

- 单页聊天界面
- 与现有问答 API 对接
- 简单 citation 展示
- 参数面板
- 可本地运行
- 可兼容 Spaces

暂时不做：

- PDF 页面预览
- 文档内高亮跳转
- 真正的多用户 session 管理
- 复杂权限控制
- 自定义前端构建链

## 15. 结论

结合当前项目状态，第一版前端最合适的方案是：

**使用 Gradio 构建一个轻量聊天式前端，并通过可插拔的 `QaClient` 适配层对接现有问答链路。**

这个方案满足：

1. 本地启动轻量
2. 能展示提问、回答与引用
3. 对 Hugging Face Spaces 兼容友好
4. 能为后续多轮对话、session 管理、展示增强预留结构空间

一句话总结：

**先用 Python 原生、Spaces 友好的方式把前端壳搭起来，再把复杂度留给后续迭代，而不是在第一版就引入过重的前端工程体系。**
