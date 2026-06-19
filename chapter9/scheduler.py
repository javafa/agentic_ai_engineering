from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from main import run        # main.py에 만든 run()
from common import log
 
def job():
    log.info("=== 정기 브리핑 작업 시작 ===")
    result = run(datetime.now().strftime("%Y-%m-%d"))
    log.info("=== 완료. 전송 상태=%s ===", result["delivery"])
 
if __name__ == "__main__":
    sched = BlockingScheduler(timezone="Asia/Seoul")
    # 월~금 07:00 (장 시작 전)
    sched.add_job(job, CronTrigger(day_of_week="mon-fri", hour=7, minute=0))
    log.info("스케줄러 시작 — 평일 07:00 KST")
    sched.start()
