#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦麦一句话点餐 —— 推荐引擎核心逻辑（可独立运行）

职责：
  1. 从用户一句话提取结构化槽位：热量上限 / 预算上限 / 品类 / 口味 / 忌口 / 人数 / 场景
  2. 约束求解：硬约束过滤 -> 组合生成 -> 打分排序 -> 生成解释
  3. 无解时给出可执行的替代路径（松弛某个约束）

说明：本文件为离线可运行版本，菜单 SAMPLE_MENU 为近似公开数据，仅用于演示。
接入麦当劳 MCP 后，可用 query-meals / list-nutrition-foods 的实时字段替换菜单。
运行：python recommend.py "预算30元要低卡"
"""

import re
import sys

# ---------------------------------------------------------------------------
# 1. 默认值（与 SKILL.md / config.example.json 保持一致）
# ---------------------------------------------------------------------------
DEFAULTS = {
    "calorie_cap": 800,    # kcal
    "budget_cap": 40.0,    # 元
    "party_size": 1,
}

# ---------------------------------------------------------------------------
# 2. 示例菜单（近似公开数据，仅演示；真实数据以麦当劳 MCP 为准）
#    category: 主菜 / 小食 / 饮料
# ---------------------------------------------------------------------------
SAMPLE_MENU = [
    {"name": "麦辣鸡腿堡",        "category": "主菜", "price": 21.5, "calorie": 510, "protein": 25,  "tags": ["辣", "鸡"]},
    {"name": "板烧鸡腿堡",        "category": "主菜", "price": 21.0, "calorie": 420, "protein": 27,  "tags": ["鸡", "清淡"]},
    {"name": "双层吉士堡",        "category": "主菜", "price": 22.0, "calorie": 440, "protein": 25,  "tags": ["牛"]},
    {"name": "巨无霸",            "category": "主菜", "price": 24.0, "calorie": 560, "protein": 28,  "tags": ["牛"]},
    {"name": "麦香鸡",            "category": "主菜", "price": 15.0, "calorie": 400, "protein": 16,  "tags": ["鸡"]},
    {"name": "吉士汉堡",          "category": "主菜", "price": 13.0, "calorie": 300, "protein": 15,  "tags": ["牛"]},
    {"name": "麦麦脆汁鸡(2块)",   "category": "主菜", "price": 23.0, "calorie": 540, "protein": 30,  "tags": ["鸡", "炸鸡"]},
    {"name": "中份薯条",          "category": "小食", "price": 12.0, "calorie": 320, "protein": 4,   "tags": []},
    {"name": "大份薯条",          "category": "小食", "price": 15.0, "calorie": 430, "protein": 5,   "tags": []},
    {"name": "麦辣鸡翅(2块)",     "category": "小食", "price": 13.0, "calorie": 250, "protein": 17,  "tags": ["辣", "鸡"]},
    {"name": "玉米杯",            "category": "小食", "price": 9.0,  "calorie": 130, "protein": 4,   "tags": ["清淡"]},
    {"name": "苹果片",            "category": "小食", "price": 7.0,  "calorie": 60,  "protein": 0.5, "tags": ["清淡", "甜"]},
    {"name": "可乐(中)",          "category": "饮料", "price": 9.0,  "calorie": 150, "protein": 0,   "tags": ["甜"]},
    {"name": "零度可乐",          "category": "饮料", "price": 9.0,  "calorie": 0,   "protein": 0,   "tags": []},
    {"name": "雪碧",              "category": "饮料", "price": 9.0,  "calorie": 140, "protein": 0,   "tags": ["甜"]},
    {"name": "橙汁",              "category": "饮料", "price": 11.0, "calorie": 170, "protein": 2,   "tags": ["甜", "清淡"]},
    {"name": "美式咖啡",          "category": "饮料", "price": 12.0, "calorie": 5,   "protein": 1,   "tags": ["咖啡因"]},
    {"name": "拿铁",              "category": "饮料", "price": 16.0, "calorie": 220, "protein": 8,   "tags": ["咖啡因", "甜"]},
]


# ---------------------------------------------------------------------------
# 3. 槽位提取
# ---------------------------------------------------------------------------
def parse_slots(text, defaults=None):
    d = dict(DEFAULTS if defaults is None else defaults)
    slots = {
        "calorie_cap": None,
        "budget_cap": None,
        "categories": [],
        "taste": [],
        "taboo": [],
        "party_size": d["party_size"],
        "meal_time": None,
        "scenario": None,
    }

    # 预算：XX元 / XX块 / ¥XX
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:元|块|￥|¥)", text)
    if m:
        slots["budget_cap"] = float(m.group(1))
    # 热量：XX大卡 / XXkcal / XX千卡
    m = re.search(r"(\d+)\s*(?:大卡|千卡|kcal)", text, re.IGNORECASE)
    if m:
        slots["calorie_cap"] = int(m.group(1))
    # 人数：XX人 / 两个人 / 两人
    m = re.search(r"(\d+)\s*人", text)
    if m:
        slots["party_size"] = int(m.group(1))
    else:
        m2 = re.search(r"[一二两三四五六七八九十]\s*个?\s*人", text)
        if m2:
            _cn = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
                   "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
            slots["party_size"] = _cn[m2.group(0)[0]]

    # 品类 / 口味 / 忌口 关键词
    keyword_map = {
        "辣": ("taste", "辣"), "清淡": ("taste", "清淡"), "解馋": ("taste", "解馋"),
        "低卡": ("taste", "低卡"), "高蛋白": ("taste", "高蛋白"), "甜": ("taste", "甜"),
        "汉堡": ("categories", "汉堡"), "炸鸡": ("categories", "炸鸡"),
        "薯条": ("categories", "小食"), "鸡翅": ("categories", "小食"),
        "饮料": ("categories", "饮料"), "咖啡": ("categories", "饮料"),
        "不要咖啡因": ("taboo", "咖啡因"), "不要辣": ("taboo", "辣"), "不吃辣": ("taboo", "辣"),
        "素食": ("taboo", "肉"), "不要肉": ("taboo", "肉"),
    }
    for kw, (cat, val) in keyword_map.items():
        if kw in text and val not in slots[cat]:
            slots[cat].append(val)

    # 场景 / 餐段
    if "健身" in text:
        slots["scenario"] = "健身后"
    for seg in ("早餐", "午餐", "晚餐", "下午茶", "夜宵"):
        if seg in text:
            slots["meal_time"] = seg
            break

    # 缺失硬约束 -> 用默认值补全（不追问，直接推荐并声明假设）
    used_default = []
    if slots["calorie_cap"] is None:
        slots["calorie_cap"] = d["calorie_cap"]
        used_default.append(f"热量上限 {d['calorie_cap']} kcal")
    if slots["budget_cap"] is None:
        slots["budget_cap"] = d["budget_cap"]
        used_default.append(f"预算上限 ¥{d['budget_cap']}")
    slots["_used_default"] = used_default
    return slots


# ---------------------------------------------------------------------------
# 4. 约束求解
# ---------------------------------------------------------------------------
def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _item_ok(item, taboo):
    for t in taboo:
        if t == "肉":
            if any(tag in ("鸡", "牛", "炸鸡") for tag in item["tags"]):
                return False
        elif t in item["tags"]:
            return False
    return True


def _build_candidates(menu):
    # 每个候选组合必须包含 1 个主菜（构成"正餐"），可再选 0~1 小食、0~1 饮料
    mains = [m for m in menu if m["category"] == "主菜"]
    sides = [m for m in menu if m["category"] == "小食"]
    drinks = [m for m in menu if m["category"] == "饮料"]
    combos = []
    for mc in mains:
        combos.append([mc])
        for s in sides:
            combos.append([mc, s])
            for d in drinks:
                combos.append([mc, s, d])
        for d in drinks:
            combos.append([mc, d])
    seen, uniq = set(), []
    for c in combos:
        key = tuple(sorted(x["name"] for x in c))
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return uniq


def _totals(combo):
    return (
        round(sum(x["price"] for x in combo), 1),
        sum(x["calorie"] for x in combo),
        round(sum(x["protein"] for x in combo), 1),
    )


def _build_explanation(f, slots, rank_pct):
    parts = []
    if "低卡" in slots["taste"]:
        parts.append(f"热量仅 {f['calorie']} kcal，是预算内偏低的组合")
    if slots["scenario"] == "健身后" or "高蛋白" in slots["taste"]:
        parts.append(f"蛋白质 {f['protein']}g，在候选中排名前 {max(rank_pct, 1)}%")
    matched = [t for t in slots["taste"]
               if any(t in it["tags"] for it in f["items"])]
    if matched:
        parts.append(f"满足你对「{'、'.join(matched)}」的偏好")
    for c in slots["categories"]:
        if c == "汉堡" and any(it["category"] == "主菜" for it in f["items"]):
            parts.append("包含汉堡主菜")
        if c == "炸鸡" and any("炸鸡" in it["tags"] for it in f["items"]):
            parts.append("包含炸鸡")
    if not parts:
        parts.append(f"¥{f['price']} 内热量 {f['calorie']} kcal、蛋白质 {f['protein']}g，综合性价比高")
    return "；".join(parts) + "。"


def solve(text, menu=None, defaults=None):
    menu = menu or SAMPLE_MENU
    slots = parse_slots(text, defaults)
    n = max(1, slots["party_size"])
    # 先按"单人"口径过滤与打分，最后再按人数放大份量与合计
    cal_cap = slots["calorie_cap"]
    bud_cap = slots["budget_cap"]
    taboo = set(slots["taboo"])

    clean = [m for m in menu if _item_ok(m, taboo)]
    candidates = _build_candidates(clean)

    feasible = []
    for c in candidates:
        price, cal, pro = _totals(c)
        if price <= bud_cap and cal <= cal_cap:
            feasible.append({"items": c, "price": price, "calorie": cal, "protein": pro})

    if not feasible:
        return _no_solution(slots, clean, bud_cap, cal_cap, n)

    max_density = max((f["protein"] / f["calorie"] for f in feasible if f["calorie"] > 0), default=0)
    cats, tastes = set(slots["categories"]), set(slots["taste"])
    total_soft = len(cats) + len(tastes)
    # 健身后 / 高蛋白：上调蛋白质权重，下调热量权重
    if slots["scenario"] == "健身后" or "高蛋白" in tastes:
        w_budget, w_cal, w_taste, w_protein = 0.2, 0.1, 0.3, 0.4
    else:
        w_budget, w_cal, w_taste, w_protein = 0.3, 0.3, 0.2, 0.2
    for f in feasible:
        budget_fit = _clamp(1 - f["price"] / bud_cap, 0, 1)
        cal_fit = _clamp(1 - f["calorie"] / cal_cap, 0, 1)
        if total_soft == 0:
            taste_match = 1.0
        else:
            hit = 0
            for it in f["items"]:
                if "汉堡" in cats and it["category"] == "主菜":
                    hit += 1
                if "炸鸡" in cats and "炸鸡" in it["tags"]:
                    hit += 1
                if "饮料" in cats and it["category"] == "饮料":
                    hit += 1
                if "小食" in cats and it["category"] == "小食":
                    hit += 1
                for t in tastes:
                    if t in it["tags"]:
                        hit += 1
            taste_match = hit / total_soft
        dens = (f["protein"] / f["calorie"] / max_density) if (max_density > 0 and f["calorie"] > 0) else 0
        f["score"] = round(w_budget * budget_fit + w_cal * cal_fit + w_taste * taste_match + w_protein * dens, 4)

    feasible.sort(key=lambda x: x["score"], reverse=True)
    ranked = sorted(feasible, key=lambda x: x["protein"], reverse=True)
    for f in feasible[:3]:
        # 按人数放大份量与合计
        if n > 1:
            for it in f["items"]:
                it["qty"] = n
            f["price"] = round(f["price"] * n, 1)
            f["calorie"] = f["calorie"] * n
            f["protein"] = round(f["protein"] * n, 1)
        else:
            for it in f["items"]:
                it["qty"] = 1
        rank_pct = int((len(ranked) - ranked.index(f)) / len(ranked) * 100) or 1
        f["explanation"] = _build_explanation(f, slots, rank_pct)

    return {"slots": slots, "recommendations": feasible[:3], "no_solution": False}


def _no_solution(slots, clean, bud_cap, cal_cap, n):
    options = []
    # 放宽热量 +80（单人口径）
    feas_cal = [c for c in _build_candidates(clean)
                if _totals(c)[0] <= bud_cap and _totals(c)[1] <= cal_cap + 80]
    if feas_cal:
        best = min(feas_cal, key=lambda c: _totals(c)[1])
        options.append(("热量", 80, best))
    # 放宽预算 +5（单人口径）
    feas_bud = [c for c in _build_candidates(clean)
                if _totals(c)[0] <= bud_cap + 5 and _totals(c)[1] <= cal_cap]
    if feas_bud:
        best = min(feas_bud, key=lambda c: _totals(c)[0])
        options.append(("预算", 5, best))
    # 按人数放大份量
    for _, _, combo in options:
        for it in combo:
            it["qty"] = n
    return {"slots": slots, "recommendations": [], "no_solution": True, "alternatives": options}


# ---------------------------------------------------------------------------
# 5. 命令行演示
# ---------------------------------------------------------------------------
def main():
    text = " ".join(sys.argv[1:]) or "预算30元要低卡"
    result = solve(text)
    print(f"用户输入：{text}\n")
    s = result["slots"]
    print("解析槽位：")
    print(f"  热量上限 = {s['calorie_cap']} kcal ｜ 预算上限 = ¥{s['budget_cap']} ｜ 人数 = {s['party_size']}")
    if s["categories"]:
        print(f"  想吃的品类 = {s['categories']}")
    if s["taste"]:
        print(f"  口味倾向 = {s['taste']}")
    if s["taboo"]:
        print(f"  忌口 = {s['taboo']}")
    if s.get("_used_default"):
        print(f"  ⚠️ 使用默认假设：{', '.join(s['_used_default'])}")
    print()

    if result["no_solution"]:
        print("⚠️ 未找到完全满足条件的组合，但你可以这样调整：")
        if result["alternatives"]:
            for kind, step, combo in result["alternatives"]:
                p, c, pr = _totals(combo)
                nn = s["party_size"]
                p, c, pr = p * nn, c * nn, round(pr * nn, 1)
                names = " + ".join(f"{x['name']}×{x.get('qty', 1)}" for x in combo)
                print(f"  - 把{kind}上限放宽 {step}：可吃【{names}】（¥{p} / {c} kcal / 蛋白 {pr} g）")
        else:
            print("  - 当前菜单无法满足，建议放宽热量或预算，或更换品类/忌口。")
        return

    print("推荐方案：")
    if s["party_size"] > 1:
        print(f"（以下为 {s['party_size']} 人合计）\n")
    for i, r in enumerate(result["recommendations"], 1):
        names = " + ".join(f"{x['name']}×{x.get('qty', 1)}" for x in r["items"])
        print(f"\n推荐 {i}：{names}")
        print(f"   合计热量 {r['calorie']} kcal ｜ 合计价格 ¥{r['price']} ｜ 蛋白质 {r['protein']} g")
        print(f"   解释：{r['explanation']}")


if __name__ == "__main__":
    main()
