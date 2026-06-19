import functools
import time

import logging, time, functools
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("briefing.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("briefing")

def with_retry(tries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """네트워크 호출에 지수 백오프 재시도를 적용하는 데코레이터.
    외부 API(거래소, 뉴스)는 일시적 오류가 잦기 때문에 한 번 실패했다고
    바로 포기하지 않고 간격을 늘려가며 다시 시도합니다."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            cur, last_err = delay, None
            for attempt in range(1, tries + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    last_err = e
                    log.warning("%s 실패(%d/%d): %s", fn.__name__, attempt, tries, e)
                    if attempt < tries:
                        time.sleep(cur)
                        cur *= backoff
            raise last_err
        return wrapper
    return deco
