import re

class PIIFilter:
    """개인정보를 탐지하고 마스킹하는 필터"""
 
    PATTERNS = {
        "phone": (
            r"01[016789]-?\d{3,4}-?\d{4}",
            "[전화번호]"
        ),
        "email": (
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            "[이메일]"
        ),
        "resident_id": (
            r"\d{6}-?[1-8]\d{6}", # 내국인(1~4)과 외국인(5~8) 모두 포함
            "[주민등록번호]"
        ),
        "card_number": (
            r"\d{4}-?\d{4}-?\d{4}-?\d{4}",
            "[카드번호]"
        ),
    }
 
    def mask(self, text: str) -> tuple[str, list[str]]:
        detected = []
        masked_text = text
 
        for pii_type, (pattern, replacement) in self.PATTERNS.items():
            # re.findall을 사용해 존재하는 모든 패턴을 확인
            matches = re.findall(pattern, masked_text)
            if matches:
                detected.append(pii_type)
                # 실제로 텍스트 치환 수행
                masked_text = re.sub(pattern, replacement, masked_text)
 
        return masked_text, detected

# 테스트
if __name__ == "__main__":
    pii_filter = PIIFilter()
    test_text = "홍길동(800101-1234567)의 번호는 010-9999-8888입니다."
    masked, types = pii_filter.mask(test_text)

    print(f"결과: {masked}")
    print(f"탐지된 항목: {types}")
