import math, io, base64
import numpy as np
import pybullet as p
import pybullet_data
from PIL import Image
from config import OBJECTS, LOCATIONS, CAM_W, CAM_H, JPEG_QUALITY, PICK_RADIUS
 
class RobotAPI:
    def __init__(self, gui: bool = False):
        self.cid = p.connect(p.GUI if gui else p.DIRECT)  # 헤드리스: DIRECT
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        self._setup()
 
    def _setup(self):
        p.resetSimulation()
        p.setGravity(0, 0, -9.8)
        p.loadURDF("plane.urdf")
        p.loadURDF("room.urdf", useFixedBase=True)            # 책 제공 방
        p.loadURDF("table/table.urdf", [0.2, 0.6, 0.0], useFixedBase=True)
        p.loadURDF("tray/tray.urdf", LOCATIONS["basket"], useFixedBase=True)
        self.robot = p.loadURDF("husky/husky.urdf", [0.0, -1.2, 0.1])  # 모바일 베이스
        self.yaw = math.pi / 2          # 바라보는 방향(+y, 테이블 쪽)
        self.held = None                # (constraint_id, body_id, name)
        self.bodies = {}                # 이름 > bodyId
        for name, o in OBJECTS.items():
            bid = p.loadURDF(o["urdf"], o["pos"], globalScaling=o.get("scale", 1.0))
            if "rgba" in o:
                p.changeVisualShape(bid, -1, rgbaColor=o["rgba"])
            self.bodies[name] = bid
        for _ in range(120):            # 물체가 바닥/테이블에 안정될 때까지
            p.stepSimulation()
 
    def reset(self):                    # 평가 때 매 태스크마다 씬을 초기화
        self._setup()

    def capture(self):
        """로봇 시점 카메라를 캡처해 (numpy RGB, base64 JPEG)를 반환한다."""
        pos, _ = p.getBasePositionAndOrientation(self.robot)
        eye = [pos[0], pos[1], pos[2] + 0.7]            # 로봇 눈 높이

        # 바라보는 방향 계산
        target = [eye[0] + math.cos(self.yaw),
                  eye[1] + math.sin(self.yaw), eye[2] - 0.3]
        view = p.computeViewMatrix(eye, target, [0, 0, 1])
        proj = p.computeProjectionMatrixFOV(60, CAM_W / CAM_H, 0.1, 8.0)

        # 이미지 촬영 및 처리
        _, _, rgba, _, _ = p.getCameraImage(
            CAM_W, CAM_H, view, proj, renderer=p.ER_TINY_RENDERER)
        rgb = np.reshape(rgba, (CAM_H, CAM_W, 4))[:, :, :3].astype(np.uint8)

        # 이미지 JPEG 압축 후 base64 직렬화
        buf = io.BytesIO()
        Image.fromarray(rgb).save(buf, format="JPEG", quality=JPEG_QUALITY)
        return rgb, base64.b64encode(buf.getvalue()).decode()

    def _xy(self, name, with_z=False):
        """이름(문자열)을 입력받아 현재 매핑된 실제 좌표를 반환한다 (내부용)"""
        if name in self.bodies:
            pos = p.getBasePositionAndOrientation(self.bodies[name])[0]
        elif name in LOCATIONS:
            pos = LOCATIONS[name]
        else:
            return None
        return pos if with_z else (pos[0], pos[1])
 
    def navigate_to(self, name: str) -> dict:
        """지정한 객체나 장소의 0.6m 앞으로 로봇을 이동시킨다."""
        tgt = self._xy(name)
        if tgt is None:
            return {"ok": False, "reason": f"'{name}'은(는) 알 수 없는 위치"}
        pos, _ = p.getBasePositionAndOrientation(self.robot)
        dx, dy = tgt[0] - pos[0], tgt[1] - pos[1]
        dist = math.hypot(dx, dy) or 1e-6
        self.yaw = math.atan2(dy, dx)            # 목표물을 바라보도록 회전각 설정
        stop = max(dist - 0.6, 0.0)              # 목표 0.6m 앞에서 정지
        nx, ny = pos[0] + dx / dist * stop, pos[1] + dy / dist * stop
        orn = p.getQuaternionFromEuler([0, 0, self.yaw])
        # 시뮬레이션 상에서 부드러운 이동 연출
        for s in range(20):
            t = (s + 1) / 20
            p.resetBasePositionAndOrientation(
                self.robot,
                [pos[0] + (nx - pos[0]) * t, pos[1] + (ny - pos[1]) * t, 0.1], orn)
            p.stepSimulation()
        return {"ok": True, "reason": f"'{name}' 근처로 이동 완료"}
 
    def pick(self, name: str) -> dict:
        """로봇이 사거리 안에 있는 물체를 집어 올린다."""
        if self.held is not None:
            return {"ok": False, "reason": "이미 다른 물체를 들고 있음"}
        bid = self.bodies.get(name)
        if bid is None:
            return {"ok": False, "reason": f"'{name}' 객체가 방에 없음"}
        rp, _ = p.getBasePositionAndOrientation(self.robot)
        op, _ = p.getBasePositionAndOrientation(bid)
        if math.hypot(op[0] - rp[0], op[1] - rp[1]) > PICK_RADIUS:
            return {"ok": False, "reason": f"'{name}'이 너무 멀리 있음. (먼저 이동 필요)"}
        # 그래스핑 추상화: 실제 물리적 제어 대신 고정적인 제약조건으로 로봇 몸체에 연결한다.
        cons = p.createConstraint(self.robot, -1, bid, -1, p.JOINT_FIXED,
                                  [0, 0, 0], [0, 0, 0.5], [0, 0, 0])
        self.held = (cons, bid, name)
        for _ in range(20):
            p.stepSimulation()
        return {"ok": True, "reason": f"'{name}'을(를) 집었음"}
 
    def place(self, name: str) -> dict:
        """들고 있는 물체를 특정 장소에 내려 놓는다."""
        if self.held is None:
            return {"ok": False, "reason": "들고 있는 물체가 없음"}
        tgt = self._xy(name, with_z=True)
        if tgt is None:
            return {"ok": False, "reason": f"'{name}'는 알 수 없는 장소"}
        cons, bid, held = self.held
        p.removeConstraint(cons) # 고정 제약조건 해제
        # 물체를 목표 장소의 약간 위(0.05m)에 두고 중력에 의해 자연스럽게 떨어지도록 설정
        p.resetBasePositionAndOrientation(bid, [tgt[0], tgt[1], tgt[2] + 0.05], [0, 0, 0, 1])
        self.held = None
        for _ in range(80):       # 물체가 바닥에 떨어져서 멈출 때까지 대기
            p.stepSimulation()
        return {"ok": True, "reason": f"'{held}'을(를) '{name}'에 놓음"}
 
    def look_around(self, _="") -> dict:
        """시점을 오른쪽으로 60도 회전하여 주변 환경을 다시 탐색한다."""
        self.yaw += math.pi / 3
        pos, _ = p.getBasePositionAndOrientation(self.robot)
        p.resetBasePositionAndOrientation(
            self.robot, pos, p.getQuaternionFromEuler([0, 0, self.yaw]))
        for _ in range(10):
            p.stepSimulation()
        return {"ok": True, "reason": "주변을 둘러봄(시점 회전)"}
 
    def position_of(self, name):
        """(평가 및 검증용) 특정 객체의 정답 좌표를 반환한다."""
        return p.getBasePositionAndOrientation(self.bodies[name])[0]
