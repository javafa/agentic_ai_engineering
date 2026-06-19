def fmt(x, d: int = 2) -> str:
    return f"{x:,.{d}f}"
 
def sign(x) -> str:
    return "▲" if x > 0 else ("▼" if x < 0 else "－")
 
 
def serialize_for_llm(indicators: dict, stocks: list, news: list) -> str:
    """노드들이 채운 State를 LLM 입력용 텍스트 블록으로 직렬화합니다.
    '수집 실패'를 그대로 표시해, LLM이 빈 값을 지어내지 않도록 합니다."""
    lines = ["[시장 지표]"]
    for name, d in indicators.items():
        if not d:
            lines.append(f"- {name}: 수집 실패")
        else:
            lines.append(
                f"- {name}: {fmt(d['last'])} "
                f"({sign(d['change'])}{fmt(abs(d['pct']))}%) [기준 {d['asof']}]"
            )
 
    lines.append("\n[관심 종목]")
    for s in stocks:
        if s.get("error"):
            lines.append(f"- {s['name']}({s['code']}): 수집 실패")
        else:
            lines.append(
                f"- {s['name']}({s['code']}): {fmt(s['last'])} "
                f"({sign(s['change'])}{fmt(abs(s['pct']))}%), "
                f"5일선 대비 {fmt(s['vs_ma5'])}%"
            )
 
    lines.append("\n[뉴스]")
    if not news:
        lines.append("- 최근 24시간 내 수집된 뉴스 없음")
    for n in news:
        lines.append(f"- [{n['keyword']}] {n['title']} ({n['source']})")
 
    return "\n".join(lines)
