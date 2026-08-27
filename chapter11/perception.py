from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_anthropic import ChatAnthropic
from config import MODEL, OBJECTS

vlm = ChatAnthropic(model=MODEL)

# 방에 존재할 수 있는 물체 카탈로그(액션 API가 인식하는 정확한 이름)
KNOWN_OBJECTS = ", ".join(OBJECTS.keys())
 
class SeenObject(BaseModel):
    name: str = Field(description="집기/놓기 액션에 사용할 간단한 영어 명사(예: teddy bear, red cube)")
    where: str = Field(description="화면상 대략 위치(예: 테이블 중앙, 왼쪽 끝, 안 보임)")
 
class Observation(BaseModel):
    scene: str = Field(description="현재 로봇이 바라보는 장면 한 줄 요약")
    objects: list[SeenObject] = Field(description="지금 카메라에 실제로 보이는 물체들의 목록")

# 명확한 제약 조건을 담은 가이드라인 제공
PERCEIVE_SYS = f"""당신은 가정용 로봇의 시각 인지 모듈입니다.
주어진 카메라 이미지에서 '실제로 보이는' 물체만 나열합니다.
보이지 않는 물체를 추측해 지어내지 않습니다(없으면 빈 목록을 반환하세요).

이 방에 있을 수 있는 물체는 다음뿐입니다: {KNOWN_OBJECTS}.
인식한 물체는 반드시 이 목록의 이름과 '철자까지 똑같이'(영문 소문자) 출력하세요.
예: 빨간 곰인형 → 'teddy bear', 노란 오리 → 'rubber duck', 초록 블록 → 'green block'.
목록에 없는 것(로봇 자신의 팔·그리퍼, 책상·바구니 같은 가구)은 출력하지 않습니다."""
 
def perceive(img_b64: str) -> Observation:
    """base64 JPEG 이미지를 받아 정형화된 시각 인지 결과(Observation)를 반환한다."""
    # LangChain의 구조화된 출력 기능 연동
    model = vlm.with_structured_output(Observation)
    # 멀티모달 입력을 위한 메시지 구성 (텍스트 질의 + 이미지 데이터)
    msg = HumanMessage(content=[
        {"type": "text", "text": "이 장면에서 보이는 물체를 인지합니다."},
        {"type": "image_url",
         "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
    ])
    return model.invoke([SystemMessage(content=PERCEIVE_SYS), msg])
