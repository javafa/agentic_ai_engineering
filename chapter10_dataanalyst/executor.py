import re
import os
import queue
import base64
from jupyter_client import KernelManager
from config import OUTPUT_DIR
 
ANSI = re.compile(r"\x1b\[[0-9;]*m")   # 트레이스백의 색상 코드 제거용

class KernelExecutor:
    """IPython 커널 하나를 계속 살려 둔다. 커널이 실행 중인 동안
    df, con(DuckDB 연결), 중간 변수가 유지되므로 멀티턴 분석이 가능하다."""
 
    def __init__(self, bootstrap: str = ""):
        self.km = KernelManager()
        self.km.start_kernel()
        self.kc = self.km.client()
        self.kc.start_channels()
        self.kc.wait_for_ready(timeout=60)
        if bootstrap:
            self.run(bootstrap)        # 데이터 로딩 등 초기화

    def run(self, code: str, timeout: int = 30) -> dict:
        msg_id = self.kc.execute(code)
        out = {"stdout": "", "result": "", "images": [], "error": None, "traceback": ""}
        while True:
            try:
                msg = self.kc.get_iopub_msg(timeout=timeout)
            except queue.Empty:
                out["error"] = "Timeout"
                out["traceback"] = f"{timeout}초 안에 끝나지 않았습니다."
                break
            if msg["parent_header"].get("msg_id") != msg_id:
                continue              # 내가 보낸 요청의 메시지만 처리
            mtype, content = msg["msg_type"], msg["content"]
            if mtype == "stream":                       # print() 출력
                out["stdout"] += content["text"]
            elif mtype in ("execute_result", "display_data"):
                data = content["data"]
                if "text/plain" in data:
                    out["result"] += data["text/plain"]
                if "image/png" in data:                 # 차트 > base64 PNG
                    out["images"].append(data["image/png"])
            elif mtype == "error":                      # 예외 발생
                out["error"] = f"{content['ename']}: {content['evalue']}"
                out["traceback"] = ANSI.sub("", "\n".join(content["traceback"]))
            elif mtype == "status" and content["execution_state"] == "idle":
                break                 # 이 요청의 모든 출력이 끝났음
        return out

    def save_images(self, images: list, prefix: str) -> list:
        paths = []
        for i, b64 in enumerate(images):
            path = os.path.join(OUTPUT_DIR, f"{prefix}_{i}.png")
            with open(path, "wb") as f:
                f.write(base64.b64decode(b64))
            paths.append(path)
        return paths

    def shutdown(self):
        self.kc.stop_channels()
        self.km.shutdown_kernel(now=True)
