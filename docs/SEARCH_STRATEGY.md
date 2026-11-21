# 检索策略配置设计

NeuroDaily 目前已经能解析字段化布尔表达式、引用命名集合、限制期刊并按来源编译查询。运行时也能区分匹配、未匹配和源记录缺字段。结构上的主要缺口是 `search.query` 和 `search.sets` 保存的是字符串。一个概念的同义词、主题词、来源变体和版本依据要从字符串或多个 profile 中反查。

## 可以借鉴的实现

| 原始研究或实现 | 可借鉴的设计 |
| --- | --- |
| 2Dsearch 的视觉查询设计 | 把 AND、OR、NOT 与分组呈现为可编辑的树，文本输入和界面操作都生成同一个结构。 [设计论文](https://research.gold.ac.uk/27127/1/2dsearch%20for%20DESIRES%20camera%20ready.pdf) |
| Polyglot Search Translator | 为同一策略生成各库语法并保留人工复查。词组、通配、字段和主题词映射应分别验证。 [随机对照试验](https://doi.org/10.5195/jmla.2020.834) · [GitHub](https://github.com/IEBH/sra-polyglot) |
| searchRxiv、PRISMA-S 和 PRESS | 保存数据库、日期、完整表达式、限制条件和外部来源。对布尔逻辑、主题词和过滤条件提供发布前审阅。 [JSON 数据结构论文](https://doi.org/10.1002/cl2.1288) · [searchRxiv](https://searchrxiv.org/about/index.html) · [PRISMA-S](https://doi.org/10.1186/s13643-020-01542-z) · [PRESS](https://doi.org/10.1016/j.jclinepi.2016.01.021) |
| litsearchr | 从已知相关文献中找高频共现词和候选同义词，人工批准后再纳入正式策略。 [论文](https://doi.org/10.1111/2041-210X.13268) · [GitHub](https://github.com/elizagrames/litsearchr) |
| ir_measures | 将标注和检索输出分开，比较召回率、P@K 与 nDCG。可沿用项目现有的 `search-quality` 固定样本和来源预览。 [GitHub](https://github.com/terrierteam/ir_measures) |

以上项目用作方法参考。本项目这一版未引入这些代码或数据集。

## 建议的数据结构

保留 JSON 作为可导入、可验证的交换格式，把检索策略独立于推送、日程和 API 帐号配置。一个 profile 选择策略版本，并应用窗口和来源组合。建议的最小结构如下。

```json
{
  "schema_version": 1,
  "id": "icu-delirium",
  "revision": 3,
  "concepts": {
    "setting": {"text": ["intensive care", "ICU"], "mesh": [{"label": "Intensive Care Units", "explode": true}]},
    "condition": {"text": ["delirium", "acute confusion"], "mesh": [{"label": "Delirium", "explode": true}]}
  },
  "expression": {"op": "and", "args": [{"concept": "setting"}, {"concept": "condition"}]},
  "source_overrides": {
    "pubmed": {"use_controlled_vocabulary": true},
    "arxiv": {"fields": ["title", "abstract"]}
  },
  "validation": {"known_relevant_ids": ["pmid:<经人工核对的条目编号>"]}
}
```

1. 先从现有字符串编译出规范化的查询树，保留原文和旧配置加载。为概念、命名集合和版本提供稳定 ID，用同一棵树驱动文本编辑和分组编辑。
2. 每个来源声明字段、距离算符、短语和主题词能力。预览列出**推给来源的查询、回到本机执行的过滤、不可执行的条件**。例如仅有 RSS 标题的记录无法验证摘要条件，应进入待确认列表。
3. 每次运行记录策略指纹、来源查询、运行日期、候选量、排除原因和待确认量。修改策略前在固定标注集对比召回率和前 K 条准确率，再根据实际日报积累漏检样本。
4. 词扩展先作为人工审阅建议。临床问题可以用 PICO 帮助组织概念，同时让研究者决定哪些概念进入检索式。对于前沿动态，先用布尔和受控词表控制候选范围，再把语义评分用于排序。

这份设计可分版上线。优先落地概念词表、编译预览和运行快照，兼容测试覆盖后再启用新格式写入。
