import re
 
class InjectionGuard:
    """기본적인 프롬프트 인젝션 탐지"""

    SUSPICIOUS_PATTERNS = [
        r"ignore\s+.*instructions", 
        r"system\s+prompt",
        r"you\s+are\s+now",
        r"dan\s+mode",
        r"jailbreak",
        # 한글 패턴
        r"시스템\s*프롬프트를?\s*(무시|변경|알려)",
        r"새로운\s*역할",
    ]

    def check(self, user_input: str) -> tuple[bool, str]:
        # 1. 소문자 변환 (비교를 위해 필수)
        lower_input = user_input.lower()

        for pattern in self.SUSPICIOUS_PATTERNS:
            # 2. re.IGNORECASE를 빼더라도 패턴 자체가 소문자여야 함
            if re.search(pattern, lower_input):
                return False, f"의심스러운 패턴 탐지: {pattern}"

        if len(user_input) > 10000:
            return False, "입력이 너무 깁니다"

        return True, "통과"
