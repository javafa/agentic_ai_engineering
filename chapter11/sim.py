import math, io, base64, time
import numpy as np
import pybullet as p
import pybullet_data
from PIL import Image
from config import (OBJECTS, LOCATIONS, CAM_W, CAM_H, JPEG_QUALITY, PICK_RADIUS,
                    GUI_STEP_SLEEP)

# ---- Franka Panda(팔) 구성 상수 ----
ARM_URDF   = "franka_panda/panda.urdf"
EE_LINK    = 11                                     # panda_grasptarget(엔드이펙터 링크)
ARM_JOINTS = [0, 1, 2, 3, 4, 5, 6]                  # 7개 회전 관절
FINGERS    = [9, 10]                                # 그리퍼 두 손가락
ARM_HOME   = [0.0, -0.6, 0.0, -2.2, 0.0, 1.8, 0.785]   # 이동 시 접은 자세
ARM_LL = [-2.9, -1.76, -2.9, -3.07, -2.9, -0.02, -2.9] # IK 관절 하한
ARM_UL = [ 2.9,  1.76,  2.9, -0.07,  2.9,  3.75,  2.9] # IK 관절 상한
ARM_JR = [u - l for l, u in zip(ARM_LL, ARM_UL)]
FINGER_OPEN, FINGER_CLOSE = 0.04, 0.0

# ---- 이동 베이스 + 팔 배치 상수 (reach 검증으로 결정한 값) ----
MOUNT_Z  = 0.70     # 팔 베이스 높이: 토르소(마스트) 위 — 책상 상판보다 높게 두어 위에서 뻗는다
ARM_FWD  = 0.25     # 팔을 베이스 중심보다 앞쪽에 마운트
MAST_BOT = 0.30     # 토르소 박스 아래 끝(베이스 상판 근처)
APPROACH_FAR  = 1.0   # 책상 등 높은 목표 앞 정차 거리(긴 베이스가 책상에 안 박히게)
APPROACH_NEAR = 0.65  # 바닥 바구니 등 낮은 목표는 더 가까이 정차(팔이 아래로 닿게)
LOW_Z    = 0.5      # 목표 높이가 이 값 미만이면 NEAR로 접근
HOVER    = 0.15     # 집기/놓기 전 물체 위로 접근하는 높이(m)

# ---- 카메라(팔 앞쪽 붐에 장착 → 팔이 시야를 가리지 않게) ----
CAM_FWD  = 0.6      # 카메라를 팔보다 이만큼 앞에 둔다
CAM_Z    = 0.9      # 카메라 높이(베이스 기준)
CAM_DROP = 0.5      # 전방 1m 지점에서 이만큼 아래를 본다(하향 틸트)


class RobotAPI:
    def __init__(self, gui: bool = False):
        self.gui = gui
        if gui:
            try:
                self.cid = p.connect(p.GUI)         # 실시간 3D 뷰어 창
            except p.error:
                self.cid = -1
            if self.cid < 0:                        # GUI 사용 불가 → 헤드리스로 폴백
                print("[경고] GUI 연결 실패 — 헤드리스(DIRECT)로 전환합니다.")
                self.gui = False
                self.cid = p.connect(p.DIRECT)
        else:
            self.cid = p.connect(p.DIRECT)          # 헤드리스: DIRECT
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        self._setup()

    def _setup(self):
        p.resetSimulation()
        p.setGravity(0, 0, -9.8)
        p.loadURDF("plane.urdf")
        p.loadURDF("room.urdf", useFixedBase=True)            # 책 제공 방
        p.loadURDF("table/table.urdf", [0.2, 0.6, 0.0], useFixedBase=True)
        p.loadURDF("tray/tray.urdf", LOCATIONS["basket"], useFixedBase=True)

        # 모바일 매니퓰레이터 = 이동 베이스(husky) + 그 위에 올린 팔(panda)
        self.base = p.loadURDF("husky/husky.urdf", [0.0, -1.2, 0.1])
        self.yaw = math.pi / 2          # 바라보는 방향(+y, 테이블 쪽)
        self.arm = p.loadURDF(ARM_URDF, [0, 0, MOUNT_Z], useFixedBase=True)
        # 베이스와 팔을 잇는 토르소(마스트) — 시각용(충돌 없음)
        vis = p.createVisualShape(p.GEOM_BOX,
                                  halfExtents=[0.06, 0.06, (MOUNT_Z - MAST_BOT) / 2],
                                  rgbaColor=[0.25, 0.25, 0.28, 1])
        self.mast = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis)
        self._reset_arm()               # 팔을 접은 기본 자세로
        self._mount_arm()               # 팔/토르소를 이동 베이스 위로 정렬

        self.held = None                # (body_id, name) — 팔이 들고 있는 물체
        self.bodies = {}                # 이름 > bodyId
        for name, o in OBJECTS.items():
            bid = p.loadURDF(o["urdf"], o["pos"], globalScaling=o.get("scale", 1.0))
            if "rgba" in o:
                p.changeVisualShape(bid, -1, rgbaColor=o["rgba"])
            self.bodies[name] = bid

        self._sim_steps(120)            # 물체가 바닥/테이블에 안정될 때까지
        if self.gui:                    # 뷰어를 보기 좋은 각도로 맞추고 잡다한 패널을 숨김
            p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)
            p.resetDebugVisualizerCamera(
                cameraDistance=3.0, cameraYaw=50, cameraPitch=-35,
                cameraTargetPosition=[0.0, 0.3, 0.3])

    def reset(self):                    # 평가 때 매 태스크마다 씬을 초기화
        self._setup()

    # ---- 팔(arm) 저수준 제어 ----
    def _reset_arm(self):
        """팔을 접은 기본 자세(ARM_HOME) + 그리퍼 열림 상태로 되돌린다."""
        for j, a in zip(ARM_JOINTS, ARM_HOME):
            p.resetJointState(self.arm, j, a)
        self._set_fingers(FINGER_OPEN)

    def _mount_arm(self):
        """팔과 토르소를 현재 이동 베이스 위(앞쪽 ARM_FWD)로 옮겨 함께 움직이게 한다."""
        bp, _ = p.getBasePositionAndOrientation(self.base)
        ax = bp[0] + ARM_FWD * math.cos(self.yaw)
        ay = bp[1] + ARM_FWD * math.sin(self.yaw)
        orn = p.getQuaternionFromEuler([0, 0, self.yaw])
        p.resetBasePositionAndOrientation(self.arm, [ax, ay, MOUNT_Z], orn)
        p.resetBasePositionAndOrientation(self.mast, [ax, ay, (MAST_BOT + MOUNT_Z) / 2], orn)

    def _set_fingers(self, width: float):
        for f in FINGERS:
            p.resetJointState(self.arm, f, width)

    def _track_held(self):
        """들고 있는 물체를 엔드이펙터(그리퍼) 바로 아래에 붙여 따라오게 한다."""
        if self.held is None:
            return
        bid, _ = self.held
        ee = p.getLinkState(self.arm, EE_LINK)[4]
        p.resetBasePositionAndOrientation(
            bid, [ee[0], ee[1], ee[2] - 0.03], p.getQuaternionFromEuler([0, 0, self.yaw]))

    def _sim_steps(self, n: int):
        """물리 시뮬레이션을 n스텝 진행한다. GUI일 때는 동작이 눈에 보이도록 잠깐씩 쉰다."""
        for _ in range(n):
            self._track_held()
            p.stepSimulation()
            if self.gui:
                time.sleep(GUI_STEP_SLEEP)

    def _move_joints(self, targets, steps: int = 60):
        """팔의 7개 관절을 현재값에서 targets로 부드럽게 보간 이동한다."""
        cur = [p.getJointState(self.arm, j)[0] for j in ARM_JOINTS]
        for s in range(steps):
            t = (s + 1) / steps
            for k, j in enumerate(ARM_JOINTS):
                p.resetJointState(self.arm, j, cur[k] + (targets[k] - cur[k]) * t)
            self._track_held()
            p.stepSimulation()
            if self.gui:
                time.sleep(GUI_STEP_SLEEP)

    def _move_ee(self, target, steps: int = 60):
        """엔드이펙터를 목표 좌표(x,y,z)로 IK로 풀어 이동시킨다."""
        ik = p.calculateInverseKinematics(
            self.arm, EE_LINK, target,
            lowerLimits=ARM_LL, upperLimits=ARM_UL, jointRanges=ARM_JR,
            restPoses=ARM_HOME, maxNumIterations=300, residualThreshold=1e-4)
        self._move_joints(list(ik[:7]), steps)

    def capture(self):
        """팔 앞쪽 붐에 달린 카메라를 캡처해 (numpy RGB, base64 JPEG)를 반환한다."""
        pos, _ = p.getBasePositionAndOrientation(self.base)
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        # 카메라를 팔보다 앞(CAM_FWD)·위(CAM_Z)에 두어 팔이 시야를 가리지 않게 한다
        eye = [pos[0] + CAM_FWD * c, pos[1] + CAM_FWD * s, pos[2] + CAM_Z]
        target = [eye[0] + c, eye[1] + s, eye[2] - CAM_DROP]   # 전방 아래(작업대)를 향함
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
        """지정한 객체나 장소의 APPROACH(=1m) 앞에 이동 베이스를 정차시킨다."""
        tgt = self._xy(name)
        if tgt is None:
            return {"ok": False, "reason": f"'{name}'은(는) 알 수 없는 위치"}
        tz = self._xy(name, with_z=True)[2]
        approach = APPROACH_NEAR if tz < LOW_Z else APPROACH_FAR  # 낮은 목표는 더 가까이
        pos, _ = p.getBasePositionAndOrientation(self.base)
        dx, dy = tgt[0] - pos[0], tgt[1] - pos[1]
        dist = math.hypot(dx, dy) or 1e-6
        self.yaw = math.atan2(dy, dx)            # 목표물을 바라보도록 회전각 설정
        stop = max(dist - approach, 0.0)         # 목표 앞에서 정지(긴 베이스가 책상에 안 박힘)
        nx, ny = pos[0] + dx / dist * stop, pos[1] + dy / dist * stop
        orn = p.getQuaternionFromEuler([0, 0, self.yaw])
        # 베이스를 부드럽게 이동시키며 팔과 들고 있는 물체도 함께 따라오게 한다
        steps = 40 if self.gui else 20
        for s in range(steps):
            t = (s + 1) / steps
            p.resetBasePositionAndOrientation(
                self.base,
                [pos[0] + (nx - pos[0]) * t, pos[1] + (ny - pos[1]) * t, 0.1], orn)
            self._mount_arm()
            self._track_held()
            p.stepSimulation()
            if self.gui:
                time.sleep(GUI_STEP_SLEEP)
        return {"ok": True, "reason": f"'{name}' 앞으로 이동(정차) 완료"}

    def pick(self, name: str) -> dict:
        """팔을 뻗어 사거리 안의 물체를 집어 올린다."""
        if self.held is not None:
            return {"ok": False, "reason": "이미 다른 물체를 들고 있음"}
        bid = self.bodies.get(name)
        if bid is None:
            return {"ok": False, "reason": f"'{name}' 객체가 방에 없음"}
        ap, _ = p.getBasePositionAndOrientation(self.arm)   # 팔 베이스 기준 거리
        op, _ = p.getBasePositionAndOrientation(bid)
        if math.hypot(op[0] - ap[0], op[1] - ap[1]) > PICK_RADIUS:
            return {"ok": False, "reason": f"'{name}'이(가) 팔 사거리 밖. (먼저 이동 필요)"}
        # 위로 접근 → 하강 → 그리퍼 닫고 잡기 → 들어올림 → 이동 자세로 접기
        self._set_fingers(FINGER_OPEN)
        self._move_ee([op[0], op[1], op[2] + HOVER], steps=50)
        self._move_ee([op[0], op[1], op[2] + 0.02], steps=30)
        self.held = (bid, name)                  # 이 시점부터 물체는 그리퍼를 따라온다
        self._set_fingers(FINGER_CLOSE)
        self._sim_steps(8)
        self._move_ee([op[0], op[1], op[2] + HOVER + 0.05], steps=30)
        self._move_joints(ARM_HOME, steps=30)
        return {"ok": True, "reason": f"'{name}'을(를) 집었음"}

    def place(self, name: str) -> dict:
        """들고 있는 물체를 팔로 특정 장소에 내려 놓는다."""
        if self.held is None:
            return {"ok": False, "reason": "들고 있는 물체가 없음"}
        tgt = self._xy(name, with_z=True)
        if tgt is None:
            return {"ok": False, "reason": f"'{name}'는 알 수 없는 장소"}
        bid, held = self.held
        # 목표 위로 이동 → 하강 → 놓고 → 안정될 때까지 대기 → 팔 회수
        self._move_ee([tgt[0], tgt[1], tgt[2] + HOVER + 0.05], steps=40)
        self._move_ee([tgt[0], tgt[1], tgt[2] + 0.08], steps=30)
        self.held = None                         # 추적 중단(= 손에서 놓음)
        p.resetBasePositionAndOrientation(
            bid, [tgt[0], tgt[1], tgt[2] + 0.05], [0, 0, 0, 1])
        self._set_fingers(FINGER_OPEN)
        self._sim_steps(60)                      # 중력으로 떨어져 멈출 때까지
        self._move_joints(ARM_HOME, steps=30)
        return {"ok": True, "reason": f"'{held}'을(를) '{name}'에 놓음"}

    def look_around(self, _="") -> dict:
        """시점을 오른쪽으로 60도 회전하여 주변 환경을 다시 탐색한다."""
        self.yaw += math.pi / 3
        pos, _ = p.getBasePositionAndOrientation(self.base)
        p.resetBasePositionAndOrientation(
            self.base, pos, p.getQuaternionFromEuler([0, 0, self.yaw]))
        self._mount_arm()
        self._track_held()
        self._sim_steps(10)
        return {"ok": True, "reason": "주변을 둘러봄(시점 회전)"}

    def position_of(self, name):
        """(평가 및 검증용) 특정 객체의 정답 좌표를 반환한다."""
        return p.getBasePositionAndOrientation(self.bodies[name])[0]

    def hold_view(self):
        """GUI 모드에서 작업이 끝난 뒤에도 사용자가 닫을 때까지 뷰어 창을 유지한다."""
        if not self.gui:
            return
        print("\n[뷰어] 창을 마우스로 둘러볼 수 있습니다. 종료하려면 Ctrl-C 를 누르세요.")
        try:
            while p.isConnected():
                p.stepSimulation()
                time.sleep(1.0 / 240.0)
        except KeyboardInterrupt:
            pass
