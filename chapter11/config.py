import os
from dotenv import load_dotenv
load_dotenv()
 
MODEL = "claude-sonnet-4-6"
MAX_STEPS = 12          # 행동 스텝 제한 (무한 루프 방지)
MAX_RECOVERY = 3        # 실패 복구 제한
CAM_W, CAM_H = 512, 384 # VLM에 전송용 해상도
JPEG_QUALITY = 70       # JPEG 압축 품질 (전송량 및 토큰 절감)
PICK_RADIUS = 0.9       # 물체를 집을 수 있는 유효 거리(m)

# 시각화(뷰어) 설정
GUI = os.getenv("ROBOT_GUI", "0") == "1"  # ROBOT_GUI=1 이면 실시간 3D 뷰어 창을 띄운다
GUI_STEP_SLEEP = 1.0 / 60.0               # 뷰어에서 동작이 보이도록 시뮬 스텝당 대기(초)
 
# 방에 배치할 객체
OBJECTS = {
    "teddy bear":  {"urdf": "teddy_vhacd.urdf", "pos": [0.4, 0.7, 0.66], "scale": 3.0},
    "rubber duck": {"urdf": "duck_vhacd.urdf",  "pos": [0.0, 0.7, 0.66], "scale": 0.7},
    "red cube":    {"urdf": "cube_small.urdf",  "pos": [-0.35, 0.6, 0.66],
                    "rgba": [0.85, 0.12, 0.12, 1]},
    "green block": {"urdf": "lego/lego.urdf",   "pos": [0.25, 0.5, 0.66], "scale": 1.5,
                    "rgba": [0.15, 0.6, 0.2, 1]},
}
# 물건을 둘 수 있는 장소
LOCATIONS = {
    "table":  [0.2, 0.6, 0.66],   # 테이블 위
    "basket": [-0.9, 0.0, 0.10],  # 바닥의 바구니(트레이)
    "shelf":  [1.1, -0.4, 0.40],  # 벽쪽 선반
}
