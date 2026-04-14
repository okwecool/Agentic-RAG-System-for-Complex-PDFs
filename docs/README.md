# 文档导航

本文档用于整理 `docs` 目录下除最初设计文档之外的开发与分析文档，方便后续按主题快速定位。

## 1. 文档分区

当前文档分为两类：

1. 开发类文档
- [`docs/development/development_plan.md`](development/development_plan.md)
- [`docs/development/api_retrieval_development_notes.md`](development/api_retrieval_development_notes.md)

2. 分析类文档
- [`docs/analysis/chunk_anomaly_report.md`](analysis/chunk_anomaly_report.md)
- [`docs/analysis/project_optimization_backlog.md`](analysis/project_optimization_backlog.md)
- [`docs/analysis/current_rag_gap_analysis.md`](analysis/current_rag_gap_analysis.md)

## 2. 推荐阅读顺序

如果想了解“当前项目应该怎么继续开发”，推荐按下面顺序阅读：

1. [`docs/development/development_plan.md`](development/development_plan.md)
用于理解整体开发路线、阶段划分和交付目标。

2. [`docs/development/api_retrieval_development_notes.md`](development/api_retrieval_development_notes.md)
用于理解当前 API、检索、生成主链的实现方式与边界。

3. [`docs/analysis/current_rag_gap_analysis.md`](analysis/current_rag_gap_analysis.md)
用于理解当前最小化 RAG 还缺什么、瓶颈在哪里。

4. [`docs/analysis/project_optimization_backlog.md`](analysis/project_optimization_backlog.md)
用于理解当前系统性优化项与中长期待办。

5. [`docs/analysis/chunk_anomaly_report.md`](analysis/chunk_anomaly_report.md)
用于查看 chunk 层面已经发现过的典型问题与修复线索。

## 3. 各文档关注点

### 3.1 开发计划

[`docs/development/development_plan.md`](development/development_plan.md)

关注点：

- 项目阶段划分
- 模块拆解
- 目录结构
- 交付物与验收标准

适合在：

- 制定阶段目标时阅读
- 评估当前开发进度时阅读

### 3.2 API 与召回开发说明

[`docs/development/api_retrieval_development_notes.md`](development/api_retrieval_development_notes.md)

关注点：

- 当前 API 调用方式
- CLI 与 HTTP 调用链路
- 检索层现状
- SearchService 的边界
- 近期召回优化方向

适合在：

- 调试 API 或问答链路时阅读
- 调整检索与生成逻辑时阅读

### 3.3 Chunk 异常巡检报告

[`docs/analysis/chunk_anomaly_report.md`](analysis/chunk_anomaly_report.md)

关注点：

- 已发现的异常文档
- chunk 异常模式
- 针对典型 PDF 的问题复盘

适合在：

- 调整 parser / cleaner / chunker 时阅读
- 分析 chunk 质量问题时阅读

### 3.4 项目整体待优化文档

[`docs/analysis/project_optimization_backlog.md`](analysis/project_optimization_backlog.md)

关注点：

- 当前系统性优化项
- 已暴露的架构瓶颈
- 中长期优化方向

适合在：

- 制定中期路线图时阅读
- 评估哪些逻辑应该保留、哪些应该升级时阅读

### 3.5 当前最小化 RAG 实现缺口分析

[`docs/analysis/current_rag_gap_analysis.md`](analysis/current_rag_gap_analysis.md)

关注点：

- 当前基础 RAG 已经做到什么程度
- 还没真正闭环的能力
- 当前最主要的质量瓶颈
- 推荐的近期推进顺序

适合在：

- 判断 MVP 还差什么时阅读
- 决定下一步优先级时阅读

## 4. 文档之间的关系

可以简单理解为：

- `development_plan.md`
  - 回答“项目整体应该怎么做”

- `api_retrieval_development_notes.md`
  - 回答“当前 API 和召回链路具体是怎么实现的”

- `chunk_anomaly_report.md`
  - 回答“chunk 层面已经出过什么问题”

- `project_optimization_backlog.md`
  - 回答“系统层面还有哪些优化项”

- `current_rag_gap_analysis.md`
  - 回答“从最小化 RAG 的角度，还差什么没完成”

## 5. 维护建议

后续新增文档时，建议遵循以下原则：

1. 开发执行类文档放在 `docs/development`
2. 问题复盘、能力分析、缺口分析放在 `docs/analysis`
3. 每篇文档开头增加“相关文档”区块
4. 避免同类信息在多个文档中长期漂移，优先通过交叉引用复用已有文档
