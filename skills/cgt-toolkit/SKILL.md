---
name: cgt-toolkit
description: 细胞与基因治疗（CGT）工具箱：把 CGT 项目问题落成可核算的参数、可执行的时间表与可核验的清单。用于（1）剂量/载体量/批次数/单例成本与 rNPV 的快速核算；（2）技术路线与靶点选型对比；（3）CMC 放行项与可比性方案设计；（4）临床剂量递增与终点体系搭建；（5）中国 818/828 双轨与美国 RMAT 等注册路径规划；（6）基因组安全与长期随访评估；（7）立项与 BD 尽调清单；（8）产出结构化中文 HTML 报告。触发词：CGT、细胞与基因治疗、CAR-T、TCR-T、TIL、CAR-NK、AAV、慢病毒、LVV、基因编辑、CRISPR、碱基编辑、先导编辑、iPSC、HSC 基因治疗、溶瘤病毒、VCN、RCL、放行、效力 assay、CMC、IND、BLA、NDA、RMAT、ATMP、818号令、828号令、rNPV、CVR、COGS、单例成本。
version: "1.0.0"
---

# CGT 工具箱

本技能把 CGT 项目里最容易"拍脑袋"的四类数字，变成可用计算器核算、可引用、可复现的结论：

1. **剂量与用量**——细胞数、载体总量、注射体积、批次数与产能缺口。
2. **成本与估值**——单例 COGS、毛利率、rNPV 与敏感性。
3. **方案与路径**——技术路线对比、放行项清单、注册时间表。
4. **判断与清单**——基因组安全、尽调与 kill criteria。

## 一、脚本能力边界

| 脚本 | 做什么 | 不做什么 |
|---|---|---|
| `scripts/cgt_calc.py cell` | 按体重/剂量算 CAR-T 总细胞数、所需载体感染量（MOI）、单批可覆盖患者数、清淋后回输浓度 | 不预测疗效，不替代工艺开发数据 |
| `scripts/cgt_calc.py aav` | 按 vg/kg 算载体总量、成品体积、按批产量的批次数缺口、每剂载体成本 | 不评估空壳率与实心率对效力的影响 |
| `scripts/cgt_calc.py rnpv` | 多适应症 rNPV、概率加权现金流、峰值销售衰减、敏感性排序 | 不替代可比公司交易倍数与市场博弈判断 |
| `scripts/cgt_calc.py cogs` | 单例成本拆解（物料/生产/放行/物流/质控）与毛利率 | 不含折旧、厂房摊销与失败批次损耗的全成本模型 |

所有脚本只依赖 Python 3 标准库，本机可直接运行。

常用命令：

```bash
# 1) CAR-T 剂量与批次
python3 scripts/cgt_calc.py cell --weight 70 --dose 2e6 --viability 0.9 --per-batch 5e9

# 2) AAV 载体用量与批次缺口
python3 scripts/cgt_calc.py aav --weight 30 --vg-per-kg 1.1e14 --titer 2e13 --batch-volume 200

# 3) rNPV 与敏感性
python3 scripts/cgt_calc.py rnpv --peak 1200 --year1 2029 --patent 2039 --pos 0.55 --cost 850

# 4) 单例 COGS
python3 scripts/cgt_calc.py cogs --price 100 --vector 18 --labor 12 --release 6 --logistics 4 --qc 5
```

## 二、参考手册索引

| 文件 | 什么时候读 |
|---|---|
| `references/modalities.md` | 不确定该走 CAR-T/TCR-T/TIL/NK/AAV/编辑哪条路线；要做路线对比表与决策树 |
| `references/cmc-release.md` | 设计放行项、效力 assay、VCN/RCL/空壳率、工艺变更后的可比性研究 |
| `references/clinical-regulatory.md` | 剂量递增设计、终点体系、单臂注册条件、中国 818/828 双轨与 FDA/EMA 路径 |
| `references/genome-safety.md` | 脱靶与在靶异常、插入位点、致瘤性、生殖系风险、长期随访（LTFU）设计 |
| `references/valuation-bd.md` | rNPV 参数、交易结构、CVR、中国定价与支付、COGS 与产能经济性 |
| `references/landscape.md` | 竞争格局盘点、靶点拥挤度判断、差异化定位（含时效性提示） |
| `references/diligence-checklist.md` | 立项、投前尽调、BD 评估的 8 维度清单与 kill criteria |

## 三、使用节奏

1. **先定性再算数**：产品类型、自体/异体、适应症线数、目标市场、阶段，五项不清楚时不要开始算。
2. **算数只用脚本**：报剂量、载体量、批次数、rNPV 时必须跑脚本，并把参数与输出一并写入报告。
3. **每个数字带口径**：CAR+ 细胞 vs 总细胞、vg/kg vs vg/眼、copies/diploid genome vs copies/µg DNA。
4. **报告用模板**：`templates/report.html` 提供九段结构（结论 / 假设 / 路线 / CMC / 临床 / 法规 / 安全 / 商业 / 风险与下一步）。

## 四、输出纪律

- 结论先行，3–5 句给判断与下一步。
- 表格优先，参数表必含"取值 / 依据 / 敏感性"三列。
- 法规写文号与生效日期；行业数据标注截止时间并提示核验。
- 明确区分「公开数据」「机制推断」「待验证假设」。
- 涉及患者处置、GMP 合规结论、监管规避的请求，一律不给结论性意见，改为给证据梳理与合规路径。
