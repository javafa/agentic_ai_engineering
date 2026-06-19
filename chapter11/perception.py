from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_anthropic import ChatAnthropic
from config import MODEL

# temperature를 0으로 설정하면 일관된 결과를 유도할 수 있다
vlm = ChatAnthropic(model=MODEL, temperature=0)
 
class SeenObject(BaseModel):
    name: str = Field(description="집기/놓기 액션에 사용할 간단한 영어 명사(예: teddy bear, red cube)")
    where: str = Field(description="화면상 대략 위치(예: 테이블 중앙, 왼쪽 끝, 안 보임)")
 
class Observation(BaseModel):
    scene: str = Field(description="현재 로봇이 바라보는 장면 한 줄 요약")
    objects: list[SeenObject] = Field(description="지금 카메라에 실제로 보이는 물체들의 목록")

# 명확한 제약 조건을 담은 가이드라인 제공
PERCEIVE_SYS = """당신은 가정용 로봇의 시각 인지 모듈입니다.
주어진 카메라 이미지에서 '실제로 보이는' 물체만 나열합니다.
보이지 않는 물체를 추측해 지어내지 않습니다(없으면 빈 목록을 반환하세요).
이름은 로봇이 후속 액션 API에서 인식할 수 있도록 간단한 영어 명사로 작성합니다."""
 
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
