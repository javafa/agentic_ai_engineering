import json
import requests
from common import with_retry

KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"

@with_retry(tries=2)
def send_slack(text: str, webhook: str) -> None:
    if not webhook:
        raise ValueError("SLACK_WEBHOOK_URL 미설정")
    # 슬랙도 길이 제한이 있어, 너무 길면 앞부분만 보냅니다.
    payload = {"text": text[:3500] + ("\n…(생략)" if len(text) > 3500 else "")}
    r = requests.post(webhook, json=payload, timeout=10)
    r.raise_for_status()

def _refresh_kakao_token(rest_api_key: str, client_secret: str, refresh_token: str) -> str:
    """refresh_token으로 새 access_token을 발급받습니다.
    access_token은 약 6시간이면 만료되므로, 매일 깨어나는 무인 에이전트는
    실행할 때마다 refresh_token으로 토큰을 새로 받는 것이 안전합니다."""
    data = {
        "grant_type": "refresh_token",
        "client_id": rest_api_key,
        "refresh_token": refresh_token,
        "client_secret": client_secret
    }
    r = requests.post(KAKAO_TOKEN_URL, data=data, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]

# @with_retry(tries=2) 필요하면 넣는다
def send_kakao(text: str, rest_api_key: str, client_secret: str, refresh_token: str) -> None:
    """카카오톡 '나에게 보내기'. 텍스트 템플릿은 최대 200자까지만 표시되므로
    한 줄 요약 같은 핵심만 담아 보냅니다(전체 본문은 슬랙으로 전송)."""
    if not (rest_api_key and refresh_token and client_secret):
        raise ValueError("KAKAO_REST_API_KEY 또는 KAKAO_REFRESH_TOKEN, client_secret 미설정")

    access_token = _refresh_kakao_token(rest_api_key, client_secret, refresh_token)
    template = {
        "object_type": "text",
        "text": text[:200],                       # 텍스트 템플릿 200자 제한
        "link": {"web_url": "https://m.stock.naver.com",
                 "mobile_web_url": "https://m.stock.naver.com"},
        "button_title": "시세 보기",
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    data = {"template_object": json.dumps(template, ensure_ascii=False)}
    r = requests.post(KAKAO_SEND_URL, headers=headers, data=data, timeout=10)
    r.raise_for_status()
    # 카카오는 성공 시 result_code 0을 돌려줍니다.
    if r.json().get("result_code") != 0:
        raise RuntimeError(f"카카오 전송 실패: {r.text}")
