# 研究地图与 API 账单

## 使用方式

- **研究动态地图**显示在日报的 AI 摘要之后。未生成摘要时，地图显示在正文列表之前。地图可按论文、临床试验、新闻与政策筛选。点击点位可查看来源、定位依据和原文链接。
- 试验注册库提供坐标时，显示登记站点。其余可确认的地区显示国家或地区级示意点。作者机构、研究地点、试验站点和新闻事件发生地分别标注。未定位的条目可从地图下方查看。
- 进入 **设置 → API 账单与地图设置**，按 API 基础地址和模型填写每百万 token 的费率和币种。账单按真实 HTTP 调用记录，包括摘要、连通性检查、定位和重试。缺少用量或适用费率的请求显示未知。历史费用保留请求发生时的费率，实际扣费以服务商账单为准。
- AI 定位默认关闭。开启后，已启用的摘要模型可尝试补充定位，使用公开的来源文字片段并保留证据。每次运行最多处理 24 个需要调用模型的候选条目。已验证的定位可从本机缓存复用。设置、账单和缓存保存在应用数据目录，账单与密钥不会写进分享的 HTML。可用 `neurodaily demo --no-open` 进行无网络演示。

## 商用许可

| 部件 | 许可和发行范围 |
| --- | --- |
| NeuroDaily 与新增页面 | [Apache-2.0](../LICENSE)。地图和账单界面使用浏览器原生 Canvas、HTML、CSS、JavaScript，无新引入的运行时库、字体、CDN 或地图瓦片服务。 |
| 底图和地点索引 | Natural Earth 数据属于公有领域，允许商用、修改和再发行。项目在日报和 [NOTICE](../NOTICE) 保留出处。 [Natural Earth 许可](https://www.naturalearthdata.com/about/terms-of-use/) |
| 既有桌面壳与 Python 服务 | Tauri 采用 MIT 或 Apache-2.0 双许可，FastAPI 为 MIT，Jinja 为 BSD-3-Clause。PyInstaller 的打包例外允许发行商用应用，所打包依赖仍适用各自许可。 [Tauri](https://github.com/tauri-apps/tauri#license) · [FastAPI](https://github.com/fastapi/fastapi/blob/master/LICENSE) · [Jinja](https://github.com/pallets/jinja/blob/main/LICENSE.txt) · [PyInstaller](https://pyinstaller.org/en/stable/license.html) |

打包发行时应随发行物保留适用的许可证和声明。上表覆盖本次新增可视化和主要框架，完整安装包还应以各平台的锁定依赖和捆绑内容为准。模型 API 调用受账户所签的服务条款约束。论文摘要、新闻文本和试验注册数据各自适用来源授权，应用许可不会授予其商业转载权。 [DeepSeek 开放平台条款](https://cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html) · [OpenAI 服务协议](https://openai.com/policies/services-agreement/) · [PubMed 数据和版权](https://www.nlm.nih.gov/databases/download.html) · [ClinicalTrials.gov 数据](https://clinicaltrials.gov/data-about-studies/csv-download)

### 底图来源

两个输入文件均固定到 Natural Earth Vector v5.1.2。

| 打包文件 | 上游及处理方法 | 上游 SHA-256 |
| --- | --- | --- |
| `natural_earth_land.json` | [1:110m 陆地](https://github.com/nvkelso/natural-earth-vector/blob/v5.1.2/geojson/ne_110m_land.geojson)。提取多边形轮廓与内环，坐标保留两位小数。 | `9e0729ee253ca7d7a5c4ae9395fb1902264c5377c52e224d13dd85010e2835d9` |
| `natural_earth_countries.json` | [1:10m Admin 0 数据](https://github.com/nvkelso/natural-earth-vector/blob/v5.1.2/geojson/ne_10m_admin_0_countries.geojson)。提取地区代码、名称及标签坐标，坐标保留三位小数。 | `239eec57ac17f100a11e2536cffc56752c318b50ae765b0918ff7aab4ce8f255` |

背景只包含陆地轮廓。地点索引只用于示意标记，未打包或绘制行政边界。

## 分类型检索与可选来源

在 **设置 → 高级检索** 中填写论文、新闻、政策和试验各自的表达式，可复用编号集合。在订阅源列表为每个 RSS 选择内容类型。旧配置仍可使用 URL 列表，可用 `sources.policy.feed_kinds` 为其中的 URL 指定类型。预览会采样启用的相关来源并展示命中、排除和缺字段的样例，预览过程不写日报或历史记录。

PubMed 日常检索同时检查发表日期和首次入库时间，显示仍使用论文发表日期。ClinicalTrials.gov 分批查询匹配词、按分页标记继续读取，并分别展示首次登记、最近更新、结果发布和本机观察到的状态变更。命中请求预算时显示覆盖不完整。 [PubMed 日期说明](https://pubmed.ncbi.nlm.nih.gov/help/#create-date-crdt) · [ClinicalTrials.gov API](https://clinicaltrials.gov/data-api/api)

在 **设置 → 数据源** 勾选要使用的可选来源。旧配置和新配置都默认关闭这些额外请求。

| 数据源 | 用途与配置 |
| --- | --- |
| `europe_pmc` | 医学文献及预印本补充。可填写 Europe PMC 语法的专用查询。 [REST API](https://dev.europepmc.org/RestfulWebService) |
| `openalex` | 脑机接口等工程交叉文献。可填 OpenAlex 文本检索词，环境变量 `OPENALEX_API_KEY` 可用于更多分页。平台提供 CC0 数据，API 额度及计费独立。 [API](https://help.openalex.org/api/) · [计费](https://help.openalex.org/access/pricing/) |
| `gdelt` | 跨语言新闻发现，保留标题、链接和索引时间。可填写 GDELT 专用表达式。 [DOC API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/) |
| `nih_brain` | 从 NIH 官方综合新闻 RSS 筛选明确提到 BRAIN Initiative 的新闻。 [NIH 新闻发布](https://www.nih.gov/news-events/news-releases) |
| `crossref` | 对本轮取得的论文按 DOI 补充可用版本关系和更正、撤稿等元数据。它在采集后运行，独立设置查询条数。 [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) |

日报使用 DOI、PMID、NCT 或原始链接关联本轮研究记录和新闻。仅标题近似的条目标记为待确认。供商用分发的报告应按来源条款决定可再利用的字段，尤其是新闻正文、出版社摘要和图片。

## 历史条目检索

**运行历史 → 历史条目检索**使用本机 SQLite 索引，可以按类型查询已生成日报。新运行自动加入索引。**导入已有任务日报**从当前 profile 的任务检查点补建历史索引，早期只保存 HTML 的日报仍可查看。中英文混合文本按标准化后的词和短语处理。

如已有 OpenSearch 混合检索实例，启动前填写 `NEURODAILY_OPENSEARCH_URL`、`NEURODAILY_OPENSEARCH_INDEX`、`NEURODAILY_OPENSEARCH_PIPELINE`、`NEURODAILY_OPENSEARCH_MODEL_ID`，需要 Basic 认证时另设 `NEURODAILY_OPENSEARCH_USERNAME` 和 `NEURODAILY_OPENSEARCH_PASSWORD`。启动后在历史条目检索页面选择 OpenSearch。已有索引需要 `profile` 和 `kind` 的 keyword 字段、`title` 和 `summary` 的文本字段、`embedding` 向量，以及混合检索 pipeline。该入口查询已有索引，本机日报继续写入 SQLite。 [OpenSearch 混合检索配置](https://docs.opensearch.org/latest/vector-search/ai-search/hybrid-search/)
