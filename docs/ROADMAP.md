# 竞品对照与接口路线

NeuroDaily 的核心任务是让研究者每天快速了解检索范围内发生了什么，并能回到具体来源、规则和日报。桌面端适合个人持续跟踪，GitHub Actions 适合在课题组的私有仓库运行。以下能力对照依据各产品公开文档，查阅日期为 2026 年 11 月 21 日。

## 竞品在哪些环节做得深

| 产品 | 最适合的工作 | 对 NeuroDaily 的启发 |
|---|---|---|
| PubMed + My NCBI | 保存字段检索和检索历史，用邮件或 RSS 跟踪同一检索式 | 用 PubMed 高级检索做可复现基线。面向明确的研究问题，核对 NeuroDaily 的规则、拉取窗口和漏检来源。 [PubMed 用户指南](https://pubmed.ncbi.nlm.nih.gov/help/) |
| ResearchRabbit | 由种子论文或馆藏探索前引、后引和相似文献，按项目收引用更新 | 给已入选的日报论文加「下一跳」入口。用户从关注的 DOI 出发探索，日报仍可按各来源规则独立复跑。 [引用图](https://learn.researchrabbit.ai/en/articles/17309356-how-to-read-the-citation-map-in-researchrabbit) · [项目提醒](https://learn.researchrabbit.ai/en/articles/17884627-how-do-i-get-alerts-for-new-papers) |
| Litmaps | 从起始论文扩展可视化图谱，按引文、共同作者或文本相似度发现新工作。Monitor 可跟踪已有图谱 | 第一版图谱只显示可回溯的关系边，给每条边标注关系与来源。语义推荐可以在后续独立评估。 [发现算法](https://docs.litmaps.com/en/articles/9029858-search-algorithms-in-litmaps) · [Monitor](https://docs.litmaps.com/en/articles/9126249-monitor-get-alerts-for-important-research) |
| Bibliometrix / Biblioshiny | 对已有语料做来源、作者、文献分析，支持主题演化、共被引、文献耦合与合作网络 | 提供可复现的冻结语料与字段覆盖率。报表内优先服务随手查看，完整计量项目可用导出的语料交接给专门工具。 [Biblioshiny 功能](https://www.bibliometrix.org/biblioshiny/) · [Bibliometrix 方法](https://www.bibliometrix.org/vignettes/Introduction_to_bibliometrix.html) |
| Zotero | 管理自己的书目和团队馆藏，适合保留阅读材料和引用记录 | 优先从日报导出入选文献，再让用户选定集合并确认写入。读写都用 Zotero 已有接口，避免重复建书目库。 [Zotero Web API v3](https://www.zotero.org/support/dev/web_api/v3/start) |

NeuroDaily 可以把细颗粒检索、多源抓取、增量报告和投递回执连成一个工作流。建议拿三个典型课题做对照。每个课题冻结一批已标注的 DOI 与 PMID，记录漏检环节、前 20 条有效率、用户从打开日报到保存值得读的条目所用时间。把 PubMed 保存的检索和 NeuroDaily 的候选配置放到相同学科、日期窗口和语料版本下比较。用已有 `search-quality` 做离线规则比较，再用定期采集检验线上覆盖。 [检索质量评估](SEARCH_QUALITY.md)

## 把文献计量嵌入 HTML

日报的「文献计量」直接使用本次检索得到的论文元数据。可以展开查看发表日期、期刊、作者和来源分布，跨年度的结果可按年份筛选。打开保存的 HTML 即可查看，数据和页面随日报保存。日期统计的样本是当次去重结果，结合来源状态看观察范围。试验、融资和政策条目仍按各自类别阅读。

| 统计或图表 | 所需数据 | 适合放哪里 |
|---|---|---|
| 日期趋势、期刊和来源分布 | 本次结果的日期、期刊、来源标识 | 日报中的趋势和条形汇总。后续可以叠加最近 30 天，按论文 ID 去重 |
| 作者合作图 | 确认身份的作者标识和同篇署名关系 | 专题视图，先标注姓名覆盖率与歧义比例。跨期统计优先使用 ORCID 或作者 ID |
| 直接引用、共被引与文献耦合 | DOI 或其他稳定 ID、参考文献列表和引文边 | 点击单篇文献后打开专用标签页。边的图例注明引用方向、共同被引或共享参考文献。 [Bibliometrix 方法](https://www.bibliometrix.org/vignettes/Introduction_to_bibliometrix.html) |
| 主题趋势与比较 | 明确定义的语料、可追踪关键词、日期、去重口径 | 独立计量报告。对比前保留时间窗口、规则版本、数据源和分母 |

图和数字最好都能点回对应的条目集合。把数据范围、缺字段数量及采集时间写在图旁边，表示确实查到零条与来源缺失的区别。近几日新论文的引文覆盖和收录延迟会影响计数，应结合元数据覆盖率解读。体量大的图可以单独输出自包含 HTML，邮件正文保留静态小结与日报链接。

## 最值得接入的接口

| 顺序 | 接口 | 首个交付 | 验收方式 |
|---|---|---|---|
| 1 | OpenAlex Works | 用户选中论文时按 DOI 补齐 OpenAlex ID、引用与参考文献。先显示一跳关系，按 ID 批量获取节点。保存来源、抓取时间和缺失状态 | 超时或限额时仍能打开日报。同一 DOI 的数据在缓存期内只取一次。每条边可以点到来源记录。 [Works 字段](https://help.openalex.org/data/works/attributes/) · [引文查询示例](https://help.openalex.org/how-to/api-recipes/) · [认证与限额](https://help.openalex.org/api/authentication/) |
| 2 | Crossref REST API | 核验 DOI 和书目元数据，补查期刊、许可、更新关系以及可获得的参考文献。保持已知预印本与期刊版的版本关系 | 打开的原文与匹配的 DOI 一致。书目缺失和服务超时具备独立状态。 [REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api) · [元数据匹配](https://www.crossref.org/documentation/retrieve-metadata) |
| 3 | Zotero | 先把日报选中文献批量生成 BibTeX。后续加写入选定合集的预览，逐条显示新增、已存在和失败 | 同一 DOI 重试时不重复导入。凭据按需要保存在本机，写入前展示目标库和条目数。 [Zotero Local API](https://www.zotero.org/support/dev/web_api/v3/local_api) · [Web API 写入](https://www.zotero.org/support/dev/web_api/v3/write_requests) |
| 4 | Bibliometrix / Biblioshiny | 导出可重复分析的数据包，附元数据、参考文献覆盖率、来源和采集日期。先选一种格式做真实往返验证 | 使用同一份数据包能够复查选集和计数。标注参与网络分析的有效条目数。 [Biblioshiny](https://www.bibliometrix.org/biblioshiny/) |

推荐顺序先把「为什么入选」「这篇论文后来被谁引用」「把它存到哪里」三个动作做顺。OpenAlex 和 Crossref 查询可放在 sidecar，浏览器报告从本地读取结果，便于缓存并保护 API key。正式新增接口时，可在现有任务进度中显示抓取、缓存命中、缺失和重试状态。
