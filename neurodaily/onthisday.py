"""NeuroDaily — "On This Day" in neuroscience, neurology, psychiatry & neurosurgery.

Focus: **landmark events**, not birthdays/deaths.
- 学术发现 (discovery)
- 关键手术 (surgery)
- 药物获批 / 首次临床应用 (drug)
- 器械 / 技术里程碑 (device)

Two layers so **every day of the year** pushes something:
1. ``EVENTS`` — day-accurate events (mostly FDA approvals, dated surgeries and
   discoveries). Only dates we can defend are included.
2. ``EVERGREEN`` — date-independent classic milestones (year-level), rotated by
   date as an honest fallback.

Each item carries ``match`` = exact | near | evergreen, surfaced to the user so
we never claim an event happened "today" when it did not.
"""
from __future__ import annotations

from datetime import date as _date

CATEGORY_LABELS = {
    "neurosurgery": "神经外科",
    "neurology": "神经病学",
    "psychiatry": "精神病学",
    "neuroscience": "神经科学",
}

KIND_LABELS = {
    "drug": "药物获批",
    "surgery": "关键手术",
    "discovery": "学术发现",
    "device": "器械/技术",
}

# ---------------------------------------------------------------------------
# Layer 1 — day-accurate EVENTS.  key = (month, day)
# ---------------------------------------------------------------------------
EVENTS: dict[tuple[int, int], list[dict]] = {
    # ---------------- January ----------------
    (1, 6): [dict(year=2023, category="neurology", kind="drug", title="Lecanemab（Leqembi）获加速批准",
                  text="FDA 加速批准抗淀粉样蛋白抗体 lecanemab 用于早期阿尔茨海默病，"
                       "是首批进入临床的抗 Aβ 疾病修饰疗法之一（2023-07-06 转为常规批准）。")],
    (1, 7): [dict(year=2022, category="psychiatry", kind="drug", title="Daridorexant（Quviviq）获批",
                  text="FDA 批准双重食欲素受体拮抗剂 daridorexant 治疗失眠，代表失眠药物"
                       "从“镇静”转向“调节觉醒”的新机制。")],

    # ---------------- February ----------------
    (2, 23): [dict(year=2007, category="psychiatry", kind="drug", title="Lisdexamfetamine（Vyvanse）获批",
                   text="FDA 批准 lisdexamfetamine 治疗注意缺陷多动障碍（ADHD），"
                        "为前药型兴奋剂；2015 年又获批治疗暴食症。")],
    (2, 27): [dict(year=2020, category="neurology", kind="drug", title="Rimegepant（Nurtec）获批",
                   text="FDA 批准口服 CGRP 受体拮抗剂 rimegepant 治疗偏头痛，"
                        "推动偏头痛进入“曲普坦之后”的 CGRP 时代。")],

    # ---------------- March ----------------
    (3, 5): [dict(year=2019, category="psychiatry", kind="drug", title="Esketamine（Spravato）获批",
                  text="FDA 批准氯胺酮衍生物 esketamine 鼻喷剂用于难治性抑郁症，"
                       "是数十年来首个新机制抗抑郁药，重启谷氨酸能抗抑郁方向。")],
    (3, 19): [dict(year=2019, category="psychiatry", kind="drug", title="Brexanolone（Zulresso）获批",
                   text="FDA 批准 brexanolone 静脉制剂治疗产后抑郁，是首个专门针对产后抑郁的药物，"
                        "机制涉及神经甾体/GABA-A 受体调节。")],
    (3, 28): [dict(year=2017, category="neurology", kind="drug", title="Ocrelizumab（Ocrevus）获批",
                   text="FDA 批准 ocrelizumab 治疗多发性硬化，是首个获批用于原发进展型 MS 的"
                        "抗 CD20 单抗，改变 MS 治疗格局。")],

    # ---------------- April ----------------
    (4, 11): [dict(year=2017, category="psychiatry", kind="drug", title="Valbenazine（Ingrezza）获批",
                   text="FDA 批准 valbenazine 治疗迟发性运动障碍（TD），是首个获批的"
                        "囊泡单胺转运体 2（VMAT2）抑制剂。")],
    (4, 18): [dict(year=1861, category="neurology", kind="discovery", title="Broca 报告“Tan”病例",
                   text="Paul Broca 在巴黎报告失语症患者“Tan”（Leborgne），确立左侧额叶"
                        "（Broca 区）与言语产生的关系——脑功能定位的开端。")],
    (4, 25): [dict(year=2023, category="neurology", kind="drug", title="Tofersen（Qalsody）获批",
                   text="FDA 加速批准反义寡核苷酸 tofersen 治疗 SOD1 突变型肌萎缩侧索硬化（ALS），"
                        "是首个针对 ALS 遗传病因的靶向药物。")],
    (4, 29): [dict(year=2016, category="psychiatry", kind="drug", title="Pimavanserin（Nuplazid）获批",
                   text="FDA 批准 pimavanserin 治疗帕金森病精神病，是首个选择性 5-HT2A 反向激动剂，"
                        "避免加重运动症状。")],

    # ---------------- May ----------------
    (5, 5): [dict(year=2017, category="neurology", kind="drug", title="Edaravone（Radicava）获批",
                  text="FDA 批准依达拉奉（edaravone）治疗 ALS，作为抗氧化应激药物为 ALS 提供"
                       "新的治疗选项。")],
    (5, 10): [dict(year=2006, category="psychiatry", kind="drug", title="Varenicline（Chantix）获批",
                   text="FDA 批准伐尼克兰用于戒烟，作为部分烟碱型乙酰胆碱受体激动剂，"
                        "成为戒烟药物治疗的重要里程碑。")],
    (5, 17): [dict(year=2018, category="neurology", kind="drug", title="Erenumab（Aimovig）获批",
                   text="FDA 批准 erenumab 用于偏头痛预防，是首个获批的 CGRP 受体单抗，"
                        "开创偏头痛预防性生物制剂时代。")],
    (5, 24): [dict(year=2019, category="neurology", kind="drug", title="Onasemnogene（Zolgensma）获批",
                   text="FDA 批准 onasemnogene abeparvovec 治疗脊髓性肌萎缩（SMA），"
                        "是首个获批的体内基因替代疗法之一。")],

    # ---------------- June ----------------
    (6, 7): [dict(year=2021, category="neurology", kind="drug", title="Aducanumab（Aduhelm）获加速批准",
                  text="FDA 加速批准 aducanumab 用于阿尔茨海默病，是近 20 年来首个获批的"
                       "抗淀粉样蛋白新药，也引发关于替代终点与疗效的巨大争议。")],
    (6, 18): [dict(year=1996, category="neurology", kind="drug", title="tPA 获批用于急性缺血性卒中",
                   text="FDA 批准阿替普酶（tPA）用于急性缺血性卒中，基于 NINDS 试验，"
                        "确立“时间就是大脑”的静脉溶栓范式。")],
    (6, 25): [dict(year=2018, category="neurology", kind="drug", title="Cannabidiol（Epidiolex）获批",
                   text="FDA 批准大麻二酚（CBD）口服液治疗 Lennox–Gastaut 与 Dravet 综合征，"
                        "是首个获批的大麻来源药物。"),
              dict(year=2020, category="neurology", kind="drug", title="Fenfluramine（Fintepla）获批",
                   text="FDA 批准芬氟拉明口服液治疗 Dravet 综合征相关发作，"
                        "为难治性发育性癫痫脑病提供新选择。")],

    # ---------------- July ----------------
    (7, 2): [dict(year=2024, category="neurology", kind="drug", title="Donanemab（Kisunla）获批",
                  text="FDA 批准 donanemab 治疗早期阿尔茨海默病，继 lecanemab 之后又一"
                       "抗淀粉样蛋白单抗进入临床。")],
    (7, 3): [dict(year=1977, category="neurology", kind="device", title="首例人体 MRI 扫描",
                  text="Raymond Damadian 团队完成首例人体全身磁共振成像扫描（“Indomitable”），"
                       "为 MRI 进入临床铺路（2003 年诺贝尔生理学或医学奖）。")],
    (7, 6): [dict(year=2023, category="neurology", kind="drug", title="Lecanemab 转为常规批准",
                  text="FDA 将 lecanemab 由加速批准转为常规批准，确认其在早期阿尔茨海默病中的"
                       "临床获益，是抗 Aβ 疗法监管路径的重要节点。")],
    (7, 10): [dict(year=2015, category="psychiatry", kind="drug", title="Brexpiprazole（Rexulti）获批",
                   text="FDA 批准 brexpiprazole 治疗精神分裂症与重性抑郁辅助治疗，"
                        "为非典型抗精神病药家族再添一员。")],
    (7, 23): [dict(year=1993, category="neurology", kind="drug", title="Interferon beta-1b（Betaseron）获批",
                   text="FDA 批准干扰素 β-1b 用于复发缓解型多发性硬化，是首个获批的 MS"
                        "疾病修饰治疗（DMT）。")],

    # ---------------- August ----------------
    (8, 4): [dict(year=2023, category="psychiatry", kind="drug", title="Zuranolone（Zurzuvae）获批",
                  text="FDA 批准口服 neuroactive steroid zuranolone 治疗产后抑郁，"
                       "把产后抑郁治疗从静脉扩展到口服短疗程。")],
    (8, 13): [dict(year=2014, category="psychiatry", kind="drug", title="Suvorexant（Belsomra）获批",
                   text="FDA 批准食欲素受体拮抗剂 suvorexant 治疗失眠，"
                        "是首个获批的食欲素（orexin）受体拮抗剂类安眠药。")],
    (8, 15): [dict(year=2008, category="neurology", kind="drug", title="Tetrabenazine（Xenazine）获批",
                   text="FDA 批准 tetrabenazine 治疗亨廷顿病舞蹈症，是首个获批用于该症状的药物。")],
    (8, 19): [dict(year=2022, category="psychiatry", kind="drug", title="Dextromethorphan/bupropion（Auvelity）获批",
                   text="FDA 批准右美沙芬/安非他酮复方治疗重性抑郁，是首个含 NMDA 受体拮抗机制的"
                        "口服快速起效抗抑郁药。")],
    (8, 20): [dict(year=2018, category="neurology", kind="drug", title="Stiripentol（Diacomit）获批",
                   text="FDA 批准 stiripentol 用于 Dravet 综合征相关发作的辅助治疗。")],

    # ---------------- September ----------------
    (9, 14): [dict(year=2018, category="neurology", kind="drug", title="Fremanezumab（Ajovy）获批",
                   text="FDA 批准 fremanezumab 用于偏头痛预防，CGRP 单抗阵营进一步扩大。")],
    (9, 17): [dict(year=2015, category="psychiatry", kind="drug", title="Cariprazine（Vraylar）获批",
                   text="FDA 批准 cariprazine 治疗精神分裂症与双相躁狂，其对 D3 受体的高亲和力"
                        "带来不同的药理特征。")],
    (9, 21): [dict(year=2010, category="neurology", kind="drug", title="Fingolimod（Gilenya）获批",
                   text="FDA 批准芬戈莫德治疗复发型多发性硬化，是首个口服 MS 疾病修饰治疗药物。")],
    (9, 26): [dict(year=2024, category="psychiatry", kind="drug", title="Xanomeline/trospium（Cobenfy）获批",
                   text="FDA 批准 xanomeline/trospium 治疗精神分裂症，是首个不依赖多巴胺 D2 受体"
                        "阻断的抗精神病药（毒蕈碱 M1/M4 激动），被视为精神药理学的范式转变。")],
    (9, 27): [dict(year=2018, category="neurology", kind="drug", title="Galcanezumab（Emgality）获批",
                   text="FDA 批准 galcanezumab 用于偏头痛预防；2018 年 CGRP 单抗密集获批，"
                        "标志偏头痛治疗进入生物制剂时代。")],
    (9, 28): [dict(year=2021, category="neurology", kind="drug", title="Atogepant（Qulipta）获批",
                   text="FDA 批准口服 CGRP 受体拮抗剂 atogepant 用于偏头痛预防，"
                        "把小分子 CGRP 靶点从急性治疗扩展到预防。")],

    # ---------------- October ----------------
    (10, 1): [dict(year=1971, category="neurosurgery", kind="device", title="首例活体头颅 CT 扫描",
                   text="Hounsfield 与 Ambrose 在伦敦完成首例活体患者头颅 CT 扫描，"
                        "清晰显示额叶肿瘤并随即手术——神经影像与神经外科的转折点"
                        "（1979 年诺贝尔生理学或医学奖）。")],
    (10, 16): [dict(year=2003, category="neurology", kind="drug", title="Memantine（Namenda）获批",
                    text="FDA 批准美金刚治疗中重度阿尔茨海默病，作为 NMDA 受体拮抗剂"
                         "与胆碱酯酶抑制剂形成互补。")],
    (10, 22): [dict(year=2012, category="neurology", kind="drug", title="Perampanel（Fycompa）获批",
                    text="FDA 批准 perampanel 治疗癫痫部分性发作，是首个获批的 AMPA 受体拮抗剂类抗癫痫药。")],
    (10, 28): [dict(year=2008, category="neurology", kind="drug", title="Lacosamide（Vimpat）获批",
                    text="FDA 批准拉考沙胺（lacosamide）治疗癫痫部分性发作，"
                         "其作用于钠通道慢失活状态的机制独具特点。")],

    # ---------------- November ----------------
    (11, 8): [dict(year=1895, category="neurology", kind="discovery", title="Röntgen 发现 X 射线",
                   text="Wilhelm Röntgen 发现 X 射线，开启医学影像时代，也为头颅 X 线、"
                        "CT 与神经影像学奠定基础（1901 年首届诺贝尔物理学奖）。")],
    (11, 21): [dict(year=2019, category="neurology", kind="drug", title="Cenobamate（Xcopri）获批",
                    text="FDA 批准 cenobamate 治疗成人局灶性癫痫发作，为药物难治性癫痫"
                         "增加一种高疗效选项。")],
    (11, 23): [dict(year=2004, category="neurology", kind="drug", title="Natalizumab（Tysabri）获批",
                    text="FDA 批准那他珠单抗治疗复发型多发性硬化，作为抗 α4-整合素单抗"
                         "显著降低复发率，也因 PML 风险被严格监测。")],
    (11, 25): [dict(year=1884, category="neurosurgery", kind="surgery", title="Godlee 首例脑肿瘤切除术",
                    text="Rickman Godlee 在 Bennett 的定位下完成首例脑肿瘤切除术，"
                         "确立“定位—开颅—切除”的现代神经外科范式。"),
               dict(year=1996, category="neurology", kind="drug", title="Donepezil（Aricept）获批",
                    text="FDA 批准多奈哌齐治疗阿尔茨海默病，成为最广泛使用的胆碱酯酶抑制剂之一。")],
    (11, 26): [dict(year=2002, category="psychiatry", kind="drug", title="Atomoxetine（Strattera）获批",
                    text="FDA 批准托莫西汀治疗 ADHD，是首个非兴奋剂类 ADHD 药物（选择性去甲肾上腺素再摄取抑制剂）。")],
    (11, 30): [dict(year=1999, category="neurology", kind="drug", title="Levetiracetam（Keppra）获批",
                    text="FDA 批准左乙拉西坦治疗癫痫，其与 SV2A 结合的全新机制"
                         "使其成为最常用的广谱抗癫痫药之一。")],

    # ---------------- December ----------------
    (12, 12): [dict(year=1995, category="neurology", kind="drug", title="Riluzole（Rilutek）获批",
                    text="FDA 批准利鲁唑治疗肌萎缩侧索硬化（ALS），是首个获批的 ALS 药物。")],
    (12, 20): [dict(year=2019, category="psychiatry", kind="drug", title="Lumateperone（Caplyta）获批",
                    text="FDA 批准 lumateperone 治疗精神分裂症；同一天 lemoborexant（Dayvigo）"
                         "亦获批用于失眠，是精神科药物密集落地的一天。"),
               dict(year=2019, category="psychiatry", kind="drug", title="Lemborexant（Dayvigo）获批",
                    text="FDA 批准食欲素受体拮抗剂 lemborexant 治疗失眠。")],
    (12, 23): [dict(year=2016, category="neurology", kind="drug", title="Nusinersen（Spinraza）获批",
                    text="FDA 批准反义寡核苷酸 nusinersen 治疗脊髓性肌萎缩（SMA），"
                         "是首个获批的 SMA 药物，推动 SMA 进入疾病修饰治疗时代。"),
               dict(year=2019, category="neurology", kind="drug", title="Ubrogepant（Ubrelvy）获批",
                    text="FDA 批准口服 CGRP 受体拮抗剂 ubrogepant 用于偏头痛急性治疗，"
                         "为曲普坦禁忌者提供新选择。")],
    (12, 24): [dict(year=1998, category="psychiatry", kind="drug", title="Modafinil（Provigil）获批",
                    text="FDA 批准莫达非尼治疗发作性睡病相关日间过度嗜睡，"
                         "推动对觉醒调控环路的理解与促觉醒药物研发。")],
    (12, 29): [dict(year=1987, category="psychiatry", kind="drug", title="Fluoxetine（Prozac）获批",
                    text="FDA 批准氟西汀（百忧解）治疗抑郁症，成为首个广泛使用的 SSRI，"
                         "深刻改变抑郁症的门诊治疗与公众认知。")],
}


# ---------------------------------------------------------------------------
# Layer 2 — date-independent classic milestones (events only, no births/deaths).
# ---------------------------------------------------------------------------
EVERGREEN: list[dict] = [
    dict(year=1700, category="neurosurgery", kind="discovery", title="埃德温·史密斯纸草书",
         text="约公元前 1700 年的埃德温·史密斯纸草书，是最早记载脑、脑膜与脊髓损伤的外科文献，"
              "被视为神经外科与神经病学的共同源头。"),
    dict(year=1861, category="neurology", kind="discovery", title="Broca 区与言语定位",
         text="Paul Broca 通过失语症患者“Tan”确立左额叶与言语产生的关系，开启脑功能定位时代。"),
    dict(year=1879, category="neurosurgery", kind="surgery", title="首例成功的脑肿瘤切除",
         text="William Macewen 在格拉斯哥完成首例成功的脑肿瘤切除，标志现代神经外科的开端。"),
    dict(year=1887, category="neurosurgery", kind="surgery", title="首例脊髓肿瘤切除",
         text="Victor Horsley 完成首例脊髓肿瘤切除，并开展实验性癫痫外科。"),
    dict(year=1906, category="neuroscience", kind="discovery", title="神经元学说获诺奖",
         text="Golgi 与 Cajal 因神经系统结构研究共享 1906 年诺贝尔生理学或医学奖，神经元学说自此确立。"),
    dict(year=1906, category="neurology", kind="discovery", title="阿尔茨海默病首次报告",
         text="Alois Alzheimer 报告首例早老性痴呆病例，后来该病以其姓氏命名。"),
    dict(year=1908, category="neurosurgery", kind="device", title="立体定向仪诞生",
         text="Horsley 与 Clarke 设计出立体定向仪，成为现代功能神经外科与 DBS 的技术基石。"),
    dict(year=1908, category="psychiatry", kind="discovery", title="“精神分裂症”命名",
         text="Eugen Bleuler 提出“精神分裂症”一词，取代“早发性痴呆”，重塑精神病学分类。"),
    dict(year=1909, category="neurosurgery", kind="discovery", title="Cushing 电刺激人感觉皮层",
         text="Harvey Cushing 首次电刺激人类感觉皮层，推动术中功能定位。"),
    dict(year=1909, category="neuroscience", kind="discovery", title="Brodmann 52 区",
         text="Korbinian Brodmann 将大脑皮质划分为 52 个细胞构筑区，至今仍是神经解剖通用语言。"),
    dict(year=1924, category="neurology", kind="device", title="人类脑电图（EEG）",
         text="Hans Berger 首次记录人类脑电，1929 年发表，开创临床神经电生理。"),
    dict(year=1935, category="psychiatry", kind="surgery", title="额叶切断术（lobotomy）",
         text="Egas Moniz 首创额叶白质切断术，1949 年获诺贝尔奖；该术式后来被严格限制，"
              "成为精神外科最具警示意义的案例。"),
    dict(year=1938, category="psychiatry", kind="device", title="电休克治疗（ECT）",
         text="Cerletti 与 Bini 引入电休克治疗，至今仍是难治性抑郁症的有效物理治疗之一。"),
    dict(year=1944, category="psychiatry", kind="discovery", title="自闭症的最早描述",
         text="Leo Kanner 描述“早期婴儿自闭症”，奠定现代孤独症谱系研究。"),
    dict(year=1949, category="psychiatry", kind="drug", title="锂盐治疗双相障碍",
         text="John Cade 发现锂盐的情绪稳定作用，开启现代精神药理学。"),
    dict(year=1952, category="psychiatry", kind="drug", title="首个抗精神病药",
         text="Delay 与 Deniker 引入氯丙嗪，精神科治疗从“收容”转向“药物”，引发去机构化浪潮。"),
    dict(year=1953, category="neuroscience", kind="discovery", title="H.M. 与海马记忆研究",
         text="患者 H.M. 接受双侧内侧颞叶切除后出现严重顺行性遗忘，确立了海马在记忆巩固中的核心作用。"),
    dict(year=1957, category="neuroscience", kind="discovery", title="多巴胺被确认为神经递质",
         text="Arvid Carlsson 等证明多巴胺是中枢神经递质，为帕金森病左旋多巴治疗与"
              "抗精神病药机制奠定基础。"),
    dict(year=1971, category="neurosurgery", kind="device", title="首例头颅 CT",
         text="Hounsfield 与 Ambrose 完成首例活体头颅 CT，神经影像与神经外科进入断层成像时代（1979 年诺贝尔奖）。"),
    dict(year=1973, category="neurology", kind="device", title="MRI 的原理",
         text="Paul Lauterbur（与 Peter Mansfield）提出用磁场梯度对 NMR 信号空间编码，"
              "奠定磁共振成像（MRI）基础（2003 年诺贝尔奖）。"),
    dict(year=1980, category="psychiatry", kind="discovery", title="DSM-III 出版",
         text="DSM-III 引入可操作诊断标准，成为现代精神科诊断标准化的分水岭。"),
    dict(year=1985, category="neuroscience", kind="device", title="经颅磁刺激（TMS）",
         text="Anthony Barker 等演示经颅磁刺激，开启无创脑调控时代。"),
    dict(year=1987, category="neurosurgery", kind="device", title="脑深部电刺激（DBS）",
         text="Alim Benabid 发现高频深部电刺激可抑制帕金森震颤，DBS 由此诞生并成为功能神经外科主力。"),
    dict(year=1990, category="neuroscience", kind="device", title="功能磁共振（fMRI）兴起",
         text="1990 年代基于血氧水平依赖（BOLD）的 fMRI 普及，使活体人脑功能成像成为常规。"),
    dict(year=1995, category="neurology", kind="drug", title="卒中静脉溶栓",
         text="NINDS 试验确立 tPA 静脉溶栓治疗急性缺血性卒中，改写卒中急救。"),
    dict(year=2015, category="neurology", kind="discovery", title="机械取栓改写卒中治疗",
         text="MR CLEAN 等多项试验证实大血管闭塞机械取栓有效，成为缺血性卒中治疗新标准。"),
]


# ---------------------------------------------------------------------------
# Long-form bodies keyed by (year, title); used instead of the short `text`.
# ---------------------------------------------------------------------------
BODIES: dict[tuple[int, str], str] = {
    (1861, "Broca 报告“Tan”病例"): (
        "1861 年 4 月，法国外科医生与人类学家保罗·布洛卡（Paul Broca）在巴黎人类学学会报告了一位特殊病人。"
        "这名被称作“Tan”的男子（本名 Louis Victor Leborgne）因长期癫痫与进行性言语丧失而住院，"
        "他能听懂他人说话、智力与理解力相对保留，却几乎只能发出一个音节——“tan”。"
        "病人去世后，布洛卡进行尸检，在其左侧额叶后下部发现一处明确的病灶。\n\n"
        "这个发现的意义远超一例个案。当时主流观点仍倾向于大脑功能整体统一、难以定位，而布洛卡的证据表明："
        "语言产生这一高级功能，可以对应到大脑一个相对局限的区域。他随后又积累多例相似病例，"
        "逐步确立了“左额叶后下部与言语运动有关”的结论，该区域后来被称为 Broca 区。\n\n"
        "从方法学上看，布洛卡示范了一条此后百年神经科学反复使用的路径：以临床症状定位脑区，再以尸检病理加以验证。"
        "这也开启了“脑功能定位”的时代，并引出后续对失语症的系统分类——例如韦尼克区与感觉性失语的发现。"
        "今天，功能磁共振与术中电刺激能够直接观察语言网络的活动，但布洛卡当年提出的核心命题——"
        "特定认知功能与特定皮层区域之间存在稳定对应——依然是临床神经病学与认知神经科学的基石。"
    ),
    (1884, "Godlee 首例脑肿瘤切除术"): (
        "1884 年 11 月 25 日，英国外科医生 Rickman Godlee 在伦敦完成了一例被载入史册的手术："
        "在明确脑部定位的前提下开颅并切除肿瘤。此前，脑部病变多被视为外科禁区，"
        "一方面缺乏定位手段，另一方面开颅的出血、感染与脑组织损伤难以控制。\n\n"
        "这一例的关键在于“先定位、后开颅”。患者由神经病学家 Alexander Hughes Bennett 依据症状"
        "（包括局灶性癫痫与进行性神经功能缺损）判断病变位于运动皮层附近，Godlee 据此设计开颅入路，"
        "术中发现了肿瘤并予以切除。尽管患者最终仍因并发症去世，但手术证明了脑肿瘤可以被定位、"
        "被显露、被切除，而不是只能被动观察。\n\n"
        "这标志着现代神经外科从“尝试”走向“体系”的转折。它把三项能力连接起来：临床神经定位、"
        "无菌与止血技术、以及敢于进入颅腔的手术决策。此后数十年，Harvey Cushing 等人进一步建立"
        "神经外科的止血、麻醉与操作规范，使开颅手术从极高死亡率逐步变为可常规开展的学科。"
        "回望 1884 年，这例手术的意义不在于“成功治愈”，而在于它第一次系统性地证明："
        "大脑不是不可触碰的黑箱，而是可以被有依据地干预的器官。"
    ),
    (1971, "首例活体头颅 CT 扫描"): (
        "1971 年 10 月 1 日，英国工程师 Godfrey Hounsfield 与放射科医生 James Ambrose 在伦敦 Atkinson Morley 医院"
        "完成了首例活体患者的头颅 CT 扫描。患者颅内的额叶病变在图像上清晰可见，并据此接受了手术。"
        "这是医学影像史上的一次范式转变：在此之前，医生要看颅内结构，往往只能依赖有创的气脑造影或血管造影。\n\n"
        "CT 的核心思想并不神秘，却极具革命性：让 X 射线从多个角度穿过人体，再用计算机把投影数据重建为断层图像。"
        "Hounsfield 与 Allan Cormack 因此分享了 1979 年诺贝尔生理学或医学奖。对神经科与神经外科而言，"
        "CT 第一次让出血、肿瘤、水肿、脑室与颅骨在活体上以可重复、相对安全的方式被看见。\n\n"
        "它的临床影响是连锁式的。急诊得以快速区分缺血性与出血性卒中，创伤性脑损伤的评估被彻底改写，"
        "术前规划与术后随访有了客观依据。更重要的是，CT 证明了“把物理测量交给计算机重建”这条路可行，"
        "直接为后来的 MRI、PET 与功能影像铺平了道路。今天回看，1971 年那台略显粗糙的 80×80 像素图像，"
        "是现代神经影像学的起点——它把“看不见的脑”变成了“可测量的脑”。"
    ),
    (1977, "首例人体 MRI 扫描"): (
        "1977 年 7 月 3 日，Raymond Damadian 团队完成了首例人体全身磁共振成像扫描，装置被命名为“Indomitable”。"
        "这次扫描历时数小时，图像粗糙，却第一次证明：无需电离辐射，也能从活体获取组织层面的信号。\n\n"
        "MRI 的物理基础来自核磁共振（NMR）。1973 年，Paul Lauterbur 提出用磁场梯度对核磁信号进行空间编码，"
        "Peter Mansfield 进一步发展了快速成像方法，二人因此获得 2003 年诺贝尔生理学或医学奖。"
        "与 CT 依赖 X 射线不同，MRI 利用强磁场与射频脉冲，对软组织对比极其敏感，能清晰区分灰质、白质与脑脊液。\n\n"
        "对神经科学而言，MRI 的意义是双重的。结构 MRI 让多发性硬化斑块、海马萎缩、肿瘤边界与白质病变"
        "得以精细刻画；而 1990 年代基于血氧水平依赖（BOLD）的功能 MRI，则把“活体人脑在执行任务时哪里在活动”"
        "变成可重复的实验。可以说，今天的认知神经科学与临床神经影像，绝大部分建立在这条技术脉络之上。"
        "从 Damadian 那次漫长而模糊的扫描，到如今亚毫米级、多模态的脑成像，MRI 用五十年时间"
        "把大脑从解剖标本变成了可动态观测的系统。"
    ),
    (1996, "tPA 获批用于急性缺血性卒中"): (
        "1996 年 6 月 18 日，美国 FDA 批准阿替普酶（tPA，组织型纤溶酶原激活剂）用于急性缺血性卒中的静脉溶栓治疗。"
        "这一决定建立在 NINDS 溶栓试验之上，也把卒中从“不可逆的灾难”推向“可干预的急症”。\n\n"
        "在此之前，急性缺血性卒中缺乏有效的再灌注手段，治疗多限于支持与二级预防。tPA 的逻辑是："
        "血栓堵塞脑血管后，越早溶解血栓、恢复血流，越能挽救缺血半暗带。试验显示，在严格的时间窗内给药，"
        "患者获得良好功能结局的比例显著提高。由此，“时间就是大脑”成为卒中救治的核心口号，"
        "也催生了卒中中心、绿色通道与院前识别体系的建设。\n\n"
        "这项批准同样带来了持续至今的讨论：溶栓时间窗的边界、出血转化的风险、影像筛选（如灌注成像）的价值，"
        "以及如何在基层医院安全开展。此后，血管内机械取栓在 2015 年前后通过多项试验确立，"
        "与大血管闭塞的再通形成互补。回望 1996 年，tPA 的意义不仅是多了一种药，更是重塑了"
        "整个神经科急症的组织方式——把“等待观察”变成了“争分夺秒的再灌注”。"
    ),
    (1987, "Fluoxetine（Prozac）获批"): (
        "1987 年 12 月 29 日，美国 FDA 批准氟西汀（商品名 Prozac）用于治疗抑郁症。"
        "它是首批广泛使用的选择性 5-羟色胺再摄取抑制剂（SSRI）之一，深刻改变了抑郁症的门诊治疗格局，"
        "也改变了公众对精神疾病的认知。\n\n"
        "从药理上看，SSRI 通过抑制突触前膜的 5-羟色胺转运体，提高突触间隙 5-羟色胺水平，"
        "从而增强 5-羟色胺能传递。与三环类抗抑郁药相比，SSRI 通常具有更好的耐受性与更低的过量毒性，"
        "这使得抗抑郁治疗可以更多地在基层与门诊开展，而不必完全依赖专科住院环境。\n\n"
        "Prozac 的社会影响同样深远。它让“抑郁症”从一个带有污名化的标签，逐渐被视为一种"
        "可以被识别、被讨论、被治疗的常见疾病；它也推动了精神药理学的产业化与初级保健中的筛查。"
        "与此同时，关于 SSRI 起效机制、安慰剂效应、起效延迟与长期使用的争论从未停止，"
        "近年甚至有“SSRI 究竟如何起效”的公开反思。无论立场如何，1987 年的这次批准都是一个分水岭："
        "它把精神科药物治疗从“少数重症的专科手段”，推向了“广泛人群的常规选择”。"
    ),
    (1996, "Donepezil（Aricept）获批"): (
        "1996 年 11 月 25 日，美国 FDA 批准多奈哌齐（商品名 Aricept）用于阿尔茨海默病。"
        "它成为此后二十余年最广泛使用的胆碱酯酶抑制剂之一，也是很多患者确诊后接触到的第一种药物。\n\n"
        "其药理基础是胆碱能假说：阿尔茨海默病患者基底前脑胆碱能神经元受损，导致皮层与海马乙酰胆碱不足，"
        "而乙酰胆碱与记忆、注意密切相关。多奈哌齐通过可逆性抑制乙酰胆碱酯酶，减少乙酰胆碱降解，"
        "从而在一定程度上改善或延缓认知症状。它的优势在于每日一次给药、耐受性相对较好，"
        "并可与后来的美金刚（NMDA 受体拮抗剂）在不同阶段形成互补。\n\n"
        "需要强调的是，胆碱酯酶抑制剂主要改善症状，并不能阻止疾病进展。正因如此，"
        "它既代表了阿尔茨海默病药物治疗的第一次系统性突破，也暴露了“对症治疗”的天花板。"
        "此后，围绕淀粉样蛋白、tau、神经炎症与代谢的疾病修饰疗法成为主线，"
        "直到 2021 年后抗 Aβ 单抗陆续获批。回看 1996 年，多奈哌齐的意义是把阿尔茨海默病"
        "从“无药可用”带入“有药可试”的时代，也为后续更严格的临床试验与生物标志体系奠定了基础。"
    ),
    (2004, "Natalizumab（Tysabri）获批"): (
        "2004 年 11 月 23 日，美国 FDA 批准那他珠单抗（商品名 Tysabri）用于复发型多发性硬化。"
        "它是一种针对 α4-整合素的单克隆抗体，通过阻断免疫细胞穿越血脑屏障进入中枢神经系统，"
        "从而显著降低复发率与病灶活动。\n\n"
        "多发性硬化被视为一种由免疫介导的中枢神经系统炎性脱髓鞘疾病。传统疾病修饰治疗多为注射用干扰素或醋酸格拉替雷，"
        "疗效有限。那他珠单抗的出现，代表了“靶向免疫细胞迁移”这一新策略，疗效在当时相当突出。"
        "然而，它很快因进行性多灶性白质脑病（PML）这一严重机会性感染风险而一度撤市，"
        "后经风险评估与监测计划重新上市，并附以严格的用药监测。\n\n"
        "这一案例在神经免疫治疗史上具有双重意义：一方面，它证明了高效靶向治疗可以大幅改变疾病活动；"
        "另一方面，它也成为“疗效与风险平衡”的经典教材——强效免疫干预必然伴随感染风险，"
        "需要在患者选择、监测与获益-风险评估上建立制度。此后，抗 CD20 单抗、S1P 受体调节剂等"
        "新一代疗法陆续出现，但那他珠单抗所确立的“高效但需严密监测”的范式，至今仍被反复引用。"
    ),
    (2010, "Fingolimod（Gilenya）获批"): (
        "2010 年 9 月 21 日，美国 FDA 批准芬戈莫德（商品名 Gilenya）用于复发型多发性硬化，"
        "成为首个口服的疾病修饰治疗药物。在此之前，多发性硬化的疾病修饰治疗几乎都依赖注射给药，"
        "依从性与生活质量受到明显限制。\n\n"
        "芬戈莫德是一种鞘氨醇-1-磷酸（S1P）受体调节剂。它通过促使淋巴细胞滞留于淋巴结，"
        "减少自身反应性淋巴细胞进入中枢神经系统，从而降低复发与病灶活动。其口服剂型极大改善了"
        "患者的用药体验，也推动了多发性硬化治疗从“注射时代”迈入“口服时代”。\n\n"
        "但口服并非没有代价。首剂给药后的心率减慢、房室传导阻滞，以及后来的黄斑水肿、肝酶升高"
        "与进行性多灶性白质脑病风险，都要求规范的首次给药监测与长期随访。芬戈莫德的获批，"
        "标志着多发性硬化治疗进入“高效、口服、需监测”的新阶段，也为后续口服药物"
        "（如富马酸二甲酯、S1P 受体调节剂家族）铺平了道路。它提醒临床：给药方式的便利，"
        "必须与安全性监测体系同步建立。"
    ),
    (2017, "Ocrelizumab（Ocrevus）获批"): (
        "2017 年 3 月 28 日，美国 FDA 批准奥瑞利珠单抗（商品名 Ocrevus）用于多发性硬化，"
        "成为首个获批用于原发进展型多发性硬化（PPMS）的疾病修饰治疗药物，同时也用于复发型 MS。\n\n"
        "奥瑞利珠单抗是一种靶向 CD20 的人源化单克隆抗体。B 细胞在多发性硬化的发病中扮演重要角色，"
        "既参与抗原呈递，也参与细胞因子网络与异位淋巴样结构的形成。通过选择性清除 CD20 阳性 B 细胞，"
        "该药能显著降低复发与影像学病灶活动。其历史性意义在于：长期以来，原发进展型 MS 缺乏"
        "被证实有效的药物，患者往往只能面对缓慢而持续的残疾累积；奥瑞利珠单抗首次在随机试验中"
        "显示出对 PPMS 进展的延缓作用。\n\n"
        "这一批准重新定义了 MS 的治疗版图：治疗靶点从“T 细胞中心”扩展到“B 细胞参与”，"
        "治疗目标从“控制复发”延伸到“延缓进展”。当然，B 细胞清除也带来感染风险与长期免疫监测的需求，"
        "并推动了对“何时启动高效治疗”“如何个体化选择”的持续讨论。回望 2017 年，"
        "它让进展型 MS 第一次拥有了被证实有效的疾病修饰选项。"
    ),
    (2021, "Aducanumab（Aduhelm）获加速批准"): (
        "2021 年 6 月 7 日，美国 FDA 以加速批准途径批准阿杜那单抗（商品名 Aduhelm）用于阿尔茨海默病，"
        "成为近二十年来首个获批的抗淀粉样蛋白新药。这一决定在科学界、临床界与监管界引发了"
        "持续而激烈的争论。\n\n"
        "阿杜那单抗靶向淀粉样蛋白 β（Aβ）聚集体，能够显著清除脑内淀粉样斑块——这是阿尔茨海默病的"
        "核心病理标志之一。支持者认为，清除斑块是干预疾病进程的必要一步；批评者则指出，"
        "两项关键试验结果不一致，认知获益的证据薄弱，而淀粉样相关影像异常（ARIA，包括脑水肿与微出血）"
        "带来真实的安全性负担。\n\n"
        "无论评价如何，这次批准都具有分水岭意义：它把“以生物标志物替代终点作为加速批准依据”"
        "这一监管路径推到聚光灯下，也促使医学界重新讨论“斑块清除是否等于临床获益”。"
        "此后，lecanemab 与 donanemab 在更完整的试验数据基础上相继获批，抗 Aβ 疗法逐步从"
        "争议走向更明确的获益-风险框架。回看 2021 年，阿杜那单抗更像是一次“压力测试”："
        "它迫使整个领域正视疾病修饰疗法在证据标准、患者选择与安全性监测上的根本难题。"
    ),
    (2023, "Lecanemab（Leqembi）获加速批准"): (
        "2023 年 1 月 6 日，美国 FDA 以加速批准途径批准 lecanemab（商品名 Leqembi）用于早期阿尔茨海默病，"
        "同年 7 月 6 日转为常规批准。它是抗淀粉样蛋白单抗中首批获得常规批准、并被证实在早期患者中"
        "减缓认知下降的药物之一。\n\n"
        "lecanemab 选择性结合可溶性 Aβ 原纤维，被认为能更早干预毒性聚集体的形成。关键试验显示，"
        "在早期阿尔茨海默病患者中，它能显著降低脑内淀粉样斑块负荷，并在认知与功能量表上"
        "带来统计学显著的减缓。与此同时，淀粉样相关影像异常（ARIA）仍是需要重点监测的安全性事件，"
        "尤其在携带 APOE4 等位基因的患者中风险更高。\n\n"
        "它的意义在于把“疾病修饰”从概念推向可及的治疗选项：诊断路径需要生物标志物确认（如 PET 或脑脊液/血液标志），"
        "治疗需要影像监测与风险分层，随访需要结构化的认知评估。这标志着阿尔茨海默病诊疗正在从"
        "“对症治疗”转向“生物学分期 + 靶向干预”的模式。当然，疗效幅度有限、费用与可及性、"
        "以及长期获益仍需真实世界数据检验。2023 年因此成为抗 Aβ 疗法从争议走向常规临床的关键一年。"
    ),
    (2024, "Donanemab（Kisunla）获批"): (
        "2024 年 7 月 2 日，美国 FDA 批准 donanemab（商品名 Kisunla）用于早期阿尔茨海默病，"
        "成为继 lecanemab 之后又一款进入临床的抗淀粉样蛋白单抗。\n\n"
        "donanemab 靶向的是已形成的淀粉样斑块中的特定表位（焦谷氨酸化 Aβ），其设计思路强调"
        "对成熟斑块的清除。关键试验显示，在早期患者中它能显著降低斑块负荷并减缓认知与功能下降；"
        "研究还采用“达到斑块清除后即可停药”的策略，试图减少长期用药负担。与同类药物一样，"
        "ARIA（脑水肿与微出血）是需要严密监测的主要风险，携带 APOE4 的患者风险更高。\n\n"
        "它的获批进一步巩固了“抗 Aβ 单抗 + 生物标志物诊断 + 影像监测”的临床路径，也让"
        "“有限疗程、达标停药”成为值得讨论的治疗模式。同时，它把几个现实问题摆上台面："
        "哪些患者真正获益最大？如何在资源有限的环境中开展输注与 MRI 监测？疗效幅度是否足以"
        "改变患者与照护者的生活？回望 2024 年，donanemab 的价值不仅是多了一个药，"
        "更是推动阿尔茨海默病治疗向“可评估、可监测、可管理”的慢病模式演进。"
    ),
    (2024, "Xanomeline/trospium（Cobenfy）获批"): (
        "2024 年 9 月 26 日，美国 FDA 批准 xanomeline/trospium（商品名 Cobenfy）用于精神分裂症，"
        "成为首个不依赖多巴胺 D2 受体阻断的抗精神病药。这一批准被视为精神药理学数十年来的"
        "一次范式转变。\n\n"
        "数十年来，抗精神病药的主流机制是阻断多巴胺 D2 受体，虽能控制阳性症状，"
        "却常伴随锥体外系反应、催乳素升高与代谢副作用，且对阴性症状与认知缺陷效果有限。"
        "Cobenfy 由毒蕈碱受体激动剂 xanomeline 与外周抗胆碱药 trospium 组成：前者作用于中枢 M1/M4 受体，"
        "改善精神病性症状与认知；后者减少外周胆碱能副作用（如胃肠道不适）。这一“中枢激动 + 外周拮抗”的组合，"
        "绕开了 D2 通路。\n\n"
        "其意义在于为“难治或不耐受”的患者提供新选择，并重新点燃了毒蕈碱靶点在精神科的兴趣。"
        "当然，新机制也带来新的安全性考量（如胃肠道反应、心率变化与肝功能监测），"
        "长期疗效与真实世界获益仍需积累。回看 2024 年，Cobenfy 的获批不仅是多了一种药，"
        "更是对“精神分裂症只能靠 D2 阻断”这一长期假设的正面挑战，可能开启非多巴胺能抗精神病药的新赛道。"
    ),
    (2019, "Esketamine（Spravato）获批"): (
        "2019 年 3 月 5 日，美国 FDA 批准艾司氯胺酮（商品名 Spravato）鼻喷剂用于治疗抵抗性抑郁症，"
        "成为数十年来首个机制全新的抗抑郁药，也把“谷氨酸能抗抑郁”推到临床前台。\n\n"
        "传统抗抑郁药以单胺类（5-羟色胺、去甲肾上腺素、多巴胺）为靶点，起效往往需要数周。"
        "氯胺酮及其 S-对映体艾司氯胺酮通过拮抗 NMDA 受体，被认为能快速促进突触可塑性，"
        "在数小时至数天内改善抑郁症状，对存在自杀意念的高危患者尤具意义。FDA 的批准附带了"
        "严格的风险管理：需在受监管的医疗机构给药并观察，以应对解离、血压升高与滥用风险。\n\n"
        "它的影响是双重的。临床上，它为治疗抵抗性抑郁提供了快速起效的选项；科学上，"
        "它把“突触可塑性与快速抗抑郁”确立为可检验的假说，推动了神经甾体、迷幻药与"
        "其他快速起效机制的研究。争议同样存在：疗效维持、复发、滥用潜力与可及性都需要长期数据。"
        "回看 2019 年，Spravato 的意义在于打破了“抗抑郁必须等数周”的惯性，"
        "让精神科重新认真对待“快速起效”这一目标。"
    ),
    (2019, "Brexanolone（Zulresso）获批"): (
        "2019 年 3 月 19 日，美国 FDA 批准 brexanolone（商品名 Zulresso）静脉制剂用于产后抑郁，"
        "成为首个专门针对产后抑郁获批的药物，也是神经甾体机制在精神科的一次重要落地。\n\n"
        "brexanolone 是别孕烯醇酮（allopregnanolone）的静脉制剂，后者是一种内源性神经甾体，"
        "可正向调节 GABA-A 受体。围产期激素剧烈波动被认为是产后抑郁的重要诱因之一，"
        "而神经甾体通路的失调可能参与其中。关键试验显示，单次 60 小时静脉输注可在数天内"
        "显著改善抑郁症状，起效速度远快于传统抗抑郁药。\n\n"
        "其获批的意义在于：它把“围产期精神健康”从被忽视的边缘议题推向监管与临床的中心，"
        "也证明了神经甾体通路可以作为精神科的治疗靶点。限制同样明显——需要连续 60 小时住院输注、"
        "监测过度镇静与意识丧失风险，成本与可及性成为推广瓶颈。此后，口服神经甾体"
        "zuranolone 于 2023 年获批，试图解决给药便利性问题。回看 2019 年，brexanolone 的批准"
        "不仅填补了产后抑郁的特异性药物治疗空白，也为“快速起效 + 神经甾体”这一方向打开了大门。"
    ),
}


BODIES_EXTRA: dict[tuple[int, str], str] = {
    (1861, "Broca 报告“Tan”病例"): (
        "从更长的历史看，布洛卡的发现还埋下了一个此后争论不休的问题：功能定位究竟能精细到什么程度？"
        "十九世纪的“定位派”相信每个功能对应一块皮层，而“整体派”强调大脑的整合性。二十世纪的教训表明，"
        "真相介于两者之间——语言既依赖相对局限的节点（如 Broca 区、Wernicke 区），也依赖分布式的网络连接。"
        "现代失语症研究借助白质纤维束成像与皮层电刺激，把“节点—通路—网络”三层结构逐步厘清；"
        "术中唤醒地图让外科医生能在切除肿瘤时保护语言区，这正是布洛卡式定位思想在手术室里的延续。"
        "同时，个体差异与可塑性提醒我们：同一病灶在不同人身上可表现迥异。布洛卡留下的不仅是“一个脑区”，"
        "更是一套方法：用行为缺损反推脑机制，再用病理或影像验证，最后回到临床干预。"
    ),
    (1884, "Godlee 首例脑肿瘤切除术"): (
        "这例手术之所以成立，离不开十九世纪末两项关键进展：一是神经病学对局灶体征的系统归纳，"
        "使病变能够在开颅前被“画”在头皮上；二是外科无菌技术与麻醉的成熟，让长时间开颅成为可能。"
        "在此之前，Macewen 于 1879 年在格拉斯哥已有成功的脑部病变处理经验，Godlee 的病例则进一步把"
        "“定位—开颅—切除—病理确认”固化为流程。此后，神经外科逐渐分化出独立的学科身份："
        "专用器械、术中止血、术后管理都开始成形。Harvey Cushing 在二十世纪初把血压监测、"
        "电凝止血与经蝶入路引入，使手术死亡率大幅下降。现代神经肿瘤学则在显微外科、术中磁共振、"
        "术中神经电生理监测与分子病理的基础上继续演进。回望 Godlee 那一刀，它的历史地位在于："
        "它把“脑部手术”从孤例变成了可复制的方法论，奠定了此后一个多世纪神经外科的基本语法。"
    ),
    (1971, "首例活体头颅 CT 扫描"): (
        "CT 的扩散速度在医学技术史上极为罕见：首例临床扫描后仅数年，美国医院便装配了数百台设备，"
        "到八十年代初，大型医院中已有相当比例配备 CT。原因在于它解决的是急诊与神经科最迫切的痛点——"
        "快速、无创地区分出血、缺血、占位与水肿。对卒中而言，CT 让“先影像、后溶栓”成为安全前提；"
        "对创伤而言，它让颅内血肿的识别从“推测”变为“看见”。同时，CT 也带来新的临床问题："
        "辐射剂量、对比剂过敏与肾病风险，以及偶然发现的过度检查。从技术脉络看，CT 的"
        "“投影—重建”思想直接启发了后续的断层与功能成像；从学科脉络看，它把放射科、神经内科与"
        "神经外科紧密地绑在同一个急诊流程里。可以说，现代卒中中心与创伤中心的组织形态，"
        "很大程度上是围绕 CT 这台机器建立起来的。"
    ),
    (1977, "首例人体 MRI 扫描"): (
        "MRI 的临床化并非一蹴而就。首例人体扫描之后，成像速度慢、运动伪影、设备成本与磁场安全等问题"
        "需要多年工程攻关；直到八十年代，MRI 才逐步进入常规临床。它的独特价值在于多参数对比："
        "T1、T2、FLAIR、弥散加权（DWI）与磁敏感加权（SWI）等序列，能从不同物理维度刻画组织。"
        "对神经科而言，DWI 让超急性期脑梗死得以早期识别，SWI 让微出血与静脉血栓更易发现，"
        "而高分辨结构像则支撑了癫痫灶定位与手术规划。MRI 也带来了新的安全规范：植入物筛查、"
        "幽闭恐惧管理、噪声防护与钆对比剂的肾源性系统性纤维化风险。更深远的是，MRI 让“脑”"
        "成为可重复测量的对象，推动了规范化脑图谱、多中心影像协作与影像基因组学。"
        "从 1977 年那次漫长的扫描到今天，MRI 已从“实验奇观”变成神经科学最基础的工具之一。"
    ),
    (1996, "tPA 获批用于急性缺血性卒中"): (
        "tPA 之后，卒中治疗的主线是“更快、更准、更彻底地再通”。一方面，院前识别、卒中单元与"
        "到院至给药时间管理被系统化，影像（尤其灌注与弥散不匹配）用于筛选超出传统时间窗仍可能获益的患者；"
        "另一方面，2015 年前后多项随机试验证实，对大血管闭塞行血管内取栓可显著改善功能结局，"
        "使“桥接治疗”（先溶栓、后取栓）成为标准路径之一。与此同时，溶栓的核心风险——症状性颅内出血——"
        "要求严格的禁忌证筛查与血压管理。tPA 的历史也提醒我们：一项疗法的价值不仅取决于药理，"
        "更取决于救治体系能否在正确的时间把药送到正确的患者手里。今天，移动卒中单元、远程卒中会诊"
        "与人工智能辅助影像正在进一步压缩时间。回看 1996 年，那纸批文真正改变的，是整个神经科急症的组织逻辑。"
    ),
    (1987, "Fluoxetine（Prozac）获批"): (
        "Prozac 的走红也带来了反思。随着处方量激增，关于“是否被过度处方”“是否削弱了对心理社会因素的处理”"
        "以及“安慰剂效应占比”的讨论持续发酵。大型研究（如 STAR*D）显示，抗抑郁药对中重度抑郁有明确获益，"
        "但对轻症的优势有限，且不同药物间的差异往往不如“是否坚持足量足疗程”重要。此后，"
        "SSRI 家族扩展到舍曲林、帕罗西汀、西酞普兰等，适应症也从抑郁延伸到焦虑、强迫、创伤后应激等。"
        "在神经科学层面，SSRI 促使研究者重新审视“单胺假说”的局限，转向神经营养、神经可塑性与"
        "炎症等更整合的机制。今天，抑郁症治疗强调药物、心理治疗与生活方式的组合，并重视个体化选药。"
        "Prozac 的历史意义因此是双面的：它既是精神科药物治疗大众化的起点，也是“用一颗药解决复杂疾病”"
        "这一简化叙事被逐步修正的起点。"
    ),
    (1996, "Donepezil（Aricept）获批"): (
        "多奈哌齐的临床使用也塑造了一套至今沿用的诊疗流程：以认知量表评估基线、定期复评、"
        "结合照料者报告与功能状态判断疗效，并在耐受性允许时逐步滴定。它让“轻度认知障碍”与"
        "“早期阿尔茨海默病”的识别变得更有意义，因为早识别意味着可以更早开始干预。"
        "同时，胆碱酯酶抑制剂的局限也推动了试验方法的演进：研究者逐渐意识到，仅靠认知量表的小幅改善"
        "难以反映疾病进程，于是生物标志物（Aβ、tau、神经变性标志）与功能结局被纳入试验设计。"
        "这条线索最终导向了抗淀粉样蛋白单抗时代。回望 1996 年，多奈哌齐不仅是一个药，"
        "更是一套“如何评估与随访认知障碍”的临床框架的开端；它让阿尔茨海默病从“被忽视的老年问题”"
        "变成了有指南、有随访、有药物可谈的疾病领域。"
    ),
    (2004, "Natalizumab（Tysabri）获批"): (
        "那他珠单抗的曲折经历深刻影响了此后的药物研发与监管。PML 事件促使业界建立了"
        "基于 JC 病毒抗体状态与既往免疫抑制暴露的风险分层，并引入强制性的风险评估与缓解策略。"
        "它也提醒：对中枢神经系统的高效免疫干预，必须同时评估机会性感染的风险。在疗效层面，"
        "那他珠单抗证明了“高效治疗”可以显著压低疾病活动，这为后来“早期高效治疗”的策略提供了依据。"
        "此后，抗 CD20 单抗、S1P 调节剂、富马酸二甲酯等相继问世，多发性硬化的治疗从“温和起步”"
        "转向“按风险与活动度分层”。回看 2004 年，那他珠单抗是一个分水岭：它既展示了靶向免疫迁移的"
        "强大威力，也用一次严重安全事件教会整个领域如何在获益与风险之间建立制度化的平衡。"
    ),
    (2010, "Fingolimod（Gilenya）获批"): (
        "芬戈莫德的口服化意义不止于便利。它改变了患者对“长期治疗”的心理预期——从定期注射的负担，"
        "转向每日一片的日常管理，从而可能提高长期依从性。与此同时，它把安全性监测推到前台："
        "首剂给药需观察心率与血压，后续需监测肝功能、眼底与感染风险。此后的口服药物"
        "（富马酸二甲酯、特立氟胺、S1P 受体调节剂家族）在疗效与安全性上各有取舍，"
        "共同构成了“口服时代”的治疗谱系。值得强调的是，口服并不等于低风险：不同机制对应不同的"
        "监测要求，个体化选择需要综合疾病活动度、生育计划、感染风险与合并症。回看 2010 年，"
        "芬戈莫德的获批是一个象征性节点——它标志着多发性硬化治疗从“注射为主”走向“多种给药途径并存”，"
        "也让“以患者为中心”的长期管理成为可能。"
    ),
    (2017, "Ocrelizumab（Ocrevus）获批"): (
        "奥瑞利珠单抗的意义还在于它改变了“进展型 MS 无药可用”的悲观预期。原发进展型 MS 长期缺乏"
        "被证实有效的疗法，患者往往在数年内持续累积残疾；首个阳性试验为该人群带来了希望，"
        "也推动了“进展独立于复发活动”等概念的讨论。在机制层面，它把 B 细胞从“抗体工厂”"
        "重新定位为免疫调节的关键参与者，促使研究者关注 B 细胞抗原呈递、细胞因子分泌与"
        "异位淋巴样结构。临床上，静脉输注的给药方式带来便利也带来管理需求：输注反应、感染风险、"
        "疫苗应答与长期免疫监测都需要规范。此后，高效疗法在早期 MS 中的应用日益普遍，"
        "治疗目标从“减少复发”扩展为“延缓进展、保护脑容量”。回看 2017 年，它让进展型 MS 第一次"
        "拥有了被证实有效的疾病修饰选项，也把 MS 治疗推向“高效、分层、个体化”的新阶段。"
    ),
    (2021, "Aducanumab（Aduhelm）获加速批准"): (
        "阿杜那单抗的余波深远。批准后，围绕其临床获益的质疑导致处方与覆盖范围受限，"
        "部分医疗系统与支付方设置了严格条件；同时，它催生了对“加速批准—确证试验”机制的检讨，"
        "推动监管机构更强调确证性证据与生物标志物替代终点的边界。对临床而言，ARIA 的管理成为"
        "抗 Aβ 治疗的必修课：治疗前需评估 APOE 基因型、基线微出血与脑淀粉样血管病风险，"
        "治疗中需按计划复查 MRI。对产业而言，它加速了更高质量试验的设计与开展，"
        "为后续 lecanemab、donanemab 的获批铺路。回看 2021 年，阿杜那单抗更像一面镜子："
        "它照出了阿尔茨海默病疾病修饰疗法的巨大期待，也照出了证据标准、患者选择与"
        "卫生经济之间的深层张力。它的教训与它的批准同样重要。"
    ),
    (2023, "Lecanemab（Leqembi）获加速批准"): (
        "lecanemab 的常规批准把“抗 Aβ 治疗”从争议带入临床路径，但也暴露了实施层面的挑战。"
        "首先，治疗前提是生物标志物确认的早期患者，这意味着需要 PET 或脑脊液/血液标志物的可及性；"
        "其次，ARIA 的监测需要基线及随访 MRI，对影像资源与随访体系提出要求；第三，"
        "静脉给药与治疗成本对医疗系统构成压力。疗效方面，减缓幅度在统计学上显著，"
        "但临床意义仍需在真实世界中评估——患者与照护者更关心的是功能维持与生活质量。"
        "此外，APOE4 携带者的 ARIA 风险更高，抗凝使用者的管理也需谨慎。回看 2023 年，"
        "lecanemab 的意义在于它把“生物学分期 + 早期干预 + 结构化监测”变成可操作的诊疗模式，"
        "同时也把阿尔茨海默病带入了一个需要长期投入与公平可及讨论的新阶段。"
    ),
    (2024, "Donanemab（Kisunla）获批"): (
        "donanemab 的“达标停药”策略值得单独讨论。它以斑块清除为节点，试图把长期用药简化为有限疗程，"
        "这在理论上可降低累积风险与费用，但也带来新的问题：停药后斑块是否会重新累积、"
        "认知获益能否维持、何时需要再次治疗，都缺乏长期数据。与 lecanemab 类似，"
        "ARIA 监测与 APOE4 风险分层是临床实施的关键；此外，不同抗 Aβ 药物之间缺乏直接头对头比较，"
        "选择往往依赖试验人群、给药方案与安全性特征。对患者而言，最重要的仍是“早期识别 + 规范评估 + 共同决策”。"
        "回看 2024 年，donanemab 让抗 Aβ 疗法从“有没有”进入“怎么用”的阶段："
        "疗效幅度、疗程设计、监测负担与可及性，共同决定了它在真实世界中的价值。"
    ),
    (2024, "Xanomeline/trospium（Cobenfy）获批"): (
        "Cobenfy 的背后是一段曲折的研发史。xanomeline 早年在阿尔茨海默病试验中显示出改善精神症状的迹象，"
        "但因外周胆碱能副作用（恶心、呕吐、腹泻）而受限；把外周拮抗剂 trospium 与之组合，"
        "正是为了“把作用留在中枢、把副作用挡在外周”。这一思路的成功，重新点燃了毒蕈碱 M1/M4 受体"
        "在精神分裂症与认知障碍中的研究兴趣。需要冷静看待的是：新机制意味着新的未知——长期疗效、"
        "对阴性症状与认知的作用、以及胃肠道与心血管安全性仍需真实世界数据；此外，"
        "其定价与可及性也会影响推广。回看 2024 年，Cobenfy 的获批不仅是多了一种药，"
        "更是对“抗精神病必须阻断 D2”这一数十年教条的正面挑战，可能开启非多巴胺能治疗的新赛道。"
    ),
    (2019, "Esketamine（Spravato）获批"): (
        "艾司氯胺酮的临床落地依赖一套“受监管给药”的模式：患者需在医疗机构内接受鼻喷给药并观察约两小时，"
        "以监测解离、血压升高与镇静；治疗通常与口服抗抑郁药联用，并按疗程安排维持。"
        "这套模式既保障了安全，也带来了可及性问题——需要专门的门诊空间、人员与流程。"
        "在科学层面，它推动了“快速起效抗抑郁”的机制研究：NMDA 受体拮抗如何触发突触可塑性、"
        "神经营养通路的作用、以及疗效能否被维持，都成为热点。争议同样存在："
        "长期疗效、滥用潜力、以及“药物本身”与“给药环境/期望”的贡献比例仍需厘清。"
        "回看 2019 年，Spravato 的最大意义或许在于改变了精神科的研发方向——"
        "从“再找一个单胺靶点”转向“寻找能快速重塑神经环路的机制”。"
    ),
    (2019, "Brexanolone（Zulresso）获批"): (
        "brexanolone 的 60 小时持续静脉输注是一种“重资产”治疗：需要住院或专门输注中心、"
        "持续监护与应急预案，因此其推广受到成本与资源的限制。但它证明了围产期抑郁可以被"
        "特异性药物快速改善，也让“产后抑郁”从社会议题进入监管与临床路径。此后，"
        "口服神经甾体 zuranolone 于 2023 年获批，试图以短疗程口服方案解决便利性问题，"
        "但其镇静相关风险仍需注意。机制上，神经甾体对 GABA-A 受体的调节提示："
        "围产期激素的剧烈波动可能通过 GABA 能系统影响情绪，这为理解产后抑郁提供了新视角。"
        "回看 2019 年，brexanolone 的意义在于它同时做到了两件事：填补了产后抑郁特异性药物治疗的空白，"
        "并把“神经甾体”这一曾经边缘的通路推到了精神科药物开发的主舞台。"
    ),
}


BODIES_CLOSING: dict[tuple[int, str], str] = {
    (1861, "Broca 报告“Tan”病例"): (
        "对今天的意义在于：功能定位必须与网络连接、个体差异和可塑性结合来看。临床上一处病灶的解释，"
        "不能脱离患者的行为表现与影像—电生理证据；术中唤醒与功能成像正是这一思想的技术延伸。"
        "失语症的康复也提示大脑具有一定重组能力，早期言语治疗与多模态评估可改善结局。"
    ),
    (1884, "Godlee 首例脑肿瘤切除术"): (
        "今天的神经外科以显微操作、术中磁共振、神经电生理监测与分子病理为支柱，但核心命题未变："
        "在最大程度切除病灶的同时保护功能。导航、荧光显影与术中超声让“看得见、切得准”成为常规，"
        "而多学科团队与术后康复则决定长期结局。Godlee 那一刀开启的，是一条从“能开颅”走向“开好颅”的演进之路。"
    ),
    (1971, "首例活体头颅 CT 扫描"): (
        "今天的急诊影像已从单次平扫扩展到灌注成像、CT 血管造影与人工智能辅助判读，低剂量方案也在降低辐射负担。"
        "但治理重点始终是：避免不必要的重复检查、规范对比剂使用、并在速度与安全之间取得平衡。"
        "CT 的故事说明，一项影像技术的价值，最终由它嵌入的临床流程来定义。"
    ),
    (1977, "首例人体 MRI 扫描"): (
        "今天，MRI 已发展出定量成像、超高场（7T）、弥散与功能连接等多种范式，成为脑科学与临床神经病学的共同基础设施。"
        "限制仍在：成本、可及性、运动伪影与植入物安全。未来，压缩感知、低场便携 MRI 与自动化分析有望进一步扩大其应用边界。"
    ),
    (1996, "tPA 获批用于急性缺血性卒中"): (
        "今天的卒中救治是“溶栓 + 取栓 + 卒中中心网络 + 影像筛选”的组合拳，时间窗正被影像与个体化评估重新定义。"
        "核心教训依旧：再有效的再通手段，也必须依托快速识别、绿色通道与规范的重症管理，才能真正转化为患者获益。"
    ),
    (1987, "Fluoxetine（Prozac）获批"): (
        "今天，SSRI 仍是抑郁与焦虑的一线选择之一，但临床更强调足量足疗程、疗效评估与联合心理治疗，"
        "并重视性功能障碍、停药反应等长期问题。对研究者而言，Prozac 留下的最大课题是："
        "如何用更整合的机制解释并预测个体化的治疗反应。"
    ),
    (1996, "Donepezil（Aricept）获批"): (
        "今天，胆碱酯酶抑制剂仍用于症状治疗，并与美金刚、抗 Aβ 单抗等形成分层策略。"
        "更重要的是，它推动建立的“量表 + 功能 + 生物标志物 + 影像”评估体系，"
        "已成为阿尔茨海默病临床试验与真实世界管理的通用语言。"
    ),
    (2004, "Natalizumab（Tysabri）获批"): (
        "今天，MS 治疗已进入高效疗法与风险分层并行的时代，JC 病毒抗体、既往免疫抑制史与治疗时长共同指导决策。"
        "那他珠单抗的经验被写进指南：越强的免疫干预，越需要制度化的风险监测与患者沟通。"
    ),
    (2010, "Fingolimod（Gilenya）获批"): (
        "今天，口服 DMT 已成为 MS 治疗的主流选项之一，首剂监测与长期安全随访也成常规。"
        "其启示在于：给药方式的革新必须与安全性管理体系同步，才能真正提升长期依从性与生活质量。"
    ),
    (2017, "Ocrelizumab（Ocrevus）获批"): (
        "今天，B 细胞靶向治疗已是高效 MS 治疗的重要支柱，感染风险评估、疫苗接种与免疫监测需前置。"
        "其意义还在于推动“早期高效治疗”理念：在不可逆残疾累积之前控制疾病活动，可能比事后补救更有价值。"
    ),
    (2021, "Aducanumab（Aduhelm）获加速批准"): (
        "今天，抗 Aβ 治疗已走向更严格的证据标准与更清晰的实施路径。阿杜那单抗的教训提醒："
        "生物标志物替代终点不能自动等同于临床获益，患者选择、ARIA 监测与支付政策必须同步设计，"
        "否则再前沿的机制也难以转化为可及的治疗。"
    ),
    (2023, "Lecanemab（Leqembi）获加速批准"): (
        "今天的落地三要素是：生物标志物确认的早期诊断、规范的 MRI 监测、以及具备输注与随访能力的诊疗中心。"
        "未来，血液标志物、皮下制剂与真实世界证据将决定抗 Aβ 疗法能否从少数中心走向更广泛的人群。"
    ),
    (2024, "Donanemab（Kisunla）获批"): (
        "今天的挑战是“怎么用得好”：个体化疗程、ARIA 风险沟通、疗效与费用的平衡，都需要真实世界研究来回答。"
        "抗 Aβ 疗法的竞争，最终会落在安全性管理、给药便利与长期获益证据上，而不只是斑块清除的幅度。"
    ),
    (2024, "Xanomeline/trospium（Cobenfy）获批"): (
        "今天，毒蕈碱靶点正式进入临床，但长期疗效、代谢与心血管安全性、以及可及性仍待观察。"
        "若后续数据稳健，它可能推动精神分裂症治疗从“单一 D2 阻断”转向“多通路组合”，"
        "并重新定义“副作用更友好”的抗精神病药标准。"
    ),
    (2019, "Esketamine（Spravato）获批"): (
        "今天，快速起效抗抑郁已从概念走向机构化实践，维持治疗策略与复发预防仍在优化。"
        "其更大价值在于打开了机制探索的闸门：NMDA、神经甾体与迷幻药等通路，正共同重塑精神科药物研发的版图。"
    ),
    (2019, "Brexanolone（Zulresso）获批"): (
        "今天，围产期精神健康正被纳入常规筛查与随访，口服神经甾体等方案在提升可及性。"
        "其启示是：把激素波动、睡眠与心理社会因素纳入同一框架，才可能真正改善母婴结局。"
    ),
}


def _decorate(e: dict, match: str) -> dict:
    item = dict(e)
    item["category_label"] = CATEGORY_LABELS.get(e.get("category", ""), e.get("category", ""))
    item["kind_label"] = KIND_LABELS.get(e.get("kind", ""), "历史事件")
    item["match"] = match
    key = (e.get("year"), e.get("title"))
    parts = [BODIES.get(key), BODIES_EXTRA.get(key), BODIES_CLOSING.get(key)]
    body = "\n\n".join(p for p in parts if p)
    if body:
        item["body"] = body
    return item


def events_for(month: int, day: int) -> list[dict]:
    """Exact day matches only (no fallback)."""
    out = [_decorate(e, "exact") for e in EVENTS.get((month, day), [])]
    out.sort(key=lambda x: x.get("year", 0), reverse=True)
    return out


def _nearest_in_month(d: _date) -> list[dict]:
    days = sorted(day for (m, day) in EVENTS if m == d.month)
    if not days:
        return []
    nearest = min(days, key=lambda day: abs(day - d.day))
    out = [_decorate(e, "near") for e in EVENTS[(d.month, nearest)]]
    for e in out:
        e["near_day"] = nearest
    out.sort(key=lambda x: x.get("year", 0), reverse=True)
    return out


def _evergreen_for(d: _date) -> list[dict]:
    item = EVERGREEN[d.toordinal() % len(EVERGREEN)]
    return [_decorate(item, "evergreen")]


def today_events(d: _date | None = None) -> list[dict]:
    """Always non-empty: exact -> near (<=3 days) -> rotating classic milestone."""
    d = d or _date.today()
    exact = events_for(d.month, d.day)
    if exact:
        return exact
    near = _nearest_in_month(d)
    if near and abs(int(near[0].get("near_day", d.day)) - d.day) <= 3:
        return near
    return _evergreen_for(d)


def day_label(events: list[dict], d: _date | None = None) -> str:
    d = d or _date.today()
    if not events:
        return f"{d.month} 月 {d.day} 日"
    match = events[0].get("match", "exact")
    if match == "exact":
        return f"{d.month} 月 {d.day} 日"
    if match == "near":
        nd = events[0].get("near_day", d.day)
        return f"{d.month} 月 {d.day} 日 · 近邻事件（本月 {nd} 日）"
    return f"{d.month} 月 {d.day} 日 · 经典里程碑（非特定日期）"


def summary_text(events: list[dict], max_items: int = 2) -> str:
    if not events:
        return "今天没有收录的条目。"
    return "；".join(f"{e['year']} · {e['title']}" for e in events[:max_items])


def _paragraphs(text: str) -> str:
    parts = (text or "").split("\n\n")
    return "".join(f'<p class="summary">{p.strip()}</p>' for p in parts if p.strip())


def render_section_html(events: list[dict], when: _date | None = None) -> str:
    if not events:
        return ""
    when = when or _date.today()
    label = day_label(events, when)
    cards = []
    for e in events:
        url = e.get("url", "")
        title = e["title"]
        title_html = (f'<a href="{url}" target="_blank" rel="noopener">{title}</a>'
                      if url else title)
        match = e.get("match", "exact")
        match_tag = ""
        if match == "near":
            match_tag = f'<span class="tag t">近邻（本月 {e.get("near_day", when.day)} 日）</span>'
        elif match == "evergreen":
            match_tag = '<span class="tag t">经典里程碑</span>'
        cards.append(
            '<details class="card otd-card" open>'
            '<summary><span class="chevron"></span><div class="card-main">'
            f'<h3>{title_html}</h3>'
            f'<div class="meta"><span class="badge b-doc">{e.get("kind_label", "历史事件")}</span>'
            f'<span class="tag tj">{e["year"]}</span>'
            f'<span class="tag t">{e.get("category_label", "")}</span>'
            f'{match_tag}</div>'
            '</div></summary>'
            f'<div class="card-body">{_paragraphs(e.get("body") or e.get("text", ""))}</div>'
            '</details>'
        )
    return (
        '<section>'
        '<div class="sec-head"><div>'
        f'<h2 class="sec-title"><span class="dot"></span>📅 历史上的今天'
        f'<span class="count">({label} · {len(events)})</span></h2>'
        '<p class="sec-desc">神经科学的历史，常由一次次关键发现、开创性手术与改变病程的新药写成。'
        '这里每天推送其中一件；若今日无精确记载，则推送最近事件或经典里程碑，并如实标注。</p>'
        '</div></div>'
        + "".join(cards)
        + '</section>'
    )


def is_enabled(cfg) -> bool:
    try:
        sched = getattr(cfg, "scheduled", None) or {}
        if isinstance(sched, dict):
            otd = sched.get("on_this_day")
            if isinstance(otd, dict):
                return bool(otd.get("enabled", True))
            if otd is False:
                return False
    except Exception:
        pass
    return True


def should_notify(cfg) -> bool:
    try:
        sched = getattr(cfg, "scheduled", None) or {}
        if isinstance(sched, dict):
            otd = sched.get("on_this_day")
            if isinstance(otd, dict):
                return bool(otd.get("notify", True))
    except Exception:
        pass
    return True
