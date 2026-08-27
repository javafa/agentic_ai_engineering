import os
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-5"
MAX_RETRIES = 3           # 코드 실행 에러에 대한 자기수정 한도 (계층 2)
MAX_REVIEW = 2            # 자기검토(원칙 위반, 품질) 재작성 한도 (계층 1, 4)
EXEC_TIMEOUT = 30         # 코드 1회 실행 제한 시간(초)
OUTPUT_DIR = "outputs"    # 차트 등 산출물 저장 폴더
MEMORY_PATH = "memory/experience.jsonl"   # 성공 사례 외부 메모리 (계층 1)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)

# 분석 원칙 — 에이전트가 스스로 출력을 검열할 때 따르는 원칙 (계층 4)
ANALYSIS_CONSTITUTION = [
    "데이터에 실제로 존재하는 값에만 근거하고, 없는 수치를 지어내지 않는다.",
    "표본 수(N)가 30 미만인 그룹의 통계는 신뢰하기 어렵다는 점을 함께 알린다.",
    "상관관계를 인과관계로 단정하지 않는다('관련 있음'과 '원인임'을 구분).",
    "개인을 식별하거나 추정하지 않고, 개인정보(PII)를 출력하지 않는다.",
    "투자, 의료, 법률에 대한 단정적 조언을 하지 않는다.",
]

# 분석 대상 데이터를 커널에 올리는 부트스트랩.
# 더미가 아니라 실제 공개 데이터(NYC 옐로, 그린 택시 운행 기록, 2026-04)를 DuckDB 테이블을 'trips'로 등록한다.
# 사내 데이터를 분석하려면 이 부분을 회사 DB 연결(예: duckdb 또는 SQLAlchemy)로 바꾸면 된다.
BOOTSTRAP_CODE = '''
%matplotlib inline
import duckdb, pandas as pd
import matplotlib.pyplot as plt
YM   = "2026-04"                    # 분석 대상 월(원하는 달로 바꾸면 그대로 동작)
BASE = "https://d37ci6vzurychx.cloudfront.net/trip-data"
ZONE = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
con = duckdb.connect()                 # 메모리 DB
con.sql("INSTALL httpfs; LOAD httpfs;")   # 원격 Parquet 읽기 확장
df = con.sql(f"""
WITH z AS (SELECT LocationID, Zone, Borough FROM read_csv('{ZONE}')),
t AS (
SELECT tpep_pickup_datetime AS pickup, tpep_dropoff_datetime AS dropoff,
       passenger_count, trip_distance, fare_amount, tip_amount, tolls_amount,
       total_amount, payment_type, PULocationID, DOLocationID, 'yellow' AS color
FROM read_parquet('{BASE}/yellow_tripdata_{YM}.parquet')
UNION ALL
SELECT lpep_pickup_datetime, lpep_dropoff_datetime,
       passenger_count, trip_distance, fare_amount, tip_amount, tolls_amount,
       total_amount, payment_type, PULocationID, DOLocationID, 'green'
FROM read_parquet('{BASE}/green_tripdata_{YM}.parquet'))
SELECT t.pickup, t.dropoff, t.passenger_count::INT AS passengers,
       t.trip_distance AS distance, t.fare_amount AS fare, t.tip_amount AS tip,
       t.tolls_amount AS tolls, t.total_amount AS total, t.color,
       CASE t.payment_type WHEN 1 THEN 'credit card' WHEN 2 THEN 'cash' END AS payment,
       pz.Zone AS pickup_zone, dz.Zone AS dropoff_zone,
       pz.Borough AS pickup_borough, dz.Borough AS dropoff_borough
FROM t
LEFT JOIN z pz ON t.PULocationID = pz.LocationID
LEFT JOIN z dz ON t.DOLocationID = dz.LocationID
WHERE t.fare_amount > 0 AND t.trip_distance > 0 AND t.payment_type IN (1, 2)
  AND date_trunc('month', t.pickup) = DATE '{YM}-01'
ORDER BY hash(t.pickup, t.PULocationID, t.DOLocationID, t.fare_amount, t.tip_amount)
LIMIT 6000
""").df()                              # 실제 NYC 옐로, 그린 택시 6,000건(결정적 표본)
con.register("trips", df)              # SQL에서 trips 테이블로 조회
'''

# LLM에게 알려줄 데이터 스키마(첫 시도 성공률을 높인다 — 계층 1 컨텍스트)
SCHEMA_HINT = """[데이터] DuckDB 테이블 'trips' (= pandas df), 2026년 04월 NYC 옐로, 그린 택시 6,000건
컬럼: pickup, dropoff (datetime), passengers(int), distance(mile), fare,
tip, tolls, total($), color(green/yellow), payment(credit card/cash),
pickup_zone, dropoff_zone, pickup_borough, dropoff_borough"""
