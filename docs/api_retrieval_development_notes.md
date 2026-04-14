# API 与召回开发说明

## 1. 当前 API 调用方式、示例与调用链路

### 1.1 环境变量

项目根目录下的 `.env` 当前支持以下配置：

```env
DASHSCOPE_API_KEY=your_api_key
DASHSCOPE_BASE_URL=your_openai_compatible_base_url
DASHSCOPE_MODEL=qwen-plus
```

这些配置由 [`src/config/settings.py`](E:/Project/Agentic_Project/Agentic-RAG-System-for-Complex-PDFs/src/config/settings.py) 自动加载。

### 1.2 HTTP API

当前问答接口：

- `POST /api/qa/ask`

请求示例：

```json
{
  "query": "Sora 2 有什么升级？",
  "top_k": 4,
  "tables_only": false
}
```

返回示例结构：

```json
{
  "query": "Sora 2 有什么升级？",
  "answer": "......",
  "confidence": "medium",
  "model": "qwen-plus",
  "embedding_backend": "sentence_transformer",
  "retrieved_count": 4,
  "citations": [
    {
      "claim": "......",
      "doc_id": "doc_xxx",
      "page_no": 5,
      "chunk_id": "doc_xxx_p5_c12",
      "excerpt": "......"
    }
  ],
  "evidence": [
    {
      "chunk_id": "doc_xxx_p5_c12",
      "doc_id": "doc_xxx",
      "page_no": 5,
      "chunk_type": "paragraph",
      "section_path": ["..."],
      "score": 0.03,
      "sources": ["bm25", "vector"],
      "text": "......"
    }
  ]
}
```

### 1.3 命令行调用方式

直接通过命令行提问：

```powershell
chcp 65001
.\scripts\ask.ps1 -Query "Sora 2 有什么升级？" -TopK 4
```

启动本地 API：

```powershell
.\scripts\start_api.ps1 -Port 8000
```

执行本地 HTTP smoke test：

```powershell
.\scripts\smoke_test_api.ps1 -BaseUrl "http://127.0.0.1:8000" -Query "Sora 2 有什么升级？"
```

### 1.4 当前调用链路

当前 HTTP 调用链路如下：

1. [`src/api/routes/qa.py`](E:/Project/Agentic_Project/Agentic-RAG-System-for-Complex-PDFs/src/api/routes/qa.py) 接收请求
2. [`src/generation/qa_service.py`](E:/Project/Agentic_Project/Agentic-RAG-System-for-Complex-PDFs/src/generation/qa_service.py) 负责编排召回与生成
3. [`src/retrieval/search_service.py`](E:/Project/Agentic_Project/Agentic-RAG-System-for-Complex-PDFs/src/retrieval/search_service.py) 执行：
   - BM25 召回
   - 向量召回
   - hybrid fusion
   - filter
   - dedup
   - collapse
4. [`src/retrieval/context_packer.py`](E:/Project/Agentic_Project/Agentic-RAG-System-for-Complex-PDFs/src/retrieval/context_packer.py) 选择证据上下文
5. [`src/generation/answer_generator.py`](E:/Project/Agentic_Project/Agentic-RAG-System-for-Complex-PDFs/src/generation/answer_generator.py) 构造 prompt 并调用模型
6. [`src/generation/factory.py`](E:/Project/Agentic_Project/Agentic-RAG-System-for-Complex-PDFs/src/generation/factory.py) 创建 LLM provider
7. [`src/generation/providers/openai_compatible.py`](E:/Project/Agentic_Project/Agentic-RAG-System-for-Complex-PDFs/src/generation/providers/openai_compatible.py) 通过 `openai` 包以 OpenAI 兼容方式调用 DashScope
8. [`src/generation/citation_auditor.py`](E:/Project/Agentic_Project/Agentic-RAG-System-for-Complex-PDFs/src/generation/citation_auditor.py) 做基础引用校验

### 1.5 当前检索加载路径

当前检索层的优先加载顺序：

1. 优先读取持久化索引 `indexes/retrieval_cache/bge_base_zh_v1_5`
2. 如果没有索引，则回退到 `artifacts/chunks`

当前本地 embedding 模型：

- `E:\Models\bge-base-zh-v1.5`

---

## 2. 之前召回存在的问题与优化记录

### 2.1 初始阶段存在的主要问题

早期召回问题主要集中在以下几类：

- 同一页、同一 section 下的多个 chunk 重复进入 top-k
- heading、paragraph、table 同时上榜，造成局部重复严重
- `tables-only` 查询经常返回 0 个结果
- 目录页、图表目录页会污染前排结果
- 图表页中的坐标轴、短数字、图例文本会被当作有效证据
- 模型生成本身没有问题，但输入证据质量不稳定

典型现象包括：

- 查询 `Sora 2` 时，结果里混入目录页、图表目录页、短数字页和重复标题
- 查询 `比亚迪 销量` 时，早期几乎拿不到有效表格结果
- 查询 `比亚迪2025年营收如何` 时，命中的往往是销量图、市占率图、终端销量走势，而不是更接近营收的证据

### 2.2 已完成的优化记录

目前已经完成的优化包括：

1. 混合召回基础能力
- 增加 BM25
- 增加向量召回
- 增加 hybrid fusion

2. 结果去重
- 去掉完全重复文本
- 去掉被同 scope 正文覆盖的短 heading

3. 结果聚合
- 按 `doc_id + page_no + section_path` 做 collapse
- 每个局部区域只保留一个代表 chunk

4. 导航页降权
- 对 `目录`、`图表目录`、`contents` 等导航型 chunk 做降权

5. 检索层重构
- 将排序相关逻辑从 `SearchService` 中拆出
- 新增 [`src/retrieval/signals.py`](E:/Project/Agentic_Project/Agentic-RAG-System-for-Complex-PDFs/src/retrieval/signals.py) 作为通用信号层

6. 通用排序信号
- query phrase overlap
- query token overlap
- 时间表达式对齐
- navigational chunk penalty
- sparse chunk penalty
- narrative chunk bonus
- structured-query preference

### 2.3 当前效果判断

目前召回质量相较最初版本已有明显改善：

- `Sora 2` 不再被目录页和重复标题严重污染
- 表格召回已经从“基本不可用”进入“可以返回有效结果”
- CLI 问答链路和 HTTP API 问答链路都已经能端到端跑通

但当前仍然存在明显短板：

- 图表证据仍然偏“弱结构化”
- 财务、指标、时间类问题仍容易受到图表碎片干扰
- 复杂 PDF 中的高价值信息很多还只是文本碎片，并未被结构化建模

---

## 3. 开发边界问题

### 3.1 SearchService 应该做什么

`SearchService` 当前应当被定义为“检索编排器”，而不是“领域语义解释器”。

它应该负责：

- BM25 召回
- 向量召回
- hybrid fusion
- 基础 filter
- dedup
- collapse
- 调用通用排序信号

### 3.2 SearchService 不应该做什么

`SearchService` 不应该直接包含：

- 行业词典
- 财务指标映射
- 公司别名逻辑
- 业务模板特判
- 垂直领域的正负关键词规则

例如下面这类逻辑，不应该继续留在 retrieval core 中：

- `营收 -> 营业收入 -> revenue`
- `营收` 与 `销量` 的硬编码对立关系
- 针对某个行业、某类报告、某家公司单独写的语义规则

### 3.3 当前边界划分

当前边界已经比之前更清楚：

- [`src/retrieval/search_service.py`](E:/Project/Agentic_Project/Agentic-RAG-System-for-Complex-PDFs/src/retrieval/search_service.py)
  - 只负责检索编排
- [`src/retrieval/signals.py`](E:/Project/Agentic_Project/Agentic-RAG-System-for-Complex-PDFs/src/retrieval/signals.py)
  - 只负责通用检索信号
- 更强的领域语义
  - 后续应上移到 profile 层
- 更强的语义排序
  - 后续应放到 reranker 层

### 3.4 当前推荐的边界判断原则

如果一个优化依赖的是：

- query 的词面形式
- 页面布局的一般特征
- chunk 的文本密度
- 是否像导航页、是否像稀疏块、是否像叙述块

那么它属于 retrieval core，可以保留在通用检索层。

如果一个优化依赖的是：

- 某个行业的指标体系
- 某类公司、某类报告的特定语义
- 某个领域的业务词典
- 特定问题模板下的业务判断

那么它应该移动到：

- domain profile
- structured extraction
- reranker
- query planning

---

## 4. 后续优化方向

### 4.1 短期方向

1. 增强通用检索信号
- 继续优化 sparse block 检测
- 继续优化 narrative block 检测
- 提升 section/path 感知能力

2. 引入轻量 reranker
- 在 hybrid retrieval 之后加入更强的排序层
- 让 retrieval core 保持通用，而将更细粒度的语义判断放到 reranker

3. 增强证据多样性
- 避免 top-k 过度集中在同一页、同一局部区域
- 在必要时加入文档/页级别的多样性控制

### 4.2 中期方向

1. 做 parent-child chunking
- 用 child chunk 做召回
- 用 parent chunk 做回答
- 保留细粒度引用，同时给生成更完整上下文

2. 做表格 / 图表的半结构化抽取
- 抽取标题、单位、时间轴、维度信息
- 从“只有原始文本”升级到“半结构化记录”

3. 更好的版面理解
- 页面分区
- 阅读顺序重建
- 显式区分正文区、侧栏区、图表区、页眉页脚区

### 4.3 长期方向

1. 引入 domain profile
- finance profile
- legal profile
- research profile

这些能力应当作为可配置扩展层存在，而不是写死在 retrieval core 里。

2. 引入 query planning
- 识别问题类型
- 判断应该优先正文、表格还是结构化数据
- 根据问题类型调整检索路径

3. 更强的 citation 对齐
- claim 级引用映射
- 句级或 claim 级证据归因

### 4.4 推荐推进顺序

建议后续按以下顺序继续推进：

1. 引入轻量 reranker
2. 实现 parent-child chunking
3. 实现表格 / 图表半结构化抽取
4. 增强页面分区与布局理解
5. 引入 domain profile

---

## 5. 当前总结

目前系统已经具备：

- 本地索引检索
- OpenAI 兼容 LLM 调用
- CLI 问答
- HTTP API 问答
- evidence 和 citation 返回

当前主要瓶颈已经不是 API 连接能力，而是证据质量：

- chunk 粒度仍不够理想
- 图表 / 表格信息仍偏弱结构化
- retrieval core 应继续保持通用
- 更高阶的语义精度应逐步迁移到 reranker、结构化抽取和 domain profile 层
