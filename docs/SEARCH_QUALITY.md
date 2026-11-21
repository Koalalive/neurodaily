# 离线检索质量评估

```bash
neurodaily search-quality
neurodaily search-quality --top 2
neurodaily --config candidate.json search-quality --corpus corpus.json --baseline baseline.json
neurodaily --profile neuro search-quality --corpus corpus.json --baseline baseline.json
```

前两条命令使用 [内置的工作记忆样本](../neurodaily/data/search_quality_sample.json)。其中的论文标题、DOI、PMID 及来源状态均为合成演示数据，只用于核对指标和诊断。默认评估前 20 条。`--top 2` 能在小样本上看到相关论文排在截断线之后的情况。

`--config` 或 `--profile` 将候选配置应用到每个用例。省略这两个全局参数时，每个用例使用自己的 `search` 规则。`--baseline` 可选，同一批论文会用基线配置重放一次。输出为 JSON，`delta` 为候选指标减去基线指标。基线与候选用相同的相关性标注。

## 准备自己的语料

1. 每个主题建立一个 `cases` 用例。先定义相关论文的判断标准，使用 DOI 或 PMID 标注已知相关论文，以及经过人工判断的干扰项。用户提供的同一篇论文的 DOI 和 PMID 放在同一个 `labels[].ids` 数组中。
2. 保留待评估来源返回且通过时间窗口的候选元数据，尽可能保存原始来源之间的重复条目。每个 `candidates` 条目使用 `Item` 的字段，至少提供 `title` 和 `source`。DOI 写在 `doi`，PMID 写在 `extra.pmid`。保存 `summary` 或 `extra.abstract`、`date`、`extra.journal`、`extra.issn` 等规则会用到的字段。可以宽召回一次并冻结候选来比较两组本地规则。
3. 把人工已知相关、但当前抓取样本没有的论文也保留在 `labels` 内。可用 `expected_sources` 标明这些论文预计出现的来源，同时在 `sources` 记下该次抓取的状态、时间范围、分页上限及其他影响覆盖的条件。
4. 固定语料、标注、配置和 NeuroDaily 版本，逐次比较报告。`corpus_sha256` 可检查两次运行使用的语料是否一致。历史报告可供挑选标注论文，但需要另外保留被过滤和缺字段的候选，才能复现各个未命中原因。

最小语料结构如下。更多字段请参照内置样本。

```json
{
  "version": 1,
  "description": "某主题的固定候选和人工标注",
  "cases": [
    {
      "name": "working-memory",
      "search": {"query": "TI=\"working memory\"", "sort": "relevance"},
      "sources": {"pubmed": {"status": "ok", "coverage": "sampled"}},
      "candidates": [
        {"title": "Working memory during delayed recall", "source": "pubmed", "extra": {"pmid": "990001001"}}
      ],
      "labels": [{"ids": ["pmid:990001001"], "relevant": true}]
    }
  ]
}
```

## 指标定义

| 输出字段 | 含义 |
| --- | --- |
| `precision_at_k` | 前 K 条中人工标注相关的论文数除以 K。候选不足 K 条或尚未标注的结果会降低这个分数。结合 `top_papers` 和 `unjudged_top_papers` 判断可比较性。 |
| `known_paper_recall` | 本次命中并进入排序的已知相关论文数除以人工标注的相关论文总数。 |
| `known_paper_recall_at_k` | 排在前 K 的已知相关论文数除以人工标注的相关论文总数。 |

`judgments` 会给每篇带标注的论文列出处理结果。

| 状态 | 含义 |
| --- | --- |
| `missing_from_capture` | 输入的冻结候选中缺少该 DOI 或 PMID。结合 `source_capture` 判断来源覆盖范围。 |
| `unknown_metadata` | 候选存在，但精确规则需要的字段不足。`missing_fields` 列出这些字段。 |
| `filtered` | 候选存在，本地精确规则将其排除。 |
| `below_top_k` | 命中精确规则，排序位于前 K 之后。 |
| `in_top_k` | 命中精确规则，排序进入前 K。 |

评估复用正式检索的本地匹配、跨来源去重和排序。它从已冻结的论文候选开始，因此显示的是同批候选上的规则和排序效果。评估过程无需网络，也不会更新检索历史或触发推送。修改的设置如果会改变远端查询、启用来源或回溯窗口，需要用新的来源抓取验证这些变化对覆盖的影响。
