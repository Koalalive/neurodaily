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
# Public API
# ---------------------------------------------------------------------------
def _decorate(e: dict, match: str) -> dict:
    item = dict(e)
    item["category_label"] = CATEGORY_LABELS.get(e.get("category", ""), e.get("category", ""))
    item["kind_label"] = KIND_LABELS.get(e.get("kind", ""), "历史事件")
    item["match"] = match
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
            f'<div class="card-body"><p class="summary">{e.get("text","")}</p></div>'
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
