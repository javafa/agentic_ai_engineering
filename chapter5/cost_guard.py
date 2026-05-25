from anthropic import Anthropic
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
client = Anthropic()


class CostGuard:
    """API 호출 비용을 추적하고 제한한다."""

    # claude-sonnet-4-5 가격 (2026년 4월 기준, 1M 토큰당)
    INPUT_COST_PER_M = 3.00    # $3.00 / 1M input tokens
    OUTPUT_COST_PER_M = 15.00  # $15.00 / 1M output tokens

    def __init__(self, daily_limit_usd: float = 10.0):
        self.daily_limit = daily_limit_usd
        self.costs: list[dict] = []  # {timestamp, input_tokens, output_tokens, cost}

    def count_tokens(self, messages: list[dict], system: str = "") -> int:
        """보낼 메시지의 입력 토큰 수를 count_tokens API로 계산한다."""
        params = {"model": "claude-sonnet-4-5", "messages": messages}
        if system:
            params["system"] = system
        return client.messages.count_tokens(**params).input_tokens

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """예상 비용을 계산한다 (USD)."""
        input_cost = (input_tokens / 200_000) * self.INPUT_COST_PER_M
        output_cost = (output_tokens / 200_000) * self.OUTPUT_COST_PER_M
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
        # 평균 출력 토큰(500)으로 비용을 추정
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
            "cost": cost,
        })

if __name__ == "__main__":
    # 1. 비용 가드 생성 (하루 한도 $10)
    guard = CostGuard(daily_limit_usd=0.50)

    system = "당신은 친절한 AI 비서입니다."
    messages = [{"role": "user", "content": "파이썬의 리스트와 튜플 차이를 알려줘."}]

    # 2. 보내기 전 — 입력 토큰을 세고 예산을 확인
    input_tokens = guard.count_tokens(messages, system=system)
    ok, reason = guard.check_budget(input_tokens)
    print(f"입력 토큰: {input_tokens}개")
    print(f"예산 확인: {reason}")

    # 3. 예산을 넘으면 호출하지 않고 중단
    if not ok:
        print("예산 초과로 요청을 보내지 않습니다.")
    else:
        # 4. 실제 API 호출
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=system,
            messages=messages,
        )
        print("\nAI 응답:", response.content[0].text)

        # 5. 호출 후 — 응답에 들어 있는 '실제' 사용량을 기록
        guard.record(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        # 6. 오늘 누적 비용 출력
        last = guard.costs[-1]
        print(f"\n이번 호출 비용: ${last['cost']:.6f}")
        print(f"오늘 누적 비용: ${guard.get_daily_total():.6f}")
