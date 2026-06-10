import os
import requests
from dotenv import load_dotenv, set_key

# 실행 파일기준의 .env 파일 경로
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(SCRIPT_DIR, '.env')
load_dotenv(dotenv_path=ENV_PATH)

REST_API_KEY = os.getenv('KAKAO_REST_API_KEY')
CLIENT_SECRET = os.getenv('KAKAO_CLIENT_SECRET')
AUTHO_CODE = os.getenv('KAKAO_AUTHORIZAION_CODE')
# 카카오 디벨로퍼스에 등록한 정확히 동일한 Redirect URI
REDIRECT_URI = 'http://localhost:8080/oauth' 

def get_initial_tokens():
    """
    1. 최초로 Access Token과 Refresh Token을 발급받는 함수
    (발급받은 인가 코드를 auth_code에 넣어 1회만 실행합니다)
    """
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": REST_API_KEY,
        "redirect_uri": REDIRECT_URI,
        "code": AUTHO_CODE,
        "client_secret":  CLIENT_SECRET
    }
    
    response = requests.post(url, data=data)
    tokens = response.json()
    
    if "access_token" in tokens:
        set_key(ENV_PATH, "KAKAO_ACCESS_TOKEN", tokens["access_token"])
        set_key(ENV_PATH, "KAKAO_REFRESH_TOKEN", tokens["refresh_token"])
        print("최초 토큰 발급 및 .env 저장 완료!")
        print("발급된 Access Token:", tokens["access_token"][:15] + "...")
    else:
        print("토큰 발급 에러:", tokens)

def refresh_kakao_token():
    """
    2. 만료된 Access Token을 갱신하는 함수
    (Refresh Token 만료일이 30일 미만이면 Refresh Token도 함께 갱신됨)
    """
    refresh_token = os.getenv('KAKAO_REFRESH_TOKEN')
    
    if not refresh_token:
        print(".env 파일에 KAKAO_REFRESH_TOKEN이 없습니다. 최초 발급을 먼저 진행해주세요.")
        return

    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": REST_API_KEY,
        "refresh_token": refresh_token
    }
    
    response = requests.post(url, data=data)
    tokens = response.json()
    
    if "access_token" in tokens:
        # Access Token은 항상 새롭게 발급되므로 업데이트
        set_key(ENV_PATH, "KAKAO_ACCESS_TOKEN", tokens["access_token"])
        print("Access Token 갱신 완료!")
        
        # 카카오 정책: Refresh Token의 남은 기간이 1개월 미만일 때만 응답에 포함됨
        if "refresh_token" in tokens:
            set_key(ENV_PATH, "KAKAO_REFRESH_TOKEN", tokens["refresh_token"])
            print("Refresh Token의 만료일이 30일 미만이라 새 토큰으로 갱신 및 저장되었습니다!")
        else:
            print("기존 Refresh Token의 유효기간이 충분하여 기존 토큰을 유지합니다.")
    else:
        print("토큰 갱신 에러 (Refresh Token이 만료되었을 수 있습니다):", tokens)

if __name__ == "__main__":
    # =========================================================================
    # [사용 방법]
    # 1. 처음 사용할 때
    #    (한 번 발급받은 인가 코드는 재사용할 수 없으므로, 실행 후 다시 주석 처리하세요)
    # =========================================================================
    
    get_initial_tokens()
    
    # =========================================================================
    # 2. 이후 사용할 때: 아래 갱신 함수만 주기적으로(혹은 API 호출 전) 실행합니다.
    # =========================================================================
    
    # refresh_kakao_token()
    pass
