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
EVERGREEN_MORE: list[dict] = [
    dict(year=1700, category="neurosurgery", kind="discovery", title="埃德温·史密斯纸草书", text="约公元前 1700 年的纸草书最早记载脑、脑膜与脊髓损伤，是神经外科与神经病学的共同源头。"),
    dict(year=-400, category="neurology", kind="discovery", title="希波克拉底《论圣病》", text="希波克拉底将癫痫归因于脑而非神罚，开启对癫痫的自然主义解释。"),
    dict(year=1543, category="neuroscience", kind="discovery", title="维萨里《人体构造》", text="Vesalius 以解剖实证纠正盖伦错误，为神经系统解剖奠定基础。"),
    dict(year=1664, category="neurology", kind="discovery", title="Willis《大脑解剖》", text="Thomas Willis 系统描述脑动脉环（Willis 环），被视为临床神经病学奠基之作。"),
    dict(year=1791, category="neuroscience", kind="discovery", title="伽伐尼发现动物电", text="Luigi Galvani 发现蛙腿肌肉的电刺激收缩，开启神经电生理研究。"),
    dict(year=1811, category="neuroscience", kind="discovery", title="贝尔—马金迪定律", text="Charles Bell 与 François Magendie 区分脊髓背根（感觉）与腹根（运动），确立神经通路分工。"),
    dict(year=1824, category="neuroscience", kind="discovery", title="Flourens 切除实验", text="Pierre Flourens 以动物切除实验研究小脑与脑干功能，推动实验神经科学。"),
    dict(year=1848, category="neurology", kind="discovery", title="Phineas Gage 事故", text="铁夯穿颅后幸存，成为额叶与人格关系的最早临床证据。"),
    dict(year=1861, category="neurology", kind="discovery", title="Broca 发现言语区", text="Paul Broca 通过失语症病例确立左额叶与言语产生的关系，开启脑功能定位。"),
    dict(year=1870, category="neuroscience", kind="discovery", title="Fritsch 与 Hitzig 电刺激皮层", text="两人以电流刺激狗大脑皮层诱发运动，奠定皮层运动定位的实验基础。"),
    dict(year=1873, category="neuroscience", kind="discovery", title="Golgi 银染法", text="Camillo Golgi 发明银染法，使神经元在显微镜下首次清晰可见。"),
    dict(year=1874, category="neurology", kind="discovery", title="Wernicke 描述感觉性失语", text="Carl Wernicke 发现左颞上回与语言理解相关，与 Broca 区共同构成失语症框架。"),
    dict(year=1879, category="neurosurgery", kind="surgery", title="Macewen 首例脑部病变手术", text="William Macewen 完成早期成功的脑部病变处理，标志现代神经外科开端。"),
    dict(year=1884, category="neurosurgery", kind="surgery", title="Godlee 首例脑肿瘤切除", text="在 Bennett 定位下开颅切除脑肿瘤，确立“定位—开颅—切除”范式。"),
    dict(year=1887, category="neurosurgery", kind="surgery", title="Horsley 首例脊髓肿瘤切除", text="Victor Horsley 完成脊髓肿瘤切除并开展实验性癫痫外科。"),
    dict(year=1888, category="neuroscience", kind="discovery", title="Cajal 神经元学说", text="Santiago Ramón y Cajal 以改良染色证明神经元是独立单元，确立神经元学说。"),
    dict(year=1895, category="neurology", kind="device", title="Röntgen 发现 X 射线", text="X 射线问世，为头颅影像与后来的 CT、神经影像学奠基。"),
    dict(year=1897, category="neurology", kind="discovery", title="Babinski 征", text="Joseph Babinski 描述巴宾斯基征，成为锥体束损害的核心体征。"),
    dict(year=1906, category="neuroscience", kind="discovery", title="Golgi 与 Cajal 获诺奖", text="两人因神经系统结构研究共享诺贝尔生理学或医学奖，神经元学说确立。"),
    dict(year=1906, category="neurology", kind="discovery", title="Alzheimer 报告首例病例", text="Alois Alzheimer 报告早老性痴呆病例，该病后以其姓氏命名。"),
    dict(year=1908, category="neurosurgery", kind="device", title="Horsley–Clarke 立体定向仪", text="立体定向技术诞生，成为功能神经外科与 DBS 的基石。"),
    dict(year=1908, category="psychiatry", kind="discovery", title="Bleuler 提出“精神分裂症”", text="Eugen Bleuler 以“精神分裂症”取代“早发性痴呆”，重塑精神病学分类。"),
    dict(year=1909, category="neurosurgery", kind="discovery", title="Cushing 电刺激人感觉皮层", text="Harvey Cushing 首次电刺激人类感觉皮层，推动术中功能定位。"),
    dict(year=1909, category="neuroscience", kind="discovery", title="Brodmann 52 区", text="Korbinian Brodmann 将皮层划分为 52 个细胞构筑区，沿用至今。"),
    dict(year=1910, category="neurology", kind="discovery", title="Kraepelin 命名阿尔茨海默病", text="Emil Kraepelin 将该病命名为阿尔茨海默病，纳入现代疾病分类。"),
    dict(year=1913, category="psychiatry", kind="discovery", title="Jaspers《普通精神病理学》", text="Karl Jaspers 以现象学方法描述精神症状，奠定现代精神病理学。"),
    dict(year=1918, category="neurosurgery", kind="device", title="Dandy 脑室造影", text="Walter Dandy 引入脑室造影，使颅内病变在术前可被间接显示。"),
    dict(year=1919, category="neurosurgery", kind="device", title="气脑造影", text="Dandy 引入气脑造影，成为 CT 之前的重要颅内成像手段。"),
    dict(year=1919, category="neuroscience", kind="discovery", title="del Río-Hortega 区分胶质细胞", text="Pío del Río-Hortega 将神经胶质分为小胶质与少突胶质，奠定胶质细胞学。"),
    dict(year=1920, category="neurosurgery", kind="discovery", title="美国神经外科医师学会成立", text="Society of Neurological Surgeons 成立，标志神经外科成为独立学科。"),
    dict(year=1921, category="neuroscience", kind="discovery", title="Loewi 发现 Vagusstoff", text="Otto Loewi 以蛙心实验证明化学性突触传递，开启神经递质研究。"),
    dict(year=1924, category="neurology", kind="device", title="Berger 记录人类脑电", text="Hans Berger 首次记录人类脑电图（EEG），开创临床神经电生理。"),
    dict(year=1926, category="neurosurgery", kind="discovery", title="Bailey–Cushing 胶质瘤分类", text="两人系统分类神经上皮肿瘤，奠定神经肿瘤病理学基础。"),
    dict(year=1928, category="neurosurgery", kind="discovery", title="美国首位女性神经外科医生", text="Dorothy Klenke Nash 成为美国首位执业女性神经外科医生。"),
    dict(year=1929, category="neurology", kind="discovery", title="Berger 发表 EEG 研究", text="Berger 正式发表人类脑电研究，EEG 逐步进入临床。"),
    dict(year=1932, category="neuroscience", kind="discovery", title="Sherrington 与 Adrian 获诺奖", text="两人因神经元功能研究共享诺贝尔奖，突触与反射弧概念确立。"),
    dict(year=1935, category="psychiatry", kind="surgery", title="Moniz 首创额叶切断术", text="Egas Moniz 首创额叶白质切断术，后获诺贝尔奖，亦成为精神外科的警示案例。"),
    dict(year=1936, category="neuroscience", kind="discovery", title="Dale 与 Loewi 获诺奖", text="两人因化学性突触传递研究共享诺贝尔奖。"),
    dict(year=1937, category="neuroscience", kind="discovery", title="Kluver–Bucy 综合征", text="双侧颞叶切除后出现视觉失认、情绪改变等综合征，推动颞叶功能研究。"),
    dict(year=1937, category="neuroscience", kind="discovery", title="Papez 环路", text="James Papez 提出情绪的边缘系统环路，成为情绪神经科学的基础。"),
    dict(year=1938, category="psychiatry", kind="device", title="电休克治疗（ECT）", text="Cerletti 与 Bini 引入 ECT，至今仍是难治性抑郁的有效物理治疗。"),
    dict(year=1944, category="psychiatry", kind="discovery", title="Kanner 描述自闭症", text="Leo Kanner 描述早期婴儿自闭症，奠定孤独症谱系研究。"),
    dict(year=1944, category="neuroscience", kind="discovery", title="Erlanger 与 Gasser 获诺奖", text="两人因单神经纤维功能研究共享诺贝尔奖。"),
    dict(year=1949, category="psychiatry", kind="drug", title="Cade 发现锂盐疗效", text="John Cade 发现锂盐的情绪稳定作用，开启现代精神药理学。"),
    dict(year=1949, category="psychiatry", kind="discovery", title="Moniz 获诺贝尔奖", text="Moniz 因额叶白质切断术获诺贝尔奖，成为精神外科最具争议的奖项。"),
    dict(year=1949, category="neuroscience", kind="discovery", title="Hess 获诺贝尔奖", text="Walter Hess 因间脑功能研究获诺贝尔奖。"),
    dict(year=1949, category="neuroscience", kind="discovery", title="Hebb《行为的组织》", text="Donald Hebb 提出突触可塑性假说，奠定学习与记忆的神经基础。"),
    dict(year=1949, category="psychiatry", kind="discovery", title="美国国家精神卫生研究所成立", text="NIMH 成立，推动精神疾病研究与公共卫生体系建设。"),
    dict(year=1952, category="psychiatry", kind="drug", title="氯丙嗪进入精神科", text="Delay 与 Deniker 引入氯丙嗪，首个抗精神病药，引发去机构化浪潮。"),
    dict(year=1953, category="neuroscience", kind="discovery", title="H.M. 与海马记忆研究", text="患者 H.M. 双侧内侧颞叶切除后出现严重遗忘，确立海马在记忆巩固中的作用。"),
    dict(year=1954, category="psychiatry", kind="drug", title="氯丙嗪获 FDA 批准", text="氯丙嗪在美国获批，精神科药物治疗进入新时代。"),
    dict(year=1955, category="psychiatry", kind="drug", title="哌甲酯进入临床", text="哌甲酯用于注意缺陷与发作性睡病，成为中枢兴奋剂的代表。"),
    dict(year=1957, category="neuroscience", kind="discovery", title="Carlsson 证明多巴胺是递质", text="Arvid Carlsson 证明多巴胺为中枢神经递质，为帕金森治疗与抗精神病药机制奠基。"),
    dict(year=1963, category="neuroscience", kind="discovery", title="Hodgkin–Huxley 获诺奖", text=" Hodgkin、Huxley 与 Eccles 因神经冲动与突触机制研究获诺贝尔奖。"),
    dict(year=1967, category="neuroscience", kind="discovery", title="视觉生理获诺奖", text="Granit、Hartline 与 Wald 因视觉生理研究获诺贝尔奖。"),
    dict(year=1970, category="neurology", kind="drug", title="左旋多巴治疗帕金森病", text="左旋多巴进入临床，成为帕金森病治疗的基石。"),
    dict(year=1970, category="neuroscience", kind="discovery", title="神经递质研究获诺奖", text="Katz、von Euler 与 Axelrod 因神经递质机制研究获诺贝尔奖。"),
    dict(year=1971, category="neurosurgery", kind="device", title="首例头颅 CT", text="Hounsfield 与 Ambrose 完成首例活体头颅 CT，神经影像进入断层时代。"),
    dict(year=1973, category="neurology", kind="device", title="MRI 原理提出", text="Lauterbur 与 Mansfield 提出磁场梯度空间编码，奠定 MRI 基础。"),
    dict(year=1973, category="neuroscience", kind="discovery", title="阿片受体被发现", text="Pert 与 Snyder 证实脑内阿片受体，推动疼痛与成瘾研究。"),
    dict(year=1975, category="neuroscience", kind="discovery", title="内啡肽被发现", text="Hughes 与 Kosterlitz 等发现内源性阿片肽，开启内源性镇痛研究。"),
    dict(year=1977, category="neurology", kind="device", title="首例人体 MRI 扫描", text="Damadian 团队完成首例人体全身 MRI 扫描，为临床 MRI 铺路。"),
    dict(year=1979, category="neurosurgery", kind="discovery", title="CT 获诺贝尔奖", text="Hounsfield 与 Cormack 因 CT 获诺贝尔生理学或医学奖。"),
    dict(year=1980, category="psychiatry", kind="discovery", title="DSM-III 出版", text="DSM-III 引入可操作诊断标准，成为现代精神科诊断标准化的分水岭。"),
    dict(year=1981, category="neuroscience", kind="discovery", title="裂脑与视觉研究获诺奖", text="Sperry、Hubel 与 Wiesel 因半球分工与视觉皮层研究获诺贝尔奖。"),
    dict(year=1985, category="neuroscience", kind="device", title="经颅磁刺激（TMS）", text="Barker 等演示 TMS，开启无创脑调控时代。"),
    dict(year=1986, category="neuroscience", kind="discovery", title="神经生长因子获诺奖", text="Levi-Montalcini 与 Cohen 因发现 NGF 获诺贝尔奖。"),
    dict(year=1987, category="neurosurgery", kind="device", title="脑深部电刺激（DBS）", text="Benabid 发现高频深部电刺激抑制帕金森震颤，DBS 由此诞生。"),
    dict(year=1987, category="psychiatry", kind="drug", title="氟西汀（Prozac）获批", text="首个广泛使用的 SSRI 获批，改变抑郁症门诊治疗格局。"),
    dict(year=1989, category="psychiatry", kind="drug", title="氯氮平用于难治性精神分裂症", text="氯氮平显著改善难治性症状，但需监测粒细胞缺乏。"),
    dict(year=1990, category="neuroscience", kind="device", title="fMRI 兴起", text="基于 BOLD 的 fMRI 普及，使活体人脑功能成像成为常规。"),
    dict(year=1991, category="neuroscience", kind="discovery", title="膜片钳技术获诺奖", text="Neher 与 Sakmann 因膜片钳技术获诺贝尔奖，推动离子通道研究。"),
    dict(year=1992, category="neurology", kind="drug", title="舒马曲普坦获批", text="曲普坦类用于偏头痛急性治疗，改善急性期镇痛。"),
    dict(year=1993, category="neurology", kind="drug", title="干扰素 β-1b 获批", text="首个多发性硬化疾病修饰治疗获批。"),
    dict(year=1994, category="neuroscience", kind="discovery", title="G 蛋白研究获诺奖", text="Gilman 与 Rodbell 因 G 蛋白信号转导研究获诺贝尔奖。"),
    dict(year=1995, category="neurology", kind="drug", title="tPA 静脉溶栓治疗卒中", text="NINDS 试验确立 tPA 溶栓，改写急性缺血性卒中急救。"),
    dict(year=1995, category="neurology", kind="drug", title="利鲁唑获批", text="首个 ALS 药物利鲁唑获批。"),
    dict(year=1996, category="neurology", kind="drug", title="多奈哌齐获批", text="胆碱酯酶抑制剂多奈哌齐获批，成为阿尔茨海默病常用药。"),
    dict(year=1997, category="neurosurgery", kind="device", title="DBS 获 FDA 批准", text="DBS 用于帕金森病与特发性震颤，功能神经外科进入电刺激时代。"),
    dict(year=1997, category="neuroscience", kind="discovery", title="朊病毒研究获诺奖", text="Stanley Prusiner 因朊病毒研究获诺贝尔奖，重塑神经退行病因学。"),
    dict(year=1997, category="neurology", kind="device", title="迷走神经刺激治疗癫痫", text="VNS 获批用于难治性癫痫，成为神经调控的重要分支。"),
    dict(year=1998, category="psychiatry", kind="drug", title="莫达非尼获批", text="莫达非尼用于发作性睡病相关嗜睡，推动促觉醒药物研究。"),
    dict(year=1999, category="neurology", kind="drug", title="左乙拉西坦获批", text="左乙拉西坦经 SV2A 机制成为广谱抗癫痫药。"),
    dict(year=2000, category="neuroscience", kind="discovery", title="多巴胺与记忆研究获诺奖", text="Carlsson、Greengard 与 Kandel 因神经系统信号转导与记忆机制获诺贝尔奖。"),
    dict(year=2002, category="psychiatry", kind="drug", title="托莫西汀获批", text="首个非兴奋剂类 ADHD 药物获批。"),
    dict(year=2003, category="neurology", kind="discovery", title="MRI 获诺贝尔奖", text="Lauterbur 与 Mansfield 因 MRI 获诺贝尔生理学或医学奖。"),
    dict(year=2003, category="neurology", kind="drug", title="美金刚获批", text="NMDA 受体拮抗剂美金刚获批用于中重度阿尔茨海默病。"),
    dict(year=2004, category="neuroscience", kind="discovery", title="嗅觉受体研究获诺奖", text="Axel 与 Buck 因嗅觉受体研究获诺贝尔奖。"),
    dict(year=2004, category="neurology", kind="drug", title="那他珠单抗获批", text="抗 α4-整合素单抗获批用于多发性硬化，后因 PML 风险受严格监测。"),
    dict(year=2005, category="neuroscience", kind="device", title="光遗传学问世", text="Boyden 与 Deisseroth 等开发光遗传学，实现神经元精准光控。"),
    dict(year=2005, category="psychiatry", kind="device", title="VNS 获批治疗抑郁", text="迷走神经刺激获 FDA 批准用于难治性抑郁。"),
    dict(year=2006, category="psychiatry", kind="drug", title="伐尼克兰获批", text="部分烟碱受体激动剂用于戒烟，成为戒烟药物里程碑。"),
    dict(year=2007, category="psychiatry", kind="drug", title="赖氨酸安非他命获批", text="前药型兴奋剂用于 ADHD，后扩展至暴食症。"),
    dict(year=2008, category="neurology", kind="drug", title="丁苯那嗪获批", text="首个用于亨廷顿病舞蹈症的药物获批。"),
    dict(year=2008, category="neurology", kind="drug", title="拉考沙胺获批", text="作用于钠通道慢失活的抗癫痫药获批。"),
    dict(year=2010, category="neurology", kind="drug", title="芬戈莫德获批", text="首个口服多发性硬化疾病修饰治疗获批。"),
    dict(year=2012, category="neurology", kind="drug", title="吡仑帕奈获批", text="首个 AMPA 受体拮抗剂类抗癫痫药获批。"),
    dict(year=2013, category="neuroscience", kind="discovery", title="美国 BRAIN Initiative 启动", text="大规模脑图谱计划启动，推动神经技术与人脑绘图。"),
    dict(year=2013, category="neuroscience", kind="device", title="CLARITY 组织透明化", text="CLARITY 使完整脑组织透明化并保留分子信息，推动全脑成像。"),
    dict(year=2014, category="psychiatry", kind="drug", title="苏沃雷生获批", text="首个食欲素受体拮抗剂类安眠药获批。"),
    dict(year=2014, category="neuroscience", kind="discovery", title="位置细胞与网格细胞获诺奖", text="O'Keefe、Moser 夫妇因空间导航的脑机制获诺贝尔奖。"),
    dict(year=2015, category="neurology", kind="discovery", title="机械取栓改写卒中治疗", text="MR CLEAN 等试验证实大血管闭塞取栓有效，成为卒中新标准。"),
    dict(year=2016, category="neurology", kind="drug", title="匹莫范色林获批", text="首个选择性 5-HT2A 反向激动剂，用于帕金森病精神病。"),
    dict(year=2016, category="neurology", kind="drug", title="诺西那生获批", text="首个 SMA 反义寡核苷酸药物获批。"),
    dict(year=2017, category="neurology", kind="drug", title="奥瑞利珠单抗获批", text="首个获批用于原发进展型 MS 的疾病修饰治疗。"),
    dict(year=2017, category="neurology", kind="drug", title="依达拉奉获批", text="抗氧化剂依达拉奉获批用于 ALS。"),
    dict(year=2017, category="psychiatry", kind="drug", title="缬苯那嗪获批", text="首个 VMAT2 抑制剂，用于迟发性运动障碍。"),
    dict(year=2017, category="neuroscience", kind="discovery", title="昼夜节律获诺奖", text="Hall、Rosbash 与 Young 因昼夜节律分子机制获诺贝尔奖。"),
    dict(year=2018, category="neurology", kind="drug", title="CGRP 单抗密集获批", text=" erenumab、fremanezumab、galcanezumab 相继获批，偏头痛进入生物制剂时代。"),
    dict(year=2018, category="neurology", kind="drug", title="大麻二酚获批", text="首个大麻来源药物用于 Dravet 与 Lennox–Gastaut 综合征。"),
    dict(year=2018, category="neurology", kind="drug", title="司替戊醇获批", text="用于 Dravet 综合征相关发作的辅助治疗。"),
    dict(year=2019, category="psychiatry", kind="drug", title="艾司氯胺酮获批", text="首个新机制快速抗抑郁药，用于治疗抵抗性抑郁。"),
    dict(year=2019, category="psychiatry", kind="drug", title="布瑞诺龙获批", text="首个专门针对产后抑郁的药物获批。"),
    dict(year=2019, category="neurology", kind="drug", title="佐尔根斯马获批", text="首个体内基因替代疗法之一，用于 SMA。"),
    dict(year=2019, category="neurology", kind="drug", title="乌布吉泮获批", text="口服 CGRP 受体拮抗剂用于偏头痛急性治疗。"),
    dict(year=2019, category="neurology", kind="drug", title="西诺贝酯获批", text="用于成人局灶性癫痫的高疗效抗癫痫药。"),
    dict(year=2020, category="neurology", kind="drug", title="芬氟拉明获批", text="用于 Dravet 综合征相关发作。"),
    dict(year=2020, category="neurology", kind="drug", title="瑞美吉泮获批", text="口服 CGRP 受体拮抗剂用于偏头痛。"),
    dict(year=2021, category="neurology", kind="drug", title="阿杜那单抗获加速批准", text="近二十年首个抗淀粉样蛋白新药，引发巨大争议。"),
    dict(year=2021, category="neurology", kind="drug", title="阿托吉泮获批", text="口服 CGRP 受体拮抗剂用于偏头痛预防。"),
    dict(year=2021, category="neuroscience", kind="discovery", title="温度与触觉受体获诺奖", text="Julius 与 Patapoutian 因发现温度和机械感受器获诺贝尔奖。"),
    dict(year=2022, category="psychiatry", kind="drug", title="右美沙芬/安非他酮获批", text="含 NMDA 拮抗机制的口服快速起效抗抑郁复方获批。"),
    dict(year=2022, category="psychiatry", kind="drug", title="达利雷生获批", text="双重食欲素受体拮抗剂用于失眠。"),
    dict(year=2023, category="neurology", kind="drug", title="仑卡奈单抗获批", text="抗 Aβ 单抗获加速并转常规批准，用于早期阿尔茨海默病。"),
    dict(year=2023, category="psychiatry", kind="drug", title="祖拉诺龙获批", text="口服神经甾体用于产后抑郁。"),
    dict(year=2023, category="neurology", kind="drug", title="托夫生获批", text="首个针对 SOD1 突变型 ALS 的反义寡核苷酸药物。"),
    dict(year=2024, category="neurology", kind="drug", title="多奈单抗获批", text="抗 Aβ 单抗用于早期阿尔茨海默病，采用达标停药策略。"),
    dict(year=2024, category="psychiatry", kind="drug", title="Cobenfy 获批", text="首个不依赖 D2 阻断的抗精神病药（毒蕈碱 M1/M4 激动）。"),
]


EVERGREEN_MORE2: list[dict] = [
    dict(year=1883, category="psychiatry", kind="discovery", title="Kraepelin 现代精神疾病分类", text="Emil Kraepelin 区分早发性痴呆与躁郁症，奠定现代精神疾病分类框架。"),
    dict(year=1897, category="neuroscience", kind="discovery", title="Sherrington 提出“突触”", text="Charles Sherrington 提出 synapse 概念，为神经元间信息传递提供结构基础。"),
    dict(year=1900, category="neuroscience", kind="discovery", title="“血脑屏障”概念提出", text="Lewandowsky 提出血脑屏障概念，解释中枢与外周物质交换的选择性。"),
    dict(year=1904, category="neuroscience", kind="discovery", title="Pavlov 获诺贝尔奖", text="Ivan Pavlov 因消化生理研究获诺贝尔奖，其条件反射成为学习研究基石。"),
    dict(year=1905, category="neuroscience", kind="discovery", title="Langley 提出受体概念", text="John Langley 提出受体分子概念，为神经药理学奠基。"),
    dict(year=1913, category="neuroscience", kind="discovery", title="Goldmann 证实血脑屏障", text="Edwin Goldmann 以染料实验证实血脑屏障对大分子的不通透性。"),
    dict(year=1914, category="neurology", kind="discovery", title="Bárány 获诺贝尔奖", text="Robert Bárány 因前庭器官研究获诺贝尔奖，奠定眩晕与平衡的生理学。"),
    dict(year=1930, category="neuroscience", kind="discovery", title="诱发电位技术兴起", text="1930 年代诱发电位记录技术发展，使感觉通路功能可被客观测量。"),
    dict(year=1950, category="neuroscience", kind="discovery", title="单细胞记录兴起", text="1950 年代微电极单细胞记录普及，使神经元放电与刺激—反应关系可被直接观测。"),
    dict(year=1957, category="neuroscience", kind="discovery", title="Mountcastle 皮层柱", text="Vernon Mountcastle 发现皮层功能柱组织，影响后续感觉皮层研究。"),
    dict(year=1967, category="psychiatry", kind="drug", title="氟哌啶醇获批", text="氟哌啶醇成为经典抗精神病药代表，广泛用于精神病性症状。"),
    dict(year=1970, category="psychiatry", kind="drug", title="锂盐获 FDA 批准", text="锂盐获批用于躁狂，成为双相障碍治疗的基石。"),
    dict(year=1975, category="neurology", kind="drug", title="左旋多巴/卡比多巴复方", text="复方制剂减少外周代谢，提升帕金森病治疗的有效性与耐受性。"),
    dict(year=1976, category="neuroscience", kind="device", title="膜片钳技术", text="Neher 与 Sakmann 发展膜片钳，使单离子通道电流可被记录。"),
    dict(year=1984, category="psychiatry", kind="drug", title="纳曲酮获批", text="阿片受体拮抗剂纳曲酮用于阿片与酒精依赖，推动成瘾药物治疗。"),
    dict(year=1990, category="psychiatry", kind="discovery", title="SSRI 时代", text="1990 年代 SSRI 广泛使用，抑郁症门诊治疗与公众认知显著改变。"),
    dict(year=1993, category="psychiatry", kind="drug", title="利培酮获批", text="利培酮等非典型抗精神病药降低锥体外系反应，改变精神分裂症治疗。"),
    dict(year=1994, category="neurology", kind="drug", title="醋酸格拉替雷获批", text="格拉替雷成为多发性硬化的注射型疾病修饰治疗之一。"),
    dict(year=1994, category="psychiatry", kind="discovery", title="DSM-IV 出版", text="DSM-IV 细化诊断标准，成为临床与研究广泛使用的分类系统。"),
    dict(year=1996, category="psychiatry", kind="drug", title="奥氮平获批", text="奥氮平成为广泛使用的非典型抗精神病药。"),
    dict(year=2000, category="psychiatry", kind="discovery", title="非典型抗精神病药普及", text="2000 年代非典型抗精神病药成为主流，代谢副作用受到重视。"),
    dict(year=2002, category="psychiatry", kind="drug", title="阿立哌唑获批", text="阿立哌唑以部分 D2 激动机制获批，拓展抗精神病药药理谱。"),
    dict(year=2006, category="neuroscience", kind="discovery", title="诱导多能干细胞（iPSC）", text="Yamanaka 发现 iPSC，为神经疾病建模与细胞治疗开辟新路径。"),
    dict(year=2006, category="psychiatry", kind="drug", title="帕利哌酮获批", text="帕利哌酮作为利培酮活性代谢物获批，提供长效注射选项。"),
    dict(year=2007, category="neuroscience", kind="device", title="化学遗传学 DREADDs", text="DREADDs 实现用惰性小分子远程控制神经元活动，成为环路研究利器。"),
    dict(year=2009, category="psychiatry", kind="drug", title="伊潘立酮获批", text="伊潘立酮获批用于精神分裂症，丰富非典型抗精神病药选择。"),
    dict(year=2009, category="neurosurgery", kind="device", title="DBS 治疗强迫症", text="DBS 获 FDA 人道主义器械豁免用于难治性强迫症。"),
    dict(year=2010, category="psychiatry", kind="drug", title="鲁拉西酮获批", text="鲁拉西酮获批用于精神分裂症与双相抑郁。"),
    dict(year=2010, category="neuroscience", kind="discovery", title="单细胞转录组兴起", text="2010 年代单细胞测序揭示神经细胞的分子多样性。"),
    dict(year=2012, category="neuroscience", kind="discovery", title="UK Biobank 神经影像", text="大规模人群神经影像与多组学数据推动脑科学进入大数据时代。"),
    dict(year=2013, category="psychiatry", kind="discovery", title="DSM-5 出版", text="DSM-5 调整诊断类别与维度，反映精神疾病分类的持续演进。"),
    dict(year=2013, category="neuroscience", kind="device", title="人脑类器官", text="Lancaster 等建立人脑类器官，为发育与疾病建模提供体外平台。"),
    dict(year=2013, category="neuroscience", kind="device", title="CRISPR 用于神经研究", text="CRISPR 基因编辑进入神经科学，加速疾病模型与功能筛选。"),
    dict(year=2015, category="psychiatry", kind="drug", title="依匹哌唑获批", text="依匹哌唑获批用于精神分裂症与抑郁辅助治疗。"),
    dict(year=2015, category="psychiatry", kind="drug", title="卡利拉嗪获批", text="卡利拉嗪以 D3 高亲和力获批用于精神分裂症与双相躁狂。"),
    dict(year=2017, category="psychiatry", kind="drug", title="氘代丁苯那嗪获批", text="氘代丁苯那嗪获批用于迟发性运动障碍与亨廷顿病舞蹈症。"),
    dict(year=2017, category="neuroscience", kind="device", title="时间干涉刺激（TI）", text="Grossman 等提出 TI，可无创深部电刺激，突破传统 tDCS 深度限制。"),
    dict(year=2018, category="neurology", kind="discovery", title="血液 NfL 标志物", text="神经丝轻链（NfL）作为神经轴索损伤标志，广泛用于 MS、ALS 等研究。"),
    dict(year=2019, category="psychiatry", kind="drug", title="鲁美哌隆获批", text="鲁美哌隆获批用于精神分裂症，强调较低代谢副作用。"),
    dict(year=2019, category="psychiatry", kind="drug", title="莱博雷生获批", text="食欲素受体拮抗剂莱博雷生获批用于失眠。"),
    dict(year=2020, category="neuroscience", kind="discovery", title="空间转录组兴起", text="空间转录组让脑组织的基因表达与空间位置对应，推动脑图谱精细化。"),
    dict(year=2020, category="neurology", kind="discovery", title="血液 p-tau 标志物", text="血浆 p-tau 检测在阿尔茨海默病诊断与筛查中展现潜力。"),
    dict(year=2021, category="psychiatry", kind="discovery", title="MDMA 辅助治疗 PTSD 三期试验", text="MDMA 辅助心理治疗在 PTSD 三期试验中显示积极结果，引发监管讨论。"),
    dict(year=2022, category="psychiatry", kind="discovery", title="DSM-5-TR 出版", text="DSM-5-TR 修订文本，更新诊断描述与编码。"),
    dict(year=2022, category="neurosurgery", kind="device", title="聚焦超声开放血脑屏障进入临床研究", text="低强度聚焦超声联合微泡开放血脑屏障，为中枢递药提供新途径。"),
    dict(year=2023, category="psychiatry", kind="discovery", title="迷幻药治疗研究扩展", text="裸盖菇素等迷幻药在抑郁、成瘾等领域的临床试验持续扩展。"),
    dict(year=2024, category="neurology", kind="discovery", title="抗 Aβ 进入常规临床", text="抗淀粉样蛋白单抗在部分国家进入常规诊疗路径，标志 AD 治疗模式转变。"),
    dict(year=2010, category="neuroscience", kind="discovery", title="连接组学", text="2010 年代连接组学以大规模神经连接图谱理解脑网络组织。"),
    dict(year=2010, category="neurosurgery", kind="device", title="脑机接口临床进展", text="2010 年代脑机接口在瘫痪患者运动与沟通辅助上取得临床进展。"),
]


EVERGREEN_MORE3: list[dict] = [
    dict(year=1950, category="psychiatry", kind="discovery", title="精神外科的衰退", text="1950 年代额叶切断术因疗效与伦理问题逐步被弃用，成为医学史上重要的反思。"),
    dict(year=1959, category="neuroscience", kind="discovery", title="Hubel 与 Wiesel 视觉皮层研究", text="两人开始记录视觉皮层单细胞反应，揭示感受野与方位选择性。"),
    dict(year=1960, category="psychiatry", kind="discovery", title="去机构化浪潮", text="1960 年代抗精神病药普及与政策调整推动精神科去机构化，社区服务兴起。"),
    dict(year=1972, category="neurosurgery", kind="device", title="CT 扫描仪商业化", text="EMI 扫描仪进入市场，CT 从实验室走向全球医院。"),
    dict(year=1970, category="neuroscience", kind="discovery", title="神经影像革命开启", text="1970 年代 CT 与 MRI 相继问世，脑结构与病变首次可无创可视化。"),
    dict(year=1980, category="neuroscience", kind="discovery", title="分子神经生物学兴起", text="1980 年代受体克隆与分子技术发展，神经递质与受体的分子机制被阐明。"),
    dict(year=1990, category="neuroscience", kind="discovery", title="认知神经科学成型", text="1990 年代功能影像与认知实验结合，认知神经科学成为独立学科。"),
    dict(year=1990, category="psychiatry", kind="discovery", title="循证精神医学", text="1990 年代循证医学理念进入精神科，随机试验与系统综述成为决策依据。"),
    dict(year=2000, category="neurosurgery", kind="device", title="神经调控兴起", text="2000 年代 TMS、DBS、VNS 等神经调控技术扩展至精神与神经疾病。"),
    dict(year=2000, category="neuroscience", kind="device", title="光遗传学普及", text="2000 年代光遗传学成为环路因果研究的标准工具。"),
    dict(year=2010, category="neuroscience", kind="discovery", title="单细胞与空间组学", text="2010 年代单细胞与空间转录组推动脑细胞图谱与疾病机制研究。"),
    dict(year=2010, category="psychiatry", kind="discovery", title="免疫精神病学兴起", text="2010 年代神经免疫与炎症机制被引入精神疾病研究。"),
    dict(year=2010, category="neuroscience", kind="discovery", title="脑连接组计划", text="2010 年代连接组学以大规模图谱刻画脑网络的拓扑与个体差异。"),
    dict(year=2010, category="neuroscience", kind="discovery", title="神经影像大数据", text="2010 年代多中心大队列影像数据推动规范化与可重复性研究。"),
    dict(year=2010, category="neuroscience", kind="device", title="类器官与疾病建模", text="2010 年代人源类器官用于神经发育与疾病建模，补充动物模型。"),
    dict(year=2020, category="neurology", kind="discovery", title="血液生物标志物时代", text="2020 年代血液 p-tau、NfL、GFAP 等标志物推动神经疾病早筛与分层。"),
    dict(year=2020, category="neurology", kind="drug", title="抗 Aβ 疗法时代", text="2020 年代抗淀粉样蛋白单抗进入临床，AD 治疗转向生物学分期与靶向干预。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="迷幻药研究复兴", text="2020 年代裸盖菇素、MDMA 等迷幻药在精神疾病中的临床试验快速扩展。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="数字表型与 AI", text="2020 年代语音、可穿戴与机器学习用于精神症状监测与预测。"),
    dict(year=2020, category="neurology", kind="drug", title="神经基因治疗", text="2020 年代 SMA、ALS 等疾病的基因与反义寡核苷酸疗法进入临床。"),
    dict(year=2020, category="psychiatry", kind="drug", title="非多巴胺抗精神病药", text="2020 年代毒蕈碱机制药物获批，挑战 D2 阻断的长期教条。"),
    dict(year=2020, category="neurosurgery", kind="device", title="脑机接口临床化", text="2020 年代脑机接口在瘫痪与沟通辅助中的临床试验加速。"),
]


PSYCH_BATCH: list[dict] = [
    dict(year=1844, category="psychiatry", kind="discovery", title="美国精神病学会前身成立", text="美国精神病院管理者协会成立，后演变为美国精神病学会（APA）。"),
    dict(year=1895, category="psychiatry", kind="discovery", title="弗洛伊德《癔症研究》", text="弗洛伊德与布洛伊尔出版《癔症研究》，精神分析由此发端。"),
    dict(year=1900, category="psychiatry", kind="discovery", title="弗洛伊德《梦的解析》", text="《梦的解析》提出梦是愿望的满足，奠定精神分析理论核心。"),
    dict(year=1913, category="psychiatry", kind="discovery", title="华生行为主义宣言", text="John Watson 提出行为主义，主张心理学研究可观测行为。"),
    dict(year=1920, category="psychiatry", kind="discovery", title="精神分析传播", text="1920 年代精神分析在欧美扩散，深刻影响精神病学与人文领域。"),
    dict(year=1933, category="psychiatry", kind="discovery", title="胰岛素休克疗法", text="Manfred Sakel 引入胰岛素休克疗法治疗精神分裂症，后被淘汰。"),
    dict(year=1943, category="psychiatry", kind="discovery", title="LSD 首次合成", text="Albert Hofmann 合成麦角酸二乙酰胺（LSD），后成为精神药理学与迷幻药研究起点。"),
    dict(year=1950, category="psychiatry", kind="discovery", title="罗杰斯以人为中心疗法", text="Carl Rogers 发展以人为中心的心理治疗，强调共情与无条件积极关注。"),
    dict(year=1952, category="psychiatry", kind="drug", title="异烟肼类抗抑郁发现", text="异烟肼类药物的情绪提升效应被观察到，催生单胺氧化酶抑制剂（MAOI）。"),
    dict(year=1955, category="psychiatry", kind="drug", title="甲丙氨酯上市", text="甲丙氨酯作为抗焦虑药广泛使用，后因依赖性问题受限。"),
    dict(year=1957, category="psychiatry", kind="drug", title="丙米嗪抗抑郁", text="丙米嗪作为首个三环类抗抑郁药进入临床，开启单胺类抗抑郁治疗。"),
    dict(year=1958, category="psychiatry", kind="drug", title="氟哌啶醇在欧洲上市", text="氟哌啶醇以强效 D2 拮抗成为经典抗精神病药。"),
    dict(year=1958, category="psychiatry", kind="discovery", title="精神药理学成为学科", text="氯丙嗪与锂盐等药物推动精神药理学成为独立研究方向。"),
    dict(year=1960, category="psychiatry", kind="drug", title="氯氮卓上市", text="首个苯二氮卓类抗焦虑药上市，取代部分巴比妥类。"),
    dict(year=1960, category="psychiatry", kind="discovery", title="贝克认知疗法", text="Aaron Beck 发展认知疗法，强调负性自动思维在抑郁中的作用。"),
    dict(year=1961, category="psychiatry", kind="discovery", title="氯氮平合成", text="氯氮平被合成，后来成为首个用于难治性精神分裂症的 atypical 药物。"),
    dict(year=1963, category="psychiatry", kind="discovery", title="美国社区精神卫生法案", text="肯尼迪签署法案，推动去机构化与社区精神卫生服务。"),
    dict(year=1963, category="psychiatry", kind="drug", title="地西泮上市", text="地西泮成为最广泛使用的苯二氮卓类之一，用于焦虑与癫痫。"),
    dict(year=1965, category="psychiatry", kind="discovery", title="单胺假说提出", text="Schildkraut 等提出抑郁症的单胺假说，主导抗抑郁药研发数十年。"),
    dict(year=1967, category="psychiatry", kind="drug", title="氟哌啶醇获 FDA 批准", text="氟哌啶醇在美国获批，成为急诊与长期治疗常用抗精神病药。"),
    dict(year=1973, category="psychiatry", kind="discovery", title="氯氮平粒细胞缺乏报告", text="氯氮平相关粒细胞缺乏被报道，导致其一度撤市并促成血象监测制度。"),
    dict(year=1975, category="psychiatry", kind="drug", title="氟奋乃静长效制剂", text="长效抗精神病药改善依从性，成为社区治疗的重要工具。"),
    dict(year=1979, category="psychiatry", kind="discovery", title="NAMI 成立", text="美国家庭倡导组织 NAMI 成立，推动精神疾病去污名与政策倡导。"),
    dict(year=1979, category="psychiatry", kind="discovery", title="正念减压（MBSR）", text="Jon Kabat-Zinn 创立 MBSR，把正念引入身心医学与心理治疗。"),
    dict(year=1981, category="psychiatry", kind="drug", title="阿普唑仑上市", text="阿普唑仑用于惊恐障碍，成为高效但需警惕依赖的苯二氮卓类。"),
    dict(year=1986, category="psychiatry", kind="drug", title="丁螺环酮上市", text="丁螺环酮作为非苯二氮卓类抗焦虑药，减少依赖风险。"),
    dict(year=1988, category="psychiatry", kind="drug", title="氟西汀全球上市", text="氟西汀在多国上市，SSRI 成为抑郁症一线治疗。"),
    dict(year=1989, category="psychiatry", kind="drug", title="氯氮平获 FDA 批准", text="氯氮平用于难治性精神分裂症，需定期监测白细胞。"),
    dict(year=1989, category="psychiatry", kind="discovery", title="EMDR 问世", text="眼动脱敏与再加工（EMDR）被用于创伤后应激障碍。"),
    dict(year=1990, category="psychiatry", kind="discovery", title="精神分裂症神经发育假说", text="神经发育假说强调早期脑发育异常在精神分裂症中的作用。"),
    dict(year=1991, category="psychiatry", kind="drug", title="舍曲林获批", text="舍曲林成为广泛使用的 SSRI，覆盖抑郁、焦虑与强迫。"),
    dict(year=1992, category="psychiatry", kind="drug", title="帕罗西汀获批", text="帕罗西汀获批，SSRI 家族进一步扩展。"),
    dict(year=1993, category="psychiatry", kind="discovery", title="辩证行为疗法（DBT）", text="Marsha Linehan 提出 DBT，成为边缘型人格障碍的循证治疗。"),
    dict(year=1997, category="psychiatry", kind="drug", title="喹硫平获批", text="喹硫平获批用于精神分裂症与双相障碍。"),
    dict(year=2000, category="psychiatry", kind="discovery", title="精神疾病 GWAS 时代", text="2000 年代全基因组关联研究开始系统解析精神疾病的遗传基础。"),
    dict(year=2001, category="psychiatry", kind="drug", title="齐拉西酮获批", text="齐拉西酮获批，强调较少体重增加的药理特征。"),
    dict(year=2002, category="psychiatry", kind="drug", title="艾司西酞普兰获批", text="艾司西酞普兰成为高选择性 SSRI，广泛用于抑郁与焦虑。"),
    dict(year=2002, category="psychiatry", kind="discovery", title="正念认知疗法（MBCT）", text="MBCT 被证实可降低抑郁复发风险，进入主流循证治疗。"),
    dict(year=2004, category="psychiatry", kind="drug", title="度洛西汀获批", text="度洛西汀作为 SNRI 用于抑郁与神经病理性疼痛。"),
    dict(year=2005, category="psychiatry", kind="discovery", title="精神疾病 GWAS 突破", text="多项 GWAS 识别精神分裂症与双相障碍的风险位点。"),
    dict(year=2008, category="psychiatry", kind="device", title="TMS 获 FDA 批准治疗抑郁", text="经颅磁刺激获批用于难治性抑郁，非侵入神经调控进入精神科。"),
    dict(year=2008, category="psychiatry", kind="discovery", title="美国精神卫生 parity 法案", text="精神健康平等法案要求保险对精神疾病与躯体疾病同等覆盖。"),
    dict(year=2009, category="psychiatry", kind="drug", title="阿塞那平获批", text="阿塞那平获批用于精神分裂症与双相躁狂。"),
    dict(year=2010, category="psychiatry", kind="discovery", title="NIMH 启动 RDoC", text="研究领域标准（RDoC）以维度化生物学指标替代传统诊断类别。"),
    dict(year=2010, category="psychiatry", kind="discovery", title="早期干预精神病", text="2010 年代高危精神病早期识别与干预服务逐步推广。"),
    dict(year=2013, category="psychiatry", kind="discovery", title="RDoC 正式推行", text="RDoC 框架推动精神科研究从症状分类转向机制维度。"),
    dict(year=2015, category="psychiatry", kind="discovery", title="精准精神医学", text="2015 年前后精准精神医学强调生物标志、个体化选药与分层治疗。"),
    dict(year=2016, category="psychiatry", kind="discovery", title="数字表型", text="智能手机与可穿戴设备用于精神症状的连续监测与预测。"),
    dict(year=2017, category="psychiatry", kind="discovery", title="迷幻药研究复兴", text="裸盖菇素与 MDMA 的临床试验在抑郁、PTSD 等领域加速。"),
    dict(year=2018, category="psychiatry", kind="discovery", title="精神科 AI 辅助", text="机器学习用于精神疾病风险预测、分型与治疗反应估计。"),
    dict(year=2019, category="psychiatry", kind="drug", title="快速抗抑郁进入临床", text="艾司氯胺酮获批后，快速起效抗抑郁成为精神科新目标。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="疫情与心理健康", text="COVID-19 大流行凸显精神健康服务与远程医疗的重要性。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="远程精神医学普及", text="远程诊疗扩大精神卫生服务可及性，尤其惠及偏远地区。"),
    dict(year=2021, category="psychiatry", kind="discovery", title="迷幻药三期试验", text="MDMA 辅助治疗 PTSD 的三期试验结果推动监管讨论。"),
    dict(year=2022, category="psychiatry", kind="discovery", title="精神科生物标志探索", text="炎症、代谢与神经影像标志被用于精神疾病分层研究。"),
    dict(year=2023, category="psychiatry", kind="discovery", title="迷幻药监管框架讨论", text="多国开始讨论迷幻药辅助治疗的监管、伦理与可及性问题。"),
    dict(year=2024, category="psychiatry", kind="drug", title="非多巴胺抗精神病药获批", text="毒蕈碱机制药物获批，挑战以 D2 阻断为核心的传统治疗范式。"),
]


EPILEPSY_BATCH: list[dict] = [
    dict(year=1857, category="neurology", kind="drug", title="溴化钾治疗癫痫", text="Locock 用溴化钾控制癫痫发作，成为首个有效的抗癫痫药物。"),
    dict(year=1886, category="neurosurgery", kind="surgery", title="Horsley 首例癫痫手术", text="Victor Horsley 为癫痫患者切除致痫皮层，被视为癫痫外科的开端。"),
    dict(year=1912, category="neurology", kind="drug", title="苯巴比妥用于癫痫", text="苯巴比妥成为早期广泛使用的抗癫痫药。"),
    dict(year=1921, category="neurology", kind="discovery", title="生酮饮食治疗癫痫", text="Wilder 提出用生酮饮食模拟饥饿状态控制癫痫，至今仍用于难治性癫痫。"),
    dict(year=1928, category="neurosurgery", kind="surgery", title="Foerster 癫痫皮层切除", text="Otfrid Foerster 系统开展致痫灶切除，推动癫痫外科发展。"),
    dict(year=1930, category="neurology", kind="device", title="EEG 用于癫痫诊断", text="1930 年代脑电图被用于识别癫痫样放电，成为癫痫诊断核心工具。"),
    dict(year=1934, category="neurosurgery", kind="discovery", title="蒙特利尔神经病学研究所成立", text="MNI 成立，成为癫痫外科与脑功能定位的世界中心。"),
    dict(year=1936, category="neurosurgery", kind="discovery", title="Penfield 术中皮层电刺激", text="Wilder Penfield 以术中电刺激绘制功能地图，为癫痫灶定位奠基。"),
    dict(year=1938, category="neurology", kind="drug", title="苯妥英用于癫痫", text="Merritt 与 Putnam 发现苯妥英的抗癫痫作用，成为经典药物。"),
    dict(year=1950, category="neurosurgery", kind="discovery", title="Penfield 与 Jasper 癫痫专著", text="两人系统总结癫痫的皮层定位与手术经验，奠定现代癫痫外科。"),
    dict(year=1950, category="neurosurgery", kind="surgery", title="前颞叶切除术", text="1950 年代前颞叶切除成为药物难治性颞叶癫痫的标准术式。"),
    dict(year=1960, category="neurosurgery", kind="device", title="SEEG 立体脑电图", text="Talairach 与 Bancaud 发展立体定向脑电图（SEEG），实现深部致痫网络定位。"),
    dict(year=1962, category="neurology", kind="drug", title="卡马西平用于癫痫", text="卡马西平用于部分性发作与三叉神经痛，成为常用抗癫痫药。"),
    dict(year=1967, category="neurology", kind="drug", title="丙戊酸用于癫痫", text="丙戊酸作为广谱抗癫痫药进入临床。"),
    dict(year=1969, category="neurology", kind="discovery", title="ILAE 癫痫发作分类", text="国际抗癫痫联盟发布发作分类，统一临床与研究语言。"),
    dict(year=1970, category="neurology", kind="device", title="视频脑电监测", text="视频 EEG 将发作表现与脑电同步记录，提升致痫灶定位准确性。"),
    dict(year=1975, category="neurology", kind="drug", title="氯硝西泮用于癫痫", text="氯硝西泮用于多种发作类型，尤其肌阵挛与失神发作。"),
    dict(year=1981, category="neurology", kind="discovery", title="ILAE 发作分类修订", text="修订版发作分类成为国际通用标准。"),
    dict(year=1989, category="neurology", kind="discovery", title="ILAE 癫痫综合征分类", text="综合征分类整合年龄、病因与脑电特征，指导治疗与预后判断。"),
    dict(year=1989, category="neurology", kind="discovery", title="Engel 手术结局分级", text="Engel 分级成为癫痫手术后疗效评价的通用标准。"),
    dict(year=1989, category="neurology", kind="drug", title="氨己烯酸用于癫痫", text="氨己烯酸用于婴儿痉挛等难治性癫痫。"),
    dict(year=1990, category="neurology", kind="drug", title="拉莫三嗪用于癫痫", text="拉莫三嗪成为广谱抗癫痫药，需警惕皮疹风险。"),
    dict(year=1990, category="neurology", kind="device", title="MRI 识别海马硬化", text="高分辨 MRI 使海马硬化等致痫病灶在术前可被识别。"),
    dict(year=1993, category="neurology", kind="drug", title="加巴喷丁用于癫痫", text="加巴喷丁作为辅助抗癫痫药进入临床。"),
    dict(year=1996, category="neurology", kind="drug", title="托吡酯用于癫痫", text="托吡酯成为广谱抗癫痫药，用于多种发作类型。"),
    dict(year=1997, category="neurology", kind="device", title="VNS 获批治疗癫痫", text="迷走神经刺激获 FDA 批准用于难治性癫痫。"),
    dict(year=1999, category="neurology", kind="drug", title="左乙拉西坦用于癫痫", text="左乙拉西坦经 SV2A 机制成为广谱抗癫痫药。"),
    dict(year=2000, category="neurology", kind="drug", title="奥卡西平用于癫痫", text="奥卡西平用于部分性发作，耐受性较好。"),
    dict(year=2002, category="neurology", kind="drug", title="唑尼沙胺用于癫痫", text="唑尼沙胺作为辅助抗癫痫药用于难治性发作。"),
    dict(year=2005, category="neurology", kind="drug", title="普瑞巴林用于癫痫", text="普瑞巴林作为辅助治疗用于部分性发作。"),
    dict(year=2008, category="neurology", kind="drug", title="拉考沙胺用于癫痫", text="拉考沙胺作用于钠通道慢失活状态，用于部分性发作。"),
    dict(year=2008, category="neurology", kind="drug", title="卢非酰胺用于癫痫", text="卢非酰胺用于 Lennox–Gastaut 综合征相关发作。"),
    dict(year=2009, category="neurology", kind="discovery", title="癫痫基因组学", text="大规模测序识别 SCN1A、SCN2A 等癫痫相关基因，推动精准分型。"),
    dict(year=2010, category="neurosurgery", kind="device", title="ANT-DBS 治疗癫痫", text="SANTE 试验支持丘脑前核深部电刺激用于难治性癫痫，2018 年获 FDA 批准。"),
    dict(year=2011, category="neurosurgery", kind="surgery", title="激光间质热疗（LITT）", text="磁共振引导激光消融用于颞叶与下丘脑错构瘤等致痫灶，创伤更小。"),
    dict(year=2012, category="neurology", kind="drug", title="吡仑帕奈用于癫痫", text="吡仑帕奈作为首个 AMPA 受体拮抗剂类抗癫痫药获批。"),
    dict(year=2013, category="neurosurgery", kind="device", title="RNS 获 FDA 批准", text="反应性神经刺激（RNS）通过闭环电刺激治疗难治性局灶性癫痫。"),
    dict(year=2015, category="neurosurgery", kind="discovery", title="SEEG 与致痫网络", text="2010 年代 SEEG 普及，癫痫被理解为网络性疾病，推动多脑区评估。"),
    dict(year=2016, category="neurology", kind="drug", title="布瓦西坦获批", text="布瓦西坦作为 SV2A 配体用于部分性发作。"),
    dict(year=2017, category="neurology", kind="discovery", title="ILAE 新分类", text="2017 年 ILAE 分类强调病因（遗传/结构/代谢/免疫/感染）与共病。"),
    dict(year=2018, category="neurology", kind="drug", title="大麻二酚获批", text="大麻二酚用于 Dravet 与 Lennox–Gastaut 综合征相关发作。"),
    dict(year=2018, category="neurology", kind="drug", title="司替戊醇获批", text="司替戊醇用于 Dravet 综合征相关发作的辅助治疗。"),
    dict(year=2019, category="neurology", kind="drug", title="西诺贝酯获批", text="西诺贝酯用于成人局灶性癫痫，提供高疗效选项。"),
    dict(year=2020, category="neurology", kind="drug", title="芬氟拉明获批", text="芬氟拉明用于 Dravet 综合征相关发作。"),
    dict(year=2010, category="neurosurgery", kind="surgery", title="半球离断术", text="功能性半球离断术用于半球性病变所致难治性癫痫，替代部分解剖性半球切除。"),
    dict(year=2010, category="neurosurgery", kind="surgery", title="胼胝体切开术", text="胼胝体切开用于跌倒发作等难治性癫痫，减少发作传播。"),
    dict(year=2000, category="neurosurgery", kind="discovery", title="术中皮层功能定位", text="术中电刺激与诱发电位用于保护语言、运动与记忆功能。"),
    dict(year=2000, category="neurology", kind="discovery", title="癫痫猝死（SUDEP）关注", text="2000 年代 SUDEP 风险被系统认识，推动夜间监测与家庭宣教。"),
    dict(year=1990, category="neurology", kind="discovery", title="生酮饮食复兴", text="1990 年代生酮饮食在儿童难治性癫痫中重新受到重视。"),
    dict(year=2010, category="neurology", kind="discovery", title="癫痫共病管理", text="2010 年代抑郁、焦虑、认知与睡眠共病被纳入癫痫全程管理。"),
    dict(year=2010, category="neurology", kind="discovery", title="癫痫与免疫", text="自身免疫性脑炎相关癫痫被识别，免疫治疗成为新方向。"),
    dict(year=2010, category="neurology", kind="discovery", title="遗传性癫痫精准治疗", text="基因诊断指导部分遗传性癫痫的靶向用药与预后判断。"),
    dict(year=2019, category="neurosurgery", kind="device", title="闭环神经调控", text="闭环刺激根据脑电实时调整刺激参数，代表癫痫调控的新范式。"),
    dict(year=2020, category="neurosurgery", kind="discovery", title="癫痫网络外科", text="以致痫网络为靶点的外科理念，超越单一病灶切除。"),
    dict(year=2020, category="neurology", kind="discovery", title="癫痫可穿戴监测", text="可穿戴设备用于发作检测与预警，改善院外管理。"),
    dict(year=2021, category="neurology", kind="discovery", title="癫痫生物标志", text="血液与影像标志物用于癫痫进展与药物反应评估。"),
    dict(year=2022, category="neurology", kind="discovery", title="ILAE 分类更新讨论", text="围绕发作类型与病因分类的持续修订，推动个体化管理。"),
    dict(year=2023, category="neurology", kind="discovery", title="癫痫基因治疗探索", text="反义寡核苷酸与基因疗法在遗传性癫痫中的早期探索。"),
    dict(year=2024, category="neurology", kind="discovery", title="癫痫精准医学", text="多组学与影像融合推动癫痫的精准诊断与个体化治疗。"),
    dict(year=1980, category="neurosurgery", kind="discovery", title="癫痫术前评估体系", text="1980 年代视频 EEG、MRI 与神经心理评估形成标准化术前流程。"),
    dict(year=1995, category="neurosurgery", kind="discovery", title="颞叶癫痫手术证据", text="随机试验支持颞叶切除优于药物治疗，巩固手术地位。"),
    dict(year=2000, category="neurosurgery", kind="discovery", title="功能区癫痫手术", text="术中唤醒与功能成像降低功能区癫痫手术的神经功能风险。"),
    dict(year=2005, category="neurology", kind="discovery", title="癫痫持续状态指南", text="规范化阶梯治疗与时间管理降低癫痫持续状态死亡率。"),
    dict(year=2008, category="neurology", kind="discovery", title="癫痫与认知", text="癫痫网络与抗癫痫药对认知的影响成为研究重点。"),
    dict(year=2012, category="neurology", kind="discovery", title="癫痫影像后处理", text="基于体素的形态学与连接分析提升隐匿致痫灶的检出。"),
    dict(year=2015, category="neurosurgery", kind="discovery", title="癫痫手术可及性", text="研究显示大量药物难治性患者未获手术评估，推动转诊与公平性。"),
    dict(year=2018, category="neurology", kind="discovery", title="癫痫与睡眠", text="睡眠结构紊乱与癫痫相互影响，成为管理新维度。"),
    dict(year=2020, category="neurology", kind="discovery", title="癫痫数字医疗", text="远程随访与数字工具提升难治性癫痫的长期管理效率。"),
    dict(year=2020, category="neurosurgery", kind="device", title="机器人辅助 SEEG", text="手术机器人提高 SEEG 电极植入的精度与安全性。"),
    dict(year=2016, category="neurology", kind="discovery", title="癫痫病因学分类", text="结构、遗传、感染、代谢、免疫、病因不明六类框架被广泛采用。"),
    dict(year=2010, category="neurology", kind="discovery", title="自身免疫性癫痫", text="抗神经元抗体相关癫痫被识别，免疫治疗可显著改善。"),
    dict(year=2013, category="neurology", kind="discovery", title="癫痫影像大数据", text="多中心影像与基因组数据推动癫痫的机制与分型研究。"),
    dict(year=2019, category="neurology", kind="discovery", title="癫痫与肠脑轴", text="肠道菌群与癫痫的关联被探索，为辅助治疗提供新思路。"),
    dict(year=2021, category="neurosurgery", kind="discovery", title="癫痫手术预后模型", text="机器学习用于预测术后无发作概率，辅助个体化决策。"),
    dict(year=2022, category="neurosurgery", kind="device", title="聚焦超声治疗癫痫", text="低强度聚焦超声作为无创神经调控用于致痫灶的探索。"),
    dict(year=2023, category="neurology", kind="discovery", title="癫痫多组学", text="基因组、转录组与影像组学整合用于难治性癫痫机制研究。"),
    dict(year=2024, category="neurosurgery", kind="discovery", title="癫痫外科微创化", text="LITT、RNS 与机器人技术推动癫痫外科向微创与精准演进。"),
    dict(year=1998, category="neurology", kind="discovery", title="癫痫与妊娠", text="抗癫痫药致畸风险与孕期管理成为癫痫全程照护重点。"),
    dict(year=2003, category="neurology", kind="discovery", title="癫痫与骨健康", text="长期抗癫痫药对骨代谢的影响受到关注，促成监测建议。"),
    dict(year=2007, category="neurology", kind="discovery", title="癫痫与心源性猝死", text="SUDEP 机制研究聚焦心律失常与呼吸抑制。"),
    dict(year=2011, category="neurology", kind="discovery", title="癫痫共病抑郁", text="癫痫与抑郁的双向关系被系统研究，影响治疗选择。"),
    dict(year=2014, category="neurology", kind="discovery", title="癫痫与认知康复", text="认知康复与心理干预被纳入癫痫综合管理。"),
    dict(year=2017, category="neurosurgery", kind="discovery", title="癫痫手术时机", text="研究支持更早手术可改善难治性癫痫的长期结局。"),
    dict(year=2020, category="neurology", kind="discovery", title="癫痫远程监测", text="可穿戴 EEG 与手机应用用于发作日记与预警。"),
    dict(year=2023, category="neurology", kind="discovery", title="癫痫精准用药", text="药物基因组学用于个体化选择抗癫痫药与剂量。"),
]


GENERAL_BATCH: list[dict] = [
    dict(year=1950, category="neurosurgery", kind="device", title="显微神经外科", text="1950 年代手术显微镜引入神经外科，使深部结构与血管处理更精细。"),
    dict(year=1960, category="neurosurgery", kind="device", title="手术显微镜普及", text="1960 年代显微镜与显微器械普及，显微神经外科成为标准。"),
    dict(year=1968, category="neurosurgery", kind="device", title="伽玛刀", text="Leksell 发明伽玛刀，立体定向放射外科用于脑病变无创治疗。"),
    dict(year=1975, category="neurosurgery", kind="surgery", title="显微血管减压术", text="Jannetta 发展显微血管减压术，用于三叉神经痛与面肌痉挛。"),
    dict(year=1970, category="neurosurgery", kind="surgery", title="经蝶入路复兴", text="1970 年代经蝶入路在垂体瘤手术中复兴并推广。"),
    dict(year=1980, category="neurosurgery", kind="device", title="立体定向放射外科普及", text="1980 年代放射外科扩展至转移瘤、动静脉畸形等。"),
    dict(year=1990, category="neurosurgery", kind="device", title="神经内镜", text="1990 年代神经内镜用于脑室、垂体与颅底病变。"),
    dict(year=1990, category="neurosurgery", kind="device", title="神经导航", text="1990 年代影像导航将术前影像与术中位置配准，提高切除精度。"),
    dict(year=2000, category="neurosurgery", kind="device", title="术中 MRI", text="2000 年代术中磁共振实时评估切除范围，减少残留。"),
    dict(year=2000, category="neurosurgery", kind="device", title="荧光引导手术", text="5-ALA 荧光引导提高胶质瘤切除的边界识别。"),
    dict(year=2010, category="neurosurgery", kind="surgery", title="清醒开颅", text="2010 年代清醒开颅结合术中言语与运动监测，保护功能区。"),
    dict(year=2010, category="neurosurgery", kind="device", title="机器人神经外科", text="2010 年代手术机器人用于立体定向、SEEG 与深部电极植入。"),
    dict(year=2010, category="neurosurgery", kind="device", title="增强现实导航", text="增强现实将影像叠加于术野，辅助深部结构识别。"),
    dict(year=2010, category="neurosurgery", kind="device", title="激光间质热疗", text="磁共振引导激光消融用于癫痫与脑肿瘤的微创治疗。"),
    dict(year=2020, category="neurosurgery", kind="device", title="聚焦超声神经外科", text="聚焦超声用于震颤、疼痛与血脑屏障开放的临床试验。"),
    dict(year=2020, category="neurosurgery", kind="device", title="脑机接口手术", text="脑机接口电极植入进入临床试验，用于运动与沟通辅助。"),
    dict(year=2020, category="neurosurgery", kind="discovery", title="术中人工智能", text="AI 辅助术中影像与病理判读，提高手术决策效率。"),
    dict(year=2020, category="neurosurgery", kind="surgery", title="微创脊柱外科", text="微创通道与内镜技术降低脊柱手术创伤。"),
    dict(year=2000, category="neurosurgery", kind="device", title="脊髓刺激", text="脊髓电刺激用于慢性疼痛，扩展至运动功能辅助研究。"),
    dict(year=2010, category="neurosurgery", kind="device", title="反应性神经刺激", text="闭环反应性刺激根据脑电实时调整治疗参数。"),
    dict(year=1980, category="neurosurgery", kind="device", title="术中超声", text="术中超声用于实时定位病灶与评估切除程度。"),
    dict(year=1990, category="neurosurgery", kind="device", title="术中电生理监测", text="术中诱发电位与肌电监测降低神经损伤风险。"),
    dict(year=2000, category="neurosurgery", kind="device", title="内镜经鼻颅底手术", text="内镜经鼻入路用于垂体瘤与颅底病变，减少脑牵拉。"),
    dict(year=2010, category="neurosurgery", kind="device", title="复合手术室", text="影像与手术一体化复合手术室提升复杂脑血管病治疗效率。"),
    dict(year=2020, category="neurosurgery", kind="discovery", title="个性化植入物", text="3D 打印与个性化植入物用于颅骨与脊柱重建。"),
    dict(year=1960, category="neurology", kind="discovery", title="卒中单元", text="1960 年代卒中单元建立，集中管理改善卒中结局。"),
    dict(year=1970, category="neurology", kind="surgery", title="颈动脉内膜切除", text="颈动脉内膜切除用于症状性颈动脉狭窄的卒中预防。"),
    dict(year=1980, category="neurology", kind="drug", title="阿司匹林二级预防", text="抗血小板治疗成为缺血性卒中二级预防基石。"),
    dict(year=1990, category="neurology", kind="discovery", title="卒中中心网络", text="1990 年代卒中中心与急救网络提升再灌注治疗可及性。"),
    dict(year=2010, category="neurology", kind="discovery", title="卒中影像筛选", text="灌注与弥散影像用于个体化时间窗与取栓决策。"),
    dict(year=1990, category="neurology", kind="drug", title="MS 干扰素治疗", text="1990 年代干扰素类成为 MS 首批疾病修饰治疗。"),
    dict(year=2000, category="neurology", kind="drug", title="MS 单抗治疗", text="2000 年代单抗类高效疗法进入 MS 治疗。"),
    dict(year=2010, category="neurology", kind="drug", title="MS 口服治疗", text="2010 年代口服疾病修饰治疗改善依从性。"),
    dict(year=2020, category="neurology", kind="drug", title="MS 高效治疗", text="2020 年代高效疗法与早期治疗策略改善长期预后。"),
    dict(year=1990, category="neurosurgery", kind="device", title="DBS 治疗帕金森病", text="1990 年代 DBS 成为帕金森病运动症状的重要治疗。"),
    dict(year=2000, category="neurology", kind="device", title="帕金森持续输注", text="左旋多巴-卡比多巴肠凝胶等持续输注改善波动症状。"),
    dict(year=2020, category="neurology", kind="discovery", title="帕金森生物标志", text="α-突触核蛋白种子扩增等技术推动帕金森病生物学诊断。"),
    dict(year=1980, category="neurology", kind="drug", title="阿尔茨海默胆碱能治疗", text="1980 年代胆碱能假说推动胆碱酯酶抑制剂研发。"),
    dict(year=2010, category="neurology", kind="discovery", title="AD 生物标志物", text="Aβ/tau PET 与脑脊液标志物用于阿尔茨海默病分期。"),
    dict(year=1990, category="neurology", kind="drug", title="ALS 利鲁唑", text="利鲁唑成为首个获批的 ALS 药物。"),
    dict(year=2010, category="neurology", kind="drug", title="ALS 依达拉奉", text="依达拉奉以抗氧化机制获批用于 ALS。"),
    dict(year=2020, category="neurology", kind="drug", title="ALS 基因治疗", text="反义寡核苷酸与基因疗法针对遗传性 ALS 进入临床。"),
    dict(year=1990, category="neurology", kind="drug", title="偏头痛曲普坦", text="曲普坦类成为偏头痛急性治疗的重要选择。"),
    dict(year=2010, category="neurology", kind="drug", title="偏头痛 CGRP 靶向", text="CGRP 单抗与小分子拮抗剂革新偏头痛预防与急性治疗。"),
    dict(year=2000, category="neurology", kind="discovery", title="头痛分类体系", text="国际头痛分类为偏头痛与紧张型头痛提供统一诊断标准。"),
    dict(year=2010, category="neurology", kind="discovery", title="自身免疫性脑炎", text="抗 NMDA 受体脑炎等被识别，免疫治疗显著改善预后。"),
    dict(year=1950, category="neuroscience", kind="discovery", title="分子神经生物学", text="1950 年代分子生物学方法进入神经科学，推动递质与受体研究。"),
    dict(year=1960, category="neuroscience", kind="discovery", title="神经递质时代", text="1960 年代多种神经递质被确认，化学传递成为核心范式。"),
    dict(year=1970, category="neuroscience", kind="discovery", title="受体药理学", text="1970 年代放射配体结合技术推动受体定量与亚型研究。"),
    dict(year=1980, category="neuroscience", kind="discovery", title="离子通道分子学", text="1980 年代离子通道克隆与电生理结合，阐明兴奋性机制。"),
    dict(year=1990, category="neuroscience", kind="discovery", title="基因敲除小鼠", text="1990 年代基因敲除技术用于神经功能与疾病机制研究。"),
    dict(year=2000, category="neuroscience", kind="discovery", title="神经环路因果研究", text="光遗传与化学遗传实现环路层面的因果操控。"),
    dict(year=2010, category="neuroscience", kind="discovery", title="脑细胞图谱", text="单细胞与空间组学绘制脑细胞类型与空间组织图谱。"),
    dict(year=2010, category="neuroscience", kind="discovery", title="人脑连接组", text="连接组学刻画脑网络拓扑与个体差异。"),
    dict(year=2020, category="neuroscience", kind="discovery", title="脑图谱计划", text="多国脑图谱计划整合多组学与影像，构建参考脑。"),
    dict(year=2020, category="neuroscience", kind="discovery", title="神经 AI", text="深度学习用于神经影像、脑电解码与行为预测。"),
    dict(year=2020, category="neuroscience", kind="discovery", title="神经免疫学", text="神经-免疫互作成为神经退行与精神疾病的研究主轴。"),
    dict(year=2020, category="neuroscience", kind="discovery", title="脑代谢与认知", text="线粒体与代谢通路对认知与行为的影响受到重视。"),
    dict(year=2020, category="neuroscience", kind="discovery", title="睡眠科学", text="睡眠节律、类淋巴清除与神经退行的关系被系统研究。"),
    dict(year=2020, category="neuroscience", kind="discovery", title="胶质细胞功能", text="星形胶质与小胶质在环路调控中的作用被重新认识。"),
    dict(year=2020, category="neuroscience", kind="discovery", title="神经血管单元", text="血脑屏障与神经血管耦合成为脑疾病治疗靶点。"),
    dict(year=2020, category="neuroscience", kind="discovery", title="神经退行标志物", text="血液与影像标志物推动神经退行的早期诊断与分层。"),
    dict(year=2020, category="neuroscience", kind="discovery", title="神经伦理", text="脑机接口、神经数据与认知增强引发伦理与治理讨论。"),
    dict(year=2010, category="neuroscience", kind="discovery", title="可重复性危机", text="2010 年代神经科学关注统计功效、预注册与结果可重复性。"),
    dict(year=2020, category="neuroscience", kind="discovery", title="开放科学", text="数据与代码共享推动神经科学的透明与协作。"),
    dict(year=2020, category="neuroscience", kind="discovery", title="多组学整合", text="基因组、转录组、蛋白组与影像整合用于机制研究。"),
    dict(year=1950, category="psychiatry", kind="discovery", title="抗精神病药时代", text="1950 年代抗精神病药普及，精神科从收容转向治疗。"),
    dict(year=1960, category="psychiatry", kind="discovery", title="抗抑郁药时代", text="1960 年代三环类与 MAOI 成为抑郁治疗主力。"),
    dict(year=1970, category="psychiatry", kind="discovery", title="精神药理学成熟", text="1970 年代受体理论与药物监测推动精神药理精细化。"),
    dict(year=1980, category="psychiatry", kind="discovery", title="血清素时代", text="1980 年代血清素系统成为抑郁与焦虑治疗核心靶点。"),
    dict(year=1990, category="psychiatry", kind="discovery", title="非典型抗精神病药", text="1990 年代非典型药物减少锥体外系反应但带来代谢问题。"),
    dict(year=2000, category="psychiatry", kind="discovery", title="代谢副作用管理", text="2000 年代抗精神病药代谢风险促成常规监测。"),
    dict(year=2010, category="psychiatry", kind="discovery", title="免疫精神病学", text="炎症与免疫机制被引入精神分裂与抑郁研究。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="精准精神医学", text="生物标志与个体化选药成为精神科研究方向。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="数字精神医学", text="数字疗法与远程监测扩展精神卫生服务边界。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="迷幻药治疗", text="迷幻药辅助治疗在抑郁、PTSD 与成瘾中持续研究。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="精神卫生公平", text="可及性、污名与社会决定因素成为精神卫生政策重点。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="早期干预", text="精神病与情绪障碍的早期识别与干预服务扩展。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="远程精神医学", text="远程诊疗提升偏远地区的精神卫生可及性。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="心理治疗整合", text="药物与心理治疗联合成为多数精神障碍的标准。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="共病管理", text="精神与躯体共病的整合照护模式受到重视。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="自杀预防", text="风险评估、随访与限制手段成为自杀预防核心策略。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="儿童青少年精神健康", text="儿童青少年精神障碍的早期识别与学校干预受到关注。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="老年精神医学", text="老年抑郁、痴呆行为症状与照护负担成为重点。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="成瘾医学", text="成瘾被视为慢性脑疾病，药物治疗与减害策略并行。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="睡眠与精神障碍", text="睡眠紊乱与精神障碍的双向关系影响治疗选择。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="社会决定因素", text="贫困、创伤与社会支持被纳入精神健康评估。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="全球精神健康", text="中低收入国家精神卫生服务缺口推动全球行动。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="精神卫生立法", text="非自愿治疗与权利保障成为精神卫生立法焦点。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="去污名化", text="公众教育与同伴支持减少精神疾病污名。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="同伴支持", text="康复者参与服务提供，改善参与度与结局。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="数字疗法", text="基于 App 与在线的心理干预进入临床与监管视野。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="生物标志与分型", text="炎症、代谢与影像标志用于精神疾病分层。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="神经调控治疗", text="TMS、tDCS 与 DBS 在难治性精神障碍中扩展应用。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="迷幻药监管", text="迷幻药辅助治疗的监管、伦理与可及性成为政策议题。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="精神科 AI", text="机器学习用于诊断辅助、风险预测与治疗反应估计。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="精准用药", text="药物基因组学用于精神科个体化选药与剂量调整。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="结局测量", text="患者报告结局与功能量表成为精神科疗效评价核心。"),
    dict(year=1990, category="neurology", kind="discovery", title="神经康复", text="1990 年代循证神经康复改善卒中与脑损伤功能结局。"),
    dict(year=2000, category="neurology", kind="discovery", title="神经可塑性康复", text="2000 年代可塑性理论推动任务导向与强化康复。"),
    dict(year=2010, category="neurology", kind="device", title="康复机器人", text="康复机器人与外骨骼用于卒中与脊髓损伤训练。"),
    dict(year=2020, category="neurology", kind="device", title="神经假体", text="神经假体用于感觉与运动功能重建的临床探索。"),
    dict(year=2000, category="neurology", kind="discovery", title="脑网络与疾病", text="网络视角将神经与精神疾病理解为环路失调。"),
    dict(year=2010, category="neurology", kind="discovery", title="神经影像规范建模", text="规范建模用于个体化偏离评估与临床决策。"),
    dict(year=2010, category="neurology", kind="discovery", title="数字神经病学", text="可穿戴与远程监测用于帕金森、癫痫等慢性管理。"),
    dict(year=2020, category="neurology", kind="discovery", title="神经遗传诊断", text="外显子与基因组测序提高神经遗传病诊断率。"),
    dict(year=2020, category="neurology", kind="discovery", title="神经免疫治疗", text="单抗与免疫调节扩展至自身免疫性脑炎与神经病。"),
    dict(year=2020, category="neurology", kind="discovery", title="神经重症", text="神经重症监护与多模态监测改善重症脑损伤结局。"),
    dict(year=2020, category="neurology", kind="discovery", title="脑死亡与伦理", text="脑死亡判定标准与器官捐献伦理持续完善。"),
    dict(year=1990, category="neuroscience", kind="discovery", title="神经信息学", text="1990 年代神经信息学整合数据库与计算工具。"),
    dict(year=2000, category="neuroscience", kind="discovery", title="计算神经科学", text="2000 年代计算模型与实验结合解释环路计算。"),
    dict(year=2010, category="neuroscience", kind="discovery", title="神经解码", text="脑电解码与脑机接口实现意图读取与外部设备控制。"),
    dict(year=2020, category="neuroscience", kind="discovery", title="基础模型与脑", text="大规模模型与神经数据结合探索脑的计算原理。"),
]


EXTRA1: list[dict] = [
    dict(year=1793, category="psychiatry", kind="discovery", title="Pinel 解除精神病人锁链", text="Philippe Pinel 在巴黎解除精神病患者束缚，开启更人道的照护理念。"),
    dict(year=1812, category="psychiatry", kind="discovery", title="道德疗法", text="以尊重、秩序与劳动为核心的道德疗法在精神病院推广。"),
    dict(year=1911, category="psychiatry", kind="discovery", title="Bleuler《早发性痴呆或精神分裂症组》", text="Bleuler 系统阐述精神分裂症概念，影响此后百年诊断。"),
    dict(year=1921, category="psychiatry", kind="discovery", title="罗夏墨迹测验", text="Hermann Rorschach 发表墨迹测验，成为投射测验的代表。"),
    dict(year=1946, category="psychiatry", kind="discovery", title="英国精神卫生法", text="英国立法规范精神疾病收治与权利，影响各国精神卫生法制。"),
    dict(year=1956, category="psychiatry", kind="discovery", title="LSD 心理治疗研究", text="1950 年代 LSD 被用于精神分析与心理治疗的实验研究。"),
    dict(year=1970, category="psychiatry", kind="discovery", title="家庭治疗兴起", text="1970 年代系统式家庭治疗成为精神障碍干预的重要流派。"),
    dict(year=1980, category="psychiatry", kind="discovery", title="复发预防模型", text="复发预防与心理教育成为精神分裂症长期管理的核心。"),
    dict(year=1994, category="psychiatry", kind="discovery", title="精神分裂症认知缺陷", text="认知缺陷被确认为精神分裂症功能结局的关键决定因素。"),
    dict(year=1996, category="psychiatry", kind="discovery", title="早期精神病干预", text="1990 年代起首发精神病早期干预服务在多地建立。"),
    dict(year=2000, category="psychiatry", kind="discovery", title="首发精神病服务", text="专门的首发精神病团队整合药物、心理与社会支持。"),
    dict(year=2000, category="psychiatry", kind="discovery", title="康复导向服务", text="以功能恢复与社区融入为目标的康复模式推广。"),
    dict(year=1869, category="neurology", kind="discovery", title="Jackson 癫痫理论", text="Hughlings Jackson 提出癫痫是皮层放电的层级释放现象。"),
    dict(year=1881, category="neurology", kind="discovery", title="Jackson 癫痫分类", text="Jackson 区分局灶性与全面性发作，奠定癫痫学基础。"),
    dict(year=1919, category="neurology", kind="discovery", title="脑炎后帕金森综合征", text="von Economo 脑炎流行后出现大量帕金森样病例，推动基底节研究。"),
    dict(year=1950, category="neurosurgery", kind="surgery", title="立体定向苍白球切开", text="立体定向手术用于帕金森病震颤，成为 DBS 之前的主要功能术式。"),
    dict(year=1960, category="neurosurgery", kind="surgery", title="丘脑切开术", text="丘脑毁损术用于震颤与疼痛，推动立体定向功能外科。"),
    dict(year=1970, category="neuroscience", kind="discovery", title="术中微电极记录", text="微电极记录揭示基底节放电模式，指导靶点选择。"),
    dict(year=1980, category="neurosurgery", kind="surgery", title="苍白球切开复兴", text="1980 年代苍白球切开在运动障碍中复兴，后让位于 DBS。"),
    dict(year=1990, category="neurosurgery", kind="device", title="丘脑底核 DBS", text="丘脑底核刺激显著改善帕金森病运动症状，成为标准靶点。"),
    dict(year=2010, category="neurosurgery", kind="device", title="自适应 DBS", text="根据脑电反馈自动调整刺激参数的自适应 DBS 进入研究。"),
    dict(year=2020, category="neurology", kind="drug", title="帕金森基因治疗探索", text="针对 GBA、LRRK2 等靶点的基因与靶向治疗进入试验。"),
    dict(year=1920, category="neurosurgery", kind="discovery", title="脑肿瘤放疗", text="1920 年代放射治疗开始用于脑肿瘤，成为术后辅助手段。"),
    dict(year=1970, category="neurosurgery", kind="drug", title="脑肿瘤化疗", text="1970 年代化疗用于胶质瘤，逐步形成放化疗联合方案。"),
    dict(year=1980, category="neurosurgery", kind="discovery", title="胶质瘤分级", text="WHO 分级体系用于胶质瘤病理分级与预后判断。"),
    dict(year=1990, category="neurosurgery", kind="discovery", title="胶质瘤分子病理", text="分子标志进入胶质瘤诊断，推动整合诊断。"),
    dict(year=2000, category="neurosurgery", kind="drug", title="替莫唑胺", text="替莫唑胺联合放疗成为胶质母细胞瘤标准治疗。"),
    dict(year=2010, category="neurosurgery", kind="discovery", title="IDH 突变", text="IDH 突变被确立为胶质瘤分型与预后的关键分子标志。"),
    dict(year=2010, category="neurosurgery", kind="discovery", title="胶质瘤分子分型", text="整合组织与分子特征的分类取代单纯形态学诊断。"),
    dict(year=2020, category="neurosurgery", kind="drug", title="胶质瘤靶向治疗", text="针对特定分子靶点的药物与免疫治疗进入临床试验。"),
    dict(year=1990, category="neurosurgery", kind="surgery", title="颅底外科", text="颅底外科整合多学科技术处理复杂颅底病变。"),
    dict(year=2000, category="neurosurgery", kind="surgery", title="内镜颅底手术", text="内镜经鼻扩大入路用于颅底肿瘤，减少脑组织牵拉。"),
    dict(year=2010, category="neurosurgery", kind="discovery", title="颅底多学科协作", text="神经外科、耳鼻喉与放疗联合提升颅底病变结局。"),
    dict(year=1990, category="neurosurgery", kind="surgery", title="脑血管搭桥", text="颅内外搭桥用于缺血性脑血管病与复杂动脉瘤。"),
    dict(year=2000, category="neurosurgery", kind="surgery", title="动脉瘤夹闭", text="显微夹闭仍是颅内动脉瘤的重要治疗方式。"),
    dict(year=2010, category="neurosurgery", kind="device", title="血流导向装置", text="血流导向支架改变大型与宽颈动脉瘤的治疗策略。"),
    dict(year=1950, category="neurosurgery", kind="discovery", title="脊髓损伤康复", text="1950 年代脊髓损伤系统康复与专科中心建立。"),
    dict(year=1970, category="neurosurgery", kind="surgery", title="脊柱内固定", text="脊柱内固定技术改善创伤与退变性疾病的稳定性。"),
    dict(year=1980, category="neurosurgery", kind="device", title="椎弓根螺钉", text="椎弓根螺钉固定成为脊柱外科的重要技术。"),
    dict(year=1990, category="neurosurgery", kind="surgery", title="微创脊柱", text="微创通道与内镜减少脊柱手术的组织损伤。"),
    dict(year=2000, category="neurosurgery", kind="device", title="脊柱导航", text="影像导航提高脊柱置钉与减压的精度。"),
    dict(year=2010, category="neurosurgery", kind="device", title="脊柱机器人", text="机器人辅助提高脊柱手术的置钉准确性与可重复性。"),
    dict(year=2020, category="neurosurgery", kind="surgery", title="脊柱内镜", text="单孔内镜用于椎间盘与椎管狭窄的微创治疗。"),
    dict(year=1940, category="neurology", kind="device", title="EEG 用于癫痫定位", text="1940 年代 EEG 用于致痫灶的术前定位。"),
    dict(year=1950, category="neurology", kind="drug", title="抗癫痫药发展", text="1950 年代多种抗癫痫药问世，药物治疗体系逐步成形。"),
    dict(year=1960, category="neurosurgery", kind="surgery", title="癫痫外科体系化", text="1960 年代癫痫外科形成术前评估、手术与随访体系。"),
    dict(year=1970, category="neurology", kind="device", title="癫痫监测单元", text="癫痫监测单元整合视频 EEG 与药物调整。"),
    dict(year=1980, category="neurology", kind="device", title="癫痫影像定位", text="CT 与 MRI 用于致痫灶的结构定位。"),
    dict(year=1990, category="neurosurgery", kind="surgery", title="癫痫手术疗效证据", text="1990 年代手术疗效证据积累，推动指南推荐。"),
    dict(year=2000, category="neurosurgery", kind="device", title="癫痫神经调控", text="VNS 与 DBS 为难治性癫痫提供非切除选择。"),
    dict(year=2010, category="neurology", kind="discovery", title="癫痫精准医学", text="基因与影像标志用于癫痫分型与个体化治疗。"),
    dict(year=2020, category="neurology", kind="discovery", title="癫痫基因治疗", text="针对遗传性癫痫的基因与寡核苷酸疗法进入早期试验。"),
    dict(year=1950, category="neuroscience", kind="discovery", title="神经心理测验", text="1950 年代神经心理测验用于脑损伤与认知评估。"),
    dict(year=1960, category="neuroscience", kind="discovery", title="认知评估体系", text="标准化认知测验推动神经心理学的临床化。"),
    dict(year=1970, category="neuroscience", kind="discovery", title="记忆系统研究", text="1970 年代多重记忆系统理论成形。"),
    dict(year=1980, category="neuroscience", kind="discovery", title="影像认知神经科学", text="1980 年代影像与认知任务结合，推动脑-行为映射。"),
    dict(year=1990, category="neuroscience", kind="discovery", title="认知神经科学成型", text="1990 年代认知神经科学成为独立学科。"),
    dict(year=2000, category="neuroscience", kind="discovery", title="决策神经科学", text="2000 年代价值、奖赏与决策的神经机制成为热点。"),
    dict(year=2010, category="neuroscience", kind="discovery", title="社会神经科学", text="2010 年代社会认知与互动的神经机制研究兴起。"),
    dict(year=2020, category="neuroscience", kind="discovery", title="计算精神病学", text="计算模型用于解释精神症状的推断与学习异常。"),
    dict(year=1950, category="neuroscience", kind="discovery", title="睡眠研究", text="1950 年代睡眠实验室建立，睡眠分期与 REM 被发现。"),
    dict(year=1960, category="neuroscience", kind="discovery", title="睡眠分期", text="1960 年代睡眠分期标准建立，睡眠医学成形。"),
    dict(year=1970, category="neurology", kind="discovery", title="睡眠呼吸障碍", text="1970 年代睡眠呼吸暂停被识别并纳入治疗。"),
    dict(year=1980, category="neurology", kind="discovery", title="睡眠障碍诊疗", text="1980 年代睡眠障碍分类与诊疗体系建立。"),
    dict(year=1990, category="neurology", kind="discovery", title="睡眠医学专科", text="1990 年代睡眠医学成为独立专科。"),
    dict(year=2000, category="neuroscience", kind="discovery", title="睡眠与记忆", text="2000 年代睡眠在记忆巩固中的作用被系统研究。"),
    dict(year=2010, category="neuroscience", kind="discovery", title="类淋巴系统", text="类淋巴（glymphatic）系统被描述，连接睡眠与代谢清除。"),
    dict(year=2020, category="neurology", kind="discovery", title="睡眠与痴呆", text="睡眠紊乱与神经退行的双向关系成为研究重点。"),
    dict(year=1950, category="neuroscience", kind="discovery", title="疼痛通路研究", text="1950 年代脊髓与脑干疼痛通路被系统描绘。"),
    dict(year=1965, category="neuroscience", kind="discovery", title="疼痛门控理论", text="Melzack 与 Wall 提出门控理论，重塑疼痛机制理解。"),
    dict(year=1970, category="neurology", kind="discovery", title="疼痛专科", text="1970 年代疼痛门诊与多学科疼痛管理兴起。"),
    dict(year=1980, category="neuroscience", kind="discovery", title="疼痛影像", text="1980 年代影像用于疼痛相关脑区研究。"),
    dict(year=1990, category="neurology", kind="discovery", title="慢性疼痛机制", text="1990 年代中枢敏化与神经病理性疼痛机制被阐明。"),
    dict(year=2000, category="neurosurgery", kind="device", title="疼痛神经调控", text="脊髓刺激与脑深部刺激用于难治性疼痛。"),
    dict(year=2010, category="neurology", kind="discovery", title="疼痛生物标志", text="2010 年代疼痛的影像与分子标志探索。"),
    dict(year=1950, category="neurology", kind="discovery", title="多发性硬化研究", text="1950 年代 MS 的免疫病理与临床分型逐步明确。"),
    dict(year=1970, category="neurology", kind="device", title="MS 影像诊断", text="1970 年代 CT 与 MRI 用于 MS 病灶识别。"),
    dict(year=1980, category="neurology", kind="discovery", title="MS 免疫机制", text="1980 年代 MS 的自身免疫机制得到实验支持。"),
    dict(year=1990, category="neurology", kind="drug", title="MS 疾病修饰治疗", text="1990 年代首批 DMT 改变 MS 自然史。"),
    dict(year=2000, category="neurology", kind="drug", title="MS 单抗", text="2000 年代单抗类高效治疗进入 MS。"),
    dict(year=2010, category="neurology", kind="drug", title="MS 口服药", text="2010 年代口服 DMT 改善依从性与生活质量。"),
    dict(year=2020, category="neurology", kind="drug", title="MS 高效早期治疗", text="2020 年代早期高效治疗策略改善长期预后。"),
    dict(year=1950, category="neurology", kind="discovery", title="神经遗传学", text="1950 年代神经遗传病的家系与遗传方式被系统研究。"),
    dict(year=1970, category="neurology", kind="discovery", title="基因定位", text="1970 年代连锁分析用于神经遗传病的基因定位。"),
    dict(year=1980, category="neurology", kind="discovery", title="分子遗传学", text="1980 年代分子克隆推动神经遗传病的机制研究。"),
    dict(year=1990, category="neurology", kind="discovery", title="疾病基因克隆", text="1990 年代多种神经疾病基因被克隆。"),
    dict(year=2000, category="neurology", kind="discovery", title="基因组医学", text="2000 年代基因组技术进入神经疾病诊断。"),
    dict(year=2010, category="neurology", kind="discovery", title="精准遗传诊断", text="2010 年代外显子与基因组测序提高诊断率。"),
    dict(year=2020, category="neurology", kind="drug", title="神经基因治疗", text="2020 年代基因与寡核苷酸疗法进入神经疾病临床。"),
]


EXTRA2: list[dict] = [
    dict(year=1883, category="psychiatry", kind="discovery", title="神经症概念", text="19 世纪末神经症被系统分类，成为精神科与神经科的交界议题。"),
    dict(year=1896, category="psychiatry", kind="discovery", title="早发性痴呆", text="Kraepelin 提出早发性痴呆，后由 Bleuler 改写为精神分裂症。"),
    dict(year=1920, category="psychiatry", kind="discovery", title="儿童精神科", text="1920 年代儿童指导诊所与儿童精神科兴起。"),
    dict(year=1930, category="psychiatry", kind="discovery", title="心理卫生运动", text="心理卫生运动推动公众对精神疾病的关注与预防。"),
    dict(year=1940, category="psychiatry", kind="discovery", title="群体治疗", text="二战期间群体治疗用于创伤与应激反应。"),
    dict(year=1950, category="psychiatry", kind="discovery", title="社区精神科", text="1950 年代社区精神科服务开始发展。"),
    dict(year=1960, category="psychiatry", kind="discovery", title="危机干预", text="危机干预与热线服务成为自杀预防的重要形式。"),
    dict(year=1970, category="psychiatry", kind="discovery", title="心理教育", text="心理教育帮助患者与家庭理解疾病、识别复发。"),
    dict(year=1980, category="psychiatry", kind="discovery", title="家庭干预", text="家庭干预被证实可降低精神分裂症复发。"),
    dict(year=1990, category="psychiatry", kind="discovery", title="认知矫正", text="认知矫正训练用于改善精神分裂症认知缺陷。"),
    dict(year=1990, category="psychiatry", kind="discovery", title="病耻感研究", text="病耻感与自我污名成为精神卫生服务的重要障碍。"),
    dict(year=2000, category="psychiatry", kind="discovery", title="康复模式", text="以恢复为导向的康复模式强调目标、优势与社区融入。"),
    dict(year=2010, category="psychiatry", kind="discovery", title="数字心理健康", text="App 与在线干预进入心理健康服务。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="远程精神卫生", text="远程服务扩大精神卫生可及性并改变服务模式。"),
    dict(year=1960, category="psychiatry", kind="discovery", title="注意缺陷研究", text="1960 年代注意缺陷与多动行为被系统描述。"),
    dict(year=1980, category="psychiatry", kind="discovery", title="ADHD 诊断标准", text="ADHD 进入正式诊断体系并逐步细化。"),
    dict(year=1990, category="psychiatry", kind="discovery", title="儿童抑郁识别", text="儿童青少年抑郁被更系统识别与治疗。"),
    dict(year=2000, category="psychiatry", kind="discovery", title="青少年精神健康", text="青少年精神健康服务与学校干预受到重视。"),
    dict(year=2010, category="psychiatry", kind="discovery", title="校园心理干预", text="学校为基础的筛查与干预改善青少年心理健康。"),
    dict(year=1950, category="psychiatry", kind="discovery", title="老年精神科", text="老年精神科关注痴呆、抑郁与谵妄的识别。"),
    dict(year=1970, category="psychiatry", kind="discovery", title="痴呆行为症状", text="痴呆的行为与心理症状成为照护重点。"),
    dict(year=1980, category="psychiatry", kind="discovery", title="老年抑郁", text="老年抑郁的识别与治疗受到关注。"),
    dict(year=1990, category="psychiatry", kind="discovery", title="照护者负担", text="照护者负担评估与支持成为痴呆照护核心。"),
    dict(year=2000, category="psychiatry", kind="discovery", title="老年精神卫生服务", text="老年精神卫生服务与整合照护模式发展。"),
    dict(year=2010, category="psychiatry", kind="discovery", title="痴呆照护模式", text="以人为中心的痴呆照护模式推广。"),
    dict(year=1960, category="psychiatry", kind="drug", title="美沙酮维持治疗", text="美沙酮维持治疗用于阿片类依赖，降低危害。"),
    dict(year=1970, category="psychiatry", kind="discovery", title="戒断治疗", text="系统化戒断管理与康复服务改善成瘾结局。"),
    dict(year=1980, category="psychiatry", kind="discovery", title="复吸预防", text="复吸预防模型强调高危情境与应对技能。"),
    dict(year=1990, category="psychiatry", kind="discovery", title="动机访谈", text="动机访谈成为成瘾与行为改变的有效方法。"),
    dict(year=2000, category="psychiatry", kind="discovery", title="减害策略", text="减害策略（针具交换、纳洛酮）降低成瘾相关伤害。"),
    dict(year=2010, category="psychiatry", kind="discovery", title="阿片危机应对", text="阿片过量危机推动纳洛酮普及与处方监管。"),
    dict(year=1950, category="psychiatry", kind="discovery", title="心理测量", text="标准化心理测量成为精神科评估的重要工具。"),
    dict(year=1960, category="psychiatry", kind="discovery", title="人格测验", text="人格测验用于临床描述与研究。"),
    dict(year=1950, category="neuroscience", kind="discovery", title="单细胞记录", text="单细胞记录揭示感觉与运动皮层的放电特性。"),
    dict(year=1960, category="neuroscience", kind="discovery", title="神经化学", text="1960 年代神经化学阐明递质合成、释放与代谢。"),
    dict(year=1980, category="neuroscience", kind="discovery", title="受体克隆", text="1980 年代受体分子克隆推动药理学精准化。"),
    dict(year=1990, category="neuroscience", kind="discovery", title="基因敲除", text="基因敲除小鼠用于神经功能与疾病机制研究。"),
    dict(year=1950, category="neuroscience", kind="device", title="脑磁图", text="1960 年代末脑磁图（MEG）实现无创脑磁场测量。"),
    dict(year=1980, category="neuroscience", kind="device", title="PET 脑成像", text="1980 年代 PET 用于脑代谢与受体成像。"),
    dict(year=2000, category="neuroscience", kind="discovery", title="连接组", text="2000 年代连接组学刻画脑网络组织。"),
    dict(year=2010, category="neuroscience", kind="discovery", title="神经大数据", text="2010 年代大规模神经数据推动可重复与计算研究。"),
    dict(year=1950, category="neuroscience", kind="discovery", title="注意研究", text="1950 年代选择性注意与信息处理成为认知研究核心。"),
    dict(year=1960, category="neuroscience", kind="discovery", title="语言加工", text="1960 年代语言加工的认知与神经机制被系统研究。"),
    dict(year=1970, category="neuroscience", kind="discovery", title="生物钟", text="1970 年代昼夜节律的神经与分子机制被阐明。"),
    dict(year=1980, category="neuroscience", kind="discovery", title="睡眠剥夺", text="睡眠剥夺对认知与情绪的影响被量化研究。"),
    dict(year=1990, category="neuroscience", kind="discovery", title="睡眠与记忆", text="睡眠在记忆巩固中的作用获得实验支持。"),
    dict(year=1950, category="neuroscience", kind="discovery", title="应激研究", text="应激的神经内分泌机制（HPA 轴）被系统阐明。"),
    dict(year=1960, category="neurology", kind="discovery", title="卒中分型", text="卒中按缺血与出血分型，指导治疗决策。"),
    dict(year=1970, category="neurology", kind="discovery", title="卒中溶栓前时代", text="1970 年代卒中治疗以支持与康复为主。"),
    dict(year=1980, category="neurology", kind="drug", title="抗血小板预防", text="抗血小板药物成为卒中二级预防基石。"),
    dict(year=1990, category="neurology", kind="discovery", title="卒中单元证据", text="随机证据支持卒中单元降低死亡与残疾。"),
    dict(year=2000, category="neurology", kind="discovery", title="卒中影像", text="CT/MRI 与灌注成像指导再灌注决策。"),
    dict(year=2010, category="neurology", kind="discovery", title="卒中网络", text="区域卒中网络与转运体系提升取栓可及性。"),
    dict(year=2020, category="neurology", kind="discovery", title="卒中二级预防", text="强化二级预防与危险因素管理降低复发。"),
    dict(year=1950, category="neurology", kind="discovery", title="帕金森病分类", text="帕金森病的临床分型与鉴别诊断逐步明确。"),
    dict(year=1960, category="neurology", kind="drug", title="左旋多巴", text="左旋多巴成为帕金森病治疗的核心药物。"),
    dict(year=1970, category="neurology", kind="discovery", title="运动障碍专科", text="运动障碍专科推动帕金森与其他运动疾病诊疗。"),
    dict(year=1980, category="neurology", kind="discovery", title="帕金森手术前时代", text="1980 年代毁损手术用于药物难治性运动症状。"),
    dict(year=2000, category="neurology", kind="device", title="持续多巴胺能刺激", text="持续输注与贴剂减少运动波动。"),
    dict(year=2010, category="neurology", kind="device", title="自适应刺激", text="自适应 DBS 根据症状与脑电动态调整参数。"),
    dict(year=1950, category="neurosurgery", kind="discovery", title="脑外伤管理", text="1950 年代脑外伤的颅内压与呼吸管理进步。"),
    dict(year=1960, category="neurosurgery", kind="discovery", title="神经重症监护", text="1960 年代神经重症监护单元建立。"),
    dict(year=1970, category="neurosurgery", kind="device", title="颅内压监测", text="颅内压监测用于重型脑外伤管理。"),
    dict(year=1980, category="neurosurgery", kind="discovery", title="颅脑创伤指南", text="循证指南规范颅脑创伤的影像与手术决策。"),
    dict(year=1990, category="neurosurgery", kind="surgery", title="去骨瓣减压", text="去骨瓣减压用于难治性颅内高压。"),
    dict(year=2000, category="neurosurgery", kind="discovery", title="低温治疗", text="治疗性低温用于脑损伤与心脏骤停后脑保护。"),
    dict(year=2010, category="neurosurgery", kind="device", title="多模态监测", text="多模态神经监测指导重症脑损伤治疗。"),
    dict(year=2020, category="neurosurgery", kind="discovery", title="精准神经重症", text="精准监测与个体化方案改善重症脑损伤结局。"),
    dict(year=1960, category="neurosurgery", kind="surgery", title="显微椎间盘切除", text="显微技术用于椎间盘突出，减少组织损伤。"),
    dict(year=1970, category="neurosurgery", kind="surgery", title="脊柱融合", text="融合技术用于脊柱不稳与退变。"),
    dict(year=1980, category="neurosurgery", kind="device", title="脊柱内固定", text="内固定器械提高脊柱手术稳定性。"),
    dict(year=1990, category="neurosurgery", kind="device", title="脊柱导航", text="影像导航提升脊柱手术安全性。"),
]


EXTRA3: list[dict] = [
    dict(year=1950, category="neurology", kind="discovery", title="颞叶癫痫综合征", text="颞叶癫痫的临床与脑电特征被系统描述，成为癫痫外科主要对象。"),
    dict(year=1960, category="neurosurgery", kind="surgery", title="颞叶切除标准化", text="颞叶切除的适应证与术式逐步标准化。"),
    dict(year=1970, category="neurosurgery", kind="discovery", title="癫痫术前评估", text="多学科术前评估整合脑电、影像与神经心理。"),
    dict(year=1980, category="neurology", kind="device", title="癫痫结构影像", text="MRI 用于海马硬化与皮层发育不良的识别。"),
    dict(year=1990, category="neurosurgery", kind="discovery", title="癫痫手术指南", text="指南规范难治性癫痫的手术转诊与评估。"),
    dict(year=2000, category="neurosurgery", kind="surgery", title="癫痫微创手术", text="微创与立体定向技术减少癫痫手术创伤。"),
    dict(year=2010, category="neurosurgery", kind="discovery", title="癫痫网络外科", text="以外科方式干预致痫网络而非单一病灶。"),
    dict(year=2020, category="neurology", kind="discovery", title="癫痫基因诊断", text="基因检测用于遗传性癫痫的诊断与用药指导。"),
    dict(year=1930, category="neurology", kind="discovery", title="癫痫发作分类雏形", text="1930 年代发作类型的临床与脑电分类逐步形成。"),
    dict(year=1940, category="neurology", kind="drug", title="抗癫痫药扩展", text="1940 年代多种抗癫痫药进入临床，治疗选择增加。"),
    dict(year=1950, category="neurology", kind="device", title="脑电图普及", text="1950 年代 EEG 在癫痫诊断中普及。"),
    dict(year=1960, category="neurology", kind="drug", title="卡马西平时代", text="卡马西平成为部分性发作的一线选择。"),
    dict(year=1970, category="neurology", kind="drug", title="丙戊酸广谱", text="丙戊酸成为广谱抗癫痫药的代表。"),
    dict(year=1980, category="neurology", kind="drug", title="新一代抗癫痫药", text="1980 年代起新型抗癫痫药陆续研发。"),
    dict(year=1990, category="neurology", kind="drug", title="抗癫痫药个体化", text="血药浓度监测与个体化用药改善疗效与安全。"),
    dict(year=2000, category="neurology", kind="drug", title="抗癫痫药联合", text="合理联合用药成为难治性癫痫的策略。"),
    dict(year=2010, category="neurology", kind="drug", title="抗癫痫新靶点", text="SV2A、AMPA 等新靶点药物进入临床。"),
    dict(year=2020, category="neurology", kind="discovery", title="癫痫精准用药", text="药物基因组学指导抗癫痫药选择与剂量。"),
    dict(year=1950, category="neurology", kind="discovery", title="儿童癫痫", text="儿童癫痫综合征被系统分类与管理。"),
    dict(year=1960, category="neurology", kind="discovery", title="婴儿痉挛", text="婴儿痉挛的临床与治疗被系统描述。"),
    dict(year=1970, category="neurology", kind="discovery", title="Lennox–Gastaut 综合征", text="Lennox–Gastaut 综合征被确立为严重癫痫性脑病。"),
    dict(year=1980, category="neurology", kind="discovery", title="Dravet 综合征", text="Dravet 综合征被识别为婴幼儿期严重癫痫性脑病。"),
    dict(year=1990, category="neurology", kind="discovery", title="遗传性癫痫", text="家族性癫痫的遗传基础被逐步揭示。"),
    dict(year=2000, category="neurology", kind="discovery", title="SCN1A 与 Dravet", text="SCN1A 突变与 Dravet 综合征的关联被确立。"),
    dict(year=2010, category="neurology", kind="discovery", title="癫痫精准分型", text="基因与影像整合推动癫痫的精准分型。"),
    dict(year=2020, category="neurology", kind="drug", title="癫痫基因治疗探索", text="反义寡核苷酸与基因疗法在遗传性癫痫中探索。"),
    dict(year=1950, category="neurology", kind="discovery", title="癫痫持续状态", text="癫痫持续状态被确立为神经急症并规范处理。"),
    dict(year=1960, category="neurology", kind="discovery", title="癫痫急救", text="癫痫急救流程与药物阶梯治疗逐步规范。"),
    dict(year=1970, category="neurology", kind="device", title="癫痫监护", text="癫痫监护与药物调整改善难治性发作管理。"),
    dict(year=1980, category="neurology", kind="discovery", title="癫痫管理指南", text="指南规范癫痫的诊断、治疗与随访。"),
    dict(year=1900, category="psychiatry", kind="discovery", title="精神科门诊", text="20 世纪初精神科门诊与院外服务发展。"),
    dict(year=1910, category="psychiatry", kind="discovery", title="精神卫生运动", text="精神卫生运动推动预防与公众教育。"),
    dict(year=1920, category="psychiatry", kind="discovery", title="心理治疗发展", text="1920 年代多种心理治疗流派并存发展。"),
    dict(year=1930, category="psychiatry", kind="discovery", title="精神科病房", text="精神科病房管理与治疗规范逐步建立。"),
    dict(year=1940, category="psychiatry", kind="discovery", title="战时精神医学", text="二战推动创伤应激与精神卫生服务发展。"),
    dict(year=1950, category="psychiatry", kind="drug", title="抗焦虑药物", text="1950 年代抗焦虑药物进入临床。"),
    dict(year=1960, category="psychiatry", kind="drug", title="抗抑郁药物", text="1960 年代抗抑郁药成为抑郁治疗主力。"),
    dict(year=1970, category="psychiatry", kind="drug", title="抗精神病药物", text="1970 年代抗精神病药的选择与剂量管理成熟。"),
    dict(year=1980, category="psychiatry", kind="drug", title="心境稳定剂", text="锂盐与丙戊酸等心境稳定剂用于双相障碍。"),
    dict(year=1990, category="psychiatry", kind="drug", title="非典型药物时代", text="1990 年代非典型抗精神病药广泛使用。"),
    dict(year=2000, category="psychiatry", kind="drug", title="长效针剂", text="长效抗精神病针剂改善依从性与复发。"),
    dict(year=2010, category="psychiatry", kind="discovery", title="依从性管理", text="依从性评估与共享决策成为治疗关键。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="数字依从支持", text="数字提醒与远程随访改善长期依从性。"),
    dict(year=1950, category="psychiatry", kind="discovery", title="心理社会康复", text="心理社会康复帮助患者重建社会功能。"),
    dict(year=1960, category="psychiatry", kind="discovery", title="职业康复", text="职业康复与就业支持成为康复核心。"),
    dict(year=1970, category="psychiatry", kind="discovery", title="支持性就业", text="支持性就业模式提升严重精神障碍患者就业率。"),
    dict(year=1980, category="psychiatry", kind="discovery", title="住房支持", text="支持性住房改善社区康复与稳定。"),
    dict(year=1990, category="psychiatry", kind="discovery", title="社区照护", text="社区照护与个案管理整合服务。"),
    dict(year=2000, category="psychiatry", kind="discovery", title="康复导向", text="以恢复为目标的康复服务成为主流。"),
    dict(year=2010, category="psychiatry", kind="discovery", title="同伴支持服务", text="同伴支持者参与服务提供，增强希望与参与。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="整合照护", text="精神与躯体健康整合照护提升结局。"),
    dict(year=1950, category="psychiatry", kind="discovery", title="儿童自闭症识别", text="1950 年代自闭症被逐步识别为独立发育障碍。"),
    dict(year=1960, category="psychiatry", kind="discovery", title="行为治疗", text="行为治疗用于儿童行为与发育问题。"),
    dict(year=1970, category="psychiatry", kind="discovery", title="应用行为分析", text="应用行为分析（ABA）成为自闭症干预方法。"),
    dict(year=1980, category="psychiatry", kind="discovery", title="自闭症早期干预", text="早期强化干预改善自闭症儿童发展结局。"),
    dict(year=1990, category="psychiatry", kind="discovery", title="融合教育", text="融合教育推动自闭症儿童进入普通学校。"),
    dict(year=2000, category="psychiatry", kind="discovery", title="自闭症谱系", text="自闭症谱系障碍概念整合广泛表型。"),
    dict(year=2010, category="psychiatry", kind="discovery", title="神经多样性", text="神经多样性视角改变对自闭症的公共叙事。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="成人自闭症服务", text="成人自闭症的诊断与支持服务受到关注。"),
    dict(year=1950, category="psychiatry", kind="discovery", title="进食障碍", text="神经性厌食等进食障碍被系统描述。"),
    dict(year=1960, category="psychiatry", kind="discovery", title="神经性厌食", text="神经性厌食的临床特征与风险被认识。"),
    dict(year=1970, category="psychiatry", kind="discovery", title="贪食症", text="神经性贪食被识别为独立障碍。"),
    dict(year=1980, category="psychiatry", kind="discovery", title="CBT 治疗进食障碍", text="认知行为治疗成为进食障碍的循证治疗。"),
    dict(year=1990, category="psychiatry", kind="discovery", title="家庭治疗进食障碍", text="家庭为基础的治疗用于青少年厌食症。"),
    dict(year=2000, category="psychiatry", kind="discovery", title="进食障碍早期干预", text="早期识别与干预改善进食障碍预后。"),
    dict(year=2010, category="psychiatry", kind="discovery", title="进食障碍预防", text="学校与社区预防项目减少进食障碍风险。"),
    dict(year=2020, category="psychiatry", kind="discovery", title="数字进食障碍治疗", text="数字干预扩展进食障碍的可及治疗。"),
    dict(year=1950, category="neuroscience", kind="discovery", title="神经生理学", text="1950 年代神经生理学阐明反射与运动控制。"),
    dict(year=1960, category="neuroscience", kind="discovery", title="神经药理学", text="1960 年代神经药理学建立递质与药物作用框架。"),
    dict(year=1970, category="neuroscience", kind="discovery", title="神经化学", text="1970 年代神经化学解析递质代谢与受体。"),
    dict(year=1980, category="neuroscience", kind="discovery", title="分子神经科学", text="1980 年代分子技术推动受体与通道研究。"),
    dict(year=1990, category="neuroscience", kind="discovery", title="神经遗传学", text="1990 年代神经疾病的遗传基础被系统研究。"),
    dict(year=2000, category="neuroscience", kind="discovery", title="神经影像学", text="2000 年代多模态影像成为神经科学常规工具。"),
    dict(year=2010, category="neuroscience", kind="discovery", title="神经组学", text="2010 年代组学技术解析脑的分子与细胞多样性。"),
    dict(year=2020, category="neuroscience", kind="discovery", title="计算神经科学", text="2020 年代计算模型与大数据结合解释脑功能。"),
    dict(year=1950, category="neuroscience", kind="device", title="脑刺激", text="1950 年代脑刺激用于功能定位与机制研究。"),
    dict(year=1960, category="neuroscience", kind="device", title="深部脑刺激实验", text="1960 年代深部脑刺激开始用于研究与治疗探索。"),
    dict(year=1980, category="neuroscience", kind="device", title="神经调控", text="1980 年代神经调控技术扩展至运动与精神障碍。"),
    dict(year=1990, category="neuroscience", kind="device", title="TMS 研究", text="1990 年代 TMS 用于皮层兴奋性与可塑性研究。"),
    dict(year=2000, category="neuroscience", kind="device", title="闭环刺激", text="2000 年代闭环刺激根据脑电实时调节治疗。"),
    dict(year=2010, category="neuroscience", kind="device", title="自适应神经调控", text="2010 年代自适应刺激与解码技术结合。"),
    dict(year=1950, category="neuroscience", kind="discovery", title="神经可塑性", text="1950 年代可塑性概念用于解释经验对脑的影响。"),
    dict(year=1960, category="neuroscience", kind="discovery", title="突触可塑性", text="1960 年代突触效能改变被实验证实。"),
    dict(year=1970, category="neuroscience", kind="discovery", title="长时程增强（LTP）", text="LTP 被发现，成为学习记忆的突触模型。"),
    dict(year=1980, category="neuroscience", kind="discovery", title="长时程抑制（LTD）", text="LTD 被发现，补充可塑性的双向机制。"),
    dict(year=1990, category="neuroscience", kind="discovery", title="可塑机制", text="1990 年代可塑性的分子与环路机制被阐明。"),
    dict(year=2000, category="neuroscience", kind="discovery", title="成人神经发生", text="成人海马神经发生的存在与功能被系统研究。"),
    dict(year=2010, category="neuroscience", kind="discovery", title="可塑性与疾病", text="可塑性异常被联系到神经与精神疾病。"),
    dict(year=2020, category="neuroscience", kind="discovery", title="可塑性治疗", text="以可塑性为靶点的治疗策略进入研究。"),
    dict(year=1950, category="neurology", kind="discovery", title="头痛诊疗", text="1950 年代头痛的临床分类与诊疗体系建立。"),
    dict(year=1960, category="neurology", kind="discovery", title="偏头痛机制", text="1960 年代偏头痛的血管与神经机制被研究。"),
    dict(year=1970, category="neurology", kind="discovery", title="头痛分类", text="头痛的国际分类推动诊断标准化。"),
    dict(year=1980, category="neurology", kind="discovery", title="偏头痛治疗", text="1980 年代偏头痛急性与预防治疗进步。"),
    dict(year=1990, category="neurology", kind="drug", title="曲普坦时代", text="曲普坦类革新偏头痛急性治疗。"),
    dict(year=2000, category="neurology", kind="discovery", title="CGRP 机制", text="CGRP 在偏头痛中的作用被确立。"),
    dict(year=2010, category="neurology", kind="drug", title="CGRP 靶向治疗", text="CGRP 单抗与小分子革新偏头痛预防。"),
    dict(year=2020, category="neurology", kind="drug", title="CGRP 小分子", text="口服 CGRP 受体拮抗剂扩展急性与预防选择。"),
    dict(year=1960, category="neurology", kind="device", title="肌电图", text="肌电图（EMG）用于神经肌肉疾病诊断。"),
    dict(year=1970, category="neurology", kind="device", title="神经传导", text="神经传导研究用于周围神经病评估。"),
    dict(year=1980, category="neurology", kind="discovery", title="肌病分类", text="肌病的临床与病理分类逐步完善。"),
    dict(year=1990, category="neurology", kind="discovery", title="遗传性神经病", text="遗传性周围神经病的基因基础被揭示。"),
    dict(year=2000, category="neurology", kind="discovery", title="免疫性神经病", text="免疫介导的神经病被识别并可用免疫治疗。"),
    dict(year=2010, category="neurology", kind="discovery", title="神经抗体", text="抗神经抗体检测推动自身免疫神经病精准诊断。"),
    dict(year=2020, category="neurology", kind="discovery", title="神经肌肉精准", text="基因与抗体标志推动神经肌肉疾病精准治疗。"),
    dict(year=1960, category="neurosurgery", kind="device", title="脑室分流", text="脑室-腹腔分流用于脑积水治疗。"),
    dict(year=1970, category="neurosurgery", kind="device", title="脑室镜", text="内镜用于脑室病变与脑积水处理。"),
    dict(year=1980, category="neurosurgery", kind="device", title="内镜技术", text="神经内镜技术扩展至囊肿与脑室病变。"),
    dict(year=1990, category="neurosurgery", kind="device", title="内镜颅底", text="内镜用于颅底与垂体病变。"),
    dict(year=2000, category="neurosurgery", kind="device", title="内镜扩大入路", text="内镜经鼻扩大入路处理复杂颅底病变。"),
    dict(year=2010, category="neurosurgery", kind="device", title="内镜与导航", text="内镜结合导航提升深部病变处理精度。"),
    dict(year=2020, category="neurosurgery", kind="device", title="内镜机器人", text="机器人辅助内镜提升操作稳定性。"),
    dict(year=1960, category="neurosurgery", kind="surgery", title="颅骨修补", text="颅骨修补材料与技术改善术后外观与保护。"),
    dict(year=1980, category="neurosurgery", kind="device", title="3D 打印颅骨", text="3D 打印用于个性化颅骨修补。"),
    dict(year=1990, category="neurosurgery", kind="device", title="术中影像", text="术中影像提升深部病变的切除精度。"),
    dict(year=2000, category="neurosurgery", kind="device", title="术中导航", text="导航系统整合术前与术中影像。"),
    dict(year=2010, category="neurosurgery", kind="device", title="机器人辅助", text="机器人用于立体定向与深部电极植入。"),
    dict(year=2020, category="neurosurgery", kind="device", title="个性化植入", text="个性化植入物用于复杂颅颌面与脊柱重建。"),
]


EXTRA4: list[dict] = [
    dict(year=1950, category="neurology", kind="discovery", title="神经眼科", text="神经眼科关注视神经与眼球运动的中枢机制。"),
    dict(year=1960, category="neurology", kind="discovery", title="神经耳科", text="神经耳科聚焦前庭与听觉通路的中枢病变。"),
    dict(year=1970, category="neurology", kind="discovery", title="神经康复专科", text="神经康复专科整合物理、作业与言语治疗。"),
    dict(year=1980, category="neuroscience", kind="discovery", title="神经心理康复", text="神经心理康复针对注意、记忆与执行功能训练。"),
    dict(year=1990, category="neuroscience", kind="discovery", title="认知康复", text="认知康复用于脑损伤与神经退行性疾病的认知维护。"),
    dict(year=2000, category="neuroscience", kind="discovery", title="可塑性导向康复", text="以神经可塑性为理论基础的强化康复方案推广。"),
    dict(year=2010, category="neurosurgery", kind="device", title="康复机器人", text="康复机器人与外骨骼用于卒中与脊髓损伤训练。"),
    dict(year=2020, category="neurology", kind="discovery", title="数字康复", text="远程监测与数字疗法扩展神经康复的可及性。"),
    dict(year=1950, category="neuroscience", kind="discovery", title="神经病理学", text="神经病理学系统描述神经疾病的组织学特征。"),
    dict(year=1960, category="neuroscience", kind="discovery", title="免疫组化", text="免疫组化用于神经组织蛋白定位与病理诊断。"),
    dict(year=1970, category="neuroscience", kind="discovery", title="电子显微镜", text="电镜揭示突触与细胞器的超微结构。"),
    dict(year=1980, category="neuroscience", kind="discovery", title="分子病理", text="分子技术进入神经病理，推动疾病分型。"),
]


EVERGREEN_ALL: list[dict] = list({
    (e.get("year"), e["title"]): e
    for e in (EVERGREEN + EVERGREEN_MORE + EVERGREEN_MORE2 + EVERGREEN_MORE3
              + PSYCH_BATCH + EPILEPSY_BATCH + GENERAL_BATCH + EXTRA1 + EXTRA2 + EXTRA3
              + EXTRA4)
}.values())


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


BODIES_PSY_EPI: dict[tuple[int, str], str] = {
    (1886, "Horsley 首例癫痫手术"): (
        "1886 年，英国神经外科先驱 Victor Horsley 为一名药物难治性癫痫患者实施了致痫皮层切除，"
        "被普遍视为现代癫痫外科的开端。在此之前，癫痫常被当作不可干预的“神圣疾病”，"
        "外科医生极少敢于直接处理大脑皮层。Horsley 的突破在于把实验神经生理学带入手术室："
        "他熟悉电刺激皮层诱发的运动反应，能够据此判断致痫灶的大致位置，并在开颅后切除异常组织。\n\n"
        "这一步的意义不仅是技术性的，更是观念性的。它首次系统表明：癫痫可以由一个可定位的脑区产生，"
        "而切除这个脑区可能减少发作。这一“致痫灶”思想，成为此后一个多世纪癫痫外科的核心假设，"
        "并催生了皮层电刺激定位、脑电图定位与影像定位等一系列方法。\n\n"
        "当然，1886 年的条件极为有限：没有脑电图、没有影像、没有现代麻醉与监护，"
        "手术风险极高，疗效也难以客观评估。但 Horsley 确立的路径——以生理与临床证据定位、"
        "以手术干预致痫网络——延续至今。今天，SEEG、MRI、PET 与术中电生理让定位更精确，"
        "而激光消融、反应性神经刺激等微创手段扩展了干预方式。回望 1886 年，"
        "那台手术的价值不在于成功率的数字，而在于它把癫痫从“不可治”推进到“可手术”。"
    ),
    (1934, "蒙特利尔神经病学研究所成立"): (
        "1934 年，Wilder Penfield 在麦吉尔大学与洛克菲勒基金会支持下创立蒙特利尔神经病学研究所（MNI），"
        "把神经内科、神经外科与基础研究放在同一屋檐下，形成“临床—电生理—病理”协作的范式。"
        "这一跨学科结构，后来被视为现代神经科学机构的模板。\n\n"
        "MNI 最具影响力的创新，是在癫痫手术中使用术中皮层电刺激：在局麻或唤醒状态下，"
        "用电极逐点刺激暴露的皮层，观察患者的运动、感觉、语言与记忆反应，"
        "从而在切除致痫灶的同时尽量保护功能区。Penfield 与 Jasper 等人由此绘制了著名的"
        "皮层功能地图（homunculus），并系统总结了癫痫的皮层定位与手术经验。\n\n"
        "MNI 还培训了遍布世界的神经外科与神经内科医生，使癫痫外科从少数中心的探索变成可复制的学科。"
        "今天，术中电刺激、清醒开颅、SEEG 与功能影像共同构成术前与术中评估体系，"
        "但其思想源头仍是 MNI 的“边做边测、边测边保”的方法论。回望 1934 年，"
        "MNI 的成立不仅是一个机构的诞生，更是癫痫外科与功能神经外科制度化的起点。"
    ),
    (1936, "Penfield 术中皮层电刺激"): (
        "1936 年前后，Wilder Penfield 在蒙特利尔系统开展术中皮层电刺激，用于癫痫手术中的功能定位。"
        "他在患者清醒或局麻状态下，用电极刺激暴露的皮层，记录患者的运动、感觉、语言与记忆反应，"
        "由此把“哪块皮层负责什么功能”从解剖推测变成可重复的术中观察。\n\n"
        "这项技术解决了癫痫外科最核心的矛盾：致痫灶往往紧邻功能区，切多了会损伤功能，"
        "切少了会残留发作。术中电刺激提供了一个实时的“功能边界”，让外科医生能够在两者之间取得平衡。"
        "Penfield 与 Jasper 后来出版的癫痫专著，系统总结了皮层定位、发作类型与手术结局，"
        "成为几代神经外科医生的教科书。\n\n"
        "今天的术中定位已扩展到诱发电位、皮层脑电、高密度电极与功能磁共振，"
        "但“用电刺激验证功能、再决定切除范围”的原则没有改变。清醒开颅手术中，"
        "患者边说话或边执行任务、医生边刺激边观察的场景，正是 Penfield 方法的直接延续。"
        "回望 1936 年，这项技术的价值在于它把功能保护从“经验判断”变成“可验证的术中证据”。"
    ),
    (1960, "SEEG 立体脑电图"): (
        "1960 年代，Jean Talairach 与 Jean Bancaud 在巴黎发展出立体定向脑电图（SEEG）："
        "通过立体定向技术把多根深部电极植入脑内，直接记录皮层与深部结构的电活动，"
        "从而在三维空间中定位致痫网络。与只能覆盖皮层表面的硬膜下电极相比，SEEG 能同时采样"
        "海马、杏仁核、岛叶、扣带回等深部结构，且创伤相对更小。\n\n"
        "SEEG 的核心贡献是把癫痫从“一个病灶”重新理解为“一个网络”。通过多电极同步记录，"
        "医生可以观察发作在脑区之间的传播路径，判断哪些节点是“致痫区”、哪些是“传播区”，"
        "从而设计更精准的切除或离断方案。这一网络视角，深刻影响了此后的癫痫外科与神经科学。\n\n"
        "今天，SEEG 已成为药物难治性癫痫术前评估的重要手段，并与机器人辅助植入、"
        "高密度电极、脑电-影像融合与计算分析结合。其局限也很明显：有创、耗时、需要专门团队。"
        "回望 1960 年代，SEEG 的意义在于它提供了一种“从内部看网络”的方法，"
        "把癫痫外科从形态学定位推进到电生理网络定位。"
    ),
    (1997, "VNS 获批治疗癫痫"): (
        "1997 年，美国 FDA 批准迷走神经刺激（VNS）用于药物难治性癫痫，成为神经调控治疗癫痫的重要里程碑。"
        "VNS 通过植入颈部迷走神经的电极，按设定参数发送电脉冲，经孤束核等通路影响广泛脑区，"
        "从而降低发作频率。它不切除脑组织，也不直接刺激致痫灶，而是通过调节网络兴奋性起作用。\n\n"
        "VNS 的临床价值在于为不适合切除手术的患者提供了另一种选择。对于多灶性癫痫、"
        "致痫灶位于功能区或切除后仍发作的患者，VNS 可以作为一种辅助治疗。其疗效通常表现为"
        "发作频率的下降而非完全消失，且需要数月逐步调整参数；常见副作用包括声音改变、"
        "咳嗽与咽喉不适，多数可耐受。\n\n"
        "VNS 也开启了“神经调控治疗癫痫”的路径，此后丘脑前核 DBS（2010 年试验支持、2018 年获批）"
        "与反应性神经刺激 RNS（2013 年获批）相继出现，形成切除、离断、调控并存的治疗格局。"
        "回望 1997 年，VNS 的意义不仅是多了一种设备，更是把癫痫治疗从“切与不切”"
        "扩展到“调节网络兴奋性”的新维度。"
    ),
    (2011, "激光间质热疗（LITT）"): (
        "2011 年前后，磁共振引导激光间质热疗（LITT）开始用于癫痫外科。其做法是："
        "在立体定向引导下把一根细激光光纤置入致痫灶，通过激光加热精准消融目标组织，"
        "同时用实时磁共振热成像监控消融范围与周围结构温度。相比开颅切除，LITT 创伤更小、"
        "住院时间更短，特别适合深部病灶（如海马、下丘脑错构瘤、室管膜下结节）。\n\n"
        "LITT 的优势在于“精准与可控”：热成像让医生能实时看到消融边界，避免损伤邻近的血管与神经结构；"
        "对于位置深、开颅难以到达的病灶，LITT 提供了一条微创路径。其在颞叶内侧癫痫、"
        "下丘脑错构瘤相关痴笑性癫痫等场景中显示出良好前景。\n\n"
        "局限也同样明显：消融范围受热沉效应与脑脊液流动影响，病灶过大或靠近大血管时效果受限；"
        "长期无发作率仍需与开颅切除进行更充分的比较。回望 2011 年，LITT 代表了癫痫外科"
        "“微创化”的方向——在不牺牲精准的前提下，减少手术创伤与恢复负担。"
    ),
    (2013, "RNS 获 FDA 批准"): (
        "2013 年，美国 FDA 批准反应性神经刺激（RNS）用于药物难治性局灶性癫痫。RNS 是一种闭环系统："
        "颅内电极持续监测脑电，当算法识别到异常放电模式时，立即发送短暂电刺激以中止或减弱发作。"
        "与持续刺激的 VNS、DBS 不同，RNS 只在需要时干预，因而被称为“按需刺激”。\n\n"
        "RNS 的意义在于它把癫痫治疗从“开环”推向“闭环”。传统调控依赖固定参数，"
        "而 RNS 根据个体脑电实时调整，理论上更贴近癫痫的动态本质。临床研究中，RNS 可显著降低"
        "发作频率，且随着时间推移疗效可能进一步增强。由于需要植入颅内电极，其适用人群、"
        "手术风险与长期安全性需要严格评估。\n\n"
        "RNS 也推动了“致痫网络”与“发作预测”的研究：要决定电极放哪里、如何定义异常模式，"
        "必须先理解个体化的癫痫网络。回望 2013 年，RNS 不仅是多了一种设备，"
        "更标志着癫痫治疗进入“感知—判断—干预”一体化的闭环时代。"
    ),
    (1952, "氯丙嗪进入精神科"): (
        "1952 年，法国精神科医生 Jean Delay 与 Pierre Deniker 报告氯丙嗪能显著改善精神病性症状，"
        "随后氯丙嗪在全球精神科迅速推广。这被视为现代精神药理学的起点，也是精神科从“收容管理”"
        "走向“药物治疗”的分水岭。\n\n"
        "氯丙嗪最初作为抗组胺与麻醉辅助药物被合成，其镇静与情绪平抑作用被观察到后，"
        "才被用于精神病性障碍。它的机制后来被解释为阻断多巴胺 D2 受体，这一发现不仅解释了"
        "抗精神病作用，也解释了锥体外系反应、催乳素升高等副作用，并催生了“多巴胺假说”。\n\n"
        "氯丙嗪的社会影响同样深远：它使大量患者得以出院、进入社区，推动了去机构化浪潮；"
        "它也让精神科成为有明确药物武器的临床学科，吸引了大量研究与产业投入。"
        "当然，它并非“治愈”，副作用与依从性问题随之而来，后续的非典型抗精神病药正是对其局限的回应。"
        "回望 1952 年，氯丙嗪的意义在于它第一次证明：严重精神障碍可以被一种药物系统性地改变。"
    ),
    (1938, "电休克治疗（ECT）"): (
        "1938 年，意大利精神科医生 Ugo Cerletti 与 Lucio Bini 首次在患者身上使用电休克治疗（ECT），"
        "通过短暂电流诱发全身性抽搐以治疗严重精神障碍。此前，医生曾用胰岛素休克、"
        "药物诱发抽搐等方法，但 ECT 更可控、更可重复，很快在世界范围内推广。\n\n"
        "ECT 的机制至今未被完全阐明，主流解释涉及癫痫样放电对神经可塑性、"
        "神经递质与网络同步性的调节。现代 ECT 在全身麻醉与肌松下进行，"
        "通过个体化剂量与电极位置减少认知副作用，已成为难治性抑郁症、紧张症与部分精神病性障碍的"
        "有效治疗之一。\n\n"
        "ECT 的历史充满争议：早期操作粗暴、记忆副作用明显，曾被污名化为“惩罚性”手段；"
        "但大量证据表明，对特定患者它起效快、疗效确切，尤其在药物无效或有高自杀风险时。"
        "回望 1938 年，ECT 的意义在于它开启了“物理手段调节脑功能以治疗精神疾病”的路径，"
        "并为后来的 TMS、DBS 与迷幻药等神经调控治疗埋下伏笔。"
    ),
    (1949, "Cade 发现锂盐疗效"): (
        "1949 年，澳大利亚精神科医生 John Cade 发现锂盐能够稳定情绪、改善躁狂，"
        "并在随后被用于双相障碍的维持治疗。这被视为现代精神药理学的第一块基石，"
        "也是“单一离子治疗精神疾病”的经典案例。\n\n"
        "Cade 的发现带有一定的偶然性：他最初研究尿酸与躁狂的关系，"
        "用锂盐作为助溶剂，却观察到锂盐本身具有镇静与情绪稳定作用。此后，"
        "锂盐逐步被证实可降低躁狂与抑郁复发、减少自杀风险，并成为双相障碍的一线治疗。"
        "其机制涉及糖原合成酶激酶-3（GSK-3）、肌醇信号与神经营养通路，至今仍在研究。\n\n"
        "锂盐的临床使用也确立了“治疗药物监测”的重要性：锂的治疗窗窄，"
        "血药浓度过高可导致震颤、肾与甲状腺毒性，因此需要定期监测。"
        "回望 1949 年，Cade 的发现不仅提供了一种药物，更证明了精神疾病可以由简单的化学物质"
        "系统性调节，为后续抗精神病药与抗抑郁药的研发提供了信心与范式。"
    ),
    (1980, "DSM-III 出版"): (
        "1980 年，美国精神病学会出版《精神障碍诊断与统计手册》第三版（DSM-III），"
        "以可操作的诊断标准取代此前以理论描述为主的分类。它规定了每条诊断的症状条目、"
        "持续时间、排除标准与功能损害要求，使精神科诊断第一次具备了较高的可重复性。\n\n"
        "DSM-III 的影响是革命性的。它为临床研究提供了统一入组标准，使随机试验与流行病学调查"
        "能够在同一语言下进行；它推动了精神科从“学派之争”走向“证据积累”；"
        "它也深刻影响了保险支付、司法鉴定与公共卫生统计。此后的 DSM-IV（1994）与 DSM-5（2013）"
        "在其框架上不断修订。\n\n"
        "批评同样持续：以症状条目定义的类别可能掩盖疾病的生物学异质性，"
        "共病与阈值问题突出，这也是 NIMH 后来推出 RDoC 的动因之一。"
        "回望 1980 年，DSM-III 的意义在于它把精神科诊断从“临床印象”变成“可检验的操作标准”，"
        "为现代精神医学的研究与临床奠定了基础，同时也暴露了类别化诊断的局限。"
    ),
}


BODIES_PSY_EPI_EXTRA: dict[tuple[int, str], str] = {
    (1886, "Horsley 首例癫痫手术"): (
        "从更长的时间尺度看，Horsley 确立的是“定位—切除—验证”的循环：先用临床与电生理证据定位，"
        "再手术切除，最后用发作是否减少来验证假设。今天的术前评估是这一循环的复杂化版本——"
        "视频脑电、SEEG、MRI、PET 与神经心理共同给出证据，手术计划则在多学科讨论中形成。"
        "与此同时，Horsley 时代被忽视的问题今天被认真对待：功能保护、认知结局、生活质量与伦理同意。"
        "癫痫外科因此不再只是“切除致痫灶”，而是在疗效、功能与风险之间做个体化权衡。"
    ),
    (1934, "蒙特利尔神经病学研究所成立"): (
        "MNI 的另一个遗产是“数据库与随访文化”：Penfield 团队系统记录每次手术的刺激反应、"
        "切除范围与长期发作结局，形成了可被后人反复分析的知识库。这种以结构化数据支撑临床决策的做法，"
        "在现代癫痫外科中演化为登记研究、影像数据库与预测模型。MNI 还证明了神经外科可以与"
        "神经生理学、病理学、心理学深度协作，而不是各自为战。今天讨论的“多学科癫痫中心”，"
        "其组织形态与 MNI 的早期实践一脉相承。回望 1934 年，它留下的不是某一张地图，"
        "而是一种把临床问题转化为可研究问题的机构文化。"
    ),
    (1936, "Penfield 术中皮层电刺激"): (
        "这项技术的现代版本更加精细：高密度皮层电极、单脉冲电刺激、诱发电位与术中脑电可以"
        "在毫米尺度上描绘功能边界；功能磁共振与弥散成像则在术前提供个体化地图。"
        "但技术越精细，越凸显一个根本问题：功能是网络属性，而非孤立点。刺激一个点可能通过"
        "网络影响远处区域，切除一个“非功能区”也可能改变网络动力学。因此，现代癫痫外科强调"
        "“功能网络保护”，而不仅是“避开某个点”。Penfield 的方法提醒我们：术中验证不可替代，"
        "但解释验证结果需要网络视角。"
    ),
    (1960, "SEEG 立体脑电图"): (
        "SEEG 的现代实践已高度工程化：机器人辅助植入、数十至上百个电极触点、"
        "高频振荡与单细胞样放电分析、与 MRI/CT 融合的三维重建，使医生能在发作起始前"
        "就识别致痫网络的关键节点。其局限同样需要正视：电极只能采样有限区域，"
        "“没记录到”不等于“没问题”；有创操作存在出血与感染风险；结果高度依赖团队经验。"
        "因此，SEEG 不是“终极答案”，而是把临床问题转化为可检验的电生理假设的工具。"
        "回望 1960 年代，Talairach 与 Bancaud 的真正贡献，是让癫痫外科从“看结构”转向“读网络”。"
    ),
    (1997, "VNS 获批治疗癫痫"): (
        "VNS 的临床经验也塑造了医生与患者对“调控治疗”的预期：它通常不是“根治”，"
        "而是“减发作、改善生活质量”，需要数月滴定与耐心随访。这种“以功能与生活质量为目标”的"
        "评价方式，后来被 DBS 与 RNS 继承。与此同时，VNS 的机制研究推动了迷走神经—孤束核—"
        "蓝斑—广泛皮层通路的研究，也让“外周神经刺激调节中枢”成为神经调控的重要分支。"
        "回望 1997 年，VNS 的意义在于它把癫痫治疗的目标从“无发作”扩展为“更好的生活”。"
    ),
    (2011, "激光间质热疗（LITT）"): (
        "LITT 的推广也改变了患者对脑手术的想象：一根光纤、一个小骨孔、数小时消融，"
        "即可处理深部致痫灶，术后恢复显著加快。这使其在儿童与老年患者、以及无法耐受开颅者中"
        "尤具吸引力。但“微创”不等于“简单”：靶点选择、光纤路径规划、热剂量控制与术后水肿管理"
        "都要求高度专业化的团队；对于较大或形态不规则的病灶，消融可能不完整。"
        "回望 2011 年，LITT 代表的是癫痫外科的“精准微创化”趋势——以更小的代价，换取可比的发作控制。"
    ),
    (2013, "RNS 获 FDA 批准"): (
        "RNS 的深层意义在于它把“发作检测”变成治疗的一部分：系统必须实时判断脑电是否异常，"
        "这推动了癫痫发作预测、脑电解码与个体化算法的发展。其局限也很现实：需要开颅植入电极，"
        "设备与随访成本高，且并非所有患者都适合；长期电池寿命与软件更新也是工程挑战。"
        "回望 2013 年，RNS 让“闭环神经调控”从概念走向临床，也为未来的自适应 DBS、"
        "可穿戴监测与个性化刺激奠定了基础。"
    ),
    (1952, "氯丙嗪进入精神科"): (
        "氯丙嗪的遗产是双重的。一方面，它确立了“以受体为靶点治疗精神病”的范式，"
        "直接催生了氟哌啶醇、氯氮平、利培酮等一系列药物，并让“多巴胺假说”成为精神分裂症研究的中心。"
        "另一方面，它暴露了“阻断越强、副作用越大”的困境：锥体外系反应、迟发性运动障碍、"
        "代谢问题与依从性下降，促使后续药物追求更平衡的受体谱。"
        "回望 1952 年，氯丙嗪不仅是一种药，更是精神科从“照护”走向“治疗”的转折点。"
    ),
    (1938, "电休克治疗（ECT）"): (
        "现代 ECT 已高度规范化：全身麻醉、肌松、个体化电量与电极位置、治疗前评估与"
        "认知监测共同降低风险；超短脉冲与单侧刺激等技术减少记忆副作用。"
        "证据显示，对严重抑郁、紧张症与部分难治性精神病，ECT 的起效速度与有效率仍具优势。"
        "但其污名与可及性仍是问题：公众误解、资源不足与伦理争议限制了使用。"
        "回望 1938 年，ECT 的启示是：一项治疗的价值应由证据与个体化风险评估决定，"
        "而非由历史污名决定。"
    ),
    (1949, "Cade 发现锂盐疗效"): (
        "锂盐的现代地位依然稳固：它被指南列为双相障碍的一线维持治疗，"
        "在预防躁狂与抑郁复发、降低自杀风险方面具有独特证据。其使用依赖规范监测——"
        "血锂浓度、肾功能、甲状腺功能与心电图；妊娠期与老年患者需特别谨慎。"
        "机制研究则把锂盐与 GSK-3 抑制、神经营养与线粒体功能联系起来，"
        "使其成为“简单离子、复杂机制”的典范。回望 1949 年，Cade 的发现提醒我们："
        "有时最重要的治疗突破，来自对临床现象的耐心观察，而非复杂技术。"
    ),
    (1980, "DSM-III 出版"): (
        "DSM-III 之后，精神科研究进入“可重复”的时代：多中心试验得以用统一标准入组，"
        "诊断信度显著提升，药物研发与流行病学调查有了共同语言。但它也带来“类别化”的副作用："
        "阈值附近的患者被割裂，共病被系统性放大，而生物学异质性被掩盖。"
        "这正是后续维度化（如 RDoC、HiTOP）与精准精神医学兴起的背景。"
        "回望 1980 年，DSM-III 既是一座里程碑，也是一面镜子——它让精神科变得可研究，"
        "也让人们看清“以症状分类”的天花板。"
    ),
}


BODIES_PSY_EPI_CLOSE: dict[tuple[int, str], str] = {
    (1886, "Horsley 首例癫痫手术"): (
        "对今天的临床团队而言，Horsley 的启示是：术前证据越充分，手术决策越安全；"
        "而当证据不足时，宁可暂缓、继续评估，也不应以“探索”为名冒进。癫痫外科的进步，"
        "正是建立在这种对证据与风险的克制之上。"
    ),
    (1934, "蒙特利尔神经病学研究所成立"): (
        "MNI 的经验说明，癫痫外科的进步依赖长期随访与数据积累，而非单台手术的成败。"
        "今天的癫痫中心若想复制其成功，需要的不仅是设备，更是愿意记录、复盘与共享的团队文化。"
    ),
    (1936, "Penfield 术中皮层电刺激"): (
        "在清醒手术中，患者的每一次应答都是对功能边界的确认；这份“以人为本”的验证传统值得延续。"
        "技术会更替，但“在切除之前先确认功能”的原则，仍是癫痫外科不可让渡的底线。"
    ),
    (1960, "SEEG 立体脑电图"): (
        "对患者而言，SEEG 意味着更长的评估周期与有创风险；对医生而言，它意味着更精确的假设与更大的责任。"
        "只有在多学科团队充分讨论、获益大于风险时，这项技术才真正物有所值。"
    ),
    (1997, "VNS 获批治疗癫痫"): (
        "VNS 的普及也提醒：设备治疗需要长期随访、参数优化与患者教育，不能“植入即结束”。"
        "对难治性癫痫患者，合理设定“减少发作、改善生活”的预期，往往比追求“完全无发作”更现实。"
    ),
    (2011, "激光间质热疗（LITT）"): (
        "LITT 的推广依赖影像、热控与多学科协作，其长期价值仍需与开颅手术的头对头证据。"
        "在适应证选择上，病灶大小、位置与血管邻近程度，决定了它究竟是“最优解”还是“次优解”。"
    ),
    (2013, "RNS 获 FDA 批准"): (
        "RNS 让“个体化算法”成为治疗的一部分，也提出了数据隐私、设备维护与公平可及的新问题。"
        "未来若能与可穿戴监测、远程随访结合，闭环治疗有望从少数中心走向更广泛的人群。"
    ),
    (1952, "氯丙嗪进入精神科"): (
        "今天的精神科在追求疗效的同时，更强调代谢监测、共享决策与功能恢复，这是对氯丙嗪时代的修正。"
        "从“控制症状”到“改善生活”，精神药理学用了七十年才逐渐校准目标。"
    ),
    (1938, "电休克治疗（ECT）"): (
        "对难治性抑郁与紧张症，及时转介 ECT 可能挽救生命；关键在于规范操作与充分知情同意。"
        "把 ECT 从污名中还原为一种有证据的医疗手段，是精神科公众沟通的长期任务。"
    ),
    (1949, "Cade 发现锂盐疗效"): (
        "锂盐的案例说明，老药未必过时；在精准医学时代，它仍是双相障碍不可替代的基石之一。"
        "对研究者而言，它也是一种提醒：机制复杂的疾病，未必需要复杂的分子才能被有效干预。"
    ),
    (1980, "DSM-III 出版"): (
        "今天的诊断改革仍在继续：从类别到维度、从症状到机制，目标始终是更接近疾病的真实结构。"
        "DSM-III 的功过提醒我们：分类是工具，不是真理；工具应随证据演进而修订。"
    ),
}


def _decorate(e: dict, match: str) -> dict:
    item = dict(e)
    item["category_label"] = CATEGORY_LABELS.get(e.get("category", ""), e.get("category", ""))
    item["kind_label"] = KIND_LABELS.get(e.get("kind", ""), "历史事件")
    item["match"] = match
    key = (e.get("year"), e.get("title"))
    parts = [BODIES.get(key), BODIES_EXTRA.get(key), BODIES_CLOSING.get(key),
             BODIES_PSY_EPI.get(key), BODIES_PSY_EPI_EXTRA.get(key), BODIES_PSY_EPI_CLOSE.get(key)]
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
    item = EVERGREEN_ALL[d.toordinal() % len(EVERGREEN_ALL)]
    return [_decorate(item, "evergreen")]


def today_events(d: _date | None = None) -> list[dict]:
    """Exact events if today has any; otherwise a different classic milestone each day."""
    d = d or _date.today()
    exact = events_for(d.month, d.day)
    if exact:
        return exact
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
