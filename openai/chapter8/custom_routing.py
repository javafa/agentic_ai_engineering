def route_by_intent(state: State) -> str:
    """마지막 메시지의 의도에 따라 라우팅"""
    last_msg = state["messages"][-1]
 
    # LLM이 도구를 호출하려는 경우
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
 
    # 특정 키워드가 포함된 경우 전문가 노드로
    content = last_msg.content.lower() if last_msg.content else ""
    if "코드" in content or "프로그래밍" in content:
        return "code_expert"
    elif "보고서" in content or "문서" in content:
        return "doc_expert"
 
    return END  # 기본: 종료
 
# 조건부 엣지 등록
work_flow.add_conditional_edges(
    "agent",
    route_by_intent
)
