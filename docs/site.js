(function () {
  "use strict";

  var T = {
    zh: {
      meta_title: "神通寰宇 NeuroDaily · 科研文献日报",
      meta_description: "神通寰宇 NeuroDaily 聚合论文、预印本、临床试验及行业动态，按研究方向定时生成可追溯的 HTML 日报。",
      skip: "跳到正文",
      nav_features: "功能",
      nav_demo: "演示",
      nav_install: "安装",
      hero_title: "神通寰宇",
      hero_line: "用一份可追溯的日报，<br>跟进领域内每天的进展。",
      hero_description: "按研究方向追踪论文、预印本、临床试验、监管与产业动态，生成带原始出处的 HTML 日报。",
      hero_install: "选择安装方式",
      hero_demo: "查看日报演示",
      features_title: "从检索到日报",
      feature1_title: "检索规则可配置",
      feature1_body: "从神经科学、肿瘤学或重症医学预设出发，按期刊、字段、关键词与布尔逻辑定义检索范围。",
      feature2_title: "结果可以追溯",
      feature2_body: "汇总期刊 RSS、PubMed、预印本和临床监管来源，查看检索状态、本地历史及每条结果的原始链接。",
      feature3_title: "定时检索与分享",
      feature3_body: "定时生成日报，按需通过邮件、飞书或企业微信推送。文献数据可导出为 JSON 或 BibTeX。",
      demo_title: "日报演示",
      demo_desc: "按版块浏览检索结果，从论文条目回到期刊或数据库。",
      demo_caption: "本地离线演示 · 神经科学预设",
      install_title: "安装与运行",
      win_title: "Windows / Linux",
      win_body: "Windows 可用 EXE 或 MSI 安装。Linux 可用 AppImage 或 DEB。",
      win_latest: "查看最新正式版",
      win_req: "系统要求",
      mac_title: "macOS",
      mac_body: "使用 Homebrew 安装，再用 <code>neurodaily web</code> 打开本机工作区。",
      mac_guide: "Homebrew 安装指南",
      docker_title: "Docker / 命令行",
      docker_body: "面向本机、服务器和定时任务，支持用 CLI 生成离线演示或真实日报。",
      docker_guide: "Docker 部署手册",
      docker_tags: "Docker Hub 镜像标签",
      docker_cli: "命令行用法",
      ref_title: "项目文档",
      ref_arch: "架构与数据流",
      ref_config: "配置参考",
      ref_actions: "GitHub Actions 手册",
      ref_en: "English documentation",
      ref_ru: "Документация на русском",
      footer_feedback: "反馈问题"
    },
    en: {
      meta_title: "NeuroDaily · Traceable research digest",
      meta_description: "NeuroDaily aggregates papers, preprints, trials and industry news by research focus, and renders a traceable HTML digest on a schedule.",
      skip: "Skip to content",
      nav_features: "Features",
      nav_demo: "Demo",
      nav_install: "Install",
      hero_title: "NeuroDaily",
      hero_line: "A traceable daily digest,<br>tracking what moves your field.",
      hero_description: "Track papers, preprints, trials, regulatory and industry news by research focus — rendered as an HTML digest with original sources.",
      hero_install: "Choose install method",
      hero_demo: "View demo digest",
      features_title: "From search to digest",
      feature1_title: "Configurable rules",
      feature1_body: "Start from neuroscience, oncology or critical-care presets; define scope by journals, fields, keywords and Boolean logic.",
      feature2_title: "Traceable results",
      feature2_body: "Aggregates journal RSS, PubMed, preprints and regulatory sources; inspect source health, local history and original links.",
      feature3_title: "Scheduled search and sharing",
      feature3_body: "Generate on schedule and share by email, Feishu or WeCom. Export literature as JSON or BibTeX.",
      demo_title: "Digest demo",
      demo_desc: "Browse by section and follow each paper back to its journal or database.",
      demo_caption: "Offline local demo · Neuroscience preset",
      install_title: "Install and run",
      win_title: "Windows / Linux",
      win_body: "Windows: EXE or MSI. Linux: AppImage or DEB.",
      win_latest: "Latest stable release",
      win_req: "System requirements",
      mac_title: "macOS",
      mac_body: "Install with Homebrew, then open the local workspace with <code>neurodaily web</code>.",
      mac_guide: "Homebrew guide",
      docker_title: "Docker / CLI",
      docker_body: "For laptops, servers and scheduled jobs; generate demo or real digests via CLI.",
      docker_guide: "Docker guide",
      docker_tags: "Docker Hub tags",
      docker_cli: "CLI usage",
      ref_title: "Documentation",
      ref_arch: "Architecture and data flow",
      ref_config: "Configuration reference",
      ref_actions: "GitHub Actions guide",
      ref_en: "English documentation",
      ref_ru: "Документация на русском",
      footer_feedback: "Report an issue"
    },
    ru: {
      meta_title: "NeuroDaily · Ежедневный научный дайджест",
      meta_description: "NeuroDaily собирает статьи, препринты, клинические испытания и отраслевые новости по вашему направлению и формирует прослеживаемый HTML-дайджест по расписанию.",
      skip: "Перейти к содержимому",
      nav_features: "Возможности",
      nav_demo: "Демо",
      nav_install: "Установка",
      hero_title: "NeuroDaily",
      hero_line: "Прослеживаемый ежедневный дайджест,<br>который держит вас в курсе.",
      hero_description: "Отслеживайте статьи, препринты, испытания, регуляторные и отраслевые новости по вашему направлению — в HTML-дайджесте со ссылками на источники.",
      hero_install: "Выбрать способ установки",
      hero_demo: "Посмотреть демо",
      features_title: "От поиска к дайджесту",
      feature1_title: "Настраиваемые правила",
      feature1_body: "Начните с пресетов по нейронаукам, онкологии или интенсивной терапии; задайте журналы, поля, ключевые слова и булеву логику.",
      feature2_title: "Прослеживаемые результаты",
      feature2_body: "RSS журналов, PubMed, препринты и регуляторные источники; статус источников, локальная история и ссылки на оригиналы.",
      feature3_title: "Расписание и публикация",
      feature3_body: "Формируйте дайджест по расписанию и отправляйте по почте, в Feishu или WeCom. Экспорт в JSON или BibTeX.",
      demo_title: "Демо дайджеста",
      demo_desc: "Просматривайте по разделам и переходите от статьи к журналу или базе данных.",
      demo_caption: "Локальное офлайн-демо · пресет Neuroscience",
      install_title: "Установка и запуск",
      win_title: "Windows / Linux",
      win_body: "Windows: EXE или MSI. Linux: AppImage или DEB.",
      win_latest: "Последняя стабильная версия",
      win_req: "Системные требования",
      mac_title: "macOS",
      mac_body: "Установите через Homebrew и откройте локальное рабочее пространство командой <code>neurodaily web</code>.",
      mac_guide: "Руководство Homebrew",
      docker_title: "Docker / CLI",
      docker_body: "Для ноутбуков, серверов и задач по расписанию; демо или реальный дайджест через CLI.",
      docker_guide: "Руководство Docker",
      docker_tags: "Теги Docker Hub",
      docker_cli: "Использование CLI",
      ref_title: "Документация",
      ref_arch: "Архитектура и поток данных",
      ref_config: "Справочник конфигурации",
      ref_actions: "Руководство GitHub Actions",
      ref_en: "English documentation",
      ref_ru: "Документация на русском",
      footer_feedback: "Сообщить о проблеме"
    }
  };

  function apply(lang, persist) {
    var dict = T[lang] || T.zh;
    document.documentElement.lang = lang === "zh" ? "zh-CN" : lang;
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      var key = el.getAttribute("data-i18n");
      if (dict[key] != null) el.innerHTML = dict[key];
    });
    var title = document.getElementById("meta-title");
    if (title) title.textContent = dict.meta_title;
    document.title = dict.meta_title;
    var desc = document.getElementById("meta-description");
    if (desc) desc.setAttribute("content", dict.meta_description);
    document.querySelectorAll("[data-lang]").forEach(function (btn) {
      btn.setAttribute("aria-pressed", btn.getAttribute("data-lang") === lang ? "true" : "false");
    });
    if (persist) {
      try { localStorage.setItem("neurodaily-site-lang", lang); } catch (e) {}
    }
  }

  document.querySelectorAll("[data-lang]").forEach(function (btn) {
    btn.addEventListener("click", function () { apply(btn.getAttribute("data-lang"), true); });
  });

  var saved = null;
  try { saved = localStorage.getItem("neurodaily-site-lang"); } catch (e) {}
  if (saved && T[saved]) {
    apply(saved, false);
  } else {
    apply("zh", false);
  }
})();
