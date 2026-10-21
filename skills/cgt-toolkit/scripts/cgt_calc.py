#!/usr/bin/env python3
"""
CGT 核算器 —— 剂量 / 载体 / 批次 / COGS / rNPV

仅依赖 Python 3 标准库。所有输出都带口径说明，便于直接粘进报告。

用法：
  cgt_calc.py cell  --weight 70 --dose 2e6 --transduction 0.4 --moi 5 --per-batch 5e9 --patients 100
  cgt_calc.py aav   --weight 30 --vg-per-kg 1.1e14 --titer 2e13 --batch-volume 200 --patients 50
  cgt_calc.py rnpv  --peak 1200 --year1 2029 --patent 2039 --pos 0.55 --cost 850
  cgt_calc.py cogs  --price 100 --vector 18 --labor 12 --release 6 --logistics 4 --qc 5

加 --json 输出机器可读结果。
"""

import argparse
import json
import math
import sys
import unicodedata
from datetime import datetime


# ---------------------------------------------------------------- helpers
def sci(x):
    """把数字格式化成易读形式（大数用科学计数）。"""
    if x == 0:
        return "0"
    if abs(x) >= 1e5:
        return f"{x:.3e}"
    if abs(x) >= 1:
        return f"{x:,.2f}".rstrip("0").rstrip(".")
    return f"{x:.4g}"


def pct(x):
    return f"{x * 100:.1f}%"


def humans(n):
    """批次数向上取整，并给出取整说明。"""
    return int(math.ceil(n - 1e-9))


def dwidth(s):
    """按终端显示宽度计算字符串宽度（中文占 2 列）。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in s)


def pad(s, width):
    return s + " " * max(0, width - dwidth(s))


def rule(title):
    line = "─" * max(28, dwidth(title) + 4)
    print(f"\n{title}\n{line}")


def row(k, v, note=""):
    print(f"  {pad(k, 28)}{pad(v, 30)}{note}")


# ---------------------------------------------------------------- cell
def cmd_cell(a):
    """自体/异体细胞治疗：细胞数、载体感染量、批次数、回输体积。"""
    car_plus = a.weight * a.dose                      # 目标 CAR+ 细胞数
    infused = car_plus / a.purity                      # 含未转导细胞的总回输活细胞
    to_transduce = car_plus / a.transduction           # 需要进入转导的 T 细胞
    vector_iu = to_transduce * a.moi                   # 需要的感染性载体颗粒（IU）
    volume_ml = infused / a.concentration              # 回输体积（按回输浓度）
    per_batch = a.per_batch
    batches_for_one = car_plus / per_batch
    batches_for_n = batches_for_one * a.patients

    rule("细胞治疗：剂量与批次")
    row("体重 / 目标剂量", f"{a.weight:g}kg @ {sci(a.dose)}/kg", "按 CAR+ 细胞计")
    row("单例目标 CAR+ 细胞", sci(car_plus), "= 体重 × 剂量")
    row("回输总活细胞", sci(infused), f"按 CAR+ 纯度 {pct(a.purity)}")
    row("需转导 T 细胞", sci(to_transduce), f"按转导效率 {pct(a.transduction)}")
    row("所需载体感染量", f"{sci(vector_iu)} IU", f"MOI = {a.moi}")
    row("回输体积", f"{volume_ml:.1f} mL", f"按 {sci(a.concentration)} cells/mL")
    row("单例占单批产能", pct(batches_for_one), f"单批 {sci(per_batch)} CAR+ cells")
    row(f"{a.patients} 例所需批数", f"{batches_for_n:.1f} 批 → {humans(batches_for_n)} 批", "未计失败率与放行损耗")
    row("满产可覆盖患者", f"{per_batch / car_plus:.1f} 例/批", "产能天花板")

    warn = []
    if a.dose > 5e6:
        warn.append("剂量超过 5×10^6 CAR+ cells/kg，需重点评估 CRS/ICANS 与神经毒性。")
    if a.transduction < 0.25:
        warn.append(f"转导效率 {pct(a.transduction)} 偏低，将放大载体需求与批间差异。")
    if a.moi > 10:
        warn.append(f"MOI={a.moi} 偏高，注意 VCN 超标与插入风险。")
    if volume_ml > 500:
        warn.append(f"回输体积 {volume_ml:.0f} mL 偏大，需确认冻存/回输工艺上限。")
    if warn:
        print("\n  ⚠ 提示")
        for w in warn:
            print(f"    · {w}")

    return {
        "car_plus_cells": car_plus,
        "infused_cells": infused,
        "cells_to_transduce": to_transduce,
        "vector_iu": vector_iu,
        "infusion_volume_ml": volume_ml,
        "batches_for_cohort": batches_for_n,
        "patients_per_batch": per_batch / car_plus,
        "warnings": warn,
    }


# ---------------------------------------------------------------- aav
def cmd_aav(a):
    """体内基因治疗：载体总量、成品体积、批次数缺口、单剂载体成本。"""
    total_vg = a.weight * a.vg_per_kg
    titer = a.titer                                   # vg/mL
    volume_ml = total_vg / titer
    per_batch_vg = titer * a.batch_volume * 1000      # batch_volume 单位 L
    batches = total_vg * a.patients / per_batch_vg
    cost_per_dose = (per_batch_vg and a.cost_per_batch * total_vg / per_batch_vg) or 0

    rule("体内基因治疗：载体用量与批次")
    row("体重 / 剂量", f"{a.weight:g}kg @ {sci(a.vg_per_kg)}/kg", "按成品滴度计")
    row("单例载体总量", f"{sci(total_vg)} vg", "= 体重 × vg/kg")
    row("成品滴度", f"{sci(titer)} vg/mL", "须为最终成品滴度，非粗纯")
    row("单例给药体积", f"{volume_ml:.1f} mL", "用于判断输注可行性")
    row("单批产量", f"{sci(per_batch_vg)} vg", f"批体积 {a.batch_volume} L")
    row(f"{a.patients} 例所需批数", f"{batches:.2f} → {humans(batches)} 批", "未计空壳率与失败率")
    if a.cost_per_batch:
        row("单例载体成本", f"{cost_per_dose:,.0f}", "货币单位同输入，按满批摊销")

    warn = []
    if a.vg_per_kg >= 1e14:
        warn.append("剂量 ≥1×10^14 vg/kg 属高剂量区间，需重点评估肝酶升高、补体激活与 TMA 风险。")
    if volume_ml > 100 and a.weight < 40:
        warn.append(f"给药体积 {volume_ml:.0f} mL 对 {a.weight} kg 受试者偏大，注意容量负荷。")
    if volume_ml > 250:
        warn.append(f"给药体积 {volume_ml:.0f} mL，需确认输注时限与临床可执行性。")
    if batches > a.patients:
        warn.append("批次数大于患者数，提示单批装量不足，产能是商业化瓶颈。")
    if warn:
        print("\n  ⚠ 提示")
        for w in warn:
            print(f"    · {w}")

    return {
        "total_vg": total_vg,
        "titer_vg_per_ml": titer,
        "dose_volume_ml": volume_ml,
        "per_batch_vg": per_batch_vg,
        "batches_needed": batches,
        "cost_per_dose": cost_per_dose,
        "warnings": warn,
    }


# ---------------------------------------------------------------- rnpv
def cmd_rnpv(a):
    """概率加权 rNPV：上市爬坡 → 平台期 → 专利到期衰减。"""
    now = a.current_year or datetime.now().year
    peak = a.peak                                     # 峰值销售（百万）
    years = []
    for y in range(now, a.patent + a.tail + 1):
        if y < a.year1:
            rev = 0.0
        elif y < a.year1 + a.ramp:
            rev = peak * (y - a.year1 + 1) / a.ramp
        elif y <= a.patent:
            rev = peak
        else:
            rev = peak * ((1 - a.decay) ** (y - a.patent))
        cf = rev * a.margin
        disc = 1 / ((1 + a.discount) ** (y - now))
        years.append({"year": y, "revenue": rev, "cashflow": cf,
                      "discounted": cf * disc, "weighted": cf * disc * a.pos})

    pv_revenue = sum(x["discounted"] for x in years)
    rnpv = sum(x["weighted"] for x in years) - a.cost

    def rnpv_with(**kw):
        p = dict(peak=a.peak, pos=a.pos, discount=a.discount, year1=a.year1,
                 margin=a.margin, patent=a.patent, ramp=a.ramp, decay=a.decay)
        p.update(kw)
        tot = 0.0
        for y in range(now, p["patent"] + a.tail + 1):
            if y < p["year1"]:
                rev = 0.0
            elif y < p["year1"] + p["ramp"]:
                rev = p["peak"] * (y - p["year1"] + 1) / p["ramp"]
            elif y <= p["patent"]:
                rev = p["peak"]
            else:
                rev = p["peak"] * ((1 - p["decay"]) ** (y - p["patent"]))
            tot += rev * p["margin"] / ((1 + p["discount"]) ** (y - now)) * p["pos"]
        return tot - a.cost

    rule("rNPV（概率加权，单位：百万）")
    row("当前年份 / 上市年", f"{now} / {a.year1}", f"爬坡 {a.ramp} 年")
    row("峰值销售", f"{peak:,.0f}", f"专利到期 {a.patent}，之后每年衰减 {pct(a.decay)}")
    row("经风险调整前收入现值", f"{pv_revenue:,.0f}", f"折现率 {pct(a.discount)}")
    row("成功概率 POS", pct(a.pos), "按阶段基准值修正，不要用乐观值")
    row("剩余研发投入", f"-{a.cost:,.0f}", "未做概率加权")
    row("rNPV", f"{rnpv:,.0f}", "rNPV = Σ(POS × FCF × DF) − 投入")

    sens = [
        ("峰值销售 −20%", rnpv_with(peak=peak * 0.8)),
        ("峰值销售 +20%", rnpv_with(peak=peak * 1.2)),
        ("POS −20%（相对）", rnpv_with(pos=a.pos * 0.8)),
        ("POS +20%（相对）", rnpv_with(pos=a.pos * 1.2)),
        ("折现率 8%", rnpv_with(discount=0.08)),
        ("折现率 12%", rnpv_with(discount=0.12)),
        ("上市推迟 2 年", rnpv_with(year1=a.year1 + 2)),
        ("专利期延长 3 年", rnpv_with(patent=a.patent + 3)),
    ]
    print("\n  敏感性")
    for name, val in sorted(sens, key=lambda x: -x[1]):
        delta = val - rnpv
        print(f"    {name:<20}{val:>10,.0f}   ({delta:+,.0f})")

    if rnpv <= 0:
        print("\n  ⚠ rNPV ≤ 0：在当前假设下该资产不成立，除非 POS 或峰值销售有硬证据支持上调。")
    if a.pos > 0.7:
        print("  ⚠ POS 高于 70%：CGT 后期资产罕见到此水平，请核对是否用了 sponsor 口径而非基准值。")

    return {"rnpv": rnpv, "pv_revenue": pv_revenue,
            "sensitivity": {k: v for k, v in sens},
            "cashflows": years}


# ---------------------------------------------------------------- cogs
def cmd_cogs(a):
    """单例成本拆解与毛利率。"""
    items = [
        ("载体/质粒", a.vector),
        ("生产人工与耗材", a.labor),
        ("放行检测", a.release),
        ("冷链物流", a.logistics),
        ("质控与留样", a.qc),
    ]
    direct = sum(v for _, v in items)
    effective = direct / (1 - a.failure_rate)
    gross = a.price - effective
    margin = gross / a.price if a.price else 0

    rule("单例成本与毛利（单位：万元/例）")
    row("终端价格", f"{a.price:,.1f}", "自费价或医保/商保谈判价")
    for name, v in items:
        row(f"  {name}", f"{v:,.1f}", pct(v / direct) if direct else "")
    row("直接成本合计", f"{direct:,.1f}", "")
    row("批失败率", pct(a.failure_rate), "失败批次成本摊到成功批次")
    row("有效 COGS", f"{effective:,.1f}", "= 直接成本 /(1−失败率)")
    row("单例毛利", f"{gross:,.1f}", pct(margin))
    row("COGS 占价格", pct(1 - margin), "行业健康区通常 <35%（自体）/<25%（异体规模化后）")

    warn = []
    if margin < 0.3:
        warn.append(f"毛利率 {pct(margin)} 偏低：自体 CGT 的支付空间通常要求毛利 ≥50% 才支撑商业化团队。")
    if margin >= 0.3 and (1 - margin) > 0.35:
        warn.append(f"COGS 占价格 {pct(1 - margin)}，高于自体 CGT 常见的 35% 参考线，需压载体与人工成本。")
    if a.failure_rate > 0.15:
        warn.append(f"批失败率 {pct(a.failure_rate)} 偏高，先解决工艺稳健性再谈放量。")
    if a.vector > 0 and a.vector / direct > 0.5:
        warn.append("载体成本占比过半，优先做滴度提升与 MOI 下调，而不是压人工。")
    if warn:
        print("\n  ⚠ 提示")
        for w in warn:
            print(f"    · {w}")

    return {"direct": direct, "effective_cogs": effective, "gross": gross,
            "margin": margin, "items": dict(items), "warnings": warn}


# ---------------------------------------------------------------- cli
def main():
    p = argparse.ArgumentParser(description="CGT 核算器：剂量 / 载体 / rNPV / COGS")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("cell", help="细胞治疗剂量与批次")
    c.add_argument("--weight", type=float, default=70)
    c.add_argument("--dose", type=float, default=2e6, help="CAR+ cells/kg")
    c.add_argument("--purity", type=float, default=0.9, help="CAR+ 纯度")
    c.add_argument("--transduction", type=float, default=0.4)
    c.add_argument("--moi", type=float, default=5)
    c.add_argument("--concentration", type=float, default=2.5e6, help="回输浓度 cells/mL")
    c.add_argument("--per-batch", type=float, default=5e9, help="单批 CAR+ 产能")
    c.add_argument("--patients", type=int, default=1)
    c.add_argument("--json", action="store_true")

    v = sub.add_parser("aav", help="AAV 载体用量与批次")
    v.add_argument("--weight", type=float, default=30)
    v.add_argument("--vg-per-kg", type=float, default=1.1e14)
    v.add_argument("--titer", type=float, default=2e13, help="vg/mL")
    v.add_argument("--batch-volume", type=float, default=200, help="单批体积 L")
    v.add_argument("--patients", type=int, default=1)
    v.add_argument("--cost-per-batch", type=float, default=0, help="单批成本（与报告货币一致）")
    v.add_argument("--json", action="store_true")

    r = sub.add_parser("rnpv", help="rNPV 与敏感性")
    r.add_argument("--peak", type=float, required=True, help="峰值销售（百万）")
    r.add_argument("--year1", type=int, required=True, help="首个上市年")
    r.add_argument("--patent", type=int, required=True, help="专利/独占到期年")
    r.add_argument("--pos", type=float, default=0.5, help="成功概率")
    r.add_argument("--cost", type=float, default=0, help="剩余研发投入（百万）")
    r.add_argument("--margin", type=float, default=0.35, help="经营利润率")
    r.add_argument("--discount", type=float, default=0.10)
    r.add_argument("--ramp", type=int, default=4, help="爬坡年数")
    r.add_argument("--decay", type=float, default=0.15, help="专利后年衰减")
    r.add_argument("--tail", type=int, default=5, help="专利后残余年数")
    r.add_argument("--current-year", type=int, default=None)
    r.add_argument("--json", action="store_true")

    g = sub.add_parser("cogs", help="单例成本与毛利")
    g.add_argument("--price", type=float, required=True, help="终端价格（万元/例）")
    g.add_argument("--vector", type=float, default=0)
    g.add_argument("--labor", type=float, default=0)
    g.add_argument("--release", type=float, default=0)
    g.add_argument("--logistics", type=float, default=0)
    g.add_argument("--qc", type=float, default=0)
    g.add_argument("--failure-rate", type=float, default=0.08)
    g.add_argument("--json", action="store_true")

    a = p.parse_args()
    result = {"cell": cmd_cell, "aav": cmd_aav, "rnpv": cmd_rnpv, "cogs": cmd_cogs}[a.cmd](a)
    if getattr(a, "json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    sys.exit(main())
