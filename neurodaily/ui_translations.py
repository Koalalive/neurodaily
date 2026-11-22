"""Translate interface copy while leaving source records and user data intact."""

from functools import lru_cache
import json
import re

from .bibliometrics import _LABELS as _BIBLIOMETRICS_LABELS


UI_LANGUAGES = ("zh", "en", "ru")

# These are the labels shared by the report, run, task, and settings screens.
# Each row contains the Chinese, English, and Russian spelling of one message.
_MESSAGES = """
界面语言|Interface language|Язык интерфейса
无法读取界面语言。|Could not read the interface language.|Не удалось прочитать язык интерфейса.
无法保存界面语言。|Could not save the interface language.|Не удалось сохранить язык интерфейса.
神通寰宇 · 设置|NeuroDaily — Settings|NeuroDaily — Настройки
⚙ 神通寰宇设置|⚙ NeuroDaily Settings|⚙ Настройки NeuroDaily
← 返回日报|← Back to dashboard|← К сводке
⚙ 设置|⚙ Settings|⚙ Настройки
设置|Settings|Настройки
历史记录|History|История
运行历史|Run history|История запусков
日报首页|Report dashboard|Главная сводка
最新日报|Latest report|Последняя сводка
尚无已保存的日报。|No saved report yet.|Сохранённых сводок пока нет.
检索历史|Search History|История поиска
清除全部历史记录|Clear all history|Очистить всю историю
← 返回日报首页|← back to dashboard|← К главной сводке
尚无检索记录，请先运行一次检索。|No searches recorded yet. Run one first.|История пуста. Сначала запустите поиск.
查看|view|просмотр
删除|delete|удалить
神通寰宇历史记录|NeuroDaily History|История NeuroDaily
相互翻译|Compare runs|Сравнить запуски
聚焦提示词|Focus prompt|Промпт по теме
本次检索范围|Search window for this run|Интервал поиска для этого запуска
神通寰宇 · 开始检索|NeuroDaily — Run now|NeuroDaily — Запуск поиска
日报生成后自动打开。AI 摘要和投递会继续处理。|The report opens when it is ready. AI summary and delivery continue in the background.|Готовая сводка откроется автоматически. ИИ-резюме и отправка выполняются в фоне.
临时覆盖时间范围（小时，可选）|Override the search window for this run (hours, optional)|Задать интервал для этого запуска (часы, необязательно)
留空使用已保存的设置|Leave blank to use saved settings|Оставьте пустым, чтобы использовать сохранённые настройки
例如填 36，把本次论文、试验、融资和新闻的窗口设为最近 36 小时。|Enter 36 to look for papers, trials, funding and news from the last 36 hours.|Например, 36 — поиск публикаций, исследований, финансирования и новостей за последние 36 часов.
返回设置|Back to settings|К настройкам
开始检索|Start search|Начать поиск
▶ 开始检索|▶ Run now|▶ Запустить поиск
正在检索…|Running…|Поиск…
查看任务进度|View progress|Ход выполнения
定时检索正在运行|Scheduled search is running|Идёт поиск по расписанию
检索正在运行|Search is running|Идёт поиск
已处理 {done}/{total} 个来源|Processed {done}/{total} sources|Обработано источников: {done}/{total}
已生成日报（{count} 条），正在打开…|Report ready ({count} items), opening…|Сводка готова ({count}), открытие…
已生成日报（{count} 条）。|Report ready ({count} items).|Сводка готова ({count}).
本次检索未生成报告|This search did not produce a report|Поиск не сформировал сводку
等待超时，请在运行历史中查看结果|Wait timed out. Check the result in run history.|Время ожидания истекло. Проверьте историю запусков.
请输入 1–8760 的整数小时|Enter a whole number of hours from 1 to 8760|Введите целое число часов от 1 до 8760
已启动，正在检索…|Search started…|Поиск запущен…
已有检索正在运行。|A search is already running.|Поиск уже выполняется.
启动失败|Could not start the search|Не удалось запустить поиск
任务 #{id}|Task #{id}|Задача №{id}
任务|Task|Задача
神通寰宇 · 任务 #{id}|NeuroDaily — Task #{id}|NeuroDaily — Задача №{id}
条结果|results|результатов
{kind} #{id} 进行中|{kind} #{id} is running|{kind}, №{id}: выполняется
定时检索|Scheduled search|Поиск по расписанию
手动检索|Manual search|Ручной поиск
检索|Search|Поиск
日报|Report|Сводка
期刊指标|Journal metrics|Показатели журналов
AI 摘要|AI summary|ИИ-резюме
投递|Delivery|Отправка
进行中|In progress|Выполняется
等待中|Waiting|Ожидает
发送中|Sending|Отправляется
完成|Completed|Завершено
失败|Failed|Ошибка
部分完成|Partially completed|Частично завершено
中断|Interrupted|Прервано
已跳过|Skipped|Пропущено
服务器已接受|Accepted by the server|Принято сервером
没有新内容|No new items|Нет новых материалов
结果未确认|Outcome unconfirmed|Результат не подтверждён
成功|Succeeded|Успешно
无匹配|No matches|Совпадений нет
超时|Timed out|Время ожидания истекло
触发限流|Rate limited|Сработало ограничение запросов
重试|Retry|Повторить
打开本次日报|Open report|Открыть сводку
计划执行|Scheduled for|Запланировано на
实际开始|Started at|Начато в
记录结束|Finished at|Завершено в
处理阶段|Processing stages|Этапы обработки
阶段|Stage|Этап
状态|Status|Состояние
更新时间|Updated|Обновлено
详情|Details|Подробности
暂无处理阶段。|No processing stages yet.|Этапы обработки пока отсутствуют.
来源进度|Source progress|Ход поиска по источникам
来源|Source|Источник
抓取|Retrieved|Получено
匹配|Matched|Совпало
暂无来源进度。|No source progress yet.|Данные о ходе поиска по источникам пока отсутствуют.
投递记录|Delivery receipts|Журнал отправки
渠道|Destination|Канал
尝试次数|Attempts|Попытки
暂无投递记录。|No delivery receipts yet.|Записи об отправке пока отсутствуют.
正在重试投递…|Retrying delivery…|Повторная отправка…
重试失败。|Delivery retry failed.|Не удалось повторить отправку.
无法连接服务。|Could not connect to the service.|Не удалось подключиться к службе.
配置文件|Profile configuration|Файл профиля
导出已保存的配置|Export saved configuration|Экспорт сохранённой конфигурации
导入配置文件|Import configuration|Импорт конфигурации
确认导入|Confirm import|Подтвердить импорт
分享学科、检索规则、期刊和数据源设置。邮件、Webhook 和本机路径由各自设备管理。|Share disciplines, queries, journals and sources. Email, webhooks and local paths are set per device.|В файл входят дисциплины, запросы, журналы и источники. Почта, вебхуки и локальные пути настраиваются на каждом устройстве.
研究预设|Research presets|Профили исследований
预设会填入研究设置，请检查后保存。|A preset fills the research fields. Review them before saving.|Профиль заполняет поля исследования. Проверьте их перед сохранением.
神经科学|Neuroscience|Нейронауки
肿瘤学|Oncology|Онкология
常规|General|Общие настройки
配置名称（如 neuro）|profile (e.g. neuro)|имя профиля (например, neuro)
学科（研究领域）|Disciplines (focus areas)|Дисциплины (области исследования)
每行一个学科，分类和关键词用逗号分隔。|One discipline per row; separate categories and keywords with commas.|По одной дисциплине в строке. Категории и ключевые слова разделяйте запятыми.
+ 添加学科|+ Add discipline|+ Добавить дисциплину
全局关键词|Global keywords|Общие ключевые слова
高级文献检索|Advanced literature search|Расширенный поиск публикаций
为当前研究配置编写检索式，并预览各来源的执行方式。|Build a query for this research profile and preview how each source applies it.|Составьте запрос для этого профиля и проверьте, как его обрабатывает каждый источник.
通过条件构建|Build with conditions|Составить из условий
纳入条件组|Include groups|Включить группы
满足所有组|Match all groups|Совпадение со всеми группами
满足任一组|Match any group|Совпадение с любой группой
+ 添加条件组|+ Add group|+ Добавить группу
加入检索式|Add to expression|Добавить в выражение
创建检索集合|Create search set|Создать набор поиска
新增条件通过 AND 与当前检索式连接。|Added conditions are joined to the current expression with AND.|Новые условия добавляются к текущему выражению через AND.
检索式|Search expression|Поисковое выражение
使用|Use|Используйте
括号|parentheses|скобки
如需关键词检索，请清空检索式并保留所有期刊。|For a keyword search, clear the expression and keep all journals.|Для поиска по ключевым словам очистите выражение и оставьте все журналы.
编号检索集合|Numbered search sets|Нумерованные наборы поиска
+ 添加检索集合|+ Add search set|+ Добавить набор поиска
在检索式中复用集合，例如|Reuse sets in the expression, for example|Используйте наборы в выражении, например
期刊范围|Journal scope|Охват журналов
所有期刊|All journals|Все журналы
仅列出的期刊|Only listed journals|Только журналы из списка
优先列出的期刊|Prioritize listed journals|Журналы из списка в приоритете
排序结果|Sort results|Сортировка результатов
默认|Default|По умолчанию
相关度|Relevance|Релевантность
最新优先|Newest first|Сначала новые
重点期刊优先|Priority journals first|Сначала приоритетные журналы
期刊名称或 ISSN|Journal names or ISSNs|Названия журналов или ISSN
期刊用逗号分隔。名称含逗号时请加双引号。|Separate journals with commas. Put names containing commas in double quotes.|Разделяйте журналы запятыми. Если в названии есть запятая, заключите его в двойные кавычки.
预览检索|Preview search|Предпросмотр поиска
按来源预览检索|Search preview by source|Предпросмотр поиска по источникам
数据源|Sources|Источники
选择是否启用，并设置每次抓取上限和回溯天数。|Enable, max results per fetch, lookback days.|Включение, лимит результатов на запрос и глубина поиска в днях.
输出|Output|Вывод
报告内容|Report content|Содержание отчёта
报告目录|Report directory|Папка сводок
文件名格式|Filename format|Формат имени файла
完成后打开报告|Open report when finished|Открыть готовую сводку
检索时间范围|Retrieval windows|Интервалы поиска
仅显示时间范围内的结果，自动检索和手动检索的范围可不同（小时）。|Only items inside each window are shown; daily and manual runs can differ (hours).|Показываются материалы из заданного интервала. Для автоматического и ручного поиска интервалы в часах могут отличаться.
每日检索论文范围（小时）|Daily: paper hours|Ежедневный поиск публикаций (часы)
手动检索论文范围（小时）|Manual: paper hours|Ручной поиск публикаций (часы)
试验范围（小时）|Trials: hours|Клинические исследования (часы)
融资范围（小时）|Funding: hours|Финансирование (часы)
新闻与政策范围（小时）|News / policy: hours|Новости и политика (часы)
定时设置|Schedule|Расписание
启用定时检索|Enable schedule|Включить расписание
执行时间|Time|Время
显示「历史上的今天」（神经科学史）|Include "On This Day" (neuroscience history)|Показывать «Этот день в истории» (история нейронаук)
每日桌面通知|Desktop notification daily|Ежедневное уведомление на рабочем столе
「历史上的今天」语言|"On This Day" language|Язык рубрики «Этот день в истории»
中文|Chinese|Китайский
调度器：…|Scheduler: …|Планировщик: …
安装或更新定时任务|Install / update schedule|Установить или обновить расписание
移除定时任务|Uninstall schedule|Удалить расписание
政策与新闻 RSS|Policy / news RSS|Политика и новости (RSS)
+ 添加 RSS|+ Add RSS|+ Добавить RSS
关注期刊|Top journals watch-list|Список отслеживаемых журналов
有 RSS 的期刊会收录到论文板块。添加别名和 ISSN 可识别不同来源中的同一期刊。|Journals with RSS are fetched for the papers section. Add aliases and ISSNs to recognize the same journal across sources.|Журналы с RSS включаются в раздел публикаций. Псевдонимы и ISSN помогают распознавать журнал в разных источниках.
+ 添加期刊|+ Add journal|+ Добавить журнал
推送设置（邮件 / Webhook）|Push settings (email / webhook)|Настройки рассылки (почта / вебхуки)
开始检索前请先保存。可按需启用推送。|Save these settings before starting a search. Delivery is optional.|Сохраните настройки перед поиском. Рассылку можно не включать.
启用邮件|Enable email|Включить почту
附上完整 HTML|Attach full HTML|Прикрепить полный HTML
收件人（用逗号或换行分隔）|Recipients (comma or newline separated)|Получатели (через запятую или с новой строки)
SMTP 服务器|SMTP host|SMTP-сервер
端口|Port|Порт
SMTP 加密方式|SMTP encryption|Шифрование SMTP
STARTTLS（常用 587）|STARTTLS (usually 587)|STARTTLS (обычно 587)
SSL/TLS（常用 465）|SSL/TLS (usually 465)|SSL/TLS (обычно 465)
用户名|Username|Имя пользователя
发件人|From|Отправитель
主题模板|Subject template|Шаблон темы письма
SMTP 应用密码|SMTP app password|Пароль приложения SMTP
留空保留原有设置|Leave blank to keep|Оставьте пустым, чтобы сохранить прежнее значение
测试邮件连通性|Test email connection|Проверить подключение почты
飞书 Webhook|Feishu webhook|Вебхук Feishu
企业微信 Webhook|WeCom webhook|Вебхук WeCom
启用 AI 摘要|Enable AI summary|Включить ИИ-резюме
API 基础地址|API base URL|Базовый URL API
模型 ID|Model ID|Идентификатор модели
服务商提供的模型 ID|Model ID from the provider|Идентификатор модели у поставщика
API 密钥|API key|Ключ API
留空保留已有密钥|Leave blank to keep the existing key|Оставьте пустым, чтобы сохранить прежний ключ
测试模型 API|Test model API|Проверить API модели
使用兼容 Chat Completions 的接口。测试使用当前输入，仅发送一条简短请求，可在保存前验证。|Use a Chat Completions-compatible API. You can test the current settings before saving with one short request.|Используйте API, совместимый с Chat Completions. Перед сохранением настройки можно проверить одним коротким запросом.
重置|Reset|Сброс
恢复内置默认配置，覆盖当前设置。|Reset config to built-in defaults (overwrites current settings).|Восстановить встроенные значения, заменив текущие настройки.
恢复默认|Reset to defaults|Восстановить значения по умолчанию
保存并开始检索|Save & continue to search|Сохранить и перейти к поиску
仅保存|Save only|Только сохранить
重新加载|Reload|Перезагрузить
搜索字段|Search field|Поле поиска
标题或摘要|Title or abstract|Название или аннотация
标题|Title|Название
摘要|Abstract|Аннотация
主题|Topic|Тема
期刊|Journal|Журнал
作者|Author|Автор
作者关键词|Author keywords|Ключевые слова автора
文献类型|Publication type|Тип публикации
出版年份|Publication year|Год публикации
出版日期|Publication date|Дата публикации
来源分类|Source category|Категория источника
匹配方式|Match type|Тип совпадения
匹配短语|Match phrase|Совпадение с фразой
全部词语|All words|Все слова
任一词语|Any word|Любое слово
检索词|Search terms|Поисковые термины
输入词语或短语|Enter words or a phrase|Введите слова или фразу
移除条件|Remove condition|Удалить условие
条件组|Condition group|Группа условий
组合条件|Combine conditions|Объединить условия
满足全部条件|Match all conditions|Совпадение со всеми условиями
满足任一条件|Match any condition|Совпадение с любым условием
排除匹配项|Exclude matches|Исключить совпадения
移除条件组|Remove group|Удалить группу
+ 添加条件|+ Add condition|+ Добавить условие
使用 #{number}|Use #{number}|Использовать набор №{number}
移除检索集合 #{number}|Remove search set #{number}|Удалить набор №{number}
请输入一个检索词。|Enter a term in a condition to continue.|Введите термин в условие, чтобы продолжить.
已创建检索集合 #{number}。|Search set #{number} created.|Набор поиска №{number} создан.
已将条件加入检索式。|Conditions added to the expression.|Условия добавлены в выражение.
无标题记录|Untitled record|Запись без названия
需更多元数据确认是否匹配。|Needs more metadata to confirm a match.|Для подтверждения совпадения нужны дополнительные метаданные.
已匹配 · {rules}|Matched · {rules}|Совпадение · {rules}
缺失字段 · {fields}|Fields unavailable · {fields}|Недоступные поля · {fields}
可用|Available|Доступен
部分覆盖|Partial coverage|Частичный охват
有限|Limited|Ограничено
不支持|Unsupported|Не поддерживается
已按设置完成抓取|Complete for this request|Запрос выполнен полностью
样本范围内的结果|Sampled coverage|Результат по выборке
仅覆盖部分请求|Only part of this request was covered|Выполнена только часть запроса
样本中无匹配|No sample matches|В выборке совпадений нет
未知|Unknown|Неизвестно
已到达抓取上限。|Candidate cap reached|Достигнут лимит кандидатов
{count} 条确认匹配|{count} confirmed matches|Подтверждённых совпадений: {count}
{count} 条匹配|{count} matches|Совпадений: {count}
{count} 条候选|{count} candidates|Кандидатов: {count}
{count} 条待确认|{count} unconfirmed|Неподтверждённых: {count}
发布日期 · {start} 至 {end}|Publication dates · {start} to {end}|Даты публикации · {start} — {end}
来源回溯 · {count} 天|Source lookback · {count} days|Глубина поиска по источнику · {count} дн.
已取得 · {count}|Retrieved · {count}|Получено · {count}
来源检索式|Source query|Запрос источника
来源检索式|Source queries|Запросы источника
设置无效。|Invalid settings.|Недопустимые настройки.
设置有变更。请重新预览。|Settings changed. Preview again to see updated results.|Настройки изменились. Повторите предпросмотр.
正在检查启用的数据源…|Checking enabled sources…|Проверяются включённые источники…
预览期间设置有变更。请重新预览。|Settings changed during the preview. Preview again.|Настройки изменились во время предпросмотра. Повторите его.
没有可供预览的数据源。|No sources available for this preview.|Для предпросмотра нет доступных источников.
{matches} 条去重匹配 · {unknown} 条缺少元数据|{matches} unique matches · {unknown} with missing metadata|Уникальных совпадений: {matches} · без метаданных: {unknown}
「{profile}」配置预览。|Preview for {profile}.|Предпросмотр профиля «{profile}».
当前配置|this profile|текущий профиль
预览失败。{error}|Preview failed. {error}|Ошибка предпросмотра. {error}
学科名称|Discipline name|Название дисциплины
arXiv 分类|arXiv categories|Категории arXiv
bioRxiv 分类|bioRxiv categories|Категории bioRxiv
关键词|Keywords|Ключевые слова
启用|On|Вкл.
每次抓取上限|max_results|Максимум результатов
回溯天数|lookback_days|Глубина поиска в днях
期刊名称|Journal name|Название журнала
网站 URL|Website URL|URL сайта
RSS（可选）|RSS (optional)|RSS (необязательно)
类别|Category|Категория
中科院分区|中科院|Категория Китайской академии наук
期刊别名|Journal aliases|Другие названия журнала
重症医学|Critical care|Интенсивная терапия
已应用「{preset}」。{hint}|{preset} applied. {hint}|Применено: {preset}. {hint}
检查重置后的检索条件并保存。|Review the reset search conditions and save.|Проверьте сброшенные условия поиска и сохраните настройки.
请检查后保存。|Review and save to use it.|Проверьте и сохраните настройки.
无法加载研究预设。|Could not load research presets.|Не удалось загрузить профили исследований.
无法加载设置|Could not load settings|Не удалось загрузить настройки
配置：{path}|Config: {path}|Конфигурация: {path}
加载失败：{error}|Load failed: {error}|Ошибка загрузки: {error}
无法读取配置文件|Could not read the configuration file|Не удалось прочитать файл конфигурации
正在校验配置…|Validating configuration…|Проверяется конфигурация…
配置文件不能超过 256 KB|Configuration files cannot exceed 256 KB|Файл конфигурации не должен превышать 256 КБ
{disciplines} 个学科 · {sources} 个数据源 · {journals} 本期刊|{disciplines} disciplines · {sources} sources · {journals} journals|Дисциплин: {disciplines} · источников: {sources} · журналов: {journals}
含高级检索规则|Includes advanced search rules|Включает расширенные правила поиска
本机专用字段将跳过|Device-specific fields will be skipped|Локальные поля будут пропущены
校验失败 · {error}|Validation failed · {error}|Ошибка проверки · {error}
已导入 {profile}|Imported {profile}|Импортировано: {profile}
导入失败 · {error}|Import failed · {error}|Ошибка импорта · {error}
正在保存…|Saving…|Сохранение…
✅ 已保存 → {path}|✅ Saved → {path}|✅ Сохранено → {path}
保存失败。{error}|Save failed. {error}|Ошибка сохранения. {error}
恢复默认设置？这将覆盖当前设置。|Reset to defaults? This overwrites current settings.|Восстановить значения по умолчанию? Текущие настройки будут заменены.
✅ 已恢复默认|✅ Reset to defaults|✅ Настройки сброшены
❌ 重置失败|❌ Reset failed|❌ Не удалось сбросить настройки
保存后生效。启动或唤醒时，软件会补跑当天错过的检索。最小化窗口可继续运行，退出应用将停止定时服务。|Save to apply. The app catches up on today’s missed time when it starts or wakes. Minimize the window to keep it running. Quitting stops the scheduled service.|Сохраните настройки. При запуске или выходе из сна приложение выполняет пропущенный за сегодня поиск. В свёрнутом приложении расписание работает, при выходе служба останавливается.
更改时间后，请点击「安装或更新定时任务」。|After changing the time, click Install / update schedule to apply.|После изменения времени установите или обновите расписание.
桌面定时：每日 {time}（本地时间）|Desktop schedule: daily at {time} (local time)|Расписание: ежедневно в {time} (местное время)
桌面定时：已关闭|Desktop schedule: off|Расписание: отключено
调度器：{loaded} / {installed}（{time}）|Scheduler: {loaded} / {installed} ({time})|Планировщик: {loaded} / {installed} ({time})
已加载|loaded|активен
未加载|not loaded|неактивен
已安装|installed|установлен
未安装|not installed|не установлен
正在检索|Searching now|Идёт поиск
等待启动|Waiting to start|Ожидается запуск
上次失败，{time} 重试|Last attempt failed. Retry {time}|Последняя попытка не удалась. Повтор: {time}
下次 {time}|Next {time}|Следующий запуск: {time}
上次 {time}（{state}）|Last {time} ({state})|Последний запуск: {time} ({state})
调度器：读取失败|Scheduler: read failed|Планировщик: ошибка чтения
移除定时任务？|Uninstall schedule？|Удалить расписание?
正在执行…|Working…|Выполняется…
已安装或更新|installed/updated|установлено или обновлено
已移除|Uninstalled|Удалено
❌ 操作失败|❌ Action failed|❌ Не удалось выполнить действие
（已设置）|(set)|(задано)
（未设置）|(not set)|(не задано)
无法保存推送设置|Failed to save push settings|Не удалось сохранить настройки рассылки
无法保存密码|Failed to save password|Не удалось сохранить пароль
正在测试…|Testing…|Проверка…
测试失败，请稍后重试。|Test failed. Try again later.|Проверка не удалась. Повторите попытку позже.
测试失败，请检查 NeuroDaily 服务是否仍在运行。|Test failed. Check that the NeuroDaily service is running.|Проверка не удалась. Убедитесь, что служба NeuroDaily работает.
已保存|Saved|Сохранено
来自环境变量|From environment variable|Из переменной среды
来自本机密钥文件|From local key file|Из локального файла ключа
待填写|Not set|Не задано
暂时无法读取 AI 设置|Could not read AI settings|Не удалось прочитать настройки ИИ
无法保存 AI 设置|Could not save AI settings|Не удалось сохранить настройки ИИ
目录|Contents|Содержание
↑ 顶部|↑ Top|↑ Наверх
🧠 AI 摘要|🧠 AI summary|🧠 ИИ-резюме
🧠 今日 AI 摘要|🧠 Today’s AI summary|🧠 ИИ-резюме за сегодня
由 AI 依据当日抓取内容生成，仅供参考；请以原文为准。|AI generated this summary from today’s results. Consult the original sources for details.|ИИ подготовил резюме по сегодняшним результатам. Подробности смотрите в первоисточниках.
📅 历史上的今天|📅 On this day|📅 Этот день в истории
历史上的今天|On this day|Этот день в истории
📄 最新论文|📄 Latest Papers|📄 Новые публикации
💊 产业与融资|💊 Industry and funding|💊 Индустрия и финансирование
🧪 临床试验|🧪 Clinical trials|🧪 Клинические исследования
🏛️ 政策与新闻|🏛️ Policy and news|🏛️ Политика и новости
📚 期刊|📚 Journals|📚 Журналы
来源状态|Source Health|Состояние источников
神经科学与精神病学日报|neuroscience & psychiatry digest|сводка по нейронаукам и психиатрии
肿瘤学日报|oncology digest|сводка по онкологии
科研日报|research digest|научная сводка
自动汇总|Auto-aggregated|Собрано автоматически
配置|Profile|Профиль
条目|Items|Материалы
论文|Papers|Публикации
产业|Industry|Индустрия
试验与会议|Trials / Conf|Исследования и конференции
政策与新闻|Policy / News|Политика и новости
🧪 临床试验与会议动态|🧪 Trials & Conference Signals|🧪 Клинические исследования и конференции
💊 产业与监管进展|💊 Commercial & Regulatory Progress|💊 Индустрия и регуляторные новости
🏛️ 政策、融资与新闻|🏛️ Policy, Funding & News|🏛️ Политика, финансирование и новости
聚焦领域内的 PubMed、arXiv 和 bioRxiv 最新论文。|New PubMed, arXiv, and bioRxiv preprints matching your focus.|Новые публикации по вашим темам из PubMed, arXiv и bioRxiv.
近期 FDA 药品审批和 510(k) 医疗器械许可。|Recent FDA drug approvals and 510(k) device clearances.|Недавние одобрения лекарств FDA и разрешения на устройства по процедуре 510(k).
新增与更新的临床研究及会议动态。|New + updated clinical studies and event signals.|Новые и обновлённые клинические исследования, а также новости мероприятий.
机构新闻、监管公告和其他动态。|Institutional press, agency announcements, and news.|Новости организаций и объявления ведомств.
排序|Sort|Сортировка
排序 · 相关性|Sort · Relevance|Сортировка · По релевантности
排序 · 最新发布|Sort · Newest first|Сортировка · Сначала новые
排序 · 重点期刊|Sort · Priority journals|Сортировка · Приоритетные журналы
相关性|Relevance ranking|По релевантности
最新发布|Most recent|По дате публикации
重点期刊|Priority journals|Приоритетные журналы
待确认|Unconfirmed|Требует проверки
官方 JCR 影响因子|Official JCR impact factor|Официальный импакт-фактор JCR
OpenAlex 两年平均被引次数（非 JCR IF）|OpenAlex two-year mean citations (not JCR IF)|Среднее число цитирований за два года по OpenAlex (отличается от JCR IF)
命中依据|Why it matched|Причина совпадения
无法判断的字段|Fields that need verification|Поля, требующие проверки
作者：|Authors:|Авторы:
通讯作者：|Corresponding authors:|Авторы для переписки:
单位：|Affiliations:|Организации:
合并来源|Combined sources|Объединённые источники
相关版本|Related versions|Связанные версии
正式发表|Published|Опубликованная версия
预印本|Preprint|Препринт
阅读原文 ↗|Read ↗|Читать ↗
本板块暂无检索结果。|No items retrieved for this category.|Для этого раздела ничего не найдено.
重点期刊列表|Top Journals|Ведущие журналы
点击期刊名称访问网站。|Curated watch-list of leading journals — click to browse each site.|Нажмите на название журнала, чтобы открыть его сайт.
IF、JCR 和中科院分区来自导入的官方表。|IF, JCR and CAS rankings come from the imported official table.|IF, JCR и категории КАН взяты из импортированной официальной таблицы.
各来源检索状态|Search status by source|Состояние поиска по источникам
候选|Candidates|Кандидаты
已抓取|Fetched|Получено
命中|Matches|Совпадения
耗时|Elapsed|Затрачено времени
正常|Healthy|Работает
无命中|No results|Нет результатов
限流|Request limited|Запросы ограничены
抓取失败|Retrieval failed|Не удалось получить данные
已停用|Disabled|Отключено
{count} 条因字段不足待确认。|{count} items awaiting confirmation due to missing fields.|Материалов на проверке из-за отсутствующих полей: {count}.
请求回溯 · {count} 天|Requested lookback · {count} days|Глубина запроса · {count} дн.
实际查询|Executed query|Выполненный запрос
结构化聚焦提示词|Structured Focus Prompt|Структурированный промпт по теме
API 账单与地图设置|API billing and map settings|Расходы API и настройки карты
AI 地理定位|AI geography|Геолокация ИИ
新闻、政策与试验检索规则|News, policy and trial rules|Правила поиска новостей, политики и испытаний
各类型独立匹配，可以使用同一组编号集合。留空时使用来源默认检索。|Each type can reuse the numbered sets. Leave blank to use the source defaults.|Каждый тип может использовать общие наборы. Пустое правило использует настройки источника.
新闻检索式|News query|Запрос новостей
政策检索式|Policy query|Запрос политики
试验检索式|Trial query|Запрос испытаний
来源专用查询（可选）|Optional source query|Запрос к источнику (необязательно)
订阅源内容类型|Feed content type|Тип содержимого ленты
自动识别|Detect automatically|Определить автоматически
未满足本类型的检索规则。|Did not match this content type’s rule.|Не соответствует правилу для этого типа.
{count} 条已排除|{count} excluded|Исключено {count}
历史条目检索|Research archive|Поиск по архиву
检索历史条目|Search archived records|Поиск архивных записей
标题、摘要或文献编号|Title, abstract or identifier|Заголовок, аннотация или идентификатор
条目类型|Record type|Тип записи
全部类型|All types|Все типы
检索后端|Search backend|Система поиска
本机索引|Local index|Локальный индекс
导入已有任务日报|Index existing task reports|Индексировать готовые отчёты
已索引 {count} 份任务日报|Indexed {count} task reports|Индексировано отчётов: {count}
显示 {count} 条结果|Showing {count} results|Показано результатов: {count}
历史检索失败。|Could not search the archive.|Ошибка поиска в архиве.
历史导入失败。|Could not index the reports.|Ошибка индексации отчётов.
相关来源|Related source|Связанный источник
原文引用编号|Identifier cited by the source|Идентификатор из источника
涉及论文|Affected paper|Затронутая публикация
待确认关联|Unconfirmed connection|Неподтверждённая связь
首次登记|First registered|Первая регистрация
登记更新|Registry update|Обновление реестра
结果发布|Results posted|Результаты опубликованы
状态变更|Status changed|Статус изменился
提示|Warnings|Предупреждения
由神通寰宇自动生成|Generated automatically by NeuroDaily|Сформировано автоматически в NeuroDaily
展开|Expand|Развернуть
折叠|Collapse|Свернуть
🕸 图谱|🕸 Citation graph|🕸 Граф цитирования
本地引用网络|Local citation network|Локальная сеть цитирований
服务未启动：请双击 scripts/启动 NeuroDaily.command，或运行 scripts/start.sh|NeuroDaily is stopped. Open scripts/启动 NeuroDaily.command or run scripts/start.sh.|Служба NeuroDaily остановлена. Откройте scripts/启动 NeuroDaily.command или запустите scripts/start.sh.
"""


_TRANSLATOR = r"""
(() => {
  const messages = CATALOG;
  const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
  const t = (source, values = {}) => String(own(messages, source) ? messages[source] : source)
    .replace(/\{([a-zA-Z_][\w]*)\}/g, (original, key) => own(values, key) ? String(values[key]) : original);
  window.ndT = t;

  const ignored = 'script,style,code,pre,textarea,[data-no-i18n],#bibliometrics table,#on-this-day,#ai-summary .card-body';
  const attributes = ['title', 'placeholder', 'aria-label'];
  function localizeText(node) {
    if (!node.parentElement || node.parentElement.closest(ignored)) return;
    const source = node.data.trim().replace(/\s+/g, ' ');
    const translated = t(source);
    if (source !== translated) node.data = node.data.replace(/^(\s*)[\s\S]*?(\s*)$/, '$1' + translated + '$2');
  }
  function localizeElement(node) {
    if (node.closest(ignored)) return;
    if (node.dataset.i18nCount !== undefined) {
      const translated = t(node.dataset.i18n, {count: node.dataset.i18nCount});
      if (node.textContent !== translated) node.textContent = translated;
    }
    for (const attribute of attributes) {
      if (!node.hasAttribute(attribute)) continue;
      const source = node.getAttribute(attribute);
      const translated = t(source);
      if (source !== translated) node.setAttribute(attribute, translated);
    }
  }
  function localize(node) {
    if (node.nodeType === Node.TEXT_NODE) { localizeText(node); return; }
    if (node.nodeType !== Node.ELEMENT_NODE || node.closest(ignored)) return;
    localizeElement(node);
    const walker = document.createTreeWalker(node, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
      acceptNode(child) {
        return child.nodeType === Node.ELEMENT_NODE && child.matches(ignored)
          ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
      }
    });
    while (walker.nextNode()) {
      const child = walker.currentNode;
      if (child.nodeType === Node.TEXT_NODE) localizeText(child);
      else localizeElement(child);
    }
  }
  document.addEventListener('DOMContentLoaded', () => {
    localize(document.documentElement);
    new MutationObserver(records => {
      for (const record of records) {
        if (record.type === 'characterData') localizeText(record.target);
        else for (const node of record.addedNodes) localize(node);
      }
    }).observe(document.body, {childList: true, characterData: true, subtree: true});
  }, {once: true});
})();
"""


@lru_cache(maxsize=len(UI_LANGUAGES))
def _translation_script(language: str) -> str:
    index = UI_LANGUAGES.index(language)
    messages = {}
    choices_by_message = [line.split("|") for line in _MESSAGES.strip().splitlines()]
    choices_by_message.extend(tuple(_BIBLIOMETRICS_LABELS[lang][key] for lang in UI_LANGUAGES)
                              for key in _BIBLIOMETRICS_LABELS["zh"])
    for choices in choices_by_message:
        for source in choices:
            if source != choices[index]:
                messages[source] = choices[index]
    payload = json.dumps(messages, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return '<script id="nd-localizer">' + _TRANSLATOR.replace("CATALOG", payload, 1) + "</script>"


def localize_document(html: str, language: str) -> str:
    """Apply a locale to one complete HTML document without rewriting its data."""
    if language not in UI_LANGUAGES:
        language = "zh"
    if not re.search(r"<html\b", html, flags=re.IGNORECASE) or not re.search(r"<head\b[^>]*>", html, flags=re.IGNORECASE):
        return html
    html = re.sub(r'<script id="nd-localizer">[\s\S]*?</script>', "", html, count=1)

    def set_language(match):
        tag = match[0]
        localized, count = re.subn(r'(?<=\s)lang\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)',
                                   f'lang="{language}"', tag, count=1, flags=re.IGNORECASE)
        return localized if count else tag[:-1] + f' lang="{language}">'

    html = re.sub(r"<html\b[^>]*>", set_language, html, count=1, flags=re.IGNORECASE)
    return re.sub(r"<head\b[^>]*>", lambda match: match[0] + _translation_script(language),
                  html, count=1, flags=re.IGNORECASE)
