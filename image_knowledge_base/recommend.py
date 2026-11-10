from __future__ import annotations

from collections import defaultdict


def score_component(component: dict, *, product_type: str, use_case: str, style: str) -> int:
    score = 0
    text = " ".join(str(component.get(k, "")) for k in ("name", "purpose", "notes", "component_type"))
    if product_type and product_type.casefold() in text.casefold(): score += 3
    if use_case and use_case.casefold() in text.casefold(): score += 3
    if style and style.casefold() in text.casefold(): score += 3
    if component.get("status") == "可复用": score += 4
    if component.get("component_type") in {"背景", "构图", "视觉风格", "信息组件"}: score += 1
    return score


def recommend(components: list[dict], *, product_type: str, use_case: str, style: str, max_items=6) -> list[dict]:
    groups = defaultdict(list)
    for component in components:
        groups[component.get("component_type", "其他")].append(component)
    result = []
    for kind, rows in groups.items():
        ranked = sorted(rows, key=lambda row: score_component(row, product_type=product_type, use_case=use_case, style=style), reverse=True)
        if ranked: result.append(ranked[0])
    remaining = sorted((row for row in components if row not in result), key=lambda row: score_component(row, product_type=product_type, use_case=use_case, style=style), reverse=True)
    return (result + remaining)[:max_items]


def explain(component: dict, product_type: str, use_case: str, style: str) -> str:
    reasons = []
    if component.get("status") == "可复用": reasons.append("已通过复用审核")
    if component.get("component_type"): reasons.append(f"属于{component['component_type']}组件")
    if style and style in (component.get("name", "") + component.get("purpose", "")): reasons.append("与目标视觉风格匹配")
    if use_case and use_case in (component.get("name", "") + component.get("purpose", "")): reasons.append("与目标用途匹配")
    return "；".join(reasons) or "根据当前分类和可用状态推荐"
