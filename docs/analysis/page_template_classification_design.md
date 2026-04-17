# 页面模板分类与图表页分区设计

## 相关文档

- 总体开发计划：[`../development/development_plan.md`](../development/development_plan.md)
- API 与检索开发说明：[`../development/api_retrieval_development_notes.md`](../development/api_retrieval_development_notes.md)
- Chunk 异常巡检报告：[`chunk_anomaly_report.md`](chunk_anomaly_report.md)
- 项目整体待优化文档：[`project_optimization_backlog.md`](project_optimization_backlog.md)
- 当前最小化 RAG 缺口分析：[`current_rag_gap_analysis.md`](current_rag_gap_analysis.md)

## 1. 文档目标

本文档用于定义一套面向复杂 PDF 的通用页面结构增强方案，重点解决以下问题：

1. 图表页、时间轴页、信息图页被当成普通正文页处理。
2. 封面、目录、声明页中的元信息污染 `section_path`。
3. 页面中的短标签、刻度、年份轴、图例被拆成大量低质量 chunk。
4. `section_builder` 与 `chunker` 缺少页面级结构信号，只能依赖 block 级启发式。

本文档只描述设计与接入方式，不要求立即引入重量级视觉模型。

## 2. 设计原则

### 2.1 通用优先

本方案不依赖具体行业词典、券商模板或单个 PDF 的特定文案，而是尽量基于：

- 页面几何结构
- 文本密度
- 数字密度
- 句子完整度
- 区域分布模式

### 2.2 先页面，后区域，再作用于 chunk

推荐按以下顺序演进：

1. `page template classification`
2. `block zoning`
3. `section_builder / chunker` 消费这些结构信号

这样可以避免继续在 `cleaner` 和 `chunker` 里堆过多局部规则。

### 2.3 轻量启发式优先

第一阶段不直接引入重量级 layout model，而是先用可解释的启发式规则构建：

- 页面粗分类
- 区域粗分区
- 页面级保护信号

当这套信号体系稳定后，再评估是否需要更强的视觉模型。

## 3. 当前问题与设计动机

结合近期异常样本，可归纳出几类典型问题：

### 3.1 封面 / 元信息误入章节树

例如：

- `证券研究报告`
- 日期
- `数据来源`
- `特别声明`

这类内容如果被识别为 `heading`，就会直接污染 `section_path`。

### 3.2 图表页 / 信息图页碎片化

例如：

- 年份轴
- 数字刻度
- 图例短词
- 时间轴节点
- 小标签块

这些元素本来属于同一个图表区域，但当前会被切成大量 `heading` / `paragraph` chunk。

### 3.3 页面结构没有显式建模

当前系统更偏 `block-first`，缺少以下显式概念：

- 当前页是不是图表重页
- 当前页是不是封面 / 目录 / 声明
- 某个 block 属于主正文区还是标签密集区

因此很多后处理规则只能在局部补救，难以稳定。

## 4. 总体方案

建议引入两层结构信号：

1. 页面级信号：`page_profile`
2. 区域级信号：`zone`

推荐链路如下：

```text
parser
  -> cleaner
  -> page profile classifier
  -> block zone annotator
  -> cleaner second pass / heading guardrails
  -> section_builder
  -> chunker
```

如果希望降低改造风险，也可以先接成：

```text
parser
  -> cleaner
  -> page profile classifier
  -> block zone annotator
  -> section_builder
  -> chunker
```

## 5. 页面模板分类设计

### 5.1 目标

为每一页生成一个粗粒度类型标签，供后续模块使用。

### 5.2 推荐分类

第一版建议包含以下标签：

- `cover`
- `toc`
- `narrative`
- `chart_heavy`
- `table_heavy`
- `mixed_layout`
- `disclaimer_or_appendix`

这些标签是通用结构标签，不绑定行业语义。

### 5.3 页面级特征

建议从以下维度构建特征：

#### 文本块统计

- `block_count`
- `heading_count`
- `table_count`
- `short_block_ratio`
- `long_block_ratio`

#### 文本内容统计

- `numeric_density`
- `year_token_density`
- `percent_token_density`
- `toc_like_pattern_ratio`
- `source_note_ratio`

#### 几何布局统计

- 是否存在明显多栏分布
- 是否存在窄块密集区域
- 是否存在多个离散小块聚簇
- 中心区域是否存在连续正文块

#### 叙述性特征

- 完整句子比例
- 平均行数
- 平均块长度
- list-item 比例

### 5.4 基础分类规则示意

#### `narrative`

常见特征：

- 长段落比例高
- 短标签块较少
- heading 数适中
- 数字密度不高

#### `chart_heavy`

常见特征：

- 短块多
- 数字多
- 年份、百分比、短标签集中
- 完整句子比例低

#### `table_heavy`

常见特征：

- 表格块多
- 数字密度高
- 行列结构明显

#### `toc`

常见特征：

- 点线 / 页码导航模式明显
- 短标题多
- 行尾页码比例高

#### `cover`

常见特征：

- 大标题显著
- 元信息块较多
- 正文块少
- 版式分区明显

### 5.5 输出建议

每页输出结构建议如下：

```json
{
  "page_no": 46,
  "page_profile": "chart_heavy",
  "page_signals": {
    "block_count": 43,
    "short_block_ratio": 0.72,
    "numeric_density": 0.31,
    "table_count": 0,
    "narrative_block_ratio": 0.12
  }
}
```

## 6. 图表页分区设计

### 6.1 目标

在页面级分类的基础上，给 block 增加一个轻量区域标签，用于：

- 降低短标签进入章节树的概率
- 将图表标签区整体聚合
- 区分主正文区与非正文区

### 6.2 推荐区域类型

第一版建议支持：

- `main`
- `header`
- `footer`
- `sidebar`
- `dense_label`
- `table_region`

必要时可扩展：

- `cover_meta`
- `chart_caption`

### 6.3 分区逻辑

#### `header / footer`

通过相对页面高度和重复位置模式判断。

#### `sidebar`

通过以下信号判断：

- 位于页面边缘
- 宽度较窄
- 与主正文区 x 轴明显分离
- 常为多短块聚集

#### `dense_label`

这是最关键的区域之一，常见特征为：

- 同一区域 block 很多
- 文本短
- 数字多
- 完整句子少
- 常见于图表、时间轴、信息图

#### `main`

通常具备：

- 长文本块
- 行数较多
- 句子更完整
- 分布相对连续

### 6.4 输出建议

每个 block 增加：

```json
{
  "block_id": "b_46_15",
  "zone": "dense_label",
  "page_profile": "chart_heavy"
}
```

## 7. 对现有模块的影响

### 7.1 对 cleaner 的影响

`cleaner` 可以利用 `page_profile` 和 `zone` 做更稳的通用处理：

- `chart_heavy + dense_label` 区内的短 heading 优先降级
- `header / footer` 内的 source note 优先过滤
- `cover` 页中的元信息块不进入正文清洗逻辑

### 7.2 对 section_builder 的影响

`section_builder` 应使用结构信号作为保护条件：

- `dense_label` 区的 heading 不参与章节树
- `cover`、`toc`、`disclaimer_or_appendix` 页上的低置信度 heading 不重置 `section_path`
- 仅 `main` 区且满足 heading 条件的 block 才参与章节构建

### 7.3 对 chunker 的影响

`chunker` 可以做更合理的聚合：

- `dense_label` 区的块优先聚成 region-level chunk
- `main` 区正文优先形成 narrative chunk
- `table_region` 内文本与 table block 做更强去重

### 7.4 对 retrieval 的影响

后续检索层可以直接消费这些结构信息：

- `chart_heavy` 页 chunk 默认轻度降权
- `toc` / `cover` 页 chunk 默认轻度降权
- `main` 区 narrative chunk 优先进入问答上下文

## 8. 数据结构建议

### 8.1 Page 扩展字段

建议在 `Page` 上增加：

```json
{
  "page_profile": "chart_heavy",
  "page_signals": {
    "block_count": 43,
    "short_block_ratio": 0.72,
    "numeric_density": 0.31
  }
}
```

### 8.2 Block 扩展字段

建议在 `Block.source_span` 或显式字段中增加：

```json
{
  "page_profile": "chart_heavy",
  "zone": "dense_label"
}
```

### 8.3 Chunk 扩展字段

建议在 chunk metadata 中保留：

- `page_profile`
- `zones`
- `source_block_count`
- `dense_label_ratio`

这样后续检索层可以直接使用。

## 9. 实现顺序建议

### Phase A：页面分类

新增 `PageProfileClassifier`

目标：

- 为每页生成 `page_profile`
- 同时输出 `page_signals`

收益：

- 最小改造即可给 cleaner / section_builder 提供更稳的条件

### Phase B：区域标注

新增 `BlockZoneAnnotator`

目标：

- 为每个 block 标记 `zone`

收益：

- 帮助过滤 `dense_label`
- 帮助识别 `sidebar`
- 帮助保护章节树

### Phase C：区域聚合

目标：

- 将 `dense_label` 区块合并成少量 region-level chunk

收益：

- 明显减少图表页碎片化

### Phase D：检索层消费结构信号

目标：

- 在 retrieval/rerank/context packing 中利用 `page_profile` 和 `zone`

收益：

- 检索结果更稳定
- 噪声 chunk 更少

## 10. 最小可落地版本

如果当前只做一个短周期版本，建议只包含以下内容：

1. `PageProfileClassifier`
2. `BlockZoneAnnotator`
3. `section_builder` 忽略 `chart_heavy + dense_label` 的 heading
4. `chunker` 将 `dense_label` 区优先聚合

这个版本就已经能明显改善：

- 图表页大量碎 chunk
- `section_path` 被标签污染
- 检索命中到无意义短标签

## 11. 暂不建议立即做的事

当前阶段不建议一开始就做：

1. 重量级视觉 layout model 全量接入
2. 针对单个模板写大量硬编码规则
3. 过早把页面分类与行业 profile 绑定
4. 跳过页面分类直接做复杂区域精分

这些会增加复杂度，但未必先带来最稳定收益。

## 12. 当前结论

页面模板分类和图表页分区，是当前 parser / cleaner / section builder / chunker 之间缺失的中间层。

它的核心价值不是“做更复杂的视觉理解”，而是给现有 RAG 主链补上一层稳定的页面结构信号。

一句话总结：

先做页面分类，再做区域标注，再让章节树和 chunk 逻辑消费这些信号，是当前复杂 PDF 质量提升最稳的路线。

## 13. 与 RAGFlow 在页面处理上的差异

结合对 RAGFlow `README` 与 `deepdoc` 说明的对照，可以把双方在页面处理上的差异概括为以下几点。

### 13.1 RAGFlow 更偏 parser 前置的页面理解

RAGFlow 的思路更接近：

- `OCR / layout recognition / TSR`
- 先识别页面组件角色
- 再进入 parser 与 template-based chunking

而当前项目更接近：

- `PyMuPDF get_text("dict")`
- 提取原始 block
- 再通过 cleaner、section_builder、chunker 做后处理修正

这意味着：

- RAGFlow 更偏 `layout-first`
- 当前项目仍然更偏 `block-first`

### 13.2 RAGFlow 的页面组件类型更显式

RAGFlow 会显式区分诸如：

- `Title`
- `Text`
- `Figure`
- `Figure caption`
- `Table`
- `Table caption`
- `Header`
- `Footer`
- `Reference`

而当前项目虽然已经具备：

- `heading`
- `paragraph`
- `list_item`
- `table`

但像 `figure_caption`、`table_caption`、`header`、`footer`、`reference` 还没有稳定成为 parser 层的一等对象。

### 13.3 RAGFlow 的表格处理更偏视觉结构识别

RAGFlow 的 DeepDoc 中将表格结构识别放在比较靠前的位置，更强调：

- 行列结构
- 表头
- 合并单元格
- 表格与说明文字的拆分

当前项目的表格链路则更偏：

- `page.find_tables()`
- 后续做伪表格过滤
- 再将表格转成文本与基础结构字段

因此在复杂表格、图表混排、说明框过滤方面，RAGFlow 的前置结构理解更充分。

### 13.4 当前项目最值得借鉴的是“分层思路”，而不是直接复刻实现

对当前项目最有参考价值的，不是直接照搬 RAGFlow 的完整视觉栈，而是借鉴它的页面处理分层：

1. 先识别页面类型
2. 再识别区域
3. 再识别 block 角色
4. 最后让 chunk 逻辑消费这些结构信号

这也正是本文档提出 `page_profile + zone` 的原因。

## 14. 结合当前问题的近期工作建议

结合已有异常样本、chunk 质量问题和与 RAGFlow 的对照，当前最值得做的工作可以归纳为三层。

### 14.1 P0：补页面结构中间层

这是当前收益最大的方向。

建议优先完成：

1. `PageProfileClassifier`
2. `BlockZoneAnnotator`
3. `section_builder` 使用 `page_profile / zone`
4. `chunker` 使用 `page_profile / zone`

这一步可以先不引入重量级视觉模型，先把页面结构信号补齐。

### 14.2 P1：补 block role 与 chunk 边界

在页面分类和分区稳定后，下一步最值得补的是 block role。

重点包括：

- `narrative_paragraph`
- `figure_caption`
- `table_caption`
- `chart_label`
- `source_note`

这样可以直接解决：

- 图表标题夹进正文 chunk
- caption 混进 narrative
- `section_path` 被图表短标签污染

### 14.3 P1：让 retrieval 消费结构信号

后续 retrieval 不应只看文本相关性，还应消费页面结构信息。

例如：

- `chart_heavy` 页中的 `dense_label` chunk 默认降权
- `cover / toc / disclaimer` 页默认降权
- `main` 区的 narrative chunk 在问答场景中优先

这会让 parser 层的提升真正传递到问答质量上。
