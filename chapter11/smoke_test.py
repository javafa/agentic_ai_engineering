import pybullet as p
import pybullet_data
 
cid = p.connect(p.DIRECT)                       # 화면 없는 서버: DIRECT
p.setAdditionalSearchPath(pybullet_data.getDataPath())  # 기본 에셋 경로
p.setGravity(0, 0, -9.8)
p.loadURDF("plane.urdf")                        # 기본 제공 바닥
 
view = p.computeViewMatrix([0, -1, 1], [0, 0, 0], [0, 0, 1])
proj = p.computeProjectionMatrixFOV(60, 4 / 3, 0.1, 8.0)
w, h, rgba, depth, seg = p.getCameraImage(
    320, 240, view, proj, renderer=p.ER_TINY_RENDERER)
print("카메라 OK:", w, "x", h, "픽셀")          # (320, 240) 이 찍히면 성공
p.disconnect()
