import tiktoken
from datetime import datetime, timedelta
 
class CostGuard:
    """API 호출 비용을 추적하고 제한한다."""
 
    # gpt-5.4-mini 가격 (2026년 4월 기준, 1M 토큰당)
    INPUT_COST_PER_M = 0.75   # $0.75 / 1M input tokens
    OUTPUT_COST_PER_M = 4.50  # $4.50 / 1M output tokens
 
    def __init__(self, daily_limit_usd: float = 10.0):
        self.daily_limit = daily_limit_usd
        self.costs: list[dict] = []  # {timestamp, input_tokens, output_tokens, cost}
        self.enc = tiktoken.get_encoding("o200k_base")
 
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """예상 비용을 계산한다 (USD)."""
        input_cost = (input_tokens / 1_000_000) * self.INPUT_COST_PER_M
        output_cost = (output_tokens / 1_000_000) * self.OUTPUT_COST_PER_M
        return input_cost + output_cost
 
    def get_daily_total(self) -> float:
        """오늘 누적 비용을 반환한다."""
        today = datetime.now().date()
        return sum(
            c["cost"] for c in self.costs
            if c["timestamp"].date() == today
        )
 
    def check_budget(self, estimated_input_tokens: int) -> tuple[bool, str]:
        """예산 내인지 확인한다."""
        daily_total = self.get_daily_total()
        # 평균 출력 토큰으로 추정
        estimated_cost = self.estimate_cost(estimated_input_tokens, 500)
 
        if daily_total + estimated_cost > self.daily_limit:
            return False, (f"일일 예산 초과 예상: "
                          f"현재 ${daily_total:.4f} + "
                          f"예상 ${estimated_cost:.4f} > "
                          f"한도 ${self.daily_limit:.4f}")
 
        return True, f"예산 여유: ${self.daily_limit - daily_total:.4f}"
 
    def record(self, input_tokens: int, output_tokens: int):
        """실제 사용량을 기록한다."""
        cost = self.estimate_cost(input_tokens, output_tokens)
        self.costs.append({
            "timestamp": datetime.now(),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost
        })
